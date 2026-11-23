"""Geometry evidence must not choose, move or suppress a correction target."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np

from core.oracle_distance_runtime import DistanceOracle
from core.oracle_landing_geometry import SceneLandingGeometry, freeze_scene_geometry
from scripts.run_oracle_distance import load_campaign, sha


def geometry():
    meta = dict(scene='sample', up_axis='Z', units='meters', resolution=.1,
                clearance_m=.18, width=20, height=20, low=[0, 0], high=[1.9, 1.9],
                body_height_band=[.18, 1.65])
    masks = {k: np.zeros((20, 20), dtype=bool) for k in ['floor','wall','furniture','doors','safe']}
    masks['floor'][:] = True
    masks['safe'][:] = True
    masks['distance'] = np.full((20,20), .5)
    return meta, masks


class LandingGeometryTests(unittest.TestCase):
    def test_world_xy_pixel_orientation_and_heading_probes(self):
        audit = SceneLandingGeometry(*geometry())
        r = audit.check_target({'target_xy': [.4, 1.2], 'target_yaw_rad': 0.})
        self.assertEqual(r['target']['pixel'], [4, 7])
        self.assertEqual(r['target']['assessment'], 'clear_in_projection')
        self.assertAlmostEqual(r['heading_probes'][-1]['xy'][0], .65)
        self.assertAlmostEqual(r['heading_probes'][-1]['xy'][1], 1.2)
        self.assertFalse(r['collision_certified'])

    def test_overlap_off_floor_clearance_and_outside_are_distinct(self):
        meta, masks = geometry()
        masks['wall'][7,4] = True
        masks['furniture'][7,4] = True
        masks['floor'][7,5] = False
        masks['distance'][7,6] = .1
        masks['safe'][7,7] = False
        audit = SceneLandingGeometry(meta,masks)
        self.assertEqual(audit.check_xy([.4,1.2])['overlapping_layers'], ['wall','furniture'])
        self.assertEqual(audit.check_xy([.5,1.2])['assessment'], 'off_projected_floor')
        self.assertEqual(audit.check_xy([.6,1.2])['assessment'], 'low_projected_clearance')
        self.assertEqual(audit.check_xy([.7,1.2])['assessment'], 'excluded_small_free_component')
        self.assertEqual(audit.check_xy([-1,1.2])['assessment'], 'outside_map')

    def test_runtime_observation_attaches_advice_without_changing_decision(self):
        meta, masks = geometry()
        masks['wall'][7,4] = True
        target = dict(id='runtime_event', target_xy=[.4,1.2], target_yaw_rad=0., branch_xy=[.2,1.2])
        decision = dict(distance_m=1., threshold_reached=True, target=target, event={'target_id':'runtime_event'})
        original = copy.deepcopy(decision)
        with tempfile.TemporaryDirectory() as tmp:
            hook = DistanceOracle.__new__(DistanceOracle)
            hook.landing_geometry = SceneLandingGeometry(meta,masks)
            hook.trigger = Mock(update=Mock(return_value=decision))
            hook.active = dict(directory=Path(tmp), index=5, observations=[])
            hook.case_root = Path(tmp); hook.maximum_distance=0.;hook.sequence=0
            hook.task = Mock(return_value=SimpleNamespace(step_count=25))
            result = hook.observe(None,dict(globalgps=[.4,2.2,1.],globalrotation=[1,0,0,0]))
            evidence=result['target'].pop('scene_geometry_audit')
            self.assertEqual(result,original)
            self.assertEqual(evidence['target']['assessment'],'projected_obstacle_overlap')
            self.assertFalse(evidence['intervention_vetoed'])
            logged=json.loads((Path(tmp)/'observations.jsonl').read_text())
            self.assertEqual(logged['target']['scene_geometry_audit'],evidence)

    def test_freeze_preserves_source_and_rejects_later_geometry_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'source/scenes/sample';src.mkdir(parents=True)
            meta,masks=geometry()
            (src/'geometry.json').write_text(json.dumps(meta))
            np.savez_compressed(src/'map_masks.npz',**masks)
            # Static candidates must not even be copied into runtime assets.
            (src/'crossings.json').write_text('not JSON; must never be read')
            config=freeze_scene_geometry(root/'source',['sample'],root/'campaign/geometry')
            self.assertEqual(len(config['files_sha256']),2)
            SceneLandingGeometry.from_manifest(config,'sample')
            campaign=root/'campaign'
            manifest=dict(protocol='auto_branch_oracle_v001',code_sha256={},landing_geometry_audit=config)
            (campaign/'manifest.json').write_text(json.dumps(manifest))
            (campaign/'cohort.json').write_text('{}')
            (campaign/'seal.json').write_text(json.dumps({k+'_sha256':sha(campaign/(k+'.json')) for k in ['manifest','cohort']}))
            load_campaign(campaign)
            (campaign/'geometry/sample/geometry.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError,'Frozen geometry changed'):
                load_campaign(campaign)
            with self.assertRaisesRegex(RuntimeError,'Frozen geometry changed'):
                SceneLandingGeometry.from_manifest(config,'sample')
            self.assertEqual(json.loads((src/'geometry.json').read_text()),meta)

    def test_bad_coordinate_frame_and_mismatched_masks_are_rejected(self):
        meta,masks=geometry()
        with self.assertRaises(ValueError):
            SceneLandingGeometry(dict(meta,up_axis='Y'),masks)
        masks['doors']=np.zeros((1,2))
        with self.assertRaisesRegex(ValueError,'shape mismatch'):
            SceneLandingGeometry(meta,masks)


if __name__=='__main__':
    unittest.main()
