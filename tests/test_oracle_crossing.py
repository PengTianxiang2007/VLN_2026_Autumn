"""Guard that interventions require a current, explicit Oracle response."""
import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from core import oracle_crossing
from core.oracle_crossing import validate_response


class OracleResponses(unittest.TestCase):
    def test_distance_uses_segments_not_only_recorded_vertices(self):
        self.assertAlmostEqual(oracle_crossing.reference_distance([5,2,100],[[0,0,0],[10,0,0]]),2.)

    def test_distance_handles_repeated_points_and_endpoint_clipping(self):
        self.assertAlmostEqual(oracle_crossing.reference_distance([4,4],[[0,0],[0,0],[1,0]]),5.)
        self.assertAlmostEqual(oracle_crossing.reference_distance([3,4],[[0,0]]),5.)

    def test_threshold_teleport_cannot_happen_early(self):
        request=dict(request_id='a',targets=[dict(id='C01')],deviation_threshold_m=3,reference_distance_m=2.999)
        response=dict(request_id='a',decision='teleport',target_id='C01',reason='Observed wrong room at crossing')
        with self.assertRaises(ValueError):validate_response(response,request)
        request['reference_distance_m']=3.
        validate_response(response,request)

    def test_delay_gate_waits_for_distance_and_native_empty_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'manifest.json'
            case=dict(episode_id='case',reference_path=[[0,0],[10,0]],crossing=dict(position=[0,0]))
            p.write_text(json.dumps(dict(multi_intervention=True,deviation_threshold_m=3,cases=[case])))
            hook=oracle_crossing.OracleCrossing(p,root/'records','http://unused')
            task=SimpleNamespace(env_offset=[0,0,0],robot=SimpleNamespace(articulation=SimpleNamespace(get_world_pose=lambda:([0,0,1],[1,0,0,0]),get_joint_positions=lambda:[0,0])))
            hook.task=lambda evaluator:task
            calls=[]
            def queued(deep=False):
                calls.append(deep)
                return dict(episode_id='case',step_id=hook.active['index'],pending_count=1)
            hook.policy=queued
            obs=[dict(globalgps=[5.,2.999,1.],globalrotation=[1.,0.,0.,0.],rgb=np.zeros((4,4,3),dtype=np.uint8))]
            hook.before(None,obs,[SimpleNamespace(data=dict(episode_id='case'))])
            self.assertEqual(calls,[])
            hook.active['index']=1;obs[0]['globalgps']=[5.,3.,1.]
            hook.before(None,obs,[SimpleNamespace(data=dict(episode_id='case'))])
            self.assertEqual(calls,[False])
            self.assertFalse((root/'records/pending.json').exists())
            self.assertEqual(hook.active['interventions'],[])

    def test_stale_response_cannot_move_robot(self):
        with self.assertRaises(ValueError):
            validate_response(dict(request_id='previous',decision='teleport',reason='Reviewed wrong branch'),dict(request_id='current'))

    def test_requires_explicit_decision_and_reason(self):
        for decision,reason in [('auto','Reviewed map'),('teleport','')]:
            with self.assertRaises(ValueError):
                validate_response(dict(request_id='a',decision=decision,reason=reason),dict(request_id='a'))

    def test_bounded_review_skip(self):
        with self.assertRaises(ValueError):
            validate_response(dict(request_id='a',decision='continue',reason='Still approaching crossing',skip_actions=100),dict(request_id='a'))
        validate_response(dict(request_id='a',decision='continue',reason='Still approaching crossing',skip_actions=4),dict(request_id='a'))

    def test_valid_teleport(self):
        validate_response(dict(request_id='a',decision='teleport',reason='Observed wrong room at crossing'),dict(request_id='a'))

    def test_multi_requires_a_frozen_target(self):
        request=dict(request_id='a',targets=[dict(id='C01')])
        for target in (None,'C99'):
            with self.assertRaises(ValueError):
                validate_response(dict(request_id='a',decision='teleport',target_id=target,reason='Observed wrong room at crossing'),request)
        validate_response(dict(request_id='a',decision='teleport',target_id='C01',reason='Observed wrong room at crossing'),request)

    def test_second_teleport_keeps_first_evidence_and_checks_memory_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'manifest.json'
            target=dict(id='C01',target_xy=[1.,0.],target_yaw_rad=0.,target_crossing_distance_m=1.)
            case=dict(episode_id='case',crossing=dict(position=[0.,0.]),crossing_id='C01',instruction='Turn at crossing',review=dict(expected='Left',actual='Right'),targets=[target],**{k:v for k,v in target.items() if k!='id'})
            path.write_text(json.dumps(dict(multi_intervention=True,cases=[case])))
            hook=oracle_crossing.OracleCrossing(path,root/'records','http://unused')
            task=SimpleNamespace(env_offset=[0,0,0],robot=SimpleNamespace(articulation=SimpleNamespace(get_world_pose=lambda:([0,0,1],[1,0,0,0]),get_joint_positions=lambda:[0,0])))
            hook.task=lambda evaluator:task
            policy_calls=[]
            def policy(deep=False):
                policy_calls.append(deep)
                return dict(episode_id='case',step_id=hook.active['index'],pending_count=0,sha256='unchanged')
            hook.policy=policy
            def teleport(evaluator,ob,c,p):return dict(ob,globalgps=[1.,0.,1.]),False
            hook.teleport=teleport
            original_write=oracle_crossing.write
            def answer(path,value):
                original_write(path,value)
                if Path(path).name=='request.json':
                    original_write(Path(path).with_name('response.json'),dict(request_id=value['request_id'],decision='teleport',target_id='C01',reason='Observed repeated wrong exit'))
            obs=[dict(globalgps=[0.,0.,1.],globalrotation=[1.,0.,0.,0.],rgb=np.zeros((4,4,3),dtype=np.uint8))]
            with patch.object(oracle_crossing,'write',side_effect=answer):
                hook.before(None,obs,[SimpleNamespace(data=dict(episode_id='case'))])
                hook.active['index']=4
                hook.before(None,obs,[SimpleNamespace(data=dict(episode_id='case'))])
            self.assertEqual(len(hook.active['interventions']),2)
            self.assertEqual(policy_calls.count(True),4)
            self.assertEqual(hook.active['intervention']['action_index'],0)
            folder=hook.active['directory']
            self.assertEqual(len(json.loads((folder/'interventions.json').read_text())),2)
            self.assertEqual(len(list(folder.glob('*/memory_proof.json'))),2)


if __name__=='__main__':unittest.main()
