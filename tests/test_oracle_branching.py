import copy
import os
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
import numpy as np
from core.oracle_branching import accounting,restore_accounting,digest

class BranchTests(unittest.TestCase):
    def test_metric_budget_stuck_restore_isolated(self):
        t=NS(step_count=1200,steps=2,warm_up_step=50,_done=False,
             done_checker=NS(stuck_checker=NS(last_iter=900,agent_last_position=np.array([1.,2.,0.]))),
             metrics={'m':NS(config='static',current_path_length=8.,pred_traj_list=[[np.array([1.,2.])]],sim_step=1199)})
        saved=accounting(t);proof=digest(saved)
        t.step_count=25001;t._done=True;t.metrics['m'].pred_traj_list[0][0][0]=99
        t.done_checker.stuck_checker.last_iter=25000
        self.assertEqual(digest(saved),proof)
        restore_accounting(t,saved)
        self.assertEqual(t.step_count,1200);self.assertFalse(t._done)
        self.assertEqual(digest(accounting(t)),proof)
        t.metrics['m'].pred_traj_list[0][0][0]=77
        self.assertEqual(digest(saved),proof)

    def test_policy_roundtrip_cache_rng_and_branch_isolation(self):
        import torch
        import random
        from core.oracle_branch_policy import FIELDS,checkpoint,content_proof
        e=NS(**{k:[] for k in FIELDS});e.step_id=13;e.last_image=np.zeros((2,2,3),dtype=np.uint8)
        e.output_ids=torch.tensor([[1,2]]);e.past_key_values=((torch.randn(2,4),torch.randn(2,4)),)
        e.model=NS(cache=[{'features':torch.randn(2,3)}],curr_t=[3])
        a=NS(evaluator=e,pending=[],calls=4,current_episode_id='test',current_episode_seed=42)
        with tempfile.TemporaryDirectory() as d:
            old=os.environ.get('VLN_BRANCH_ROOT');os.environ['VLN_BRANCH_ROOT']=d
            try:
                saved,_,_=checkpoint(a,2,13,dict(operation='save',key='test_short'))
                expected=(random.random(),np.random.random(),torch.rand(1).item())
                e.model.cache[0]['features'].zero_();e.step_id=99;a.pending=[3]
                restored,resets,steps=checkpoint(a,9,99,dict(operation='restore',key='test_short'))
                self.assertEqual(restored['content_sha256'],saved['content_sha256'])
                self.assertEqual((resets,steps,e.step_id,a.pending),(2,13,13,[]))
                self.assertEqual((random.random(),np.random.random(),torch.rand(1).item()),expected)
                e.model.cache[0]['features'].zero_()
                checkpoint(a,2,13,dict(operation='restore',key='test_short'))
                self.assertEqual(content_proof(a,2),saved['content_sha256'])
                with self.assertRaises(FileExistsError):checkpoint(a,2,13,dict(operation='save',key='test_short'))
                a.pending=[1]
                with self.assertRaises(ValueError):checkpoint(a,2,13,dict(operation='save',key='pending'))
            finally:
                if old is None:os.environ.pop('VLN_BRANCH_ROOT',None)
                else:os.environ['VLN_BRANCH_ROOT']=old

if __name__=='__main__':unittest.main()
