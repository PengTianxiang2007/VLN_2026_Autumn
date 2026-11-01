import argparse
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evaluation_launcher', ROOT / 'scripts/evaluate.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
from core.paths import model_environment, model_python, model_root


def arguments(**values):
    defaults = dict(backbone='streamvln', benchmark='r2r', gpu=0, sim_gpu=None,
                    episodes=1, output=None, mode='physical', preflight_only=False, resume=None)
    defaults.update(values)
    return argparse.Namespace(**defaults)


class LaunchTests(unittest.TestCase):
    def test_four_habitat_routes_use_correct_evaluator_and_limit(self):
        for backbone in ['streamvln', 'janusvln']:
            for benchmark in ['r2r', 'rxr']:
                with self.subTest(backbone=backbone, benchmark=benchmark):
                    command, env, cwd, output = launcher.build_command(arguments(backbone=backbone, benchmark=benchmark))
                    self.assertEqual(cwd, model_root(backbone))
                    self.assertEqual(command[0], str(model_python(backbone)))
                    self.assertIn('config/vln_' + benchmark + '.yaml', command)
                    flag = '--max_eval_episodes' if backbone == 'streamvln' and benchmark == 'rxr' else '--episode_limit'
                    self.assertEqual(command[command.index(flag)+1], '1')
                    self.assertEqual(env['CUDA_VISIBLE_DEVICES'], '0')
                    self.assertFalse(output.exists())

    def test_full_split_does_not_add_episode_cap(self):
        command, _, _, _ = launcher.build_command(arguments(episodes=0))
        self.assertNotIn('--episode_limit', command)
        self.assertNotIn('--max_eval_episodes', command)

    def test_both_vlnverse_routes_preserve_mode_and_complete_episode_subset(self):
        for backbone, method in [('streamvln', 'StreamVLN'), ('janusvln', 'JanusVLN')]:
            command, env, cwd, output = launcher.build_command(arguments(backbone=backbone, benchmark='vlnverse', mode='flash', sim_gpu=3))
            self.assertIn(method, command)
            self.assertEqual(command[command.index('--mode')+1], 'flash')
            self.assertEqual(command[command.index('--limit-episodes')+1], '1')
            self.assertEqual(command[command.index('--sim-gpu')+1], '3')
            self.assertIsNone(output)
            self.assertTrue(env['VLNVERSE_VENV'].startswith(str(ROOT)))

    def test_source_precedence_does_not_inherit_old_pythonpath(self):
        with patch.dict(os.environ, PYTHONPATH='/old/source'):
            for model in ['streamvln', 'janusvln']:
                paths = model_environment(model)['PYTHONPATH'].split(os.pathsep)
                self.assertNotIn('/old/source', paths)
                self.assertTrue(all(Path(p).is_relative_to(ROOT) for p in paths))
                self.assertIn(str(ROOT / 'benchmarks/habitat_ce/habitat-lab-v0.2.4/habitat-lab'), paths)

    def test_incompatible_arguments_are_rejected(self):
        for values in [dict(sim_gpu=2), dict(resume='old_run'), dict(mode='flash'), dict(benchmark='vlnverse',output='somewhere')]:
            with self.assertRaises(ValueError):
                launcher.build_command(arguments(**values))

    def test_result_check_rejects_partial_or_nonfinite_metrics(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            (output/'summary.json').write_text(json.dumps(dict(length=1)))
            row=dict(success=0,spl=0,os=0,ne=1)
            (output/'result.json').write_text(json.dumps(row)+'\n')
            self.assertTrue(launcher.validate_result(output,1)['passed'])
            with self.assertRaises(RuntimeError):launcher.validate_result(output,2)
            row['ne']=float('inf')
            (output/'result.json').write_text(json.dumps(row)+'\n')
            with self.assertRaises(RuntimeError):launcher.validate_result(output,1)


if __name__ == '__main__':
    unittest.main()
