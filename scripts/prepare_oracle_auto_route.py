"""Freeze an annotation-free Oracle and native baseline on the same explicit tasks.

CPU only. This does not start a model, simulator, queue or network request.
"""
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.oracle_auto_route import PROTOCOL, build_auto_cohort
from core.oracle_distance import positive
from core.paths import isaac_root, model_python, resource_root, simulation_python
from scripts.prepare_oracle_distance import patch_runtime, save, sha, source_files

DEFAULT_CONFIG = ROOT / 'experiments/oracle_recovery/auto_route_v001/config.json'


def read_episode_ids(path):
    text = Path(path).read_text(encoding='utf-8').strip()
    values = json.loads(text) if text.startswith('[') else text.splitlines()
    if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
        raise ValueError('Use a JSON string list or one episode ID per line')
    return [v.strip() for v in values if v.strip()]


def prepare(official, episode_ids, config, output, protocol=PROTOCOL, geometry_root=None):
    out = Path(output).resolve()
    official = Path(official).resolve()
    if out.exists():
        raise FileExistsError('Preserving existing output: ' + str(out))
    branch_mode = protocol == 'auto_branch_oracle_v001'
    if protocol not in (PROTOCOL, 'auto_branch_oracle_v001'):
        raise ValueError('Unknown automatic Oracle protocol')
    if geometry_root is not None and not branch_mode:
        raise ValueError('Geometry audit is prepared only for the online branch protocol')
    fields = {'schema', 'seed', 'threshold_m', 'landing_offset_m'} | ({'branch'} if branch_mode else set())
    if set(config) != fields or config['schema'] != 1:
        raise ValueError('Unexpected auto-route config fields or schema')
    threshold = positive(config['threshold_m'], 'threshold')
    offset = positive(config['landing_offset_m'], 'landing offset')
    if branch_mode:
        from core.oracle_auto_branch import validate_settings
        validate_settings(config['branch'], threshold)
    with gzip.open(official, 'rt') as stream:
        cohort = build_auto_cohort(json.load(stream)['episodes'], episode_ids, config['seed'])
    cohort['protocol'] = protocol
    cohort['source_sha256'] = {str(official): sha(official)}
    names = sorted(set(source_files()) | {'scripts/prepare_oracle_auto_route.py'})
    if branch_mode:
        names.append('scripts/prepare_oracle_auto_branch.py')
    originals = {n: sha(ROOT/n) for n in names}
    patch_names = ('benchmarks/vlnverse/runner/service.py',
                   'benchmarks/vlnverse/runner/run_full.py',
                   'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py')
    patches = {n: patch_runtime(n, (ROOT/n).read_text()) for n in patch_names}
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)
    diff = subprocess.check_output(['git', 'diff', 'HEAD'], cwd=ROOT)
    out.mkdir(parents=True)
    code = out/'code'
    for name in names:
        dest = code/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, dest)
        if sha(dest) != originals[name]:
            raise RuntimeError('Source changed during freezing: ' + name)
    for name, value in patches.items():
        (code/name).write_text(value)
    arm = 'auto_branch' if branch_mode else 'auto_route'
    settings = dict(mode=arm, threshold_m=threshold, landing_offset_m=offset)
    if branch_mode:
        settings['branch'] = config['branch']
    arms = {'baseline': {'mode': 'baseline', 'threshold_m': None}, arm: settings}
    env = {'STREAMVLN_VENV': str(model_python('streamvln').parent.parent),
           'VLNVERSE_VENV': str(simulation_python().parent.parent),
           'PENG_ISAAC_ROOT': str(isaac_root()), 'VLN_RESOURCE_ROOT': str(resource_root()),
           'VLN_OUTPUT_ROOT': str(out/'runs'), 'VLN_ORACLE_MANIFEST': str(out/'manifest.json'),
           'VLN_CODE_COMMIT': head, 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
           'PYTHONDONTWRITEBYTECODE': '1'}
    origin = ('Fixed inferred divergence point from the walked/reference trajectory prefix' if branch_mode else
              'Current-pose reference projection')
    manifest = dict(schema=1, protocol=protocol, prepared_at=datetime.now(timezone.utc).isoformat(),
                    execution_backend='native_reproduction', git_head=head, worktree_dirty=bool(dirty),
                    cases=cohort['cases'], episode_ids=[c['episode_id'] for c in cohort['cases']],
                    episodes=cohort['episodes'], events=0, annotation_required=False, seed=config['seed'],
                    arms=arms, onset_m=threshold, config=config, code_root=str(code),
                    source_sha256=originals, code_sha256={n: sha(code/n) for n in names}, runtime_env=env,
                    official_split_sha256=sha(official), dataset_source_sha256=cohort['source_sha256'],
                    interpretation='Same tasks and seeds, independent native runs. ' + origin + ' '
                                   'plus forward arc offset. Privileged reference-route Oracle, no human annotations. '
                                   'No claim of unseen tasks until the separate historical-ID audit is complete.')
    installed = simulation_python().parent.parent/'lib/python3.10/site-packages/internutopia'
    manifest['simulation_backend_sha256'] = {str(installed/n): sha(installed/n) for n in
        ('core/runner.py', 'core/task/task.py', 'core/scene/isaacsim/scene.py', 'core/util/clear_task.py')}
    if geometry_root is not None:
        from core.oracle_landing_geometry import freeze_scene_geometry
        manifest['landing_geometry_audit'] = freeze_scene_geometry(
            geometry_root, [c['scene'] for c in cohort['cases']], out/'geometry')
    save(out/'cohort.json', cohort)
    save(out/'manifest.json', manifest)
    save(out/'seal.json', dict(manifest_sha256=sha(out/'manifest.json'), cohort_sha256=sha(out/'cohort.json')))
    save(out/'status.json', dict(phase='prepared', simulation_started=False))
    save(out/'episode_ids.json', manifest['episode_ids'])
    (out/'git_status.txt').write_text(dirty)
    (out/'git_diff.patch').write_bytes(diff)
    protocol_dir = 'auto_branch_v001' if branch_mode else 'auto_route_v001'
    shutil.copy2(ROOT/'experiments/oracle_recovery'/protocol_dir/'README.md', out/'protocol.md')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode-ids-file', type=Path, required=True)
    parser.add_argument('--official-split', type=Path,
                        default=resource_root()/'assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--expected-episodes', type=int, help='Reject a list with a different count')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    ids = read_episode_ids(args.episode_ids_file)
    if args.expected_episodes is not None and len(ids) != args.expected_episodes:
        parser.error('Episode count does not match --expected-episodes')
    manifest = prepare(args.official_split, ids, json.loads(args.config.read_text()), args.output)
    print(json.dumps(dict(output=str(args.output.resolve()), protocol=PROTOCOL,
                         episodes=manifest['episodes'], arms=list(manifest['arms']),
                         simulation_started=False), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
