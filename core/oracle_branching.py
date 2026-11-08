"""Shared uncorrected trunk and semantic-delay intervention branches.

Snapshots are resumed ONLY through canonical pose correction. They are not a general
PhysX checkpoint: contact/renderer caches are not serializable. No prefix is replayed.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import random
import time
import urllib.request
import numpy as np
from core.oracle_crossing import OracleCrossing, plain, write, reference_distance

ARMS = ('short','medium','long')
STAGES = ('continue','onset','short','medium','long','clear','abort')


def digest(value):
    # Numeric state content, independent of array storage addresses.
    return hashlib.sha256(json.dumps(plain(value),sort_keys=True,default=str).encode()).hexdigest()


def accounting(task):
    return dict(task={k:copy.deepcopy(getattr(task,k)) for k in ('step_count','steps','warm_up_step','_done')},
                stuck=copy.deepcopy(vars(task.done_checker.stuck_checker)),
                metrics={k:copy.deepcopy({n:v for n,v in vars(m).items() if n not in ('config','task_config','metric_config')})
                         for k,m in task.metrics.items()})


def restore_accounting(task, state):
    for k,v in state['task'].items():setattr(task,k,copy.deepcopy(v))
    task.done_checker.stuck_checker.__dict__.clear()
    task.done_checker.stuck_checker.__dict__.update(copy.deepcopy(state['stuck']))
    for k,values in state['metrics'].items():
        metric=task.metrics[k]
        for name in list(vars(metric)):
            if name not in ('config','task_config','metric_config'):delattr(metric,name)
        for name,v in values.items():setattr(metric,name,copy.deepcopy(v))
    if digest(accounting(task))!=digest(state):raise RuntimeError('Accounting restore mismatch')


class BranchOracle(OracleCrossing):
    def __init__(self,e):
        super().__init__(os.environ['VLN_ORACLE_MANIFEST'],os.environ['VLN_ORACLE_RECORDS'],e.agent.base_url)
        self.branch_root=Path(os.environ['VLN_BRANCH_ROOT']);self.snapshots={};self.event=None
        self.trunk_closed=False;self.mode='trunk';self.last_review=-1
        self.calibration=json.loads((self.branch_root/'calibration.json').read_text())

    def rpc(self,operation,key):
        req=urllib.request.Request(self.agent_url+'/branch/checkpoint',
            data=json.dumps(dict(operation=operation,key=key)).encode(),headers={'Content-Type':'application/json'})
        with self.opener.open(req,timeout=240) as r:return json.load(r)

    def begin(self,e,eid):
        super().start(eid,e)
        self.case_root=self.root/eid
        self.active['directory']=self.case_root/'trunk'
        (self.active['directory']/'frames').mkdir(parents=True,exist_ok=False)
        self.active.update(interventions=[],intervention=None)
        self.mode='trunk';self.snapshots={};self.event=None;self.last_review=-1;self.trunk_closed=False
        # A live model round-trip gate BEFORE any policy action. No physics step or reset.
        key=eid+'_roundtrip'
        saved=self.rpc('save',key);loaded=self.rpc('restore',key)
        assert saved['content_sha256']==loaded['content_sha256']
        write(self.case_root/'policy_roundtrip.json',dict(saved=saved,restored=loaded))

    def capture(self,e,ob,arm,response):
        import torch
        s=self.active;t=self.task(e);runner=e.env.env.runner
        key=s['episode_id']+'_'+arm
        policy=self.rpc('save',key)
        state=dict(accounting=accounting(t),ob=copy.deepcopy(ob),active=copy.deepcopy(s),
                   rng=(random.getstate(),np.random.get_state(),torch.get_rng_state(),torch.cuda.get_rng_state_all()),
                   runner={k:copy.deepcopy(getattr(runner,k)) for k in ('render_trigger','_render','finished_tasks')},
                   target_id=self.event['target_id'],response=response,event=copy.deepcopy(self.event),key=key,
                   pose=plain(t.robot.articulation.get_world_pose()),
                   joints=plain(t.robot.articulation.get_joint_positions()),
                   physics_time_index=runner.get_current_time_step_index())
        p=self.case_root/('snapshot_'+arm+'.pkl')
        with p.open('xb') as f:pickle.dump(state,f)
        self.snapshots[arm]=p
        proof=dict(arm=arm,key=key,action_index=s['index'],physics_ticks=t.step_count,
                   reference_distance_m=reference_distance(ob['globalgps'],self.cases[s['episode_id']]['reference_path']),
                   target_id=state['target_id'],event=state['event'],response=response,policy=policy,
                   accounting_sha256=digest(state['accounting']),prefix_sha256=digest(s['observations']))
        write(self.case_root/('snapshot_'+arm+'.json'),proof)
        write(self.case_root/'snapshots.json',{k:str(v) for k,v in self.snapshots.items()})

    def restore(self,e,arm):
        import torch
        with self.snapshots[arm].open('rb') as f:state=pickle.load(f)
        self.mode=arm;self.active=copy.deepcopy(state['active']);self.active['directory']=self.case_root/arm
        (self.active['directory']/'frames').mkdir(parents=True,exist_ok=False)
        with (self.active['directory']/'observations.jsonl').open('w') as f:
            for row in self.active['observations']:f.write(json.dumps(row)+'\n')
        t=self.task(e);runner=e.env.env.runner
        restore_accounting(t,state['accounting'])
        for k,v in state['runner'].items():setattr(runner,k,copy.deepcopy(v))
        proof=self.rpc('restore',state['key'])
        random.setstate(state['rng'][0]);np.random.set_state(state['rng'][1])
        torch.set_rng_state(state['rng'][2]);torch.cuda.set_rng_state_all(state['rng'][3])
        write(self.active['directory']/'restore_proof.json',dict(policy=proof,
             accounting_sha256=digest(accounting(t)),expected_accounting_sha256=digest(state['accounting']),
             shared_prefix_sha256=digest(self.active['observations']),source=str(self.snapshots[arm]),
             scope='restore accounting and policy then IMMEDIATE canonical correction; no uncorrected physics rollback'))
        self.last_review=-1;self.event=None
        return self.correct(e,state['ob'],state['target_id'],state['response'],state['event'])

    def correct(self,e,ob,target_id,response,event):
        from PIL import Image
        s=self.active;c=self.cases[s['episode_id']]
        target=next(t for t in c['targets'] if t['id']==target_id)
        directory=s['directory']/f'correction_{len(s["interventions"])+1:02d}'
        directory.mkdir(exist_ok=False)
        before=self.policy(deep=True)
        result,ended=self.teleport(e,ob,target,directory)
        after=self.policy(deep=True)
        assert before['sha256']==after['sha256'],'Correction changed policy memory'
        write(directory/'memory_proof.json',dict(before=before,after=after,equal=True))
        iv=dict(number=len(s['interventions'])+1,arm=self.mode,action_index=s['index'],
                before_position=plain(ob['globalgps']),after_position=plain(result['globalgps']),
                before_rotation=plain(ob['globalrotation']),after_rotation=plain(result['globalrotation']),
                target_id=target_id,target_xy=target['target_xy'],target_yaw_rad=target['target_yaw_rad'],
                response=response,event=event,memory_unchanged=True,stable=not ended,
                physics_ticks=self.task(e).step_count,physics_settle_ticks=50,
                goal_distance_m=float(np.linalg.norm(np.asarray(result['globalgps'])[:2]-np.asarray(c['reference_path'][-1])[:2])))
        s['interventions'].append(iv);s['teleported']=True
        if s['intervention'] is None:s['intervention']=iv
        write(directory/'intervention.json',iv);write(s['directory']/'interventions.json',s['interventions'])
        if result.get('rgb') is not None:Image.fromarray(result['rgb']).save(directory/'after.jpg')
        self.event=None
        print('BRANCH_CORRECTION '+json.dumps(iv,ensure_ascii=False),flush=True)
        return result,ended

    def observe(self,e,ob,terminal=False):
        from PIL import Image
        s=self.active;i=s['index'];path=s['directory']/'frames'/f'{i:04d}.jpg'
        if ob.get('rgb') is not None:Image.fromarray(ob['rgb']).save(path,quality=90)
        row=dict(action_index=i,position=plain(ob['globalgps']),rotation=plain(ob['globalrotation']),
                 frame=str(path),intervention_count=len(s['interventions']),physics_ticks=self.task(e).step_count,
                 terminal=terminal)
        s['observations'].append(row)
        with (s['directory']/'observations.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')

    def review(self,e,ob):
        s=self.active;c=self.cases[s['episode_id']];i=s['index'];policy=self.policy()
        if policy['pending_count'] or i==self.last_review or (self.mode=='trunk' and self.trunk_closed):return ob,False
        self.last_review=i
        p=s['directory']/f'review_{i:04d}';p.mkdir(exist_ok=False)
        from PIL import Image
        Image.fromarray(ob['rgb']).save(p/'before.png')
        request=dict(request_id=f'{s["episode_id"]}_{self.mode}_{i}',episode_id=s['episode_id'],mode=self.mode,
                     action_index=i,position=plain(ob['globalgps']),rotation=plain(ob['globalrotation']),policy=policy,
                     instruction=c['instruction'],targets=c['targets'],history=s['observations'][-12:],
                     case_directory=str(s['directory']),previous_interventions=s['interventions'],
                     intervention_count=len(s['interventions']),crossing_id=c['crossing_id'],
                     crossing_distance_m=float(np.linalg.norm(np.asarray(ob['globalgps'])[:2]-c['crossing']['position'])),
                     expected=c['review']['expected'],original_error=c['review']['actual'],
                     target_xy=c['target_xy'],target_yaw_rad=c['target_yaw_rad'],
                     calibration=self.calibration[s['episode_id']],event=self.event,
                     saved_arms=list(self.snapshots),physics_ticks=self.task(e).step_count)
        write(p/'request.json',request);write(self.root/'pending.json',dict(status='waiting',request=str(p/'request.json'),mode=self.mode))
        print('BRANCH_WAIT '+str(p/'request.json'),flush=True)
        while not (p/'response.json').exists():time.sleep(.25)
        response=json.loads((p/'response.json').read_text())
        if response.get('request_id')!=request['request_id'] or response.get('stage') not in STAGES:
            raise ValueError('Invalid semantic review')
        if len(response.get('reason',''))<12:raise ValueError('Evidence reason required')
        write(self.root/'pending.json',dict(status='responded',request=str(p/'request.json')))
        stage=response['stage']
        if stage=='abort':raise RuntimeError(response['reason'])
        if stage=='clear':
            if self.mode=='trunk' and self.event is not None:self.trunk_closed=True
            self.event=None
        elif stage=='onset':
            if self.event is not None:raise ValueError('Do not overwrite an active error event')
            target=response['target_id']
            if target not in {t['id'] for t in c['targets']}:raise ValueError('Unknown correction target')
            self.event=dict(action_index=i,physics_ticks=self.task(e).step_count,calls=policy['calls'],
                            target_id=target,reason=response['reason'],request=str(p/'request.json'))
        elif stage in ARMS:
            if self.event is None or i<=self.event['action_index']:raise ValueError('Delayed correction needs an earlier actual-error confirmation')
            if self.mode=='trunk':
                expected=ARMS[len(self.snapshots)]
                if stage!=expected:raise ValueError('Capture semantic stages in order without duplicates')
                self.capture(e,ob,stage,response)
                if stage=='long':return ob,True
            elif ARMS.index(stage)>=ARMS.index(self.mode):
                return self.correct(e,ob,self.event['target_id'],response,self.event)
        return ob,False

    def result(self,e,ob,arm,triggered=True):
        metrics=plain(next(iter(ob['metrics'].values()))[0])
        p=self.case_root/arm;p.mkdir(exist_ok=True)
        result=dict(episode_id=self.active['episode_id'],arm=arm,status='complete',triggered=triggered,
                    metrics=metrics,interventions=copy.deepcopy(self.active['interventions']) if triggered else [],
                    source_trunk=None if triggered else str(self.case_root/'trunk'),
                    actions=self.active['index'],physics_ticks=self.task(e).step_count)
        write(p/'result.json',result)
        return result


def run(e):
    """One original episode per process; three branch results in separate files."""
    from vlnverse.evaluator.vln_pe_evaluator import runner_status_code
    oracle=BranchOracle(e)
    e.review=None;e.oracle=None;e._rss_budget=0;e._completed_this_run=0
    _,infos=e.env.reset()
    from vlnverse.utils import progress_log_multi_util
    progress_log_multi_util.trace_start(trajectory_id=e.now_path_key(infos[0]))
    obs=e.warm_up()
    e.reset_seeded_agent(infos,[0]);e.fake_obs=obs[0][e.robot_name]
    ob=e._obs_remove_robot_name(obs)[0]
    e.runner_status=np.full((1,),runner_status_code.NORMAL,runner_status_code)
    eid=infos[0].data['episode_id'];oracle.begin(e,eid)
    action=[{e.robot_name:{'stand_still':[]}}];ended=False;trunk_terminal=None
    while e.env.is_running():
        oracle.observe(e,ob)
        ob,last=oracle.review(e,ob)
        if last:break
        _,action=e.get_action([ob],action);oracle.action(action[0][e.robot_name])
        obs,term=e.env_step(action);ob=obs[0];ended=bool(term[0])
        if ended:
            oracle.observe(e,ob,True);trunk_terminal=copy.deepcopy(ob);break
    if not ended and len(oracle.snapshots)!=3:raise RuntimeError('Trunk interrupted before branching')
    results=[]
    # Save natural terminal outcomes before restoring any earlier branch.
    if trunk_terminal is not None:
        for arm in ARMS:
            if arm not in oracle.snapshots:results.append(oracle.result(e,trunk_terminal,arm,False))
        write(oracle.case_root/'trunk/result.json',dict(metrics=plain(next(iter(ob['metrics'].values()))[0]),actions=oracle.active['index']))
    for arm in ARMS:
        if arm not in oracle.snapshots:continue
        ob,ended=oracle.restore(e,arm)
        e.runner_status[:]=runner_status_code.NORMAL
        while not ended and e.env.is_running():
            oracle.observe(e,ob)
            ob,ended=oracle.review(e,ob)
            if ended:break
            _,action=e.get_action([ob],action);oracle.action(action[0][e.robot_name])
            obs,term=e.env_step(action);ob=obs[0];ended=bool(term[0])
        if not ended:raise RuntimeError('Branch interrupted')
        oracle.observe(e,ob,True);results.append(oracle.result(e,ob,arm))
    if len(results)!=3:raise RuntimeError('Missing paired results')
    write(oracle.case_root/'results.json',results)
    write(oracle.root/'pending.json',dict(status='episode_complete',episode_id=eid))
    # Native LMDB here is only a launcher completion marker for this one episode;
    # experimental metrics are the THREE independently labelled results above.
    e.terminate_ops([ob],infos,[True])
    e.env.close()
