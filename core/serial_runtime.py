"""Native VLNVerse hooks for serial, monocular recovery. No GT routing decisions."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import time
import urllib.request

import numpy as np
from PIL import Image

from core.oracle_crossing import plain
from core.oracle_checkpoint_pair import CheckpointPair
from core.serial_pipeline import SerialAPI, SerialDecisions, save, sha
from core.seeding import episode_seed
from core.serial_batch import batch_progress, record_episode_failure


def action_id(action, robot):
    entry=action[0][robot]
    if 'stop' in entry: return 0
    discrete=entry.get('move_by_discrete')
    return int(discrete[0]) if discrete else None


def has_recovery_cycle(events, require_original_motion=False):
    """A pose restore or immediate local STOP alone is not a physical round trip."""
    phase=0
    for event in events:
        kind=event['kind']
        if kind=='rollback': phase=1
        elif kind=='correction_started' and phase==1: phase=2
        elif kind=='action' and event['controller']=='local' and phase in (2,3):
            if 'move_by_discrete' in event['action']: phase=3
        elif kind=='handoff': phase=4 if phase==3 else 0
        elif kind=='action' and event['controller']=='original' and phase==4:
            if 'move_by_discrete' in event['action'] or ('stop' in event['action'] and not require_original_motion): return True
    return False


class SerialHook:
    api_type = SerialAPI
    decisions_type = SerialDecisions
    correction_source = 'r2r_v007'
    require_original_motion = False

    def __init__(self, evaluator):
        self.e=evaluator
        self.output=Path(os.environ['VLN_SERIAL_OUTPUT'])
        self.config=json.loads((self.output/'config.json').read_text())
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.base=evaluator.agent.base_url
        self.reset=evaluator.reset_seeded_agent; evaluator.reset_seeded_agent=self.after_reset
        self.action=evaluator.get_action; evaluator.get_action=self.before_action
        self.step=evaluator.env_step; evaluator.env_step=self.step_with_terminal
        self.terminate=evaluator.terminate_ops; evaluator.terminate_ops=self.finish_before_reset
        self.active=False; self.saved=None; self.terminal=None; self.engine=None; self.api=None
        self.skipping=False; self.skip_observation=None
        self.native_close=evaluator.env.close
        evaluator.env.close=self.retain_close

    def request(self, path, body=None):
        request=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,
                                       headers={'Content-Type':'application/json'})
        with self.opener.open(request,timeout=180) as r: return json.load(r)

    def policy(self): return self.request('/oracle/state')

    def rpc(self, operation, key):
        return self.request('/branch/checkpoint',dict(operation=operation,key=key))

    def task(self):
        tasks=list(self.e.env.env.runner.current_tasks.values())
        if len(tasks)!=1: raise RuntimeError('Serial pipeline requires one native environment')
        return tasks[0]

    def event(self, kind, **data):
        row=dict(kind=kind,time=time.time(),episode_id=self.eid,leg=self.leg,action_count=self.action_count,**plain(data))
        with (self.folder/'events.jsonl').open('a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
        save(self.output/'live.json',row)
        print('SERIAL_EVENT '+json.dumps({k:v for k,v in row.items() if k not in ('answer','filtered','node','selection')},ensure_ascii=False),flush=True)

    def after_reset(self, infos, indices):
        if not indices: return self.reset(infos,indices)
        if indices!=[0] or len(infos)!=1: raise RuntimeError('Unexpected environment layout')
        self.close_decisions()
        self.eid=infos[0].data['episode_id']
        self.folder=self.output/'episodes'/self.eid/('attempt_%d'%time.time_ns()); self.folder.mkdir(parents=True)
        self.leg=0; self.sequence=0; self.action_count=0; self.recoveries=0; self.handoffs=0
        self.local=False; self.pending=None; self.saved=None; self.active=True; self.terminal=None
        self.skipping=False; self.skip_observation=None
        self.instruction=infos[0].data['instruction']['instruction_text']
        self.reset(infos,indices)
        self.api=self.api_type(self.folder,self.config)
        self.engine=self.decisions_type(self.api,self.instruction,self.event)
        self.initial_joints=plain(self.task().robot.articulation.get_joint_positions())
        state=self.policy()
        if state['episode_id']!=self.eid or state['step_id']!=0 or state['pending_count']:
            raise RuntimeError('Native task reset did not clear policy state')
        self.event('episode_started',policy=state,instruction=self.instruction)

    def camera_metadata(self):
        return {}

    def frame(self, ob, local=False):
        if ob.get('rgb') is None: raise RuntimeError('Missing fresh RGB')
        index=len(self.engine.frames) if not local else self.local_steps
        path=self.folder/'frames'/('%06d.png'%self.sequence); path.parent.mkdir(exist_ok=True)
        Image.fromarray(np.asarray(ob['rgb'],dtype=np.uint8)).save(path)
        pos,quat=self.task().robot.articulation.get_world_pose()
        frame=dict(index=index,path=str(path),sha256=sha(path),world_position=plain(pos),world_orientation=plain(quat),
                   position=plain(ob.get('globalgps')),rotation=plain(ob.get('globalrotation')),sequence=self.sequence,
                   **self.camera_metadata())
        self.sequence+=1
        with (self.folder/'observations.jsonl').open('a') as f:
            f.write(json.dumps(dict(frame,leg=self.leg,local=local,physics_ticks=self.task().step_count))+'\n')
        return frame

    def new_leg(self, progress=None):
        self.engine.close(); self.leg+=1
        self.engine=self.decisions_type(self.api,self.instruction,self.event,prior_progress=progress)
        self.pending=None

    def restore_main(self, reason):
        if self.saved is None: return
        restored=self.rpc('restore',self.saved['key'])
        if restored['content_sha256']!=self.saved['proof']['content_sha256']:
            raise RuntimeError('Original task policy restoration failed')
        save(self.saved['directory']/'memory_restore.json',dict(reason=reason,restored=restored,saved=self.saved['proof'],equal=True))
        self.saved=None

    def handoff(self, reason):
        self.restore_main(reason)
        self.local=False; self.handoffs+=1
        self.event('handoff',reason=reason,local_steps=self.local_steps,local_stop_is_task_stop=False)
        self.new_leg(self.recovery_progress)

    def select_route(self, pending):
        return self.api.choose(pending['target'], self.engine.frames, self.instruction)

    def observe_main(self, frame):
        if self.pending:
            self.engine.frames.append(frame)
        else:
            self.pending = self.engine.observe(frame)

    def decline_takeover(self, pending):
        self.new_leg(pending['progress'])

    def after_handoff(self, ob):
        pass

    def review_main_stop(self):
        return None

    def correction_instruction(self, selection, fresh):
        return self.api.correction(selection, fresh)

    def recover(self, ob):
        pending=self.pending; target=pending['target']
        if target is None: raise RuntimeError('Deviation has no trusted checkpoint')
        # Do not discard the original model's already generated action queue.
        if self.policy()['pending_count']: return ob,False
        if len(self.engine.frames)-1>pending['detected_at']:
            gate=dict(id='G%04d'%self.action_count,index=len(self.engine.frames)-1,emittedAt=len(self.engine.frames)-1)
            answer=self.api.deviation(target,gate,self.engine.frames,self.instruction,pending['progress'])
            self.event('deviation_gate',answer=answer)
            if not answer or answer['verdict']!='deviated':
                self.decline_takeover(pending); return ob,False
        selection=self.select_route(pending)
        self.event('route_selected' if selection['status']=='selected' else 'route_unresolved',selection=selection)
        if selection['status']!='selected':
            self.decline_takeover(pending); return ob,False
        source=self.engine.frames[target['index']]
        directory=self.folder/('recovery_%03d'%(self.recoveries+1)); directory.mkdir()
        save(directory/'decision.json',dict(deviation=pending,selection=selection,checkpoint=source))
        restored,ended=self.rollback(ob,target,source,directory,'save')
        if ended: return restored,True
        return self.start_correction(restored,pending,selection,directory),False

    def rollback(self, ob, target, source, directory, operation):
        key='serial_'+hashlib.sha256(str(directory).encode()).hexdigest()[:24]
        proof=self.rpc(operation,key)
        self.saved=dict(key=key,proof=proof,directory=directory)
        save(directory/'memory_save.json',proof)
        # Reuse the established physical stance/restoration routine, with the
        # exact live saved root pose. No reference trajectory is consulted.
        helper=object.__new__(CheckpointPair)
        helper.active=dict(episode_id=self.eid,initial_height=float(source['world_position'][2]-self.task().env_offset[2]),standing_joints=self.initial_joints)
        helper.saved_root_pose=(np.array(source['world_position']),np.array(source['world_orientation']))
        w,x,y,z=source['world_orientation']; yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
        position=(np.array(source['world_position'])-np.array(self.task().env_offset))[:2].tolist()
        restored,ended=helper.restore_pose(self.e,ob,dict(target_xy=position,target_yaw_rad=yaw),directory)
        self.recoveries+=1
        save(directory/'pose_restore.json',dict(saved=source,actual_position=plain(restored['globalgps']),
                                                actual_rotation=plain(restored['globalrotation']),ended=ended,
                                                physical_budget_restored=False,physics_ticks=self.task().step_count))
        self.event('rollback',target=target['id'],frame=target['index'],ended=ended)
        if ended:
            self.restore_main('terminal_during_restore')
        return restored,ended

    def start_correction(self, restored, pending, selection, directory):
        self.local_steps=0
        fresh=self.frame(restored,local=True)
        self.local_instruction=self.correction_instruction(selection,fresh)
        save(directory/'instruction.json',dict(instruction=self.local_instruction,source=self.correction_source,
                                                restored_observation=fresh['path'],rgb=fresh['path']))
        self.e.agent.reset([0],episode_ids=[self.eid],episode_seeds=[episode_seed(self.config['seed'],self.eid)])
        policy=self.policy()
        if policy['step_id']!=0 or policy['pending_count'] or policy['history_images']:
            raise RuntimeError('Local correction policy was not cleared')
        self.local=True; self.pending=None; self.recovery_progress=pending['progress']
        self.event('correction_started',instruction=self.local_instruction,policy=policy)
        return restored

    def before_action(self, observations, action):
        try:
            return self._before_action(observations,action)
        except Exception as error:
            if not self.active: raise
            self.defer_episode(error,'policy_or_pipeline')
            self.skip_observation=observations[0]
            # No STOP or synthetic navigation result is sent to the simulator.
            return observations,action

    def _before_action(self, observations, action):
        from vlnverse.evaluator.vln_pe_evaluator import runner_status_code
        if not self.active or self.e.runner_status[0]!=runner_status_code.NORMAL:
            return self.action(observations,action)
        ob=observations[0]
        if not self.local:
            frame=self.frame(ob)
            self.observe_main(frame)
            if self.pending:
                ob,ended=self.recover(ob)
                if ended:
                    self.terminal=ob; return [ob],action
        else:
            self.frame(ob,local=True)
        if self.local and self.local_steps>=self.config['local_action_budget'] and not self.policy()['pending_count']:
            self.handoff('local_action_budget')
            self.after_handoff(ob)
        while True:
            supplied=dict(ob)
            supplied['instruction']=self.local_instruction if self.local else self.instruction
            result,actions=self.action([supplied],action)
            actual=action_id(actions,self.e.robot_name)
            if actual!=0:
                break
            if self.local:
                self.event('local_stop',executed_in_simulator=False)
                self.handoff('local_stop')
                self.after_handoff(ob)
                continue
            alarm=self.review_main_stop()
            if alarm is None:
                break
            self.pending=alarm
            ob,ended=self.recover(ob)
            if ended:
                self.terminal=ob; return [ob],action
        if not self.local and self.engine.frames:
            self.engine.frames[-1]['action_after']={0:'STOP',1:'FORWARD',2:'LEFT',3:'RIGHT',None:'WAIT'}[actual]
        self.event('action',action=plain(actions[0][self.e.robot_name]),controller='local' if self.local else 'original')
        self.action_count+=1
        if self.local: self.local_steps+=1
        return result,actions

    def step_with_terminal(self, actions):
        if self.skip_observation is not None:
            ob=self.skip_observation; self.skip_observation=None
            return [ob],[True]
        if self.terminal is not None:
            ob=self.terminal; self.terminal=None; return [ob],[True]
        return self.step(actions)

    def finish_before_reset(self, observations, infos, terminated):
        if self.active and terminated[0]:
            self.restore_main('task_terminal')
            metrics=plain(next(iter(observations[0]['metrics'].values()))[0])
            self.event('episode_finished',metrics=metrics,recoveries=self.recoveries,handoffs=self.handoffs)
            events=[json.loads(line) for line in (self.folder/'events.jsonl').read_text().splitlines()]
            save(self.folder/'result.json',dict(episode_id=self.eid,metrics=metrics,recoveries=self.recoveries,
                                               handoffs=self.handoffs,actions=self.action_count,phase='complete',
                                               full_chain_observed=has_recovery_cycle(events,self.require_original_motion)))
            self.active=False; self.close_decisions()
        return self.terminate(observations,infos,terminated)

    def consume_failed_episode(self, info):
        if not self.skipping: return False
        if info.data['episode_id']!=self.eid: raise RuntimeError('Failure/reset episode mismatch')
        self.skipping=False
        return True

    def defer_episode(self, error, stage):
        request_dirs=sorted((self.folder/'requests').glob('*'))
        last_request=str(request_dirs[-1]) if request_dirs else None
        row=record_episode_failure(self.output,self.eid,self.folder,repr(error),stage,
                                   action_count=self.action_count,last_request=last_request)
        self.event('episode_skipped',failure=row)
        self.active=False; self.skipping=True
        try:
            self.restore_main('episode_skipped')
        finally:
            self.close_decisions()

    def close_decisions(self):
        if self.engine is not None: self.engine.close(); self.engine=None
        if self.api is not None: self.api.close(); self.api=None

    def failed(self, error):
        # Record before Isaac shutdown, which can suppress exception exit codes.
        message=repr(error)
        for key in ('JEV_API_KEY','DEEPSEEK_API_KEY'):
            if os.environ.get(key): message=message.replace(os.environ[key],'[REDACTED]')
        save(self.output/'runtime_error.json',dict(error=message,time=time.time(),phase='restoring_policy'))
        cleanup_error=None
        try:
            if self.active: self.defer_episode(error,'simulator_or_reset')
            else: self.restore_main('runtime_failure')
        except Exception as e: cleanup_error=type(e).__name__
        finally:
            self.close_decisions()
            save(self.output/'runtime_failure.json',dict(error=message,time=time.time(),cleanup_error=cleanup_error))
        print('SERIAL_FAILED '+message,flush=True)

    def retain_close(self):
        if self.active: return self.native_close()
        progress=batch_progress(self.output)
        if progress['pending']: return self.native_close()
        self.close_decisions()
        save(self.output/'simulator_retained.json',dict(pid=os.getpid(),time=time.time(),**progress))
        print('SERIAL_SIMULATOR_RETAINED',flush=True)
        while not (self.output/'simulator_retained.release').exists(): time.sleep(1)
        return self.native_close()


def install(evaluator):
    if not hasattr(evaluator,'_serial_hook'):
        config = json.loads((Path(os.environ['VLN_SERIAL_OUTPUT'])/'config.json').read_text())
        hook = SerialHook
        if config['deviation'] == 'v006':
            from core.serial_v006_runtime import V006Hook
            hook = V006Hook
        evaluator._serial_hook=hook(evaluator)
    return evaluator._serial_hook
