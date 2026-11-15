"""CPU contracts for the JEV local-node scoring interface."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from core.jev_node import (
    DIRECTION_KEYS,
    build_compact_fallback_noul_request,
    build_near_fallback_noul_request,
    build_noul_request,
    build_request,
    call_api,
    question_translation,
    noul_question_translation,
    near_fallback_question_translation,
    compact_fallback_question_translation,
    request_digest,
    request_without_images,
    validate_noul_response,
    validate_response,
)


def response(score=2.0):
    probabilities = ['0', '0.2', '0.6', '0.2', '0']
    return {
        'model': 'jev-1.14.0',
        'answers': {
            'node_score': {
                'type': 'score',
                'score': score,
                'confidence': 0.8,
                'legend': {str(i): str(i) for i in range(5)},
                'probabilities': {
                    str(i): float(value) for i, value in enumerate(probabilities)
                },
            },
            **{
                key: {'type': 'noul', 'noul': 0.7}
                for key in DIRECTION_KEYS
            },
        },
        'usage': {'input_tokens': 100, 'output_tokens': 10},
    }


class JevNodeTest(unittest.TestCase):
    def fixture(self, directory):
        images = []
        for frame in range(3):
            path = Path(directory) / ('F%04d.png' % frame)
            Image.new('RGB', (320, 240), (frame, frame, frame)).save(path)
            images.append({
                'frame': frame,
                'rgb': path.name,
                'rgb_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        return images

    def test_request_contains_typed_score_and_all_directions(self):
        with tempfile.TemporaryDirectory() as directory:
            images = self.fixture(directory)
            request, audit = build_request(images, directory)
            self.assertEqual(request['model'], 'jev-1.14.0')
            self.assertEqual(len(request['assets']), 3)
            self.assertEqual(set(request['questions']), {
                'node_score', *DIRECTION_KEYS
            })
            self.assertEqual(
                request['questions']['node_score']['type'], 'score'
            )
            self.assertEqual(
                len(request['questions']['node_score']['criteria']), 5
            )
            self.assertTrue(all(
                request['questions'][key]['type'] == 'noul'
                for key in DIRECTION_KEYS
            ))
            self.assertEqual([row['frame'] for row in audit], [0, 1, 2])
            self.assertTrue(all(
                row['prepared_format'] == 'png' for row in audit
            ))
            sanitized = request_without_images(request)
            self.assertNotIn(
                'data_base64',
                json.dumps(sanitized),
            )
            self.assertEqual(len(request_digest(request)), 64)

    def test_changed_source_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            images = self.fixture(directory)
            (Path(directory) / images[0]['rgb']).write_bytes(b'changed')
            with self.assertRaises(ValueError):
                build_request(images, directory)

    def test_response_is_mapped_to_existing_five_point_scale(self):
        interpretation = validate_response(response())
        self.assertEqual(interpretation['score'], 3)
        self.assertEqual(interpretation['score_continuous_1_5'], 3.0)
        self.assertEqual(
            set(interpretation['directional_probabilities']),
            set(DIRECTION_KEYS),
        )

    def test_invalid_probability_and_score_mismatch_are_rejected(self):
        value = response()
        value['answers']['left_route']['noul'] = 1.1
        with self.assertRaises(ValueError):
            validate_response(value)
        value = response()
        value['answers']['node_score']['probabilities']['2'] = 0.9
        with self.assertRaises(ValueError):
            validate_response(value)

    def test_complete_chinese_translation_preserves_question_shape(self):
        translated = question_translation()
        self.assertEqual(
            set(translated['questions']), {'node_score', *DIRECTION_KEYS}
        )
        self.assertEqual(
            len(translated['questions']['node_score']['criteria']), 5
        )

    def test_noul_variant_returns_yes_probability_only(self):
        with tempfile.TemporaryDirectory() as directory:
            images = self.fixture(directory)
            request, _ = build_noul_request(images, directory)
        self.assertEqual(
            request['questions']['fallback_point']['type'], 'noul'
        )
        raw = {
            'model': 'jev-1.14.0',
            'answers': {
                'fallback_point': {'type': 'noul', 'noul': 0.73},
            },
            'usage': {'input_tokens': 100, 'output_tokens': 5},
        }
        probability = validate_noul_response(raw)
        self.assertAlmostEqual(probability['probability_yes'], 0.73)
        self.assertAlmostEqual(probability['probability_no'], 0.27)
        translated = noul_question_translation()
        self.assertIn('fallback_point', translated['questions'])

    def test_near_fallback_variant_is_self_contained(self):
        with tempfile.TemporaryDirectory() as directory:
            images = self.fixture(directory)
            request, _ = build_near_fallback_noul_request(images, directory)
            translated = near_fallback_question_translation()
        serialized = json.dumps(request, ensure_ascii=False)
        self.assertNotRegex(serialized, r'\bv1\b|original v1|最初 v1')
        self.assertIn('RULE 1: STRICT LOCAL-DISTANCE LIMIT', serialized)
        self.assertIn('5 action steps', serialized)
        self.assertIn('7 action steps', serialized)
        self.assertIn('规则一：严格的局部距离限制', json.dumps(
            translated, ensure_ascii=False
        ))

    def test_compact_fallback_variant_is_self_contained(self):
        with tempfile.TemporaryDirectory() as directory:
            images = self.fixture(directory)
            request, _ = build_compact_fallback_noul_request(images, directory)
            translated = compact_fallback_question_translation()
        serialized = json.dumps(request, ensure_ascii=False)
        self.assertNotRegex(serialized, r'\bv1\b|original v1|最初 v1')
        self.assertIn('5 future action steps', serialized)
        self.assertIn('at most 7 steps', serialized)
        self.assertIn('回退点是指', json.dumps(translated, ensure_ascii=False))

    def test_transport_retries_transient_status(self):
        first = type('Process', (), {
            'stdout': '__JEV_HTTP_STATUS__:000',
            'stderr': 'connection reset',
        })()
        second = type('Process', (), {
            'stdout': json.dumps(response()) + '__JEV_HTTP_STATUS__:200',
            'stderr': '',
        })()
        with tempfile.TemporaryDirectory() as directory:
            with patch('core.jev_node.subprocess.run', side_effect=[first, second]), patch(
                'core.jev_node.time.sleep'
            ) as sleep:
                raw, latency, transport = call_api(
                    'https://api.site/v1/systemone',
                    'test-key',
                    {'request': 'fixture'},
                    10,
                    Path(directory) / 'request.json',
                    attempts=3,
                )
        self.assertEqual(raw['model'], 'jev-1.14.0')
        self.assertEqual(transport, {'attempts': 2, 'statuses': [0, 200]})
        self.assertGreaterEqual(latency, 0)
        sleep.assert_called_once_with(2)


if __name__ == '__main__':
    unittest.main()
