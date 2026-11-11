"""Portable exporter checks. No network, browser dependencies or dataset required."""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('jev_export', ROOT / 'scripts/export_jev_sampling_lab.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jev-export-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = {
            'cases': [{'episode_id': 'example · F0', 'frames': [{'frame': 0, 'jev': {'probability_yes': .8}, 'qwen': {'score': 5}}]}],
            'summary': {'valid_calls': 1, 'jev_mean_probability': .8, 'qwen_mean_score': 5},
            'images': {'image': 'assets/frame.webp'}, 'maps': {},
            'prompt_en': '</script><p>literal prompt</p>', 'prompt_zh': '中文原文',
        }
        self.assets = {'assets/frame.webp': b'fixture-image'}
        template = (ROOT / 'core/jev_sampling_lab/template.html').read_text(encoding='utf-8')
        for font in re.findall(r'url\((assets/[^)]+)\)', template):
            self.assets[font] = b'fixture-font'

    def html(self):
        serialized = json.dumps(self.payload).replace('</', '<\/')
        return '<script id="payload" type="application/json">' + serialized + '</script>'

    def write_html(self):
        source = self.root / 'source.html'
        source.write_text(self.html(), encoding='utf-8')
        for name, data in self.assets.items():
            target = self.root / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(data)
        return source

    def check_export(self, destination):
        html = (destination / 'index.html').read_text(encoding='utf-8')
        payload = module.extract_payload(html)
        self.assertEqual(payload['cases'][0]['frames'][0]['jev'], {'probability_yes': .8})
        self.assertNotIn('qwen', payload['cases'][0]['frames'][0])
        self.assertEqual(payload['prompt_en'], self.payload['prompt_en'])
        self.assertNotIn('</script><p>literal prompt', html)
        for name, data in self.assets.items():
            self.assertEqual((destination / name).read_bytes(), data)
        self.assertTrue((destination / 'app.js').is_file())
        manifest = json.loads((destination / 'manifest.json').read_text(encoding='utf-8'))
        self.assertFalse(manifest['sampling_default'])
        self.assertEqual(manifest['display_mode'], 'full_recording')
        self.assertEqual(manifest['sampling_input_mode'], 'current_prefix')

    def test_html_and_zip_export_match(self):
        source = self.write_html()
        module.export(source, self.root / 'html_export')
        archive = self.root / 'source.zip'
        with ZipFile(archive, 'w') as z:
            z.writestr('site/source.html', self.html())
            for name, data in self.assets.items():
                z.writestr('site/' + name, data)
        module.export(archive, self.root / 'zip_export')
        for name in ['html_export', 'zip_export']:
            self.check_export(self.root / name)
        self.assertEqual((self.root / 'html_export/index.html').read_bytes(), (self.root / 'zip_export/index.html').read_bytes())

    def test_existing_destination_is_preserved(self):
        source = self.write_html()
        destination = self.root / 'existing'
        destination.mkdir()
        (destination / 'keep').write_text('original')
        with self.assertRaises(FileExistsError):
            module.export(source, destination)
        self.assertEqual((destination / 'keep').read_text(), 'original')

    def test_missing_assets_fail_before_writing(self):
        source = self.root / 'source.html'
        source.write_text(self.html(), encoding='utf-8')
        with self.assertRaises(ValueError):
            module.export(source, self.root / 'missing')
        self.assertFalse((self.root / 'missing').exists())

    def test_unsafe_or_remote_assets_are_rejected(self):
        source = self.write_html()
        for value in ['../secret.json', 'assets/../../secret.json', 'https://example.com/image.png', 'C:\\secret.png']:
            self.payload['images']['image'] = value
            source.write_text(self.html(), encoding='utf-8')
            with self.assertRaises(ValueError):
                module.export(source, self.root / 'unsafe')
        self.assertFalse((self.root / 'unsafe').exists())


if __name__ == '__main__':
    unittest.main()
