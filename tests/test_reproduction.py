import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from core.seeding import configured_seed, episode_seed
from core.vlnverse_reproduction import (digest_json, select_complete_scenes, verify_resume,
                                      verify_rows, summarize_complete_seeds)


class ReproductionTests(unittest.TestCase):
    def test_gpu_admission_excludes_busy_low_memory_and_disallowed_cards(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/reproduce_streamvln_vlnverse.py'
        spec = importlib.util.spec_from_file_location('reproduction_queue', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        rows = [dict(index=0,free_mib=42000,utilization=0), dict(index=1,free_mib=16000,utilization=0),
                dict(index=2,free_mib=40000,utilization=80), dict(index=3,free_mib=35000,utilization=5)]
        self.assertEqual(module.eligible_gpus(rows,None,set()),[0,3])
        self.assertEqual(module.eligible_gpus(rows,None,{0}),[3])
        self.assertEqual(module.eligible_gpus(rows,[0],set()),[0])
        self.assertEqual(module.eligible_gpus(rows,[3,0],set()),[3,0])

    def setUp(self):
        self.episodes = [dict(episode_id='a1', scan='a', instruction='left'),
                         dict(episode_id='b1', scan='b', instruction='right'),
                         dict(episode_id='a2', scan='a', instruction='forward')]

    def row(self, episode_id, seed, success=1):
        return dict(episode_id=episode_id, run_seed=seed, episode_seed=episode_seed(seed, episode_id),
                    SR=success, SPL=success * .5, NE=1, OS=1, TL=2, FR=0, StR=0)

    def test_scene_selection_keeps_every_instruction_and_rejects_unknown_scenes(self):
        self.assertEqual([e['episode_id'] for e in select_complete_scenes(self.episodes, ['a'])], ['a1', 'a2'])
        for scenes in ([], ['missing'], ['a', 'a']):
            with self.assertRaises(ValueError): select_complete_scenes(self.episodes, scenes)

    def test_resume_rejects_seed_scene_order_or_annotation_changes(self):
        meta = dict(seed=2, scenes=['a', 'b'], episode_ids=['a1', 'b1', 'a2'], dataset_sha256=digest_json(self.episodes))
        verify_resume(meta, self.episodes, 2, ['b', 'a'])
        for seed, scenes, data in [(3, ['a','b'], self.episodes), (2, ['a'], self.episodes),
                                  (2, ['a','b'], list(reversed(self.episodes)))]:
            with self.assertRaises(ValueError): verify_resume(meta, data, seed, scenes)
        modified = copy.deepcopy(self.episodes)
        modified[0]['instruction'] = 'changed'
        with self.assertRaises(ValueError): verify_resume(meta, modified, 2)

    def test_scoring_rejects_missing_duplicate_wrong_seed_and_nonfinite_rows(self):
        rows = [self.row('a1', 2), self.row('a2', 2)]
        self.assertEqual(verify_rows(rows, ['a1','a2'], 2)['SPL'], .5)
        bad = [rows[:1], [rows[0], rows[0]], [self.row('a1',3), rows[1]]]
        changed = copy.deepcopy(rows); changed[0]['NE'] = float('nan'); bad.append(changed)
        for data in bad:
            with self.assertRaises(ValueError): verify_rows(data, ['a1','a2'], 2)

    def test_episode_seed_survives_interpreter_restart_and_python_hash_seed(self):
        command = [sys.executable, '-c', "from core.seeding import episode_seed; print(episode_seed(3, 'a1'))"]
        outputs = [subprocess.check_output(command, text=True, env=dict(os.environ, PYTHONHASHSEED=str(s))).strip() for s in (1,77)]
        self.assertEqual(outputs, [str(episode_seed(3,'a1'))]*2)
        self.assertNotEqual(episode_seed(3,'a1'), episode_seed(4,'a1'))
        self.assertNotEqual(episode_seed(3,'a1'), episode_seed(3,'a2'))
        with patch.dict(os.environ, VLN_EVAL_SEED='0'): self.assertEqual(configured_seed(), 0)

    def test_partial_campaign_is_not_reported_as_five_seed_result(self):
        manifest=dict(seeds=[0,1,2,3,4],episodes_per_seed=2,total_episode_runs=10,episode_ids=['a1','a2'])
        rows=[self.row(e,s,success=s%2) for s in range(5) for e in ('a1','a2')]
        partial=summarize_complete_seeds(rows[:-1],manifest)
        self.assertFalse(partial['complete'])
        self.assertNotIn('mean_std_across_seeds',partial)
        result=summarize_complete_seeds(rows,manifest)
        self.assertTrue(result['complete'])
        self.assertAlmostEqual(result['mean_std_across_seeds']['SR']['mean'],.4)
        self.assertEqual(result['mean_std_across_seeds']['SR']['n'],5)


if __name__ == '__main__':
    unittest.main()
