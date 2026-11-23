"""Freeze the 33-task distance Oracle and executable simulator source. CPU only."""
import argparse
import ast
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.oracle_distance import build_cohort, positive
from core.paths import isaac_root, model_python, resource_root, simulation_python

DEFAULT_DATASET = ROOT / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
DEFAULT_CONFIG = ROOT / 'experiments/oracle_recovery/distance_v001/config.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('Runtime integration anchor changed: ' + before[:100])
    return source.replace(before, after)


def patch_runtime(relative, source):
    """Patch only the newly frozen copy; original navigation sources stay untouched."""
    marker = '# Frozen distance Oracle runtime v001'
    if marker in source:
        raise ValueError('Runtime already patched')
    if relative.endswith('/service.py'):
        source = replace_once(source,
            "    def do_GET(self):\n        self.respond({'ready': True, 'method': args.method, 'model_calls': agent.calls})",
            "    def do_GET(self):\n"
            "        if self.path.startswith('/oracle/state'):\n"
            "            from core.oracle_policy_state import audit\n"
            "            self.respond(audit(agent, resets, deep='deep=1' in self.path))\n"
            "            return\n"
            "        self.respond({'ready': True, 'method': args.method, 'model_calls': agent.calls})")
        source = replace_once(source, "            if self.path == '/agent/init':",
            "            if self.path == '/branch/checkpoint':\n"
            "                from core.oracle_branch_policy import checkpoint\n"
            "                result, resets, steps = checkpoint(agent, resets, steps, body)\n"
            "                self.respond(result)\n"
            "            elif self.path == '/agent/init':")
    elif relative.endswith('/vln_pe_evaluator.py'):
        source = replace_once(source, '    def eval(self):\n',
            "    def eval(self):\n"
            "        from core.oracle_distance_native import install\n"
            "        install(self)\n")
    elif relative.endswith('/run_full.py'):
        # Preserve the original launcher byte for byte, including its original
        # memory-budget restart/resume and owned-process cleanup behavior.
        ast.parse(source)
        return source
    ast.parse(source)
    return marker + '\n' + source


def validate_config(config):
    names = ('early', 'short', 'medium', 'long')
    if set(config['thresholds_m']) != set(names):
        raise ValueError('Require early/short/medium/long thresholds')
    values = [positive(config['thresholds_m'][n], n) for n in names]
    if any(a >= b for a, b in zip(values, values[1:])):
        raise ValueError('Distance thresholds must strictly increase')
    for name in ('landing_offset_m', 'checkpoint_capture_radius_m', 'checkpoint_threshold_m'):
        positive(config[name], name)
    if config['checkpoint_threshold_m'] < values[0]:
        raise ValueError('Checkpoint threshold cannot be below the common onset threshold')
    if config['checkpoint_max_returns'] != 1:
        raise ValueError('Checkpoint protocol supports one return followed by native navigation')
    if type(config['seed']) is not int or not 0 <= config['seed'] < 2**31:
        raise ValueError('Invalid seed')


def source_files():
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    prefixes = ('backbone/streamvln/', 'benchmarks/habitat_ce/',
                'benchmarks/vlnverse/runner/', 'benchmarks/vlnverse/upstream/')
    selected = {n for n in tracked if n.startswith(prefixes) and (ROOT / n).is_file()}
    # Explicit allowlist: never include credentials, downloaded assets or environments.
    selected.update('core/' + n + '.py' for n in (
        '__init__', 'paths', 'seeding', 'vlnverse_runtime', 'vlnverse_reproduction',
        'vlnverse_review', 'jev_live_stream', 'jev_stream', 'jev_request_runner', 'jev_node',
        'agent_route_choice', 'oracle_crossing', 'oracle_branching', 'oracle_branch_policy',
        'oracle_policy_state', 'oracle_checkpoint_pair', 'oracle_distance', 'oracle_distance_runtime',
        'oracle_distance_native', 'oracle_auto_route', 'oracle_auto_branch', 'oracle_landing_geometry'))
    selected.update(('scripts/evaluate.py', 'scripts/export_vlnverse_results.py',
                     'scripts/prepare_oracle_distance.py', 'scripts/run_oracle_distance.py'))
    return sorted(selected)


