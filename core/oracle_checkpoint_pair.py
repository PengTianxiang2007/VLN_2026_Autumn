"""Paired real checkpoint return; Oracle controls discrete actions, never target poses.

Canonical stabilization is shared across arms; no claim of bitwise PhysX rollback.
The policy is frozen during external actions and resumes with its pre-checkpoint memory.
"""
import copy
import json
import math
import os
from pathlib import Path
import pickle
import random
import time
import numpy as np
from core.oracle_branching import BranchOracle, accounting, restore_accounting, digest
from core.oracle_crossing import plain, write

ARMS=('streamvln','oracle_actions')

def validate(response, request):
    if response.get('request_id')!=request['request_id']:raise ValueError('Wrong request')
    if len(response.get('reason',''))<12:raise ValueError('Visual evidence required')
    decision=response.get('decision')
    allowed={'continue','checkpoint','error','abort'} if request['mode']=='trunk' else {'continue','verdict','abort'}
    if request['mode']=='oracle_actions':allowed={'action','handoff','abort'}
    if decision not in allowed:raise ValueError('Decision forbidden for this arm')
    if decision=='action' and (type(response.get('action')) is not int or response['action'] not in (1,2,3)):
        raise ValueError('Oracle only executes forward/left/right')
    if decision in ('verdict','handoff') and response.get('choice') not in ('correct','wrong','uncertain'):
        raise ValueError('Explicit local choice assessment required')
    return decision

class CheckpointPair(BranchOracle):
    def begin(self,e,eid):
        super().begin(e,eid)
        self.checkpoint_path=None;self.error=None;self.local_choice=None;self.handed_back=False
        self.external_actions=0

    def save_checkpoint(self,e,ob,response):
        if self.checkpoint_path:raise ValueError('One preregistered checkpoint per case')
        self.event={'target_id':'ACTUAL_SAVED_POSE','reason':response['reason']}
        self.capture(e,ob,'checkpoint',response)
        self.checkpoint_path=self.snapshots['checkpoint'];self.event=None

    def restore(self,e,arm):
        import torch
        with self.checkpoint_path.open('rb') as f:state=pickle.load(f)
        self.mode=arm;self.active=copy.deepcopy(state['active']);self.active['directory']=self.case_root/arm
        (self.active['directory']/'frames').mkdir(parents=True,exist_ok=False)
        with (self.active['directory']/'observations.jsonl').open('w') as f:
            for row in self.active['observations']:f.write(json.dumps(row)+'\n')
        task=self.task(e);runner=e.env.env.runner
        restore_accounting(task,state['accounting'])
        for k,v in state['runner'].items():setattr(runner,k,copy.deepcopy(v))
        proof=self.rpc('restore',state['key'])
        random.setstate(state['rng'][0]);np.random.set_state(state['rng'][1])
        torch.set_rng_state(state['rng'][2]);torch.cuda.set_rng_state_all(state['rng'][3])
        self.last_review=-1;self.local_choice=None;self.handed_back=False;self.external_actions=0
        before=self.policy(deep=True)
        # Reuse the verified stance routine, but intercept its requested target:
        # the only permitted pose is the actual root pose saved before the error.
        pos,quat=state['pose'];w,x,y,z=quat
        yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
        target={'target_xy':(np.asarray(pos)-np.asarray(task.env_offset))[:2].tolist(),'target_yaw_rad':yaw}
        self.active['initial_height']=float(pos[2]-task.env_offset[2])
        self.saved_root_pose=(np.asarray(pos),np.asarray(quat))
        ob,ended=self.restore_pose(e,state['ob'],target,self.active['directory'])
        after=self.policy(deep=True)
        if before['sha256']!=after['sha256']:raise RuntimeError('Restore changed model memory')
        write(self.active['directory']/'restore_proof.json',dict(policy=proof,source=str(self.checkpoint_path),
            saved_world_pose=state['pose'],actual_position=plain(ob['globalgps']),actual_rotation=plain(ob['globalrotation']),
            accounting_before_sha256=digest(state['accounting']),physics_ticks_after=task.step_count,
            memory_unchanged=True,scope='actual checkpoint root pose plus common 50 tick stance stabilization'))
        return ob,ended

    def restore_pose(self,e,ob,target,path):
        # A narrow proxy overrides only the pose setter of the existing stance routine.
        # No target coordinates from the map can reach the articulation.
        art=self.task(e).robot.articulation._articulation
        original=art.set_world_pose
        position,orientation=self.saved_root_pose
        calls=[]
        def exact_pose(*args,**kwargs):
            calls.append(True)
            return original(position=position.copy(),orientation=orientation.copy())
        art.set_world_pose=exact_pose
        try:result=super().teleport(e,ob,target,path)
        finally:art.set_world_pose=original
        if len(calls)!=1:raise RuntimeError('Unexpected pose setter count')
        return result

    def review(self,e,ob):
        s=self.active;i=s['index']
        if self.mode=='oracle_actions' and self.handed_back:return {'decision':'continue'}
        if self.mode=='streamvln' and self.local_choice is not None:return {'decision':'continue'}
        policy=self.policy()
        if policy['pending_count'] or i==self.last_review:return {'decision':'continue'}
        self.last_review=i
        p=s['directory']/f'review_{i:04d}';p.mkdir(exist_ok=False)
        from PIL import Image
        Image.fromarray(ob['rgb']).save(p/'before.jpg',quality=90)
        c=self.cases[s['episode_id']]
        req=dict(request_id=f'{s["episode_id"]}_{self.mode}_{i}',mode=self.mode,episode_id=s['episode_id'],
            action_index=i,position=plain(ob['globalgps']),rotation=plain(ob['globalrotation']),
            instruction=c['instruction'],reference_path=c['reference_path'],crossing=c['crossing'],
            expected=c['review']['expected'],original_error=c['review']['actual'],
            history=s['observations'][-8:],checkpoint=str(self.checkpoint_path) if self.checkpoint_path else None,
            error=self.error,policy=policy,physics_ticks=self.task(e).step_count,image=str(p/'before.jpg'))
        write(p/'request.json',req);write(self.root/'pending.json',{'status':'waiting','request':str(p/'request.json')})
        print('CHECKPOINT_PAIR_WAIT '+str(p/'request.json'),flush=True)
        while not (p/'response.json').exists():time.sleep(.5)
        response=json.loads((p/'response.json').read_text());decision=validate(response,req)
        write(self.root/'pending.json',{'status':'responded','request':str(p/'request.json')})
        if decision=='abort':raise RuntimeError(response['reason'])
        if decision=='checkpoint':self.save_checkpoint(e,ob,response)
        elif decision=='error':
            if not self.checkpoint_path:raise ValueError('Cannot restore an unsaved checkpoint')
            with self.checkpoint_path.open('rb') as f:state=pickle.load(f)
            if i<=state['active']['index']:raise ValueError('Error must occur after checkpoint')
            self.error=dict(action_index=i,physics_ticks=self.task(e).step_count,response=response,request=str(p/'request.json'))
            write(self.case_root/'actual_error.json',self.error)
        elif decision in ('verdict','handoff'):
            self.local_choice=dict(choice=response['choice'],reason=response['reason'],action_index=i,request=str(p/'request.json'))
            write(s['directory']/'local_choice.json',self.local_choice)
            if decision=='handoff':
                self.handed_back=True
                write(s['directory']/'handoff.json',dict(policy=self.policy(deep=True),external_actions=self.external_actions,**self.local_choice))
        return response

    def finish_arm(self,e,ob,arm,triggered):
        result=self.result(e,ob,arm,triggered)
        result.update(local_choice=self.local_choice if triggered else None,external_actions=self.external_actions if triggered else 0,
                      error=self.error,checkpoint=str(self.checkpoint_path) if self.checkpoint_path else None,
                      protocol='actual_checkpoint_action_pair_v1')
        write(self.case_root/arm/'result.json',result)
        return result

