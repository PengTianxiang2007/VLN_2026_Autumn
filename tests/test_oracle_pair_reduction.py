import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.reduce_oracle_pair import boundary_safe, selected_episodes, safe_signal
from core.seeding import episode_seed
from core.vlnverse_reproduction import digest_json
from scripts.export_vlnverse_results import export_run


class PairReductionTests(unittest.TestCase):
    def test_scored_boundary_allows_stop(self):
        self.assertTrue(boundary_safe(2, {'a', 'b'}, 'b', 2))

    def test_in_flight_next_case_is_not_interrupted(self):
        self.assertFalse(boundary_safe(2, {'a', 'b'}, 'c', 2))
        self.assertTrue(boundary_safe(3, {'a', 'b', 'c'}, 'c', 2))

    def test_count_and_lmdb_must_agree(self):
        self.assertFalse(boundary_safe(2, {'a'}, 'a', 2))
        self.assertFalse(boundary_safe(1, {'a'}, 'a', 2))

    def test_subset_preserves_original_inputs_and_order(self):
        original = [{'episode_id': 'b', 'instruction': 'B'}, {'episode_id': 'a', 'instruction': 'A'}, {'episode_id': 'c'}]
        self.assertEqual(selected_episodes(original, {'a', 'b'}), original[:2])
        with self.assertRaises(ValueError):
            selected_episodes(original, {'unknown'})

    def test_reused_pid_is_never_signaled(self):
        with patch('scripts.reduce_oracle_pair.alive', return_value=True), patch('scripts.reduce_oracle_pair.identity', return_value={'pid': 123, 'start_ticks': 'new'}), patch('scripts.reduce_oracle_pair.os.kill') as kill:
            with self.assertRaises(RuntimeError):
                safe_signal({'pid': 123, 'start_ticks': 'old'}, 15)
            kill.assert_not_called()

    def test_native_export_accepts_derived_subset_and_checks_original_scores(self):
        import lmdb
        import msgpack_numpy
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); run = root / 'derived'; dataset = root / 'dataset'
            (dataset / 'val_unseen').mkdir(parents=True)
            episodes = [dict(episode_id='scene_1', trajectory_id=1, scan='scene'),
                        dict(episode_id='scene_2', trajectory_id=2, scan='scene')]
            with gzip.open(dataset / 'val_unseen/val_unseen.json.gz', 'wt') as stream:
                json.dump({'episodes': episodes}, stream)
            (run / 'storage/samples').mkdir(parents=True)
            (run / 'run.json').write_text(json.dumps(dict(run_id='original', dataset=str(dataset),
                episode_ids=['scene_1', 'scene_2'], seed=2, scenes=['scene'], dataset_sha256=digest_json(episodes))))
            db = lmdb.open(str(run / 'storage/samples/sample_data.lmdb'), map_size=2**20)
            with db.begin(write=True) as txn:
                txn.put(b'eval_rank_0', b'original rank metadata')
                for e in episodes:
                    info = dict(episode_id=e['episode_id'], reproduction_run_seed=2,
                        reproduction_episode_seed=episode_seed(2, e['episode_id']), success=1, spl=.5,
                        NE=1, osr=1, TL=2, steps=10, pred_path=[])
                    txn.put(f"{e['trajectory_id']}_{e['episode_id']}".encode(),
                            msgpack_numpy.packb(dict(info=info, fail_reason='success')))
            db.close()
            score = root / 'benchmarks/vlnverse/upstream/logs/original/kujiale_result.json'
            score.parent.mkdir(parents=True)
            score.write_text(json.dumps({'val_unseen': dict(Count=2, SR=1, SPL=.5, NE=1, OS=1, TL=2, FR=0, StR=0)}))
            with patch('scripts.export_vlnverse_results.PROJECT', root):
                proof = export_run(run)
                self.assertTrue(proof['passed']); self.assertEqual(proof['episodes'], 2)
                score.write_text(json.dumps({'val_unseen': {'Count': 3}}))
                with self.assertRaises(ValueError):
                    export_run(run)


if __name__ == '__main__':
    unittest.main()
