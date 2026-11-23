"""CPU checks for annotation-free landing, live timing and baseline isolation."""
import copy
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import numpy as np

from core.oracle_auto_route import PROTOCOL, AutoRouteTrigger, automatic_target, build_auto_cohort
from core.oracle_distance_native import install
from core.oracle_distance_runtime import DistanceOracle
from scripts.run_oracle_distance import (inherited_results, job_environment, job_plan,
                                         native_progress, verify_arm)


def official_episode(eid='a'):
    return dict(episode_id=eid, scan='scene', instruction={'instruction_text': 'Go ahead.'},
                reference_path=[[0., 0., 0.], [20., 0., 0.]])


class GeometryTests(unittest.TestCase):
    def test_current_projection_offset_and_corner_heading(self):
        target = automatic_target([.5, -2, 90], [[0, 0], [1, 0], [1, 5]])
        self.assertEqual(target['projection_xy'], [.5, 0.])
        self.assertEqual(target['target_xy'], [1., .75])
        self.assertAlmostEqual(target['target_yaw_rad'], math.pi/2)
        self.assertEqual(target['actual_offset_m'], 1.25)
        corner = automatic_target([.5, -2], [[0, 0], [1, 0], [1, 5]], .5)
        self.assertEqual(corner['target_xy'], [1., 0.])
        self.assertAlmostEqual(corner['target_yaw_rad'], math.pi/2)
        self.assertNotIn('crossing_position', target)

    def test_endpoint_clamp_and_goal_radius_are_explicit(self):
        target = automatic_target([9.5, 2], [[0, 0], [10, 0]])
        self.assertEqual(target['target_xy'], [10., 0.])
        self.assertEqual(target['actual_offset_m'], .5)
        self.assertTrue(target['clamped_to_route_end'])
        self.assertTrue(target['near_goal_3m'])
        self.assertEqual(target['target_yaw_rad'], 0.)

    def test_equal_distance_loop_and_degenerate_segments(self):
        reference = [[0, 0], [0, 0], [10, 0], [0, 0]]
        target = automatic_target([5, 2], reference)
        self.assertEqual(target['projection_reference_arc_m'], 5.)
        self.assertEqual(target['target_xy'], [6.25, 0.])
        for route in ([[0, 0]], [[0, 0], [0, 0]], [[0, 0], [math.nan, 0]]):
            with self.subTest(route=route), self.assertRaises(ValueError):
                automatic_target([0, 1], route)
        for bad in (0, -1, math.inf, math.nan):
            with self.subTest(offset=bad), self.assertRaises(ValueError):
                automatic_target([0, 1], [[0, 0], [10, 0]], bad)

    def test_cohort_needs_only_official_fields_and_preserves_official_order(self):
        episodes = [official_episode('a'), official_episode('b')]
        before = copy.deepcopy(episodes)
        cohort = build_auto_cohort(episodes, ['b', 'a'])
        self.assertEqual([c['episode_id'] for c in cohort['cases']], ['a', 'b'])
        self.assertFalse(cohort['annotation_required'])
        self.assertEqual(cohort['events'], 0)
        self.assertTrue(all('targets' not in c for c in cohort['cases']))
        self.assertEqual(episodes, before)
        for ids in ([], ['unknown'], ['a', 'a']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                build_auto_cohort(episodes, ids)

    def test_excursion_keeps_identity_but_target_tracks_latest_pose(self):
        trigger = AutoRouteTrigger(official_episode())
        self.assertFalse(trigger.update([2, .749], 1)['threshold_reached'])
        first = trigger.update([2, .75], 2)
        later = trigger.update([5, 1.2], 5)
        self.assertEqual(first['event'], later['event'])
        self.assertEqual(first['target']['target_xy'], [3.25, 0.])
        self.assertEqual(later['target']['target_xy'], [6.25, 0.])
        self.assertEqual(later['target']['computed_at_action_index'], 5)
        self.assertIsNone(trigger.update([5, 0], 6)['target'])
        self.assertEqual(trigger.update([5, .75], 7)['event']['excursion'], 2)


class RuntimeTests(unittest.TestCase):
    def fixture(self, root):
        hook = DistanceOracle.__new__(DistanceOracle)
        case = build_auto_cohort([official_episode()], ['a'])['cases'][0]
        hook.cases = {'a': case}
        hook.manifest = {'protocol': PROTOCOL, 'onset_m': .75}
        hook.settings = {'mode': 'auto_route', 'landing_offset_m': 1.25}
        hook.threshold = .75
        hook.arm = 'auto_route'
        hook.case_root = root
        hook.root = root.parent
        hook.active = dict(episode_id='a', index=4, directory=root, observations=[],
                           interventions=[], intervention=None)
        hook.trigger = AutoRouteTrigger(case)
        hook.checkpoints = {}
        hook.seen_events = set()
        hook.completed_interventions = []
        hook.maximum_distance = 1.
        hook.executed_actions = 0
        task = NS(is_done=lambda: False, step_count=200)
        hook.task = lambda _: task
        hook.policy = Mock(side_effect=lambda deep=False: dict(episode_id='a',
                           step_id=hook.active['index'], pending_count=0, sha256='same'))
        def teleport(e, ob, target, path):
            task.step_count += 50
            return dict(ob, globalgps=[*target['target_xy'], 1.]), False
        hook.teleport = Mock(side_effect=teleport)
        return hook

    def ob(self, x=2., y=1.):
        return dict(globalgps=[x, y, 1.], globalrotation=[1., 0., 0., 0.],
                    rgb=np.zeros((2, 2, 3), dtype=np.uint8))

    def test_queue_wait_cancels_recovered_deviation_and_uses_new_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'a'; root.mkdir()
            hook = self.fixture(root)
            hook.policy = lambda deep=False: dict(episode_id='a', step_id=4, pending_count=2)
            ob = self.ob()
            hook.automatic_review(None, ob, hook.trigger.update(ob['globalgps'], 4))
            hook.teleport.assert_not_called()
            hook.policy = lambda deep=False: dict(episode_id='a', step_id=hook.active['index'],
                                                  pending_count=0, sha256='same')
            near = self.ob(5, 0)
            hook.automatic_review(None, near, hook.trigger.update(near['globalgps'], 4))
            hook.teleport.assert_not_called()
            with patch('builtins.print'):
                for index, x in [(8, 5), (12, 8)]:
                    hook.active['index'] = index
                    current = self.ob(x)
                    out, ended = hook.automatic_review(None, current,
                        hook.trigger.update(current['globalgps'], index))
                    self.assertFalse(ended)
                    self.assertEqual(out['globalgps'], [x+1.25, 0., 1.])
            self.assertEqual(len(hook.completed_interventions), 2)
            self.assertEqual(hook.task(None).step_count, 300)
            for p in root.glob('correction_*/memory_proof.json'):
                self.assertTrue(json.loads(p.read_text())['equal'])
            result = hook.finish_result({'metrics': {'m': [{'success': 0}]}})
            self.assertEqual(result['protocol'], PROTOCOL)
            self.assertEqual(sum(result['event_intervention_counts'].values()), 2)

    def test_stale_target_terminal_and_changed_memory_cannot_succeed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'a'; root.mkdir()
            hook = self.fixture(root); ob = self.ob()
            decision = hook.trigger.update(ob['globalgps'], 3)
            with self.assertRaisesRegex(RuntimeError, 'stale'):
                hook.automatic_review(None, ob, decision)
            hook.teleport.assert_not_called()
            task = hook.task(None); task.is_done = lambda: True
            self.assertTrue(hook.automatic_review(None, ob, decision)[1])
            hook.teleport.assert_not_called()
            task.is_done = lambda: False
            proofs = iter(['before', 'after'])
            hook.policy = lambda deep=False: dict(episode_id='a', step_id=4, pending_count=0,
                                                   sha256=next(proofs) if deep else 'same')
            with self.assertRaisesRegex(RuntimeError, 'policy memory'):
                hook.automatic_review(None, ob, hook.trigger.update(ob['globalgps'], 4))


class ComparisonTests(unittest.TestCase):
    def manifest(self, code='/snapshot'):
        return dict(protocol=PROTOCOL, seed=2, code_root=code, episode_ids=['a', 'b'],
                    arms={'baseline': {'mode': 'baseline', 'threshold_m': None},
                          'auto_route': {'mode': 'auto_route', 'threshold_m': .75}},
                    runtime_env={'VLN_ORACLE_MANIFEST': '/campaign/manifest.json',
                                 'VLN_DISTANCE_ARM': 'stale', 'HF_HUB_OFFLINE': '1'})

    def test_baseline_has_no_oracle_hook_and_same_ids_seeds_in_both_jobs(self):
        manifest = self.manifest()
        jobs = job_plan(Path('/campaign'), manifest, list(manifest['arms']), ['a', 'b'], 2, 3)
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(job['episode_ids'], ['a', 'b'])
            self.assertIn('--episode-ids', job['command'])
            self.assertEqual(job['command'][job['command'].index('--seed')+1], '2')
        base = job_environment(Path('/campaign'), manifest, jobs[0], {'VLN_DISTANCE_ARM': 'old'})
        self.assertFalse(any(k.startswith(('VLN_ORACLE_', 'VLN_DISTANCE_', 'VLN_BRANCH_')) for k in base))
        with patch.dict('os.environ', base, clear=True):
            evaluator = NS(); install(evaluator)
            self.assertFalse(hasattr(evaluator, '_distance_hook'))
        auto = job_environment(Path('/campaign'), manifest, jobs[1], {})
        self.assertEqual(auto['VLN_DISTANCE_ARM'], 'auto_route')
        with self.assertRaises(ValueError): inherited_results(manifest, ['/old'])

    def test_baseline_verifies_native_scores_without_fabricating_oracle_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign = Path(tmp); manifest = self.manifest()
            job = dict(arm='baseline', run_id='run', episode_ids=['a', 'b'])
            run = campaign/'runs/vlnverse/streamvln/results/run'; run.mkdir(parents=True)
            (run/'validation.json').write_text(json.dumps({'passed': True, 'episodes': 2}))
            (run/'result.json').write_text(json.dumps({'status': 'complete'}))
            (run/'episodes.jsonl').write_text('\n'.join(json.dumps({'episode_id': e}) for e in ['a', 'b']))
            self.assertEqual(len(verify_arm(campaign, manifest, job)), 2)
            self.assertFalse((campaign/'oracle_records').exists())
            (run/'episodes.jsonl').write_text(json.dumps({'episode_id': 'a'}))
            with self.assertRaises(RuntimeError): verify_arm(campaign, manifest, job)

    def test_partial_native_score_write_is_not_an_experiment_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign = Path(tmp); manifest = self.manifest(tmp)
            score = campaign/'benchmarks/vlnverse/upstream/logs/run/kujiale_result.json'
            score.parent.mkdir(parents=True); score.write_text('{')
            job = dict(arm='baseline', run_id='run', episode_ids=['a', 'b'])
            self.assertIsNone(native_progress(campaign, manifest, job)['official_scored'])
            score.write_text(json.dumps({'val_unseen': {'Count': 1}}))
            self.assertEqual(native_progress(campaign, manifest, job)['official_scored'], 1)


if __name__ == '__main__':
    unittest.main()
