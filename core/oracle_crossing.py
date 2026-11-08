"""Live assistant-controlled pose correction, with unchanged StreamVLN memory.

Reference information is used only by this simulator-side Oracle, never by policy.
Only explicit response files can authorize a teleport. Waiting freezes physics.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import time
import urllib.request

import numpy as np


def write(path, value):
    path=Path(path)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(path)


def plain(x):
    if hasattr(x,'tolist'):return x.tolist()
    if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [plain(v) for v in x]
    return x


def reference_distance(position, reference):
    """Shortest horizontal distance to the full reference polyline, in meters."""
    point=np.asarray(position,dtype=float)[:2]
    route=np.asarray(reference,dtype=float)[:,:2]
    if len(route)==0:raise ValueError('Reference route is empty')
    if len(route)==1:return float(np.linalg.norm(point-route[0]))
    starts=route[:-1];segments=np.diff(route,axis=0)
    squared=np.sum(segments*segments,axis=1)
    fraction=np.divide(np.sum((point-starts)*segments,axis=1),squared,
                       out=np.zeros_like(squared),where=squared>1e-12)
    closest=starts+np.clip(fraction,0,1)[:,None]*segments
    return float(np.min(np.linalg.norm(closest-point,axis=1)))


def validate_response(response, request):
    if response.get('request_id') != request['request_id']:
        raise ValueError('Oracle response/request mismatch')
    if response.get('decision') not in ('continue','teleport','abort'):
        raise ValueError('Invalid Oracle decision')
    if not isinstance(response.get('reason'),str) or len(response['reason'])<8:
        raise ValueError('Oracle decision must contain an explicit evidence-based reason')
    if response['decision']=='continue' and not 1<=response.get('skip_actions',1)<=8:
        raise ValueError('At most eight navigation actions between Oracle reviews')
    if response['decision']=='teleport' and 'targets' in request:
        if response.get('target_id') not in {t['id'] for t in request['targets']}:
            raise ValueError('Select an explicit frozen crossing target')
    if response['decision']=='teleport' and request.get('deviation_threshold_m') is not None:
        if request['reference_distance_m']<request['deviation_threshold_m']:
            raise ValueError('Deviation threshold has not been reached')


class OracleCrossing:
    def __init__(self, manifest, root, agent_url):
        m=json.loads(Path(manifest).read_text())
        self.cases={c['episode_id']:c for c in m['cases']}
        self.multi=m.get('multi_intervention',False)
        self.threshold=m.get('deviation_threshold_m')
        if self.threshold is not None:assert float(self.threshold)>0
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.agent_url=agent_url
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.active=None

    @classmethod
    def from_environment(cls, evaluator):
        manifest=os.environ.get('VLN_ORACLE_MANIFEST')
        return cls(manifest,os.environ['VLN_ORACLE_RECORDS'],evaluator.agent.base_url) if manifest else None

    def policy(self,deep=False):
        with self.opener.open(self.agent_url+'/oracle/state'+('?deep=1' if deep else ''),timeout=120) as r:
            return json.load(r)

    def task(self, evaluator):
        tasks=list(evaluator.env.env.runner.current_tasks.values())
        assert len(tasks)==1
        return tasks[0]

    def start(self, eid, evaluator):
        if self.active:
            assert self.active['episode_id']==eid
            return
        task=self.task(evaluator)
        path=self.root/eid/f'attempt_{time.time_ns()}'
        path.mkdir(parents=True,exist_ok=False)
        (path/'frames').mkdir()
        pos,rot=task.robot.articulation.get_world_pose()
        self.active=dict(episode_id=eid,directory=path,index=0,teleported=False,next_review=0,near_seen=False,
                         initial_height=float(pos[2]-task.env_offset[2]),standing_joints=plain(task.robot.articulation.get_joint_positions()),
                         observations=[],intervention=None,interventions=[])
        write(path/'case.json',dict(episode_id=eid,status='running',started_at=time.time(),case=self.cases[eid]))

    def before(self,evaluator,obs,infos):
        from PIL import Image
        info=infos[0]
        if info is None:return obs,None
        eid=info.data['episode_id'];self.start(eid,evaluator)
        s=self.active;c=self.cases[eid];ob=obs[0]
        i=s['index'];position=plain(ob['globalgps']);rotation=plain(ob['globalrotation'])
        rgb=ob.get('rgb')
        if rgb is not None:
            Image.fromarray(np.asarray(rgb,dtype=np.uint8)).save(s['directory']/'frames'/f'{i:04d}.jpg',quality=90)
        deviation=reference_distance(position,c['reference_path']) if self.threshold is not None else None
        record=dict(action_index=i,position=position,rotation=rotation,frame=f'frames/{i:04d}.jpg',teleported=s['teleported'],intervention_count=len(s['interventions']),reference_distance_m=deviation)
        s['observations'].append(record)
        with (s['directory']/'observations.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
        if (s['teleported'] and not self.multi) or i<s['next_review']:return obs,None
        if self.threshold is not None and deviation<self.threshold:return obs,None
        distance=math.dist(position[:2],c['crossing']['position'])
        if distance<=2.5:s['near_seen']=True
        if self.threshold is None and not s['near_seen']:return obs,None
        policy=self.policy()
        assert policy['episode_id']==eid and policy['step_id']==i
        if policy['pending_count']!=0:return obs,None
        request_id=f'{eid}_{i:04d}_{time.time_ns()}'
        path=s['directory']/request_id;path.mkdir()
        if rgb is None:raise RuntimeError('No fresh RGB for Oracle inspection')
        Image.fromarray(np.asarray(rgb,dtype=np.uint8)).save(path/'before.png')
        request=dict(request_id=request_id,episode_id=eid,action_index=i,created_at=time.time(),
                     position=position,rotation=rotation,crossing_id=c['crossing_id'],
                     crossing_distance_m=distance,target_xy=c['target_xy'],target_yaw_rad=c['target_yaw_rad'],
                     instruction=c['instruction'],expected=c['review']['expected'],original_error=c['review']['actual'],
                     history=s['observations'][-12:],policy=policy,case_directory=str(s['directory']))
        if self.multi:
            request.update(targets=c['targets'],intervention_count=len(s['interventions']),
                           previous_interventions=s['interventions'])
        request.update(deviation_threshold_m=self.threshold,reference_distance_m=deviation)
        write(path/'request.json',request)
        write(self.root/'pending.json',dict(status='waiting',request=str(path/'request.json'),episode_id=eid,action_index=i))
        print('ORACLE_WAIT '+str(path/'request.json'),flush=True)
        while not (path/'response.json').exists():
            time.sleep(.25)
        response=json.loads((path/'response.json').read_text());validate_response(response,request)
        write(self.root/'pending.json',dict(status='responded',request=str(path/'request.json'),decision=response['decision']))
        if response['decision']=='abort':raise RuntimeError('Oracle aborted: '+response['reason'])
        if response['decision']=='continue':
            s['next_review']=i+response.get('skip_actions',1)
            return obs,None
        before=self.policy(deep=True)
        assert before['pending_count']==0 and before['step_id']==i
        target=next(t for t in c['targets'] if t['id']==response['target_id']) if self.multi else c
        result,terminal=self.teleport(evaluator,ob,target,path)
        after=self.policy(deep=True)
        assert before['sha256']==after['sha256'],'Navigation memory changed during simulator-side intervention'
        write(path/'memory_proof.json',dict(before=before,after=after,equal=True))
        s['teleported']=True
        intervention=dict(request_id=request_id,action_index=i,response=response,
                          before_position=position,before_rotation=rotation,
                          after_position=plain(result['globalgps']),after_rotation=plain(result['globalrotation']),
                          number=len(s['interventions'])+1,target_id=target.get('id',c['crossing_id']),
                          target_xy=target['target_xy'],target_yaw_rad=target['target_yaw_rad'],
                          translation_m=math.dist(position[:2],plain(result['globalgps'])[:2]),
                          target_crossing_distance_m=target['target_crossing_distance_m'],memory_unchanged=True,
                          stable=not terminal,assisted=True,physics_settle_ticks=50,request_directory=str(path))
        intervention.update(deviation_threshold_m=self.threshold,trigger_reference_distance_m=deviation)
        s['interventions'].append(intervention)
        if s['intervention'] is None:
            s['intervention']=intervention
            write(s['directory']/'intervention.json',intervention)
        write(path/'intervention.json',intervention)
        write(s['directory']/'interventions.json',s['interventions'])
        s['next_review']=i+4
        if result.get('rgb') is not None:
            Image.fromarray(np.asarray(result['rgb'],dtype=np.uint8)).save(path/'after.png')
            Image.fromarray(np.asarray(result['rgb'],dtype=np.uint8)).save(s['directory']/'frames'/f'{i:04d}_after.jpg',quality=90)
        print('ORACLE_TELEPORTED '+json.dumps(intervention),flush=True)
        return [result],([True] if terminal else None)

    def teleport(self,evaluator,ob,case,path):
        """Physical stance maintenance is separate from navigation policy memory."""
        task=self.task(evaluator);robot=task.robot;art=robot.articulation._articulation
        s=self.active
        assert task.data['episode_id']==s['episode_id'] and not task.is_done()
        position=np.array([*case['target_xy'],s['initial_height']],dtype=float)+np.asarray(task.env_offset)
        # Isaac's root articulation quaternion uses w,x,y,z.
        yaw=case['target_yaw_rad'];quat=np.array([math.cos(yaw/2),0.,0.,math.sin(yaw/2)])
        art.set_world_pose(position=position,orientation=quat)
        art.set_world_velocity(np.zeros(6))
        art.set_joint_positions(np.asarray(s['standing_joints']))
        art.set_joint_velocities(np.zeros(len(s['standing_joints'])))
        discrete=robot.controllers['move_by_discrete']
        discrete.current_action=None;discrete.current_steps=0
        # Standing and discrete walking can hold separate low-level controllers.
        # Reset their local motion/terrain buffers, never the navigation service.
        pending=list(robot.controllers.values());seen=set()
        while pending:
            loco=pending.pop()
            if id(loco) in seen:continue
            seen.add(id(loco));pending.extend(getattr(loco,'sub_controllers',None) or [])
            if not hasattr(loco,'_old_policy_obs'):continue
            loco._apply_times_left=0
            loco._old_joint_positions[:]=0
            loco._old_policy_obs[:]=0
            loco.update_height_samples_trigger=0
            loco.dynamic_height_samples=type(loco.dynamic_height_samples)()
        robot.current_action=None
        task.warm_up_step=50
        # Stand for one physical control interval; task budget/metrics continue.
        # No navigation request is sent during these 50 ticks.
        result=None;ended=False
        for _ in range(50):
            # Native warm-up excludes standing ticks from the task budget.
            # This is an intervention inside a live episode: count those ticks.
            if task.warm_up_step>1:
                task.step_count+=1
            out,_,term,_,_=evaluator.env.step([{evaluator.robot_name:{'stand_still':[]}}])
            result=out[0][evaluator.robot_name]
            if term[0]:ended=True;break
        assert result is not None
        error=math.dist(plain(result['globalgps'])[:2],case['target_xy'])
        if error>.35 and not ended:raise RuntimeError(f'Pose correction drift exceeded 0.35m: {error}')
        w,x,y,z=plain(result['globalrotation'])
        actual_yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
        yaw_error=abs(math.atan2(math.sin(actual_yaw-yaw),math.cos(actual_yaw-yaw)))
        if not ended and yaw_error>math.radians(15):
            raise RuntimeError(f'Pose correction yaw drift exceeded 15 degrees: {math.degrees(yaw_error)}')
        if not ended and ('rgb' not in result or not result['finish_action']):
            raise RuntimeError('Pose correction did not return a fresh complete observation')
        return result,ended

    def action(self,act):
        if not self.active:return
        s=self.active
        with (s['directory']/'actions.jsonl').open('a') as f:
            f.write(json.dumps(dict(action_index=s['index'],action=plain(act)))+'\n')
        s['index']+=1

    def finish(self,eid,ob,metrics):
        s=self.active
        if s is None:
            # A warm-up failure can occur before the first normal action.
            path=self.root/eid/f'attempt_{time.time_ns()}';path.mkdir(parents=True)
            result=dict(episode_id=eid,status='complete',intervention=None,interventions=[],actions=0,warmup_failure=True,metrics=plain(metrics))
        else:
            assert s['episode_id']==eid
            path=s['directory'];result=dict(episode_id=eid,status='complete',intervention=s['intervention'],interventions=s['interventions'],actions=s['index'],metrics=plain(metrics))
        if self.threshold is not None:
            positions=[r['position'] for r in s['observations']] if s else []
            if isinstance(ob,dict) and ob.get('globalgps') is not None:positions.append(plain(ob['globalgps']))
            maximum=max((reference_distance(p,self.cases[eid]['reference_path']) for p in positions),default=None)
            result.update(deviation_threshold_m=self.threshold,max_reference_distance_m=maximum,
                          threshold_reached=maximum is not None and maximum>=self.threshold)
        write(path/'result.json',result)
        write(self.root/'pending.json',dict(status='episode_complete',episode_id=eid))
        self.active=None
