import math
import unittest
import tempfile
from pathlib import Path
from core.jev_capture import estimate_headings,camera_position,VIEW_SETS,VIEW_OFFSETS


def row(i,x,y,a):return dict(frame=i,position=[x,y,1],action_after_observation={'move_by_discrete':[a]})


class HeadingTests(unittest.TestCase):
    def test_absolute_alignment_recovers_known_camera_rotation(self):
        import cv2
        import numpy as np
        from core.jev_capture import align_reference
        rng=np.random.RandomState(7);source=rng.randint(0,256,(480,640),dtype=np.uint8)
        source=cv2.GaussianBlur(source,(3,3),.5)
        angle=math.radians(12);k=np.array([[320,0,320],[0,320,240],[0,0,1.]])
        rotation=np.array([[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]])
        target=cv2.warpPerspective(source,k@rotation@np.linalg.inv(k),(640,480))
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'source.png';b=Path(tmp)/'render.png';cv2.imwrite(str(a),source);cv2.imwrite(str(b),target)
            result=align_reference(a,[dict(id=0,path=b,world_yaw_deg=73)])
            self.assertTrue(result['accepted']);self.assertAlmostEqual(result['base_yaw_deg'],61,delta=1)

    def test_visual_rotation_replaces_unexecuted_turn_and_invalid_visual_falls_back(self):
        f=[row(0,0,0,2),row(1,0,0,2),row(2,0,0,0)]
        visual=[None,dict(valid=True,delta_yaw_deg=2),dict(valid=False)]
        r=estimate_headings(f,[1,0,0,0],visual)
        self.assertAlmostEqual(r[1]['base_yaw_deg'],2);self.assertAlmostEqual(r[2]['base_yaw_deg'],17)

    def test_action_is_applied_only_to_next_observation(self):
        r=estimate_headings([row(0,0,0,2),row(1,0,0,3),row(2,0,0,0)],[1,0,0,0])
        for actual,expected in zip(r,[0,15,0]):self.assertAlmostEqual(actual['base_yaw_deg'],expected)

    def test_forward_displacement_corrects_drift_but_turn_translation_does_not(self):
        r=estimate_headings([row(0,0,0,1),row(1,.3,.1,2),row(2,.6,.2,0)],[1,0,0,0])
        self.assertAlmostEqual(r[1]['base_yaw_deg'],math.degrees(math.atan2(.1,.3))*.5)
        self.assertIsNone(r[2]['displacement_check'])
        self.assertAlmostEqual(r[2]['base_yaw_deg'],r[1]['base_yaw_deg']+15)

    def test_collision_or_tiny_drift_is_not_an_orientation_measurement(self):
        for x,y in [(0,.01),(-.4,0)]:
            r=estimate_headings([row(0,0,0,1),row(1,x,y,0)],[1,0,0,0]);self.assertEqual(r[1]['base_yaw_deg'],0)

    def test_no_future_frames_affect_heading(self):
        f=[row(0,0,0,1),row(1,.3,.1,3),row(2,.3,.1,2)]
        self.assertEqual(estimate_headings(f[:2],[1,0,0,0]),estimate_headings(f,[1,0,0,0])[:2])

    def test_camera_offset_rotates_and_view_sets_cover_requested_directions(self):
        p=camera_position([1,2,1],90,[.2,0,.72]);self.assertAlmostEqual(p[0],1);self.assertAlmostEqual(p[1],2.2);self.assertAlmostEqual(p[2],1.72)
        self.assertEqual([VIEW_OFFSETS[i] for i in VIEW_SETS['180']],[315,0,45])
        self.assertEqual([VIEW_OFFSETS[i] for i in VIEW_SETS['360']],list(range(0,360,45)))


if __name__=='__main__':unittest.main()
