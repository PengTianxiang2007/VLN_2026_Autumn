import unittest
from core.oracle_checkpoint_pair import validate
class ProtocolTests(unittest.TestCase):
    def response(self,**kw):return dict(request_id='x',reason='Actual visible branch evidence required.',**kw)
    def test_forbid_pose_and_stop_actions(self):
        for decision in ('teleport','checkpoint','error','continue'):
            with self.assertRaises(ValueError):validate(self.response(decision=decision),dict(request_id='x',mode='oracle_actions'))
        for act in (0,-1,4,True,1.0):
            with self.assertRaises(ValueError):validate(self.response(decision='action',action=act),dict(request_id='x',mode='oracle_actions'))
        for act in (1,2,3):self.assertEqual(validate(self.response(decision='action',action=act),dict(request_id='x',mode='oracle_actions')),'action')
    def test_no_control_in_stream_arm(self):
        with self.assertRaises(ValueError):validate(self.response(decision='action',action=1),dict(request_id='x',mode='streamvln'))
        self.assertEqual(validate(self.response(decision='verdict',choice='wrong'),dict(request_id='x',mode='streamvln')),'verdict')
    def test_handoff_requires_result(self):
        with self.assertRaises(ValueError):validate(self.response(decision='handoff'),dict(request_id='x',mode='oracle_actions'))
        self.assertEqual(validate(self.response(decision='handoff',choice='correct'),dict(request_id='x',mode='oracle_actions')),'handoff')
if __name__=='__main__':unittest.main()

class SavedPoseTests(unittest.TestCase):
    def test_pose_restorer_ignores_map_target(self):
        import numpy as np
        from types import SimpleNamespace as NS
        from unittest.mock import patch
        from core.oracle_checkpoint_pair import CheckpointPair
        from core.oracle_branching import BranchOracle
        got=[]
        def setter(**kw):got.append(kw)
        art=NS(set_world_pose=setter)
        obj=object.__new__(CheckpointPair);obj.task=lambda e:NS(robot=NS(articulation=NS(_articulation=art)))
        obj.saved_root_pose=(np.array([1.,2.,3.]),np.array([.9,.1,.2,.3]))
        def fake_teleport(self,e,ob,target,path):
            art.set_world_pose(position=np.array([999,999,999]),orientation=np.array([1,0,0,0]));return {},False
        with patch.object(BranchOracle,'teleport',fake_teleport):obj.restore_pose(None,{}, {'target_xy':[999,999]},None)
        np.testing.assert_array_equal(got[0]['position'],[1.,2.,3.])
        np.testing.assert_array_equal(got[0]['orientation'],[.9,.1,.2,.3])
        self.assertIs(art.set_world_pose,setter)
