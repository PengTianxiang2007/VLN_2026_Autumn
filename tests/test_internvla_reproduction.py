import importlib.util
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('n1_reproduction', ROOT / 'scripts/reproduce_internvla_n1_vlnverse.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
download_spec = importlib.util.spec_from_file_location('n1_download', ROOT / 'scripts/prepare_internvla_n1.py')
download = importlib.util.module_from_spec(download_spec)
download_spec.loader.exec_module(download)
compat_spec = importlib.util.spec_from_file_location('n1_compat', ROOT / 'backbone/internvla_n1/checkpoint_compatibility.py')
compat = importlib.util.module_from_spec(compat_spec)
compat_spec.loader.exec_module(compat)


class Response(io.BytesIO):
    def __init__(self, body, start):
        super().__init__(body)
        self.status = 206 if start else 200
        self.headers = {'Content-Range': f'bytes {start}-{start+len(body)-1}/6'}


class N1ReproductionTests(unittest.TestCase):
    def test_only_exact_unused_mask_tokens_are_allowed(self):
        self.assertFalse(any(compat.loading_errors({'unexpected_keys': list(compat.UNUSED_MASK_TOKENS)}).values()))
        self.assertTrue(any(compat.loading_errors({'missing_keys': ['model.embed_tokens.weight']}).values()))
        self.assertTrue(any(compat.loading_errors({'unexpected_keys': ['model.other.mask_token']}).values()))

    def test_range_validation_rejects_wrong_offset_or_total(self):
        self.assertTrue(download.valid_range('Content-Range: bytes 4-9/10\r\n', '206', 4, 10, 9, 3))
        self.assertFalse(download.valid_range('Content-Range: bytes 0-9/10\r\n', '206', 4, 10, 9, 3))
        self.assertFalse(download.valid_range('Content-Range: bytes 4-9/11\r\n', '206', 4, 10, 9, 3))
        self.assertFalse(download.valid_range('Content-Range: bytes 4-9/10\r\n', '200', 4, 10, 9, 3))
        self.assertFalse(download.valid_range('Content-Range: bytes 4-9/10\r\n', '206', 4, 10, 9, 7))

    def test_busy_gpu_is_never_selected(self):
        self.assertIsNone(runner.placement({0: {'free': 48000, 'util': 95}}, set()))

    def test_reserved_gpu_is_never_selected(self):
        self.assertIsNone(runner.placement({0: {'free': 48000, 'util': 0}}, {0}))

    def test_colocated_requires_headroom(self):
        self.assertIsNone(runner.placement({0: {'free': 41999, 'util': 0}}, set()))
        self.assertEqual(runner.placement({0: {'free': 45000, 'util': 0}}, set()), (0, 0))

    def test_split_placement_keeps_simulator_headroom(self):
        snapshot = {0: {'free': 35000, 'util': 0}, 1: {'free': 41000, 'util': 0}}
        self.assertEqual(runner.placement(snapshot, set()), (0, 1))
        snapshot[1]['free'] = 39000
        self.assertIsNone(runner.placement(snapshot, set()))

    def test_heavy_scene_requires_distinct_gpus(self):
        self.assertIsNone(runner.placement({0: {'free': 48000, 'util': 0}}, set(), separate=True))
        snapshot = {0: {'free': 48000, 'util': 0}, 1: {'free': 45000, 'util': 0}}
        self.assertNotEqual(*runner.placement(snapshot, set(), separate=True))

    def test_config_preserves_official_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            path = runner.write_config(Path(d), 12345)
            text = path.read_text()
            self.assertIn('h1_internvla_n1_cfg_vlnverse_fine_val_unseen.py', text)
            self.assertNotIn('max_step', text)
            self.assertNotIn('robot_flash', text)
            self.assertNotIn('filter_stairs', text)

    def test_completed_smoke_does_not_count_toward_825(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(runner, 'CAMPAIGN', Path(d)):
            runner.atomic(Path(d) / 'completed/smoke.json', {'completed': 2})
            runner.atomic(Path(d) / 'completed/scene.json', {'completed': 25})
            self.assertEqual(runner.status()['completed'], 25)
            self.assertEqual(runner.status()['complete_scenes'], 1)

    def test_interrupted_transfer_resumes_without_losing_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'weights'
            path.with_name('weights.partial').write_bytes(b'ab')
            with mock.patch.object(download.urllib.request, 'urlopen', side_effect=[Response(b'cd', 2), Response(b'ef', 4)]) as open_url, mock.patch.object(download.time, 'sleep'), mock.patch('builtins.print'):
                row = download.fetch((path, 'https://example.test/weights', 6, hashlib.sha256(b'abcdef').hexdigest()))
            self.assertEqual(path.read_bytes(), b'abcdef')
            self.assertEqual(open_url.call_args_list[0].args[0].get_header('Range'), 'bytes=2-')
            self.assertEqual(open_url.call_args_list[1].args[0].get_header('Range'), 'bytes=4-')
            self.assertEqual(row['size'], 6)

    def test_hash_mismatch_never_promotes_partial_to_weight(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'weights'
            with mock.patch.object(download.urllib.request, 'urlopen', return_value=Response(b'bad', 0)), mock.patch.object(download.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'SHA256 mismatch'):
                    download.fetch((path, 'https://example.test/weights', 3, hashlib.sha256(b'yes').hexdigest()))
            self.assertFalse(path.exists())
            self.assertEqual(path.with_name('weights.partial').read_bytes(), b'bad')


if __name__ == '__main__':
    unittest.main()