def run(e):
    from vlnverse.evaluator.vln_pe_evaluator import runner_status_code
    from vlnverse.utils import progress_log_multi_util
    oracle=CheckpointPair(e);e.review=None;e.oracle=None;e._rss_budget=0;e._completed_this_run=0
    _,infos=e.env.reset();progress_log_multi_util.trace_start(trajectory_id=e.now_path_key(infos[0]))
    obs=e.warm_up();e.reset_seeded_agent(infos,[0]);e.fake_obs=obs[0][e.robot_name]
    ob=e._obs_remove_robot_name(obs)[0];e.runner_status=np.full((1,),runner_status_code.NORMAL,runner_status_code)
    eid=infos[0].data['episode_id'];oracle.begin(e,eid)
    action=np.array([{e.robot_name:{'stand_still':[]}}]);ended=False
    while e.env.is_running():
        oracle.observe(e,ob);response=oracle.review(e,ob)
        if response['decision']=='error':break
        _,action=e.get_action([ob],action);oracle.action(action[0][e.robot_name])
        obs,term=e.env_step(action);ob=obs[0];ended=bool(term[0])
        if ended:oracle.observe(e,ob,True);break
    results=[]
    if ended:
        for arm in ARMS:results.append(oracle.finish_arm(e,ob,arm,False))
    elif oracle.error:
        for arm in ARMS:
            e.runner_status[:]=runner_status_code.NORMAL
            ob,ended=oracle.restore(e,arm)
            while not ended and e.env.is_running():
                oracle.observe(e,ob);response=oracle.review(e,ob)
                external=arm=='oracle_actions' and not oracle.handed_back
                if external:
                    if response['decision']!='action':raise RuntimeError('External control requires explicit action')
                    action=np.array([{e.robot_name:{'move_by_discrete':[response['action']]}}]);oracle.external_actions+=1
                else:_,action=e.get_action([ob],action)
                oracle.action(action[0][e.robot_name])
                obs,term=e.env_step(action);ob=obs[0];ended=bool(term[0])
            if not ended:raise RuntimeError('Branch interrupted')
            oracle.observe(e,ob,True);results.append(oracle.finish_arm(e,ob,arm,True))
    else:raise RuntimeError('Trunk interrupted')
    write(oracle.case_root/'results.json',results)
    write(oracle.root/'pending.json',{'status':'episode_complete','episode_id':eid})
    e.terminate_ops([ob],infos,[True]);e.env.close()
