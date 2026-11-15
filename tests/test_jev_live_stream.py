"""CPU-only contract for causal JEV scoring during live navigation."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from core.jev_live_stream import JevLiveReview


ROOT = Path(__file__).resolve().parents[1]


def fake_run_task(task):
    probability = ((task['frame'] % 9) + 1) / 10
    return {
        'phase': 'complete',
        'episode_id': task['episode_id'],
        'scene': task['scene'],
        'group': task['group'],
        'frame': task['frame'],
        'image_frames': [row['frame'] for row in task['images']],
        'answer': {
            'probability_yes': probability,
            'probability_no': 1 - probability,
        },
        'question_version': 'v004',
        'latency_seconds': 0.0,
        'transport': {'attempts': 1, 'statuses': [200]},
    }


class JevLiveReviewTest(unittest.TestCase):
    def setUp(self):
        self.previous_key = os.environ.get('JEV_API_KEY')
        os.environ['JEV_API_KEY'] = 'cpu-test-key'

    def tearDown(self):
        if self.previous_key is None:
            os.environ.pop('JEV_API_KEY', None)
        else:
            os.environ['JEV_API_KEY'] = self.previous_key

    def test_live_stream_is_causal_and_bounded(self):
        checks = ROOT / 'outputs/checks'
        checks.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=checks) as directory:
            settings = {
                'output_dir': directory,
                'seed': 0,
                'window_n': 11,
                'max_delay_steps': 5,
                'max_in_flight': 5,
                'attempts': 5,
                'timeout': 120,
            }
            review = JevLiveReview(settings, 'live_test', directory)
            path_key = 'kujiale_0272_0_0'
            with patch('core.jev_live_stream.run_jev_task', side_effect=fake_run_task):
                review.start(path_key)
                for step in range(15):
                    review.observe(
                        path_key,
                        {
                            'rgb': np.full((480, 640, 3), step, dtype=np.uint8),
                            'globalgps': [float(step), 0.0, 0.0],
                        },
                        {'move_by_discrete': [1]},
                    )
                review.finish(
                    path_key,
                    {
                        'success': 0.0,
                        'spl': 0.0,
                        'NE': 1.0,
                        'osr': 0.0,
                        'TL': 1.0,
                        'steps': 15,
                        'fail_reason': 'test',
                    },
                )
            review.close()
            produced = list(Path(directory).glob('seed_0/**/episode.json'))
            self.assertEqual(len(produced), 1)
            data = json.loads(produced[0].read_text())
            self.assertEqual(len(data['calls']), 15)
            self.assertEqual(len(data['streaming']['raw']), 15)
            self.assertTrue(data['streaming']['prefix_invariant'])
            self.assertLessEqual(
                data['max_unresolved_step_lag'],
                5,
            )


if __name__ == '__main__':
    unittest.main()
