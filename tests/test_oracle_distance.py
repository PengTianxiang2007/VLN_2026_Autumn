"""CPU regression tests for geometric triggers and live intervention boundaries."""
import copy
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import numpy as np

from core.oracle_distance import DistanceTrigger, landing_target, project_reference, build_cohort
from core.oracle_distance_runtime import DistanceOracle
from core.oracle_checkpoint_pair import CheckpointPair
from scripts.prepare_oracle_distance import patch_runtime, validate_config
from scripts.run_oracle_distance import job_plan, load_campaign, wait_for_resources, idle_pair


def example_case():
    reference = [[0, 0, 0], [20, 0, 0]]
    events = [{'id': 'a', 'frame': 10, 'position': [3, 0, 1]},
              {'id': 'b', 'frame': 30, 'position': [10, 0, 1]}]
    return {'episode_id': 'case', 'reference_path': reference,
            'targets': [landing_target(e, reference) for e in events]}


class GeometryTests(unittest.TestCase):
    def test_projection_in_segment_with_height_and_duplicates(self):
        result = project_reference([5, 2, 100], [[0, 0], [0, 0], [10, 0]])
        self.assertEqual(result, {'distance_m': 2., 'point': [5., 0.], 'arc_m': 5.})
        self.assertAlmostEqual(project_reference([13, 4], [[0, 0], [10, 0]])['distance_m'], 5.)
        self.assertAlmostEqual(project_reference([3, 4], [[0, 0]])['distance_m'], 5.)
        with self.assertRaises(ValueError):
            project_reference([math.nan, 0], [[0, 0]])

    def test_landing_follows_polyline_turn_not_straight_extrapolation(self):
        event = {'id': 'a', 'frame': 0, 'position': [.8, 0, 9]}
        target = landing_target(event, [[0, 0], [1, 0], [1, 2]], .75)
        self.assertAlmostEqual(target['target_xy'][0], 1.)
        self.assertAlmostEqual(target['target_xy'][1], .55)
        self.assertAlmostEqual(target['target_yaw_rad'], math.pi / 2)
        corner = landing_target(event, [[0, 0], [1, 0], [1, 2]], .2)
        self.assertAlmostEqual(corner['target_yaw_rad'], math.pi / 2)

    def test_threshold_equality_queue_independent_and_fixed_excursion_target(self):
        trigger = DistanceTrigger(example_case(), 3., .75)
        trigger.update([3, 0], 0)
        self.assertFalse(trigger.update([3, .749], 1)['threshold_reached'])
        onset = trigger.update([3, .75], 2)
        self.assertEqual(onset['event']['target_id'], 'a')
        self.assertFalse(onset['threshold_reached'])
        # Moving near b while still away from the route must not change this event.
        decision = trigger.update([10, 3], 99)
        self.assertTrue(decision['threshold_reached'])
        self.assertEqual(decision['event']['target_id'], 'a')
        self.assertEqual(decision['event']['onset_action_index'], 2)
        trigger.update([10, 0], 100)
        self.assertEqual(trigger.update([10, 3], 101)['event']['target_id'], 'b')

    def test_cohort_preserves_two_events_on_one_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'inputs').mkdir(); (root / 'evaluation').mkdir()
            (root / 'inputs/episodes.jsonl').write_text(json.dumps({'episode_id': 'case', 'seed': 2, 'instruction': 'Walk.'})+'\n')
            (root / 'evaluation/episodes.jsonl').write_text(json.dumps({'episode_id': 'case', 'scene': 'room', 'trajectory': 'trajectory.json'})+'\n')
            events = [{'episode_id': 'case', 'type': 'wrong_choice', 'id': str(i), 'frame': i,
                       'position': [i, 0, 1]} for i in (0, 1)]
            (root / 'evaluation/events.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
            (root / 'trajectory.json').write_text(json.dumps({'reference_path': [[0, 0], [10, 0]],
                'frames': [{'frame': i, 'position': [i, i, 1]} for i in range(4)]}))
            cohort = build_cohort(root)
            self.assertEqual((cohort['episodes'], cohort['events']), (1, 2))
            self.assertEqual(len(cohort['cases'][0]['targets']), 2)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        quiet = patch('builtins.print')
        quiet.start()
        self.addCleanup(quiet.stop)

    def hook(self, root, mode='route'):
        hook = object.__new__(DistanceOracle)
        case = example_case()
        hook.cases = {'case': case}
        hook.manifest = {'onset_m': .75, 'checkpoint_capture_radius_m': 1.}
        hook.settings = {'mode': mode}
        hook.threshold = 1.5
        hook.arm = 'short' if mode == 'route' else 'checkpoint'
        hook.case_root = root
        hook.active = {'episode_id': 'case', 'index': 4, 'directory': root,
                       'interventions': [], 'intervention': None, 'observations': []}
        hook.trigger = DistanceTrigger(case, 1.5, .75)
        hook.checkpoints = {}; hook.snapshots = {}; hook.event = None
        hook.seen_events = set(); hook.completed_interventions = []
        hook.task = lambda e: NS(is_done=lambda: False, step_count=200)
        hook.policy = lambda deep=False: {'episode_id': 'case', 'step_id': hook.active['index'],
                                         'pending_count': 0, 'sha256': 'same'}
        hook.teleport = lambda e, ob, target, path: (dict(ob, globalgps=[*target['target_xy'], 1.]), False)
        return hook

    def observation(self, position=(3., 1.5, 1.)):
        return {'globalgps': list(position), 'globalrotation': [1., 0., 0., 0.],
                'rgb': np.zeros((4, 4, 3), dtype=np.uint8)}

    def test_queue_wait_rechecks_distance_and_repeated_corrections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); hook = self.hook(root); ob = self.observation()
            hook.policy = lambda deep=False: {'episode_id': 'case', 'step_id': 4, 'pending_count': 2}
            decision = hook.trigger.update(ob['globalgps'], 4)
            hook.automatic_review(None, ob, decision)
            self.assertEqual(list(root.iterdir()), [])
            hook.policy = lambda deep=False: {'episode_id': 'case', 'step_id': hook.active['index'], 'pending_count': 0, 'sha256': 'same'}
            # A transient excursion resolved while the queue drained: no stale teleport.
            near = self.observation((3., 0., 1.))
            hook.automatic_review(None, near, hook.trigger.update(near['globalgps'], 5))
            self.assertEqual(hook.completed_interventions, [])
            for i in (8, 12):
                hook.active['index'] = i
                corrected, ended = hook.automatic_review(None, ob, hook.trigger.update(ob['globalgps'], i))
                self.assertFalse(ended)
                self.assertEqual(corrected['globalgps'], [3.75, 0., 1.])
            self.assertEqual(len(hook.completed_interventions), 2)
            self.assertEqual(len(list(root.glob('correction_*/memory_proof.json'))), 2)
            self.assertFalse((root / 'pending.json').exists())

    def test_terminal_cannot_trigger_and_memory_mutation_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            hook = self.hook(Path(tmp)); ob = self.observation()
            decision = hook.trigger.update(ob['globalgps'], 4)
            hook.task = lambda e: NS(is_done=lambda: True, step_count=200)
            self.assertTrue(hook.automatic_review(None, ob, decision)[1])
            self.assertEqual(hook.completed_interventions, [])
            hook.task = lambda e: NS(is_done=lambda: False, step_count=200)
            calls = []
            def policy(deep=False):
                if deep: calls.append(True)
                return {'episode_id': 'case', 'step_id': 4, 'pending_count': 0, 'sha256': str(len(calls))}
            hook.policy = policy
            with self.assertRaisesRegex(RuntimeError, 'policy memory'):
                hook.automatic_review(None, ob, decision)

    def test_checkpoint_requires_actual_saved_state_and_returns_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); hook = self.hook(root, 'checkpoint'); ob = self.observation()
            decision = hook.trigger.update(ob['globalgps'], 4)
            hook.automatic_review(None, ob, decision)
            self.assertEqual(hook.completed_interventions, [])
            self.assertTrue((root / 'skipped_triggers.jsonl').exists())
            # Capture only an actually visited point with empty policy queue.
            near = self.observation((3., 0., 1.))
            def capture(e, image, name, response):
                self.assertEqual(image['globalgps'], near['globalgps'])
                hook.snapshots[name] = root / (name + '.pkl')
            hook.capture = capture
            hook.automatic_review(None, near, hook.trigger.update(near['globalgps'], 5))
            self.assertIn('a', hook.checkpoints)
            with patch.object(CheckpointPair, 'restore', return_value=(near, False)) as restore:
                hook.automatic_review(None, ob, hook.trigger.update(ob['globalgps'], 8))
                hook.automatic_review(None, ob, hook.trigger.update(ob['globalgps'], 12))
                self.assertEqual(restore.call_count, 1)
            self.assertEqual(hook.completed_interventions[0]['memory_rule'], 'restore_checkpoint')


