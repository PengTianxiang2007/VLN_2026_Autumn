"""Known geometric branch locations and causal integration boundaries; CPU only."""
import copy
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from core.oracle_auto_branch import (PROTOCOL, DEFAULTS, AutoBranchTrigger,
                                     ReferenceGeometry, validate_settings)
from core.oracle_distance_runtime import DistanceOracle
from scripts.run_oracle_distance import job_environment, job_plan, inherited_results


def straight_prefix():
    return [[i/10., 0.] for i in range(21)]


def feed(trigger, points, start=0):
    return [trigger.update(p, start+i) for i, p in enumerate(points)]


class BranchGeometryTests(unittest.TestCase):
    def test_same_reference_can_diverge_at_a_or_b_without_preselected_crossings(self):
        reference = [[0, 0], [3, 0], [3, 4], [8, 4]]
        prefix_a = [[i/10., 0] for i in range(31)]
        prefix_b = prefix_a + [[3, i/10.] for i in range(1, 41)]
        for prefix, wrong, anchor, landing, yaw in [
            (prefix_a, [[3+i/10., 0] for i in range(1, 11)], [3, 0], [3, 1.25], math.pi/2),
            (prefix_b, [[3, 4+i/10.] for i in range(1, 11)], [3, 4], [4.25, 4], 0.),
        ]:
            with self.subTest(anchor=anchor):
                # Poisoned static labels cannot influence this algorithm.
                t = AutoBranchTrigger({'reference_path': reference, 'targets': [{'position': [999, 999]}]})
                before = feed(t, prefix)
                self.assertTrue(all(r['target'] is None for r in before))
                after = feed(t, wrong, len(prefix))
                target = next(r['target'] for r in after if r['target'])
                self.assertLess(math.dist(target['branch_xy'], anchor), .06)
                self.assertLess(math.dist(target['target_xy'], landing), .06)
                self.assertAlmostEqual(target['target_yaw_rad'], yaw)

    def test_correct_at_a_then_diverge_at_b_uses_new_walked_history(self):
        t = AutoBranchTrigger({'reference_path': [[0, 0], [3, 0], [3, 4], [8, 4]]})
        before = feed(t, [[i/10., 0] for i in range(41)])
        first = next(r['target'] for r in before if r['target'])
        t.after_correction(first['target_xy'], 41, first)
        y = first['target_xy'][1]
        continued = [[3, y+(4-y)*i/30] for i in range(1, 31)]
        continued += [[3, 4+i/10.] for i in range(1, 11)]
        later = feed(t, continued, 42)
        second = next(r['target'] for r in later if r['target'])
        self.assertNotEqual(first['id'], second['id'])
        self.assertLess(math.dist(second['branch_xy'], [3, 4]), .06)
        self.assertLess(math.dist(second['target_xy'], [4.25, 4]), .06)
        self.assertEqual(second['target_yaw_rad'], 0.)
        self.assertGreater(second['branch_evidence']['action_interval'][0], 41)

    def test_known_departures_and_missed_turn(self):
        examples = [
            ('right_angle', [[0, 0], [10, 0]], straight_prefix()+[[2, i/10.] for i in range(1, 12)], [2, 0], [3.25, 0]),
            ('diagonal', [[0, 0], [10, 0]], straight_prefix()+[[2+i/10., i/10.] for i in range(1, 12)], [2, 0], [3.25, 0]),
            ('missed_turn', [[0, 0], [2, 0], [2, 5]], [[i/10., 0] for i in range(32)], [2, 0], [2, 1.25]),
            ('offset_prefix', [[0, 0], [10, 0]], [[i/10., .1] for i in range(21)]+[[2, .1+i/10.] for i in range(1, 12)], [2, 0], [3.25, 0]),
        ]
        for name, reference, positions, anchor, landing in examples:
            with self.subTest(name=name):
                decisions = feed(AutoBranchTrigger({'reference_path': reference}), positions)
                first = next(r for r in decisions if r['target'] is not None)
                self.assertLess(math.dist(first['target']['branch_xy'], anchor), .06)
                self.assertLess(math.dist(first['target']['target_xy'], landing), .06)
                self.assertLess(first['event']['branch']['fit_rmse_m'], .02)
                if name == 'missed_turn':
                    self.assertAlmostEqual(first['target']['target_yaw_rad'], math.pi/2)

    def test_parallel_wrong_path_and_queue_delay_cannot_move_anchor(self):
        t = AutoBranchTrigger({'reference_path': [[0, 0], [20, 0]]})
        rows = feed(t, straight_prefix()+[[2+i/10., i/10.] for i in range(1, 12)])
        first = next(r for r in rows if r['target'] is not None)
        later = feed(t, [[3.1+i/10., 1.1] for i in range(1, 71)], len(rows))[-1]
        self.assertEqual(first['event'], later['event'])
        self.assertEqual(first['target']['branch_xy'], later['target']['branch_xy'])
        self.assertEqual(first['target']['target_xy'], later['target']['target_xy'])
        self.assertGreater(later['matched_reference_arc_m'], 9.)
        self.assertLess(later['target']['branch_reference_arc_m'], 2.1)

    def test_turning_jitter_does_not_manufacture_motion_evidence(self):
        t = AutoBranchTrigger({'reference_path': [[0, 0], [10, 0]]})
        positions = [[0, 0]]+[[.005*math.sin(i), .005*math.cos(i)] for i in range(200)]
        decisions = feed(t, positions)
        self.assertEqual(len(t.history), 1)
        self.assertFalse(any(r['target'] for r in decisions))

    def test_branch_at_start_requires_motion_before_confirmation(self):
        t = AutoBranchTrigger({'reference_path': [[0, 0], [10, 0]]})
        rows = feed(t, [[0, i/10.] for i in range(11)])
        first = next(r for r in rows if r['target'] is not None)
        self.assertEqual(first['target']['branch_xy'], [0., 0.])
        self.assertEqual(first['target']['target_xy'], [1.25, 0.])
        self.assertGreaterEqual(first['event']['branch']['raw_motion_observations'], 3)

    def test_missing_shared_prefix_and_sparse_observations_fail_closed(self):
        t = AutoBranchTrigger({'reference_path': [[0, 0], [10, 0]]})
        rows = feed(t, [[i/10., 1.] for i in range(20)])
        self.assertTrue(all(r['target'] is None for r in rows))
        self.assertEqual(rows[-1]['branch_unresolved_reason'], 'no_shared_route_prefix_in_window')
        t = AutoBranchTrigger({'reference_path': [[0, 0], [10, 0]]})
        rows = feed(t, [[0, 0], [0, 1.]])
        self.assertIsNone(rows[-1]['target'])
        self.assertEqual(rows[-1]['branch_unresolved_reason'], 'insufficient_motion_observations')

    def test_loop_correspondence_keeps_the_later_reference_occurrence(self):
        reference = [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0], [4, 0], [4, -4]]
        positions = []
        for a, b in zip(reference[:5], reference[1:5]):
            positions += [[a[k]+(b[k]-a[k])*i/40 for k in (0, 1)] for i in range(40)]
        positions += [[i/10., 0] for i in range(21)]
        positions += [[2, -i/10.] for i in range(1, 12)]
        rows = feed(AutoBranchTrigger({'reference_path': reference}), positions)
        first = next(r for r in rows if r['target'] is not None)
        self.assertAlmostEqual(first['target']['branch_reference_arc_m'], 18., delta=.06)
        self.assertAlmostEqual(first['target']['reference_arc_m'], 19.25, delta=.06)

    def test_threshold_hysteresis_cancels_execution_without_moving_branch(self):
        t = AutoBranchTrigger({'reference_path': [[0, 0], [10, 0]]})
        rows = feed(t, straight_prefix()+[[2, i/10.] for i in range(1, 9)])
        original = rows[-1]['event']
        low = t.update([2, .7], 30)
        self.assertFalse(low['threshold_reached']); self.assertIsNone(low['target'])
        self.assertEqual(low['event'], original)
        self.assertEqual(t.update([2, .9], 31)['event'], original)
        self.assertIsNone(t.update([2, .2], 32)['event'])
        self.assertEqual(len(t.history), 1)

    def test_reference_resampling_does_not_change_branch_and_endpoint_is_logged(self):
        positions = straight_prefix()+[[2+i/10., i/10.] for i in range(1, 12)]
        references = ([[0, 0], [10, 0]], [[i/10., 0] for i in range(101)])
        anchors = []
        for reference in references:
            rows = feed(AutoBranchTrigger({'reference_path': reference}), positions)
            anchors.append(next(r['target']['branch_xy'] for r in rows if r['target']))
        self.assertLess(math.dist(*anchors), 1e-8)
        landing = ReferenceGeometry([[0, 0], [3, 0]]).landing(2.5, 1.25)
        self.assertTrue(landing['clamped_to_route_end'])
        self.assertEqual(landing['actual_offset_m'], .5)
        self.assertTrue(landing['near_goal_3m'])

    def test_prefix_causality_and_correction_reinitializes_with_actual_pose(self):
        positions = straight_prefix()+[[2, i/10.] for i in range(1, 9)]
        t = AutoBranchTrigger({'reference_path': [[0, 0], [20, 0]]})
        prefix = feed(t, positions); saved = copy.deepcopy(prefix)
        feed(t, [[3+i/10., 1.] for i in range(20)], len(prefix))
        self.assertEqual(prefix, saved)
        target = prefix[-1]['target']
        t.after_correction([3.27, .04], 80, target)
        self.assertIsNone(t.event)
        self.assertEqual(len(t.history), 1)
        self.assertEqual(t.history[0]['position'], [3.27, .04])
        self.assertEqual(t.history[0]['s'], 0.)
        self.assertAlmostEqual(t.progress, 3.27)

    def test_invalid_parameters_are_rejected(self):
        validate_settings(DEFAULTS)
        for key, value in [('shared_distance_m', .8), ('resample_m', 1.), ('max_fit_rmse_m', math.nan)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_settings(dict(DEFAULTS, **{key: value}))

    def test_detour_rejoin_ends_old_event_before_the_next_branch(self):
        reference = [[0, 0], [4, 0], [4, 6], [0, 6], [0, 12]]
        t = AutoBranchTrigger({'reference_path': reference})
        points = straight_prefix()+[[2, i/10.] for i in range(1, 61)]
        rows = feed(t, points)
        first = next(r['event'] for r in rows if r['target'])
        self.assertTrue(any(r['reference_relocalized_on_rejoin'] for r in rows))
        self.assertIsNone(rows[-1]['event'])
        next_points = [[2-i/10., 6] for i in range(1, 11)]+[[1, 6-i/10.] for i in range(1, 11)]
        later = feed(t, next_points, len(points))
        second = next(r['event'] for r in later if r['target'])
        self.assertNotEqual(first['target_id'], second['target_id'])
        self.assertAlmostEqual(second['branch']['reference_arc_m'], 13., delta=.08)


class RuntimeTests(unittest.TestCase):
    def fixture(self, root):
        hook = DistanceOracle.__new__(DistanceOracle)
        hook.cases = {'a': {'episode_id': 'a', 'reference_path': [[0, 0], [20, 0]]}}
        hook.manifest = {'protocol': PROTOCOL}
        hook.settings = {'mode': 'auto_branch', 'landing_offset_m': 1.25, 'branch': DEFAULTS}
        hook.threshold = .75; hook.arm = 'auto_branch'; hook.case_root = root; hook.root = root.parent
        hook.active = dict(episode_id='a', index=0, directory=root, observations=[], interventions=[], intervention=None)
        hook.trigger = AutoBranchTrigger(hook.cases['a'])
        hook.checkpoints = {}; hook.seen_events = set(); hook.completed_interventions = []
        hook.maximum_distance = 1.; hook.executed_actions = 0
        task = NS(is_done=lambda: False, step_count=200)
        hook.task = lambda _: task
        hook.policy = Mock(side_effect=lambda deep=False: dict(episode_id='a', step_id=hook.active['index'], pending_count=0, sha256='same'))
        def teleport(e, ob, target, path):
            task.step_count += 50
            return dict(ob, globalgps=[*target['target_xy'], 1.]), False
        hook.teleport = Mock(side_effect=teleport)
        return hook

    def test_unresolved_branch_does_not_request_policy_or_teleport(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'a'; root.mkdir(); hook = self.fixture(root)
            ob = dict(globalgps=[0, 1, 1], globalrotation=[1, 0, 0, 0])
            decision = hook.trigger.update(ob['globalgps'], 0)
            hook.automatic_review(None, ob, decision)
            hook.policy.assert_not_called(); hook.teleport.assert_not_called()
            skipped = json.loads((root/'skipped_triggers.jsonl').read_text())
            self.assertEqual(skipped['reason'], 'insufficient_motion_observations')

    def test_queue_delay_retains_anchor_and_teleport_starts_new_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'a'; root.mkdir(); hook = self.fixture(root)
            points = straight_prefix()+[[2+i/10., i/10.] for i in range(1, 9)]
            rows = feed(hook.trigger, points)
            hook.active['index'] = len(points)-1
            ob = dict(globalgps=[*points[-1], 1.], globalrotation=[1, 0, 0, 0])
            original = rows[-1]['target']['target_xy']
            hook.policy = Mock(return_value=dict(episode_id='a', step_id=hook.active['index'], pending_count=2))
            hook.automatic_review(None, ob, rows[-1]); hook.teleport.assert_not_called()
            decision = feed(hook.trigger, [[3+i/10., 1.] for i in range(40)], len(points))[-1]
            hook.active['index'] = len(points)+39
            hook.policy = lambda deep=False: dict(episode_id='a', step_id=hook.active['index'], pending_count=0, sha256='same')
            ob['globalgps'] = [6.9, 1., 1.]
            with patch('builtins.print'):
                out, ended = hook.automatic_review(None, ob, decision)
            self.assertFalse(ended); self.assertEqual(out['globalgps'][:2], original)
            self.assertEqual(len(hook.trigger.history), 1)
            self.assertEqual(hook.trigger.history[0]['s'], 0.)
            self.assertEqual(hook.task(None).step_count, 250)
            self.assertTrue(json.loads((root/'correction_001/memory_proof.json').read_text())['equal'])
            result = hook.finish_result({'metrics': {'m': [{'success': 0}]}})
            self.assertEqual(result['protocol'], PROTOCOL)

    def test_baseline_isolation_and_no_inherited_old_protocol(self):
        manifest = dict(protocol=PROTOCOL, seed=2, code_root='/snapshot', episode_ids=['a'],
                        arms={'baseline': {'mode': 'baseline', 'threshold_m': None},
                              'auto_branch': {'mode': 'auto_branch', 'threshold_m': .75}},
                        runtime_env={'VLN_ORACLE_MANIFEST': '/snapshot/manifest.json'})
        jobs = job_plan(Path('/campaign'), manifest, list(manifest['arms']), ['a'], 2, 3)
        self.assertEqual([j['episode_ids'] for j in jobs], [['a'], ['a']])
        baseline = job_environment(Path('/campaign'), manifest, jobs[0], {'VLN_DISTANCE_ARM': 'old'})
        self.assertNotIn('VLN_DISTANCE_ARM', baseline); self.assertNotIn('VLN_ORACLE_MANIFEST', baseline)
        auto = job_environment(Path('/campaign'), manifest, jobs[1], {})
        self.assertEqual(auto['VLN_DISTANCE_ARM'], 'auto_branch')
        with self.assertRaises(ValueError): inherited_results(manifest, ['/old'])


if __name__ == '__main__':
    unittest.main()
