"""Original lifecycle equivalence and the narrow distance-Oracle hooks."""
import ast
import copy
from enum import Enum
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS, ModuleType
import unittest
from unittest.mock import patch

from core.oracle_distance_native import NativeDistanceHook, check_reset
from core.seeding import episode_seed
from scripts.prepare_oracle_distance import patch_runtime, source_files
from scripts.run_oracle_distance import job_plan, inherited_results, admission, wait_for_resources


def policy(eid='a'):
    state = {k: [] for k in ('rgb_list','depth_list','pose_list','intrinsic_list','time_ids','action_seq','pending')}
    state.update(episode_seed=episode_seed(2,eid),output_ids=None,past_key_values=None,last_image=None,
                 model_cache=[{}],model_curr_t=[0])
    return dict(episode_id=eid,step_id=0,pending_count=0,state=state)


class NativeTests(unittest.TestCase):
    def test_explicit_gpu3_sharing_uses_original_flag_without_auto_selection(self):
        manifest={'arms':{'early':{'threshold_m':.75}},'episode_ids':['a'],'seed':2,'code_root':'/snapshot'}
        job=job_plan(Path('/run'),manifest,['early'],['a'],3,3,allow_shared_gpu=True)[0]
        self.assertIn('--allow-shared-gpu',job['command'])
        self.assertEqual(job['command'][job['command'].index('--gpu')+1],'3')
        rows='0, 32000, 16000, 100\n1, 32000, 16000, 100\n2, 22000, 26000, 100\n3, 4000, 44000, 0\n'
        with patch('scripts.run_oracle_distance.subprocess.check_output',return_value=rows), \
             patch('scripts.run_oracle_distance.Path.read_text',return_value='MemAvailable: 200000000 kB\n'), \
             patch('scripts.run_oracle_distance.check_gpu') as check, patch('scripts.run_oracle_distance.time.sleep'):
            with self.assertRaises(RuntimeError):admission(3,3)
            admission(3,3,allow_shared_gpu=True)
            self.assertEqual(check.call_count,2)
            check.assert_called_with(3,32000,allow_shared=True)
        with self.assertRaises(ValueError):wait_for_resources(None,{},3,3,1,auto_gpu=True,allow_shared_gpu=True)

    def test_native_evaluator_identical_except_hook_installation(self):
        root=Path(__file__).resolve().parents[1]
        name='benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py'
        original=(root/name).read_text()
        modified=patch_runtime(name,original)
        stripped=modified.replace('# Frozen distance Oracle runtime v001\n','').replace(
            '        from core.oracle_distance_native import install\n        install(self)\n','')
        self.assertEqual(stripped,original)
        self.assertEqual(ast.dump(ast.parse(stripped)),ast.dump(ast.parse(original)))
        names=source_files()
        self.assertNotIn('core/oracle_distance_batch.py',names)
        self.assertNotIn('scripts/run_oracle_distance_batch.py',names)

    def test_all_scenes_go_to_one_original_invocation_per_condition(self):
        manifest={'arms':{'early':{'threshold_m':.75},'short':{'threshold_m':1.5}},
                  'episode_ids':['scene_a_1','scene_a_2','scene_b_1'],'seed':2,'code_root':'/snapshot'}
        jobs=job_plan(Path('/run'),manifest,list(manifest['arms']),manifest['episode_ids'],2,3,
                      [{'arm':'early','episode_id':'scene_a_1'}])
        self.assertEqual(len(jobs),2)
        self.assertEqual(jobs[0]['episode_ids'],['scene_a_2','scene_b_1'])
        self.assertEqual(len(jobs[1]['episode_ids']),3)
        for j in jobs:
            self.assertNotIn('--rss-budget-mib',j['command'])
            self.assertNotIn('--limit-episodes',j['command'])
            self.assertNotIn('--scenes',j['command'])

    def test_memory_and_seed_leaks_rejected(self):
        check_reset(policy(),'a',2)
        for key,value in [('rgb_list',['old']),('past_key_values','old'),('model_cache',[{'old':1}]),
                          ('model_curr_t',[1]),('episode_seed',0)]:
            proof=policy();proof['state'][key]=value
            with self.subTest(key=key), self.assertRaises(RuntimeError):check_reset(proof,'a',2)

    def fixture(self,root):
        class Status(Enum): NORMAL=0; WARM_UP=1
        modules={name:ModuleType(name) for name in ('vlnverse','vlnverse.evaluator','vlnverse.evaluator.vln_pe_evaluator')}
        modules['vlnverse.evaluator.vln_pe_evaluator'].runner_status_code=Status
        calls=[];instances=[]
        e=NS(robot_name='h1',runner_status=[Status.NORMAL])
        e.reset_seeded_agent=lambda infos,ids:calls.append(('reset',infos[0].data['episode_id']))
        e.get_action=lambda obs,action:(calls.append(('action',obs[0]['position'])) or (obs,[{'h1':{'move':[1]}}]))
        e.env_step=lambda action:(calls.append(('physics',)) or ([{'position':'after'}],[False]))
        e.terminate_ops=lambda obs,infos,term:(calls.append(('native_score_and_reset',bool(term[0]))) or (False,infos))
        class Oracle:
            def __init__(self,e):self.manifest={'seed':2};self.arm='early';self.index=0;self.ended=False;instances.append(self)
            def begin(self,e,eid):self.eid=eid;self.active={'episode_id':eid};self.case_root=root/eid;self.case_root.mkdir()
            def policy(self,deep):return policy(self.eid)
            def task(self,e):return NS(step_count=1,config=NS(scene_asset_path='scene'))
            def observe(self,e,ob,terminal=False):calls.append(('observe',self.eid,terminal));return {}
            def automatic_review(self,e,ob,decision):return dict(ob,position='corrected'),self.ended
            def record_action(self,action):self.index+=1
            def finish_result(self,ob):calls.append(('oracle_result',self.eid))
        return e,modules,calls,instances,Oracle,Status

    def test_warmup_is_native_and_two_tasks_have_independent_oracle_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            e,modules,calls,instances,Oracle,Status=self.fixture(Path(tmp))
            with patch.dict(sys.modules,modules),patch('core.oracle_distance_native.DistanceOracle',Oracle):
                hook=NativeDistanceHook(e)
                e.runner_status=[Status.WARM_UP]
                e.get_action([{'position':'warmup'}],[])
                self.assertEqual(instances,[])
                for eid in ('a','b'):
                    infos=[NS(data={'episode_id':eid})]
                    e.reset_seeded_agent(infos,[0]);e.runner_status=[Status.NORMAL]
                    e.get_action([{'position':'raw'}],[])
                    e.env_step([])
                    e.terminate_ops([{'metrics':{'m':[{'success':1}]}}],infos,[True])
                    self.assertIsNone(hook.oracle)
            self.assertEqual([o.index for o in instances],[1,1])
            self.assertEqual([c for c in calls if c[0]=='reset'],[('reset','a'),('reset','b')])
            self.assertEqual(sum(c[0]=='physics' for c in calls),2)
            for eid in ('a','b'):
                self.assertTrue((Path(tmp)/eid/'native_scoring_complete.json').exists())

    def test_terminal_during_correction_goes_to_native_scoring_without_extra_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            e,modules,calls,instances,Oracle,Status=self.fixture(Path(tmp))
            with patch.dict(sys.modules,modules),patch('core.oracle_distance_native.DistanceOracle',Oracle):
                hook=NativeDistanceHook(e);infos=[NS(data={'episode_id':'a'})]
                e.reset_seeded_agent(infos,[0]);instances[0].ended=True
                e.get_action([{'position':'raw','metrics':{'m':[{'success':0}]}}],[])
                obs,term=e.env_step([])
                self.assertEqual(term,[True])
                e.terminate_ops(obs,infos,term)
            self.assertFalse(any(c[0] in ('action','physics') for c in calls))
            self.assertIn(('native_score_and_reset',True),calls)

    def test_inherited_protocol_and_hash_are_checked(self):
        manifest=dict(protocol='p',config={},cases=[],official_split_sha256='x',arms={'early':{'threshold_m':.75}})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch('scripts.run_oracle_distance.load_campaign',return_value=dict(manifest,config={'changed':True})):
                with self.assertRaises(ValueError):inherited_results(manifest,[root])
            (root/'oracle_records/early/a').mkdir(parents=True)
            (root/'oracle_records/early/a/result.json').write_text('{}')
            (root/'a.complete.json').write_text(json.dumps(dict(job={'arm':'early','episode_id':'a'},result_sha256='bad')))
            with patch('scripts.run_oracle_distance.load_campaign',return_value=manifest):
                with self.assertRaisesRegex(RuntimeError,'hash mismatch'):inherited_results(manifest,[root])


if __name__=='__main__':unittest.main()
