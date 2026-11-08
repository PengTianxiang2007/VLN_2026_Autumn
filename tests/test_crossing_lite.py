"""Critical input isolation, temporal boundaries, sampling and score contracts."""
import json
from pathlib import Path
import tempfile
import unittest

from core.crossing_lite import request, select_cases, sha, validate, windows


class CrossingLiteTest(unittest.TestCase):
    def observations(self):
        return [dict(frame=i, eligible_for_inference=i < 4, terminal=i == 4,
                     rgb_reused=i == 4, rgb='image.webp', rgb_sha256='abc',
                     instruction='SECRET INSTRUCTION', position=[8, 9, 10],
                     newly_executed_actions=['SECRET ACTION']) for i in range(5)]

    def test_exact_windows_and_terminal(self):
        rows = list(windows(self.observations()))
        self.assertEqual([t for t, _ in rows], [0, 1, 2, 3])
        self.assertEqual([[im['frame'] for im in ims] for _, ims in rows], [[0], [0, 1], [0, 1, 2], [1, 2, 3]])
        self.assertNotIn('SECRET', json.dumps(rows))

    def test_no_stale_substitution(self):
        rows = self.observations()
        rows[1]['eligible_for_inference'] = False
        with self.assertRaises(ValueError):
            list(windows(rows))

    def test_actual_wire_is_rgb_only(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'image.webp'
            path.write_bytes(b'RGB bytes used for isolated serialization test')
            ims = [{'frame': i, 'rgb': path.name, 'rgb_sha256': sha(path)} for i in range(3)]
            wire = request('FROZEN PROMPT', ims, temp, 'model', 123)
            self.assertEqual([x['text'] for x in wire['messages'][1]['content'] if x['type'] == 'text'],
                             ['Previous observation t-2:', 'Previous observation t-1:', 'Current observation t:', 'Score the CURRENT local route-choice situation.'])
            self.assertEqual(len([x for x in wire['messages'][1]['content'] if x['type'] == 'image_url']), 3)
            self.assertFalse(wire['chat_template_kwargs']['enable_thinking'])
            self.assertEqual(wire['response_format']['json_schema']['schema']['properties']['score']['enum'], [1, 2, 3, 4, 5])
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                request('FROZEN PROMPT', ims, temp, 'model', 123)

    def test_reject_wrong_history(self):
        for ids in ([0, 2], [1, 0], [0, 1, 2, 3], [2]):
            with self.assertRaises(ValueError):
                request('prompt', [dict(frame=i, rgb_sha256='abc') for i in ids], '.', 'model', 1, False)

    def test_score_validation(self):
        for i in range(1, 6):
            self.assertEqual(validate({'score': i, 'reason': '视觉依据'})['score'], i)
        for value in (0, 6, True, 2.0, '3'):
            with self.assertRaises(ValueError):
                validate({'score': value, 'reason': '依据'})
        with self.assertRaises(ValueError):
            validate({'score': 3, 'reason': '', 'extra': True})

    def test_sampling_fixed_counts_scene_coverage(self):
        rows = [dict(episode_id=f'{g}_{s}_{n}', group=g, scene=str(s))
                for g in ('failure', 'success') for s in range(10) for n in range(3)]
        a = select_cases(rows, {'failure': 10, 'success': 20}, 20261107)
        self.assertEqual(a, select_cases(list(reversed(rows)), {'failure': 10, 'success': 20}, 20261107))
        self.assertEqual(len({r['episode_id'] for r in a}), 30)
        for group, count in [('failure', 10), ('success', 20)]:
            part = [r for r in a if r['group'] == group]
            self.assertEqual(len(part), count)
            self.assertEqual(len({r['scene'] for r in part}), 10)


if __name__ == '__main__':
    unittest.main()