class PreparationTests(unittest.TestCase):
    def test_auto_gpu_does_not_share_and_can_use_one_idle_card(self):
        cards = '0, gpu0, 0, 48000, 0\n1, gpu1, 0, 48000, 0\n2, gpu2, 2000, 46000, 0\n3, gpu3, 0, 48000, 0\n'
        with patch('scripts.run_oracle_distance.subprocess.check_output', side_effect=[cards, 'gpu0, 99\ngpu1, 100\n']):
            self.assertEqual(idle_pair(2, 3), (3, 3))
        with patch('scripts.run_oracle_distance.subprocess.check_output', side_effect=[cards, 'gpu0, 99\ngpu1, 100\ngpu3, 102\n']):
            with self.assertRaisesRegex(RuntimeError, 'No idle GPU'):
                idle_pair(2, 3)

    def test_busy_gpu_waits_before_launch_and_zero_budget_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); state = {'simulation_started': False}
            with patch('scripts.run_oracle_distance.admission', side_effect=[RuntimeError('GPU occupied'), [{'idle': True}]]), patch('scripts.run_oracle_distance.time.sleep') as sleep:
                self.assertEqual(wait_for_resources(root, state, 2, 3, 60), [{'idle': True}])
                sleep.assert_called_once()
                self.assertFalse(json.loads((root / 'status.json').read_text())['simulation_started'])
            with patch('scripts.run_oracle_distance.admission', side_effect=RuntimeError('GPU occupied')):
                with self.assertRaisesRegex(RuntimeError, 'waiting expired'):
                    wait_for_resources(root, state, 2, 3, 0)

    def test_real_source_patch_anchors_and_original_launcher_preserved(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('benchmarks/vlnverse/runner/service.py', 'benchmarks/vlnverse/runner/run_full.py',
                     'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py'):
            source = (root / name).read_text()
            changed = patch_runtime(name, source)
            if name.endswith('run_full.py'):
                self.assertEqual(source, changed)
                continue
            self.assertNotEqual(source, changed)
            with self.assertRaises(ValueError):
                patch_runtime(name, changed)

    def test_config_and_job_scopes(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / 'experiments/oracle_recovery/distance_v001/config.json').read_text())
        validate_config(config)
        bad = copy.deepcopy(config); bad['thresholds_m']['early'] = math.nan
        with self.assertRaises(ValueError): validate_config(bad)
        manifest = {'arms': {'early': {'threshold_m': .75}}, 'episode_ids': ['case'], 'seed': 2, 'code_root': '/snapshot'}
        jobs = job_plan(Path('/campaign'), manifest, ['early'], ['case'], 1, 2)
        self.assertEqual(len(jobs), 1)
        self.assertIn('--episode-ids', jobs[0]['command'])
        self.assertIn('physical', jobs[0]['command'])
        with self.assertRaises(ValueError): job_plan(Path('/campaign'), manifest, ['early'], ['unknown'], 1, 2)
        with self.assertRaises(ValueError): job_plan(Path('/campaign'), manifest, ['early', 'early'], ['case'], 1, 2)

    def test_mutated_manifest_is_rejected_before_source_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'seal.json').write_text(json.dumps({'manifest_sha256': 'wrong'}))
            (root / 'manifest.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'manifest changed'):
                load_campaign(root)


if __name__ == '__main__':
    unittest.main()
