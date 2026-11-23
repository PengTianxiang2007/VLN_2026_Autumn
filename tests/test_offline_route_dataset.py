import json
import math
from pathlib import Path
import tempfile
import unittest

from core.offline_route_dataset import OfflineRouteDataset
from scripts.build_offline_route_dataset import reference_direction


class OfflineDatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);folder=self.root/'inputs'/'example';folder.mkdir(parents=True)
        (folder/'task.json').write_text(json.dumps(dict(episode_id='example',instruction='Go forward.')))
        self.records=[]
        for t in range(3):
            views=[dict(image=f'observations/{t}/{i}.png',relative_yaw_deg=(i*45+180)%360-180) for i in range(8)]
            self.records.append(dict(episode_id='example',step=t,simulation_time_s=100+t,episode_elapsed_s=t,
                robot_pose={'heading_deg':90},native_camera_pose={},calibration={},
                previous_action=None if t==0 else {'move_by_discrete':[t]},
                native_front={'image':f'observations/{t}/native.png'},views_180=[views[i] for i in [1,0,7]],views_360=views,
                action={'future_action':['MUST NOT LEAK']},reference_path=['MUST NOT LEAK'],terminal=t==2))
        self.file=folder/'observations.jsonl'
        self.file.write_text(''.join(json.dumps(r)+'\n' for r in self.records))
        self.ds=OfflineRouteDataset(self.root)

    def test_causal_cutoff_does_not_even_parse_future(self):
        with self.file.open('a') as f:f.write('INVALID FUTURE RECORD\n')
        context=self.ds.context('example',2,'180')
        self.assertEqual([r['step'] for r in context['observations']],[0,1,2])
        last=context['observations'][-1]
        self.assertEqual(last['previous_action'],{'move_by_discrete':[2]})
        self.assertFalse({'action','reference_path','terminal'} & last.keys())
        self.assertIsNone(context['observations'][0]['previous_action'])

    def test_view_order_and_native_front_are_separate(self):
        half=self.ds.context('example',1,'180')['observations'][-1]
        self.assertEqual([v['relative_yaw_deg'] for v in half['views']],[45,0,-45])
        self.assertEqual(len(self.ds.context('example',1,'360')['observations'][-1]['views']),8)
        native=self.ds.context('example',1,'front')['observations'][-1]['views']
        self.assertEqual(len(native),1);self.assertTrue(native[0]['image'].endswith('native.png'))

    def test_missing_step_and_escape_rejected(self):
        with self.assertRaises(IndexError):self.ds.context('example',3)
        with self.assertRaises(ValueError):self.ds.context('example',-1)
        with self.assertRaises(ValueError):self.ds.task('../example')
        self.records[0]['native_front']['image']='../../escape.png'
        self.file.write_text(json.dumps(self.records[0])+'\n')
        with self.assertRaises(ValueError):self.ds.context('example',0,'front')

    def test_reference_lookahead_crosses_corner_without_using_robot_yaw_as_camera_yaw(self):
        c=dict(reference_path=[[0,0,0],[0,0,0],[0,2,0],[2,2,0]],nearest_reference_arc_m=[1.5],
               features={'reference_length_m':4})
        r=dict(step=0,robot_pose={'position_world_m':[0,1.5,1], 'heading_deg':90})
        d=reference_direction(c,r)
        self.assertEqual(d['target_world_m'],[.75,2,0])
        self.assertAlmostEqual(d['relative_to_current_robot_deg'],math.degrees(math.atan2(.5,.75))-90)
        self.assertFalse(d['feasible_action_validated'])

    def test_reference_direction_wrap_and_endpoint(self):
        c=dict(reference_path=[[0,0,0],[-2,-.4,0]],nearest_reference_arc_m=[1.9],
               features={'reference_length_m':math.hypot(2,.4)})
        r=dict(step=0,robot_pose={'position_world_m':[0,0,1], 'heading_deg':175})
        d=reference_direction(c,r)
        self.assertEqual(d['target_world_m'],[-2,-.4,0])
        self.assertAlmostEqual(d['relative_to_current_robot_deg'],16.309932474)


if __name__=='__main__':unittest.main()
