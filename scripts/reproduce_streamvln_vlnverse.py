"""Freeze 250 episodes and schedule their 50 scene/seed units on available GPUs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.paths import resource_root, model_python, simulation_python, isaac_root
from core.vlnverse_reproduction import make_manifest, verify_rows, summarize_complete_seeds, METRICS
from core.seeding import SEED_SCHEME
from core.vlnverse_runtime import placement, retry_delay
from scripts.evaluate import check_gpu


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(campaign, fingerprints):
    if campaign.exists():
        raise FileExistsError('Preserving existing campaign: ' + str(campaign))
    if subprocess.check_output(['git', '-C', str(PROJECT), 'status', '--porcelain'], text=True).strip():
        raise RuntimeError('Commit and review the reproduction implementation before freezing it.')
    annotation = resource_root() / 'assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz'
    with gzip.open(annotation, 'rt') as f:
        manifest = make_manifest(json.load(f)['episodes'])
    weights = json.loads(fingerprints.read_text())
    if not weights['complete']:
        raise RuntimeError('Model fingerprint generation is incomplete.')
    for row in weights['files']:
        info = Path(row['path']).stat()
        if (info.st_size, info.st_mtime_ns, info.st_ino) != (row['bytes'], row['mtime_ns'], row['inode']):
            raise RuntimeError('Model changed since its SHA256 was computed: ' + row['path'])
    asset_root = resource_root() / 'assets/VLNVerse'
    scene_manifest = json.loads((asset_root / 'fine_val_unseen_scene_manifest.json').read_text())
    if not set(manifest['scene_counts']) <= {scene['folder'] for scene in scene_manifest}:
        raise RuntimeError('Scene manifest does not contain every selected scene.')
    assets = [item for scene in scene_manifest if scene['folder'] in manifest['scene_counts'] for item in scene['files']]
    def check_asset(item):
        path = asset_root / 'scenes' / item['path']
        if not path.is_file() or path.stat().st_size != item['size']:
            raise RuntimeError('Missing or changed scene asset: ' + str(path))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(check_asset, assets))
    commit = subprocess.check_output(['git', '-C', str(PROJECT), 'rev-parse', 'HEAD'], text=True).strip()
    campaign.mkdir(parents=True)
    snapshot = campaign / 'code'
    snapshot.mkdir()
    with tempfile.TemporaryFile() as stream:
        subprocess.run(['git', '-C', str(PROJECT), 'archive', '--format=tar', commit], stdout=stream, check=True)
        stream.seek(0)
        with tarfile.open(fileobj=stream) as archive:
            for member in archive.getmembers():
                if not member.isdir() and not member.isfile():
                    raise RuntimeError('Unexpected non-regular file in source snapshot: ' + member.name)
                if not (snapshot / member.name).resolve().is_relative_to(snapshot):
                    raise RuntimeError('Unsafe source archive member.')
            archive.extractall(snapshot)
    files = subprocess.check_output(['git', '-C', str(PROJECT), 'ls-files', '-z']).decode().split('\0')
    code_hashes = {name: sha256(snapshot / name) for name in files if name}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    runtime_env = dict(STREAMVLN_VENV=str(model_python('streamvln').parent.parent),
                       JANUSVLN_VENV=str(model_python('janusvln').parent.parent),
                       VLNVERSE_VENV=str(simulation_python().parent.parent), PENG_ISAAC_ROOT=str(isaac_root()),
                       VLN_RESOURCE_ROOT=str(resource_root()), VLN_OUTPUT_ROOT=str(campaign / 'runs'),
                       VLN_SIM_CACHE_ROOT=str(PROJECT / 'benchmarks/vlnverse/runner'),
                       VLN_CODE_COMMIT=commit, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', PIP_NO_INDEX='1')
    units = [dict(seed=seed, scene=scene, expected=count,
                  run_id=f'peng_fine_streamvln_physical_{stamp}_s{seed}_{scene}')
             for seed in manifest['seeds'] for scene, count in sorted(manifest['scene_counts'].items())]
    manifest.update(created_at=now(), campaign=str(campaign), code_root=str(snapshot), code_commit=commit,
                    code_sha256=code_hashes, runtime_env=runtime_env, seed_scheme=SEED_SCHEME,
                    annotation=str(annotation), checked_scene_assets=len(assets), units=units,
                    protocol=dict(physics_tick_cap=25000, warm_up_ticks=500, rgb_resolution=[640,480],
                                  do_sample=False, save_rgb_frames_per_episode=2))
    write_json(campaign / 'manifest.json', manifest)
    write_json(campaign / 'model_fingerprints.json', weights)
    write_json(campaign / 'status.json', dict(status='prepared', completed_episode_runs=0, expected_episode_runs=1250, prepared_at=now()))
    print(json.dumps(dict(prepared=True, campaign=str(campaign), scenes=10, episodes_per_seed=250,
                         total_episode_runs=1250, checked_scene_assets=len(assets), code_commit=commit)), flush=True)


def run_path(manifest, unit):
    return Path(manifest['runtime_env']['VLN_OUTPUT_ROOT']) / 'vlnverse/streamvln/results' / unit['run_id']


def collect(campaign, manifest):
    rows, scene_results = [], []
    completed_units = 0
    for unit in manifest['units']:
        path = run_path(manifest, unit)
        if not (path / 'result.json').exists():
            continue
        result = json.loads((path / 'result.json').read_text())
        proof = json.loads((path / 'validation.json').read_text())
        if result.get('status') != 'complete' or not proof['passed']:
            raise RuntimeError('Invalid completed unit: ' + str(path))
        group = [json.loads(line) for line in (path / 'episodes.jsonl').read_text().splitlines() if line]
        means = verify_rows(group, manifest['scene_episode_ids'][unit['scene']], unit['seed'])
        if any(r['scene'] != unit['scene'] for r in group):
            raise RuntimeError('Episode has the wrong scene.')
        rows.extend(group)
        scene_results.append(dict(seed=unit['seed'], scene=unit['scene'], Count=len(group), **means))
        completed_units += 1
    summary = summarize_complete_seeds(rows, manifest)
    summary.update(completed_units=completed_units, expected_units=50, scenes=scene_results, updated_at=now())
    write_json(campaign / 'summary.json', summary)
    if rows:
        fields = ['run_seed','scene','episode_id','episode_seed',*METRICS,'steps','fail_reason','run_id']
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)
        temporary = campaign / 'episodes.csv.tmp'
        temporary.write_text(buffer.getvalue()); temporary.replace(campaign / 'episodes.csv')
    return summary


def eligible_gpus(rows, allowed, busy):
    eligible = [row['index'] for row in rows if (allowed is None or row['index'] in allowed)
                and row['index'] not in busy and row['free_mib'] >= 34000 and row['utilization'] <= 15]
    return sorted(eligible, key=allowed.index) if allowed is not None else eligible


def gpu_rows():
    text = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.free,utilization.gpu',
                                    '--format=csv,noheader,nounits'], text=True)
    return [dict(index=int(parts[0]), free_mib=int(parts[1]), utilization=int(parts[2]))
            for parts in (line.split(',') for line in text.strip().splitlines())]


def available_memory_mib():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) // 1024
    return 0


def run(campaign, gpus, max_workers, allow_shared):
    manifest = json.loads((campaign / 'manifest.json').read_text())
    snapshot = Path(manifest['code_root'])
    for name, expected in manifest['code_sha256'].items():
        if sha256(snapshot / name) != expected:
            raise RuntimeError('Frozen source file changed: ' + name)
    for row in json.loads((campaign / 'model_fingerprints.json').read_text())['files']:
        info = Path(row['path']).stat()
        if (info.st_size,info.st_mtime_ns,info.st_ino)!=(row['bytes'],row['mtime_ns'],row['inode']):
            raise RuntimeError('Frozen model changed: ' + row['path'])
    env = dict(os.environ, **manifest['runtime_env'])
    status = dict(status='running', started_at=now(), launcher_pid=os.getpid(), allowed_gpus=gpus,
                  allow_shared_gpu=allow_shared, expected_episode_runs=1250, expected_units=50,
                  code_commit=manifest['code_commit'], max_workers=max_workers)
    lock = (campaign / 'campaign.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    active = {}
    steady = {}
    recovery_path = campaign / 'recovery.json'
    recovery = json.loads(recovery_path.read_text()) if recovery_path.exists() else {'failures':{},'blocked':{},'separate_scenes':['kujiale_0234']}
    retry_at = {}
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    if signal.getsignal(signal.SIGHUP) != signal.SIG_IGN:
        signal.signal(signal.SIGHUP, stop)
    try:
        summary = collect(campaign, manifest)
        pending = [i for i, unit in enumerate(manifest['units']) if not (run_path(manifest, unit)/'result.json').exists() and unit['run_id'] not in recovery['blocked']]
        gate = campaign / 'first_scene_gate.json'
        if 0 not in pending and not gate.exists():
            first = manifest['units'][0]
            write_json(gate, dict(passed=True, seed=first['seed'], scene=first['scene'],
                                 episodes=first['expected'], recovered=True, checked_at=now()))
        launch_dir = campaign / 'launches'; launch_dir.mkdir(exist_ok=True)
        while pending or active:
            for index, worker in list(active.items()):
                process = worker['process']
                if process.poll() is None:
                    continue
                worker['log'].close()
                del active[index]
                if process.returncode:
                    unit = manifest['units'][index]
                    failure_file = run_path(manifest, unit) / 'failure.json'
                    failure = json.loads(failure_file.read_text()) if failure_file.exists() else {'kind':'unclassified'}
                    run_id = unit['run_id']
                    failures = recovery['failures'].get(run_id, 0) + 1
                    recovery['failures'][run_id] = failures
                    if failure['kind'] == 'gpu_oom' and unit['scene'] not in recovery['separate_scenes']:
                        recovery['separate_scenes'].append(unit['scene'])
                    delay = retry_delay(failure['kind'], failures)
                    event = dict(event='unit_retry' if delay is not None else 'unit_blocked', run_id=run_id, failures=failures, failure=failure, log=worker['log_path'])
                    if delay is None:
                        recovery['blocked'][run_id] = event
                    else:
                        pending.append(index)
                        retry_at[index] = time.monotonic() + delay
                    write_json(recovery_path, recovery)
                    with (campaign/'recovery_events.jsonl').open('a') as events:
                        events.write(json.dumps(event)+'\n')
                    print(json.dumps(event), flush=True)
                    continue
                unit = manifest['units'][index]
                path = run_path(manifest, unit)
                summary = collect(campaign, manifest)
                if not (path / 'result.json').exists() or not (path / 'validation.json').exists():
                    raise RuntimeError('Unit did not pass complete-scene validation.')
                if index == 0:
                    write_json(gate, dict(passed=True, seed=unit['seed'], scene=unit['scene'],
                        episodes=unit['expected'], validation=str(path/'validation.json'), checked_at=now()))
                print(json.dumps(dict(event='unit_complete', seed=unit['seed'], scene=unit['scene'],
                    completed_units=summary['completed_units'], completed_episode_runs=summary['completed_episode_runs'])), flush=True)
            rows = gpu_rows()
            busy = {g for worker in active.values() for g in (worker['gpu'], worker['sim_gpu'])}
            # Require two consecutive low-load observations for each GPU.
            available = [r for r in rows if r['index'] not in busy and r['utilization'] <= 15]
            steady = {r['index']:steady.get(r['index'],0)+1 for r in available}
            ready_rows = [r for r in available if steady[r['index']] >= 2]
            for index in list(pending):
                if len(active) >= max_workers or available_memory_mib() < 65536: break
                if time.monotonic() < retry_at.get(index,0): continue
                if not gate.exists() and (active or index != 0): continue
                pair = placement(ready_rows, gpus, busy, manifest['units'][index]['scene'] in recovery['separate_scenes'])
                if pair is None: continue
                gpu, sim_gpu = pair
                try:
                    check_gpu(gpu, 25000 if gpu != sim_gpu else 34000, allow_shared)
                    if sim_gpu != gpu: check_gpu(sim_gpu,40000,allow_shared)
                except RuntimeError:
                    continue
                pending.remove(index)
                unit = manifest['units'][index]
                path = run_path(manifest, unit)
                command = [sys.executable, str(snapshot / 'scripts/evaluate.py'), '--backbone', 'streamvln',
                           '--benchmark', 'vlnverse', '--gpu', str(gpu), '--sim-gpu', str(sim_gpu), '--episodes', '0', '--mode', 'physical',
                           '--seed', str(unit['seed']), '--scenes', unit['scene']]
                command += ['--resume' if (path / 'run.json').exists() else '--run-id', unit['run_id']]
                if allow_shared:
                    command.append('--allow-shared-gpu')
                log_path = launch_dir / f'{unit["run_id"]}_{time.time_ns()}.log'
                log = log_path.open('w')
                worker_env = env.copy()
                if sim_gpu != 0:
                    worker_env['VLN_SIM_CACHE_ROOT'] = str(campaign / 'sim_cache' / f'gpu_{sim_gpu}')
                # Preserve prior failure evidence; do not mistake it for a new failure.
                failure_file = path / 'failure.json'
                if failure_file.exists():
                    failure_file.rename(path / f'failure_{time.time_ns()}.json')
                process = subprocess.Popen(command, cwd=snapshot, env=worker_env, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                active[index] = dict(process=process, log=log, log_path=str(log_path), gpu=gpu, sim_gpu=sim_gpu)
                print(json.dumps(dict(event='unit_started', seed=unit['seed'], scene=unit['scene'],
                    expected=unit['expected'], run_id=unit['run_id'], gpu=gpu, pid=process.pid)), flush=True)
                # Re-read GPU/RAM availability before admitting another model load.
                break
            workers = []
            for index, worker in active.items():
                unit = manifest['units'][index]
                official = snapshot / 'benchmarks/vlnverse/upstream/logs' / unit['run_id'] / 'kujiale_result.json'
                try:
                    current = json.loads(official.read_text())['val_unseen']['Count'] if official.exists() else 0
                except (ValueError, KeyError):
                    current = 0
                workers.append(dict(**unit, gpu=worker['gpu'], sim_gpu=worker['sim_gpu'], pid=worker['process'].pid,
                                    log=worker['log_path'], completed=current))
            status.update(status='running' if active else 'waiting_for_resources', workers=workers,
                          completed_episode_runs=summary['completed_episode_runs']+sum(w['completed'] for w in workers),
                          validated_episode_runs=summary['completed_episode_runs'], completed_units=summary['completed_units'],
                          pending_units=len(pending), blocked_units=recovery['blocked'], available_memory_mib=available_memory_mib(),
                          gpu_snapshot=rows, first_scene_passed=gate.exists(), updated_at=now())
            write_json(campaign / 'status.json', status)
            if pending or active:
                time.sleep(10)
        summary = collect(campaign, manifest)
        if not summary['complete'] or summary['completed_episode_runs'] != 1250:
            raise RuntimeError('Campaign incomplete after the planned 50 units.')
        status.update(status='complete', completed_episode_runs=1250, completed_units=50, finished_at=now())
    except BaseException as error:
        status.update(status='stopped' if isinstance(error, KeyboardInterrupt) else 'failed', error=str(error), updated_at=now())
        raise
    finally:
        for worker in active.values():
            process = worker['process']
            if process.poll() is None:
                # Each group was created by this supervisor; its runner cleans its model/simulator children.
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=60)
            worker['log'].close()
        write_json(campaign / 'status.json', status)
        lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare','run','status'])
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--fingerprints', type=Path)
    parser.add_argument('--gpus', type=int, nargs='+', help='Allowed GPU indices; default all visible cards')
    parser.add_argument('--max-workers', type=int, default=2)
    parser.add_argument('--allow-shared-gpu', action='store_true')
    args = parser.parse_args()
    if args.max_workers < 1 or (args.gpus is not None and any(g < 0 for g in args.gpus)):
        parser.error('Invalid worker count or GPU index.')
    campaign = args.campaign.resolve()
    if args.action == 'prepare':
        if args.fingerprints is None: parser.error('prepare requires --fingerprints')
        prepare(campaign, args.fingerprints.resolve())
    elif args.action == 'run':
        run(campaign, args.gpus, args.max_workers, args.allow_shared_gpu)
    else:
        print((campaign / 'status.json').read_text())


if __name__ == '__main__':
    main()
