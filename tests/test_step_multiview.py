import copy
import math
import unittest
from unittest.mock import Mock
import numpy as np
from core.step_multiview import turn_world_z, pose_record, angle_delta, assert_unchanged, OFFSETS, FRONT, fresh_render, temporary_visibility
from scripts.prepare_step_multiview import select_tasks


class MultiviewTests(unittest.TestCase):
    def test_robot_visibility_restored_on_render_failure(self):
        class Attr:
            def __init__(self, authored):self.authored=authored;self.value='inherited'
            def Get(self):return self.value
            def Set(self,value):self.value=value;self.authored=True
            def Clear(self):self.authored=False;self.value='inherited'
            def HasAuthoredValueOpinion(self):return self.authored
        for authored in (False,True):
            a=Attr(authored)
            with self.assertRaises(ValueError):
                with temporary_visibility(a) as proof:
                    self.assertEqual(a.Get(),'invisible')
                    raise ValueError('render failed')
            self.assertEqual(a.Get(),'inherited');self.assertEqual(a.authored,authored)
            self.assertTrue(proof['restored'])

    def test_frozen_time_waits_for_render_not_simulation_timestamp(self):
        camera=Mock()
        camera.get_current_frame.side_effect=[dict(rendering_frame=4,rendering_time=1.),dict(rendering_frame=5,rendering_time=1.)]
        camera.get_rgba.return_value=np.zeros((480,640,4),dtype=np.uint8)
        render=Mock()
        rgb,frame=fresh_render(camera,render,4)
        self.assertEqual(frame['rendering_frame'],5);self.assertEqual(frame['rendering_time'],1.)
        self.assertEqual(render.call_count,2);self.assertEqual(rgb.shape,(480,640,3))

    def test_stale_render_is_rejected_even_with_valid_pixels(self):
        camera=Mock();camera.get_current_frame.return_value=dict(rendering_frame=4)
        with self.assertRaises(RuntimeError):fresh_render(camera,Mock(),4)
        camera.get_rgba.assert_not_called()

    def test_current_heading_not_world_axes(self):
        # USD camera looking along +X, +Z up.
        q=np.array([.5,.5,-.5,-.5])
        for robot_yaw in (0,47,179,-173):
            for offset in OFFSETS:
                pose=pose_record([1,2,3],turn_world_z(q,robot_yaw+offset),camera=True)
                self.assertAlmostEqual(angle_delta(pose['heading_deg'],robot_yaw+offset),0,places=8)

    def test_roll_pitch_preserved_under_yaw(self):
        q=np.array([.7,.2,-.6,-.3]);q/=np.linalg.norm(q)
        start=pose_record([0,0,0],q,camera=True)
        for offset in OFFSETS:
            p=pose_record([0,0,0],turn_world_z(q,offset),camera=True)
            self.assertAlmostEqual(p['forward_world'][2],start['forward_world'][2])
            self.assertAlmostEqual(angle_delta(p['heading_deg'],start['heading_deg']+offset),0,places=8)

    def test_front_set_left_center_right(self):
        self.assertEqual([angle_delta(OFFSETS[i],0) for i in FRONT],[45,0,-45])

    def test_detects_time_pose_and_joint_changes(self):
        state=dict(physics_ticks=10,world_time=1.,world_step=10,position=[1,2,3],rotation=[1,0,0,0],
                   joints=[0,1],joint_velocities=[0,0],camera_position=[1,2,4],camera_rotation=[1,0,0,0])
        assert_unchanged(state,copy.deepcopy(state))
        for key in state:
            other=copy.deepcopy(state)
            if isinstance(other[key],list):other[key][0]+=.1
            else:other[key]+=.1
            with self.assertRaises(RuntimeError):assert_unchanged(state,other)

    def test_cohort_requires_exact_union_and_preserves_official_order(self):
        old=[dict(episode_id=str(i),status='crossing') for i in range(48)]
        new=dict(selected_ids=[str(i) for i in range(48,104)])
        official=[dict(episode_id=str(i)) for i in range(103,-1,-1)]
        selected,_,_=select_tasks(old,new,official)
        self.assertEqual(selected,official)
        new['selected_ids'][0]='0'
        with self.assertRaises(ValueError):select_tasks(old,new,official)


if __name__=='__main__':unittest.main()
