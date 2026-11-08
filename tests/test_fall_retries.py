import unittest
import hashlib
import json
from pathlib import Path
import tempfile

from core.fall_replay import FallReplay
from scripts.test_fall_retries import rollback_point, admission_failure, campaign_worker_pids
from unittest.mock import patch


def frames(n):
    return [dict(terminal=False, action_index=i, action={'move_by_discrete': [1]})
            for i in range(n)] + [dict(terminal=True, action_index=n, action={})]


class FallRetryTests(unittest.TestCase):
    def test_gpu_lock_contention_is_retryable_without_masking_other_errors(self):
        failure = dict(kind='unclassified', phase='launcher', log_tail='fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)\nBlockingIOError: [Errno 11] Resource temporarily unavailable')
        self.assertEqual(admission_failure(failure)['kind'], 'gpu_admission')
        for other in [dict(failure, phase='simulator'), dict(failure, log_tail='ValueError: wrong episode')]:
            self.assertEqual(admission_failure(other)['kind'], 'unclassified')

    def test_resource_accounting_combines_both_arms_and_unpublished_new_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'status_reset.json').write_text(json.dumps(dict(workers=[dict(pid=1)])))
            (root/'status_replay.json').write_text(json.dumps(dict(workers=[dict(pid=2)])))
            (root/'admitted_workers.json').write_text(json.dumps(dict(pids=[1, 2, 3, 4])))
            with patch('scripts.test_fall_retries.process_alive', side_effect=lambda pid: pid != 4):
                self.assertEqual(campaign_worker_pids(root), {1, 2, 3})

    def test_exactly_ten_executed_actions_between_checkpoint_and_fall(self):
        for n in (10, 13, 123, 313):
            actions, index = rollback_point(frames(n))
            self.assertEqual(len(actions[index:]), 10)
            self.assertEqual(len(actions[:index]), n - 10)

    def test_warmup_and_short_prefix_falls_have_no_ten_action_checkpoint(self):
        for n in (0, 1, 9):
            actions, index = rollback_point(frames(n))
            self.assertIsNone(index)

    def test_rejects_incomplete_or_noncontiguous_evidence(self):
        missing = frames(13)
        del missing[5]
        for invalid in (missing, frames(13)[:-1], frames(13) + frames(1)):
            with self.assertRaises(ValueError):
                rollback_point(invalid)

    def test_stop_is_not_treated_as_a_pre_fall_navigation_action(self):
        data = frames(13)
        data[5]['action'] = {'stop': []}
        with self.assertRaises(ValueError):
            rollback_point(data)


class ReplayHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        data = frames(13)
        for i, row in enumerate(data):
            row['position'] = [i * 0.1, 0, 1]
        source = self.root / 'steps.jsonl'
        source.write_text(''.join(json.dumps(r) + '\n' for r in data))
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps(dict(cases=[dict(episode_id='test', rollback_eligible=True,
            rollback_action_index=3, original_actions=[1] * 13, source_steps=str(source),
            source_steps_sha256=hashlib.sha256(source.read_bytes()).hexdigest())])))
        self.harness = FallReplay(manifest, self.root / 'records')

    def obs(self, index):
        return dict(globalgps=[index * 0.1, 0, 1], globalrotation=[1, 0, 0, 0])

    def metrics(self, reason='fall'):
        return dict(fail_reason=reason, reproduction_run_seed=2, reproduction_episode_seed=1, success=0, NE=5)

    def test_exact_prefix_override_and_native_handover_with_mismatch_accounting(self):
        for index in range(3):
            self.assertEqual(self.harness.choose('test', self.obs(index), {'move_by_discrete': [2]}),
                             {'move_by_discrete': [1]})
        proposal = {'move_by_discrete': [3]}
        self.assertIs(self.harness.choose('test', self.obs(3), proposal), proposal)
        result = self.harness.finish('test', self.obs(4), self.metrics())
        self.assertTrue(result['checkpoint_reached'])
        self.assertEqual(result['proposed_action_mismatches_in_prefix'], 3)
        self.assertEqual(result['actions_after_checkpoint'], 1)
        self.assertEqual(result['outcome'], 'fall_after_checkpoint')
        self.assertTrue(result['checkpoint']['within_0_5m'])
        self.assertTrue(result['fall_within_10_actions_after_checkpoint'])

    def test_prefix_fall_is_not_a_successful_rollback(self):
        self.harness.choose('test', self.obs(0), {'move_by_discrete': [1]})
        result = self.harness.finish('test', self.obs(1), self.metrics())
        self.assertFalse(result['checkpoint_reached'])
        self.assertEqual(result['outcome'], 'fall_before_checkpoint')
        self.assertIsNone(result['fall_within_10_actions_after_checkpoint'])

    def test_warmup_fall_retains_a_terminal_record_without_any_action(self):
        result = self.harness.finish('test', self.obs(0), self.metrics())
        self.assertEqual(result['actions_executed'], 0)
        self.assertEqual(result['outcome'], 'fall_before_checkpoint')

    def test_deviated_checkpoint_remains_visible_in_result(self):
        for index in range(4):
            observation = self.obs(index)
            observation['globalgps'][1] = 2
            self.harness.choose('test', observation, {'move_by_discrete': [1]})
        result = self.harness.finish('test', self.obs(4), self.metrics('not_reach_goal'))
        self.assertEqual(result['checkpoint']['xy_error_m'], 2)
        self.assertFalse(result['checkpoint']['within_0_5m'])
        self.assertFalse(result['exact_original_state_restored'])

    def test_changed_original_evidence_fails_closed(self):
        (self.root / 'steps.jsonl').write_text('tampered')
        with self.assertRaises(ValueError):
            self.harness.choose('test', self.obs(0), {'move_by_discrete': [1]})
