"""Evaluate the original StreamVLN/JanusVLN policies on R2R, RxR or VLNVerse."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import math
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.paths import ensure_data_links, model_environment, model_python, model_root, output_root, resource_root


def build_command(args):
    env = model_environment(args.backbone, args.gpu)
    if args.benchmark == 'vlnverse':
        if args.output:
            raise ValueError('VLNVerse uses run IDs; set VLN_OUTPUT_ROOT to choose its base directory.')
        command = [sys.executable, str(PROJECT / 'benchmarks/vlnverse/runner/run_full.py'),
                   '--method', 'StreamVLN' if args.backbone == 'streamvln' else 'JanusVLN',
                   '--gpu', str(args.gpu), '--mode', args.mode, '--limit-episodes', str(args.episodes)]
        if args.sim_gpu is not None:
            command += ['--sim-gpu', str(args.sim_gpu)]
        if args.preflight_only:
            command.append('--preflight-only')
        if args.resume:
            command += ['--resume', args.resume]
        for flag, value in [('--seed', getattr(args, 'seed', None)), ('--run-id', getattr(args, 'run_id', None))]:
            if value is not None:
                command += [flag, str(value)]
        if getattr(args, 'scenes', None):
            command += ['--scenes', *args.scenes]
        if getattr(args, 'allow_shared_gpu', False):
            command.append('--allow-shared-gpu')
        return command, env, PROJECT, None
    if getattr(args, 'seed', None) is not None or getattr(args, 'scenes', None) or getattr(args, 'run_id', None):
        raise ValueError('--seed, --scenes and --run-id currently apply to VLNVerse only.')
    if args.resume or args.sim_gpu is not None or args.mode != 'physical':
        raise ValueError('--resume, --sim-gpu and --mode apply to VLNVerse only.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    output = Path(args.output).resolve() if args.output else output_root() / args.backbone / args.benchmark / stamp
    root = model_root(args.backbone)
    checkpoint = resource_root() / 'models' / ('StreamVLN_R2R_v1_3' if args.backbone == 'streamvln' else 'JanusVLN_Extra')
    evaluator = ('streamvln/streamvln_eval_rxr.py' if args.benchmark == 'rxr' else 'streamvln/streamvln_eval.py') if args.backbone == 'streamvln' else 'src/evaluation.py'
    command = [str(model_python(args.backbone)), '-m', 'torch.distributed.run', '--standalone',
               '--nproc_per_node=1', evaluator, '--model_path', str(checkpoint),
               '--habitat_config_path', 'config/vln_' + args.benchmark + '.yaml',
               '--eval_split', 'val_unseen', '--output_path', str(output)]
    if args.episodes:
        flag = '--max_eval_episodes' if args.backbone == 'streamvln' and args.benchmark == 'rxr' else '--episode_limit'
        command += [flag, str(args.episodes)]
    return command, env, root, output


def check_gpu(gpu, minimum, allow_shared=False):
    lines = subprocess.check_output(['nvidia-smi', '-i', str(gpu), '--query-gpu=uuid,memory.free',
                                     '--format=csv,noheader,nounits'], text=True).strip().split(',')
    uuid, free = lines[0].strip(), int(lines[1])
    rows = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
                                    '--format=csv,noheader'], text=True)
    occupied = [row for row in rows.splitlines() if row.split(',')[0].strip() == uuid]
    if occupied and not allow_shared:
        raise RuntimeError(f'GPU {gpu} is occupied; choose an idle GPU or coordinate --allow-shared-gpu.')
    if free < minimum:
        raise RuntimeError(f'GPU {gpu} has {free} MiB free; require {minimum} MiB.')
    return dict(gpu=gpu, free_mib=free, existing_processes=occupied)


def validate_result(output, expected):
    summary = json.loads((output / 'summary.json').read_text())
    rows = [json.loads(line) for line in (output / 'result.json').read_text().splitlines() if line.strip()]
    if not rows or summary['length'] != len(rows) or (expected and len(rows) != expected):
        raise RuntimeError('Unexpected completed episode count: ' + str(summary))
    for row in rows:
        for key in ('success', 'spl', 'os', 'ne'):
            if not math.isfinite(float(row[key])):
                raise RuntimeError('Nonfinite metric: ' + key)
    return dict(passed=True, episodes=len(rows), summary=summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backbone', choices=['streamvln', 'janusvln'], required=True)
    parser.add_argument('--benchmark', choices=['r2r', 'rxr', 'vlnverse'], required=True)
    parser.add_argument('--gpu', type=int, required=True, help='Physical GPU index')
    parser.add_argument('--sim-gpu', type=int)
    parser.add_argument('--episodes', type=int, default=0, help='0 = full split; positive = complete-episode validation subset')
    parser.add_argument('--mode', choices=['physical', 'flash'], default='physical')
    parser.add_argument('--output')
    parser.add_argument('--resume', help='Existing VLNVerse run ID')
    parser.add_argument('--run-id', help='Explicit new VLNVerse run ID')
    parser.add_argument('--seed', type=int, help='StreamVLN VLNVerse run seed')
    parser.add_argument('--scenes', nargs='+', help='Complete VLNVerse scenes; incompatible with --episodes')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--allow-shared-gpu', action='store_true', help='Only after coordinating access to an occupied GPU')
    args = parser.parse_args()
    if args.gpu < 0 or args.episodes < 0 or (args.sim_gpu is not None and args.sim_gpu < 0):
        parser.error('GPU indices and episode count must be nonnegative.')
    command, env, cwd, output = build_command(args)
    record = dict(arguments=vars(args), command=command, cwd=str(cwd), model_python=str(model_python(args.backbone)),
                  output=str(output) if output else str(output_root() / 'vlnverse'))
    print(json.dumps(record, indent=2), flush=True)
    if args.dry_run:
        return
    if not model_python(args.backbone).is_file():
        raise FileNotFoundError('Missing model environment; see docs/ENVIRONMENT.md')
    ensure_data_links(args.backbone)
    minimum = 30000 if args.backbone == 'janusvln' else 22000
    if args.benchmark == 'vlnverse':
        separate = args.sim_gpu is not None and args.sim_gpu != args.gpu
        minimum = (39000 if separate else 45000) if args.backbone == 'janusvln' else (25000 if separate else 32000)
    record['gpu'] = check_gpu(args.gpu, minimum, args.allow_shared_gpu)
    if args.sim_gpu is not None and args.sim_gpu != args.gpu:
        record['sim_gpu'] = check_gpu(args.sim_gpu, 12000, args.allow_shared_gpu)
    if args.benchmark == 'vlnverse':
        subprocess.run(command, cwd=cwd, env=env, check=True)
        return
    if args.preflight_only:
        print(json.dumps(dict(preflight_passed=True, **record)), flush=True)
        return
    with open('/tmp/vln_2026_gpu_' + str(args.gpu) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        output.mkdir(parents=True, exist_ok=False)
        git = subprocess.run(['git', '-C', str(PROJECT), 'rev-parse', 'HEAD'], text=True, capture_output=True)
        record.update(git_commit=git.stdout.strip() if git.returncode == 0 else None,
                      started_at=datetime.now(timezone.utc).isoformat())
        (output / 'launch.json').write_text(json.dumps(record, indent=2) + '\n')
        with (output / 'run.log').open('w') as log:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        record.update(exit_code=result.returncode, finished_at=datetime.now(timezone.utc).isoformat())
        (output / 'launch.json').write_text(json.dumps(record, indent=2) + '\n')
        if result.returncode:
            raise RuntimeError('Evaluation failed; see ' + str(output / 'run.log'))
        validation = validate_result(output, args.episodes)
        (output / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
        print(json.dumps(validation, indent=2), flush=True)


if __name__ == '__main__':
    main()