def prepare(dataset, config, output):
    validate_config(config)
    out = Path(output).resolve()
    if out.exists():
        raise FileExistsError('Preserving existing output: ' + str(out))
    cohort = build_cohort(dataset, config['landing_offset_m'], config['thresholds_m'])
    if (cohort['episodes'], cohort['events']) != (config['expected_episodes'], config['expected_events']):
        raise ValueError('Unexpected cohort size: %s/%s' % (cohort['episodes'], cohort['events']))
    official = resource_root() / 'assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz'
    with gzip.open(official, 'rt') as stream:
        episodes = {e['episode_id']: e for e in json.load(stream)['episodes']}
    for case in cohort['cases']:
        episode = episodes.get(case['episode_id'])
        if episode is None or episode['scan'] != case['scene']:
            raise ValueError('Episode missing or scene mismatch in official split')
        if episode['instruction']['instruction_text'] != case['instruction']:
            raise ValueError('Official instruction differs from annotation dataset')
        if episode['reference_path'] != case['reference_path']:
            raise ValueError('Official reference route differs from annotation dataset')
    names = source_files()
    originals = {n: sha(ROOT / n) for n in names}
    patch_names = ('benchmarks/vlnverse/runner/service.py', 'benchmarks/vlnverse/runner/run_full.py',
                   'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py')
    patches = {n: patch_runtime(n, (ROOT / n).read_text()) for n in patch_names}
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)
    diff = subprocess.check_output(['git', 'diff', 'HEAD'], cwd=ROOT)
    out.mkdir(parents=True, exist_ok=False)
    code = out / 'code'
    for name in names:
        dest = code / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
        if sha(dest) != originals[name]:
            raise RuntimeError('Source changed during freezing: ' + name)
    for name, value in patches.items():
        (code / name).write_text(value)
    arms = {name: {'mode': 'route', 'threshold_m': value} for name, value in config['thresholds_m'].items()}
    arms['checkpoint'] = {'mode': 'checkpoint', 'threshold_m': config['checkpoint_threshold_m']}
    env = {'STREAMVLN_VENV': str(model_python('streamvln').parent.parent),
           'VLNVERSE_VENV': str(simulation_python().parent.parent), 'PENG_ISAAC_ROOT': str(isaac_root()),
           'VLN_RESOURCE_ROOT': str(resource_root()), 'VLN_OUTPUT_ROOT': str(out / 'runs'),
           'VLN_ORACLE_MANIFEST': str(out / 'manifest.json'), 'VLN_CODE_COMMIT': head,
           'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    manifest = dict(schema=1, protocol='distance_oracle_v001', prepared_at=datetime.now(timezone.utc).isoformat(),
                    execution_backend='native_reproduction',
                    git_head=head, worktree_dirty=bool(dirty), cases=cohort['cases'],
                    episode_ids=[c['episode_id'] for c in cohort['cases']],
                    episodes=cohort['episodes'], events=cohort['events'], seed=config['seed'],
                    arms=arms, onset_m=config['thresholds_m']['early'],
                    checkpoint_capture_radius_m=config['checkpoint_capture_radius_m'],
                    config=config, code_root=str(code), source_sha256=originals,
                    code_sha256={n: sha(code / n) for n in names}, runtime_env=env,
                    official_split_sha256=sha(official), dataset_source_sha256=cohort['source_sha256'],
                    interpretation='Independent full simulation per arm/task. Distance-triggered privileged Oracle; no online GPT. No shared-prefix claim.')
    installed = simulation_python().parent.parent / 'lib/python3.10/site-packages/internutopia'
    manifest['simulation_backend_sha256'] = {str(installed / n): sha(installed / n) for n in
        ('core/runner.py', 'core/task/task.py', 'core/scene/isaacsim/scene.py', 'core/util/clear_task.py')}
    save(out / 'cohort.json', cohort)
    save(out / 'manifest.json', manifest)
    save(out / 'seal.json', {'manifest_sha256': sha(out / 'manifest.json'), 'cohort_sha256': sha(out / 'cohort.json')})
    save(out / 'status.json', {'phase': 'prepared', 'simulation_started': False})
    (out / 'git_status.txt').write_text(dirty)
    (out / 'git_diff.patch').write_bytes(diff)
    shutil.copy2(ROOT / 'experiments/oracle_recovery/distance_v001/README.md', out / 'protocol.md')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--thresholds', nargs=4, type=float, metavar=('EARLY', 'SHORT', 'MEDIUM', 'LONG'))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if args.thresholds:
        config['thresholds_m'] = dict(zip(('early', 'short', 'medium', 'long'), args.thresholds))
        config['checkpoint_threshold_m'] = args.thresholds[0]
    manifest = prepare(args.dataset, config, args.output)
    print(json.dumps({'output': str(args.output.resolve()), 'episodes': manifest['episodes'],
                      'events': manifest['events'], 'arms': manifest['arms'], 'simulation_started': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
