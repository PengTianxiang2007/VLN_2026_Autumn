import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.watch_oracle_comparison import final_report


class ComparisonReportTests(unittest.TestCase):
    def fixture(self, root, missing=True, oracle_success=1):
        states = {}
        for arm in ('baseline', 'auto_branch'):
            d = root / arm
            d.mkdir()
            (d / 'episode_ids.json').write_text(json.dumps(['navigated', 'warmup_fall']))
            rows = [dict(episode_id=eid, scene='scene', episode_seed=i, run_seed=2,
                         SR=int(i == 0 and arm == 'auto_branch'), SPL=0, NE=2,
                         steps=1000 if i == 0 else 500, fail_reason='fall')
                    for i, eid in enumerate(['navigated', 'warmup_fall'])]
            (d / 'episodes.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
            validation = d / 'validation.json'
            validation.write_text(json.dumps(dict(passed=True, episodes=2,
                                                  metrics={'SR': sum(r['SR'] for r in rows) / 2})))
            states[arm] = {'validation': str(validation)}
        for eid, success, interventions in [('navigated', oracle_success, [{}]), ('warmup_fall', 0, [])]:
            if missing and eid == 'warmup_fall':
                continue
            d = root / 'auto_branch/oracle_records/auto_branch' / eid
            d.mkdir(parents=True)
            (d / 'result.json').write_text(json.dumps(dict(status='complete',
                metrics={'success': success}, interventions=interventions)))
        return states

    def test_native_scored_case_without_oracle_record_is_kept_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = final_report(root, self.fixture(root))
            self.assertEqual(report['completed_total'], 4)
            self.assertEqual(report['arms']['auto_branch']['successes'], 1)
            self.assertEqual(report['paired_wins'], 1)
            self.assertEqual(report['oracle_results_missing'], ['warmup_fall'])
            self.assertIsNone(report['interventions'])
            self.assertEqual(report['recorded_interventions'], 1)
            with (root / 'comparison.csv').open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]['oracle_result_status'], 'missing')
            self.assertEqual(rows[1]['interventions'], '')
            self.assertFalse((root / 'auto_branch/oracle_records/auto_branch/warmup_fall/result.json').exists())

    def test_complete_oracle_records_preserve_known_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = final_report(root, self.fixture(root, missing=False))
            self.assertEqual(report['interventions'], 1)
            self.assertTrue(report['intervention_counts_complete'])

    def test_existing_oracle_score_mismatch_still_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            states = self.fixture(root, oracle_success=0)
            with self.assertRaises(AssertionError):
                final_report(root, states)
            self.assertFalse((root / 'comparison.csv').exists())


if __name__ == '__main__':
    unittest.main()
