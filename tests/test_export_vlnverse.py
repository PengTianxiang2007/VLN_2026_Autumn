"""Run with the existing VLNVerse Python to exercise the real LMDB format."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.seeding import episode_seed
from core.vlnverse_reproduction import digest_json
from scripts import export_vlnverse_results as exporter


@unittest.skipUnless(importlib.util.find_spec('lmdb') and importlib.util.find_spec('msgpack_numpy'),
                     'Requires the existing VLNVerse environment')
class ExportTests(unittest.TestCase):
    def setUp(self):
        import lmdb
        import msgpack_numpy

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / 'run'
        dataset = self.run / 'dataset'
        (dataset / 'val_unseen').mkdir(parents=True)
        episodes = [dict(episode_id='a1', trajectory_id='t1', scan='a')]
        with gzip.open(dataset / 'val_unseen/val_unseen.json.gz', 'wt') as stream:
            json.dump(dict(episodes=episodes), stream)
        (self.run / 'run.json').write_text(json.dumps(dict(seed=0, scenes=['a'], episode_ids=['a1'],
            run_id='test', dataset=str(dataset), dataset_sha256=digest_json(episodes))))
        samples = self.run / 'storage/samples'
        samples.mkdir(parents=True)
        self.database = lmdb.open(str(samples / 'sample_data.lmdb'), map_size=1024**2)
        self.addCleanup(self.database.close)
        info = dict(episode_id='a1', reproduction_run_seed=0, reproduction_episode_seed=episode_seed(0, 'a1'),
                    success=1, spl=.5, NE=1, osr=1, TL=2, steps=100, pred_path=[[0, 0, 0]])
        with self.database.begin(write=True) as txn:
            txn.put(b'eval_rank_0', msgpack_numpy.packb({'a': ['t1_a1']}, use_bin_type=True))
            txn.put(b'timestamp_', msgpack_numpy.packb({'timestamp': 1}, use_bin_type=True))
            txn.put(b't1_a1', msgpack_numpy.packb(dict(info=info, fail_reason='success'), use_bin_type=True))
        chunk = self.run / 'storage/chunks/one'
        chunk.mkdir(parents=True)
        self.trace = chunk / 'agent_trace.jsonl'
        self.trace.write_text(json.dumps(dict(episode_id='a1', run_seed=0,
            episode_seed=episode_seed(0, 'a1'), forced_smoke_stop=False)) + '\n')
        official = self.root / 'benchmarks/vlnverse/upstream/logs/test'
        official.mkdir(parents=True)
        (official / 'kujiale_result.json').write_text(json.dumps(dict(val_unseen=dict(
            Count=1, SR=1, SPL=.5, NE=1, OS=1, TL=2, FR=0, StR=0))))

    def export(self):
        self.database.close()
        with patch.object(exporter, 'PROJECT', self.root):
            return exporter.export_run(self.run)

    def test_official_rank_metadata_is_not_a_scored_episode(self):
        proof = self.export()
        self.assertTrue(proof['passed'])
        self.assertEqual(proof['episodes'], 1)
        self.assertEqual(proof['model_trace_records_verified'], 1)
        self.assertEqual(proof['metrics']['SPL'], .5)

    def test_unexpected_nonmetadata_record_is_still_rejected(self):
        with self.database.begin(write=True) as txn:
            txn.put(b'unexpected', b'not a score')
        with self.assertRaisesRegex(ValueError, 'LMDB keys differ'):
            self.export()

    def test_wrong_model_seed_is_still_rejected(self):
        trace = json.loads(self.trace.read_text())
        trace['run_seed'] = 1
        self.trace.write_text(json.dumps(trace) + '\n')
        with self.assertRaisesRegex(ValueError, 'Model-service seed differs'):
            self.export()


if __name__ == '__main__':
    unittest.main()
