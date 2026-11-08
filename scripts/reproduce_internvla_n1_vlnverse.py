"""Seed-0 full fine Val Unseen, isolated official N1 agent/evaluator, safe queue."""
import argparse
import collections
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'backbone/internvla_n1'
CAMPAIGN = ROOT / 'outputs/reproduction/internvla_n1_fine825_seed0_20261102'
RESOURCE = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng')
ASSETS = RESOURCE / 'assets/VLNVerse'
CHECKPOINT = RESOURCE / 'models/InternVLA-N1-wo-dagger'
PYTHON = MODEL / '.venv/bin/python'
SIM_PYTHON = ROOT / 'benchmarks/vlnverse/.venv/bin/python'


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def prepare():
    annotation = ASSETS / 'data/raw_data/final_splits/fine_val_unseen.json.gz'
    episodes = json.load(gzip.open(annotation, 'rt'))['episodes']
    counts = collections.Counter(e['scan'] for e in episodes)
    assert len(episodes) == 825 and len(counts) == 33
    assert len({e['episode_id'] for e in episodes}) == 825
    manifest = {'seed': 0, 'seed_scope': 'official seed 0 at each scene worker startup; original within-scene order',
                'episodes': 825, 'scene_counts': dict(sorted(counts.items())),
                'annotation_sha256': hashlib.sha256(annotation.read_bytes()).hexdigest(),
                'checkpoint_repo': 'InternRobotics/InternVLA-N1-wo-dagger',
                'checkpoint_revision': '377366bc480b6643b807b6ea8fa642715683cf7b',
                'mode': 'official H1 flash', 'max_step': 400, 'warm_up_step': 500,
                'episode_ids': [e['episode_id'] for e in episodes]}
    path = CAMPAIGN / 'manifest.json'
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise RuntimeError('Manifest changed; refusing to resume')
    atomic(path, manifest)
    for scene in counts:
        group = [e for e in episodes if e['scan'] == scene]
        atomic(CAMPAIGN / 'datasets' / (scene + '.json'), group)
    atomic(CAMPAIGN / 'datasets/smoke.json', episodes[:2])
    print(json.dumps({'episodes': len(episodes), 'scenes': len(counts), 'seed': 0}))


def gpu_snapshot():
    text = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.free,utilization.gpu', '--format=csv,noheader,nounits'], text=True)
    return {int(v[0]): {'free': int(v[1]), 'util': int(v[2])} for line in text.splitlines() if (v := line.split(','))}


def placement(snapshot, excluded, separate=False):
    candidates = [g for g, v in snapshot.items() if g not in excluded and v['util'] <= 15]
    candidates.sort(key=lambda g: snapshot[g]['free'], reverse=True)
    if not separate:
        for g in candidates:
            if snapshot[g]['free'] >= 42000:
                return g, g
    # Keep generous headroom until model and simulator peaks are measured.
    for g in candidates:
        if snapshot[g]['free'] >= 30000:
            for sim in candidates:
                if sim != g and snapshot[sim]['free'] >= 40000:
                    return g, sim
    return None


def stop(process):
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def write_config(output, port):
    official = MODEL / 'vendor/scripts/eval/configs/h1_internvla_n1_cfg_vlnverse_fine_val_unseen.py'
    config = output / 'config.py'
    config.write_text(f'''import runpy
eval_cfg = runpy.run_path({str(official)!r})['eval_cfg']
eval_cfg.agent.server_host = '127.0.0.1'
eval_cfg.agent.server_port = {port}
eval_cfg.agent.model_settings['model_path'] = {str(CHECKPOINT)!r}
eval_cfg.agent.model_settings['vis_debug_path'] = {str(output / 'videos')!r}
eval_cfg.task.task_name = 'evaluation'
eval_cfg.task.scene.scene_data_dir = {str(ASSETS / 'scenes')!r}
eval_cfg.task.robot_usd_path = {str(ASSETS / 'Embodiments/vln-pe/h1/h1_internvla.usd')!r}
eval_cfg.dataset.dataset_settings['base_data_dir'] = {str(output / 'dataset/fine')!r}
''')
    return config


def worker(scene, gpu, sim_gpu):
    # Lock names match the existing StreamVLN queue, preventing cross-campaign races.
    locks = []
    for g in sorted({gpu, sim_gpu}):
        f = open(f'/tmp/peng_vlnverse_gpu_{g}.lock', 'a')
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(f)
    current = gpu_snapshot()
    if current[gpu]['util'] > 15 or current[sim_gpu]['util'] > 15:
        raise RuntimeError('GPU became busy before startup')
    if current[gpu]['free'] < (42000 if gpu == sim_gpu else 30000) or (gpu != sim_gpu and current[sim_gpu]['free'] < 40000):
        raise RuntimeError('GPU headroom changed before startup')
    output = CAMPAIGN / 'runs' / scene / str(time.time_ns())
    output.mkdir(parents=True)
    episodes = json.loads((CAMPAIGN / 'datasets' / (scene + '.json')).read_text())
    atomic(output / 'episodes.json', episodes)
    target = output / 'dataset/fine/val_unseen/val_unseen.json.gz'
    target.parent.mkdir(parents=True)
    with gzip.open(target, 'wt') as f:
        json.dump({'episodes': episodes}, f)
    (output / 'checkpoints').mkdir()
    (output / 'checkpoints/depth_anything_v2_vits.pth').symlink_to(RESOURCE / 'models/Depth-Anything-V2-Small/depth_anything_v2_vits.pth')
    (output / 'vis_debug_pix').mkdir()
    env = os.environ.copy()
    for key in ('VLN_EVAL_SEED', 'PENG_SMOKE_BACKEND', 'VLN_SIM_RENDER_GPU', 'PYTHONPATH',
                'http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY'):
        env.pop(key, None)
    env.update(CUDA_VISIBLE_DEVICES=str(gpu), PYTHONHASHSEED='0', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1',
               NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost', N1_RUN_ROOT=str(output))
    agent = sim = None
    result = {'scene': scene, 'seed': 0, 'gpu': gpu, 'sim_gpu': sim_gpu, 'output': str(output), 'expected': len(episodes), 'started': time.time()}
    def interrupted(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupted)
    try:
        with (output / 'agent.log').open('w') as log:
            agent = subprocess.Popen([str(PYTHON), '-u', str(MODEL / 'service.py'), '--output', str(output), '--checkpoint', str(CHECKPOINT)],
                                     cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        result['agent_pid'] = agent.pid
        atomic(output / 'execution.json', result)
        deadline = time.monotonic() + 1800
        while not (output / 'ready.json').exists():
            if agent.poll() is not None: raise RuntimeError('Model startup failed')
            if time.monotonic() > deadline: raise RuntimeError('Model startup timeout')
            time.sleep(5)
        port = json.loads((output / 'ready.json').read_text())['port']
        config = write_config(output, port)
        sim_env = dict(env, CUDA_VISIBLE_DEVICES=str(sim_gpu), VLN_SIM_RENDER_GPU=str(sim_gpu))
        with (output / 'simulator.log').open('w') as log:
            sim = subprocess.Popen(['bash', str(MODEL / 'run_sim.sh'), str(config)], cwd=output, env=sim_env,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        result['simulator_pid'] = sim.pid
        atomic(output / 'execution.json', result)
        while sim.poll() is None:
            if agent.poll() is not None: raise RuntimeError('Model service exited')
            if (output / 'inference_error.txt').exists() or (output / 'service_error.txt').exists():
                raise RuntimeError('Model inference error; scores rejected')
            newest = max((output / 'agent.log').stat().st_mtime, (output / 'simulator.log').stat().st_mtime)
            if time.time() - newest > 900: raise RuntimeError('No runtime progress for 15 minutes')
            time.sleep(5)
        if sim.returncode != 0: raise RuntimeError(f'Simulator exited {sim.returncode}')
        subprocess.run([str(SIM_PYTHON), str(MODEL / 'validate_results.py'), str(output)], check=True, env=env,
                       stdout=(output / 'validation.log').open('w'), stderr=subprocess.STDOUT)
        result.update(status='complete', completed=len(episodes), finished=time.time())
        atomic(CAMPAIGN / 'completed' / (scene + '.json'), result)
    except BaseException as e:
        result.update(status='failed', error=repr(e), finished=time.time())
        raise
    finally:
        stop(sim)
        stop(agent)
        atomic(output / 'execution.json', result)


def status():
    done = [json.loads(p.read_text()) for p in (CAMPAIGN / 'completed').glob('*.json') if p.stem != 'smoke']
    value = {'completed': sum(x['completed'] for x in done), 'expected': 825, 'complete_scenes': len(done), 'seed': 0}
    metadata = CAMPAIGN / 'checkpoint_metadata.json'
    if metadata.exists():
        received = total = 0
        for item in json.loads(metadata.read_text())['siblings']:
            if not item['rfilename'].endswith('.safetensors'):
                continue
            target = CHECKPOINT / item['rfilename']
            if not target.exists():
                target = target.with_name(target.name + '.partial')
            received += target.stat().st_size if target.exists() else 0
            total += item['size']
        value['weights'] = {'bytes': received, 'total_bytes': total, 'percent': round(100*received/total, 2)}
    return value


def supervise():
    prepare()
    lock = (CAMPAIGN / 'supervisor.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    active = {}
    previous = {}
    failures = {}
    while True:
        for scene, job in list(active.items()):
            if job['process'].poll() is not None:
                if job['process'].returncode != 0:
                    failures[scene] = {'returncode': job['process'].returncode, 'log': job['log']}
                del active[scene]
        snapshot = gpu_snapshot()
        eligible = {g: v for g, v in snapshot.items() if g in previous and v['util'] <= 15 and previous[g]['util'] <= 15}
        progress = status()
        state = dict(progress, pid=os.getpid(), updated=time.time(), active={s: {k: v for k, v in j.items() if k != 'process'} for s, j in active.items()}, failures=failures)
        ready = (CAMPAIGN / 'assets_verified.json').exists() and (CAMPAIGN / 'imports_verified.json').exists()
        smoke_passed = (CAMPAIGN / 'completed/smoke.json').exists()
        state['phase'] = 'waiting_assets_or_dependencies' if not ready else ('evaluation' if smoke_passed else 'smoke_validation')
        execution = CAMPAIGN / 'download_execution.json'
        if execution.exists():
            download = json.loads(execution.read_text())
            proc = Path('/proc') / str(download['pid'])
            try:
                alive = proc.joinpath('stat').read_text().split()[21] == download['start_ticks'] and 'prepare_internvla_n1.py' in proc.joinpath('cmdline').read_text()
            except OSError:
                alive = False
            state['download'] = dict(download, alive=alive)
            if not (CAMPAIGN / 'assets_verified.json').exists() and not alive:
                state['phase'] = 'blocked_download_error'
        if failures:
            state['phase'] = 'blocked_runtime_error'
        if progress['completed'] == 825:
            state['phase'] = 'complete'
            all_rows = []
            for p in (CAMPAIGN / 'completed').glob('*.json'):
                if p.stem == 'smoke': continue
                run = Path(json.loads(p.read_text())['output'])
                all_rows.extend(json.loads((run / 'validated_rows.json').read_text()))
            manifest = json.loads((CAMPAIGN / 'manifest.json').read_text())
            assert len(all_rows) == 825 and {r['episode_id'] for r in all_rows} == set(manifest['episode_ids'])
            atomic(CAMPAIGN / 'all_results.json', all_rows)
            atomic(CAMPAIGN / 'summary.json', {k: sum(float(r['info'][k]) for r in all_rows) / 825 for k in ('success', 'spl', 'NE', 'osr', 'TL')})
            atomic(CAMPAIGN / 'status.json', state)
            return
        atomic(CAMPAIGN / 'status.json', state)
        if ready and not failures and len(active) < 8:
            scenes = list(json.loads((CAMPAIGN / 'manifest.json').read_text())['scene_counts']) if smoke_passed else ['smoke']
            pending = [s for s in scenes if s not in active and not (CAMPAIGN / 'completed' / (s + '.json')).exists()]
            excluded = {g for j in active.values() for g in (j['gpu'], j['sim_gpu'])}
            # Existing queue holds these same advisory locks; probe before starting.
            for g in eligible:
                f = open(f'/tmp/peng_vlnverse_gpu_{g}.lock', 'a')
                try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError: excluded.add(g)
                finally: f.close()
            available_kib = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
            groups = 0
            for proc in Path('/proc').glob('[0-9]*/cmdline'):
                try:
                    cmd = proc.read_bytes()
                    if b'VLN_2026_Autumn' in cmd and b'/service.py' in cmd and b'--checkpoint' in cmd:
                        groups += 1
                except (OSError, PermissionError): pass
            selected = placement(eligible, excluded, separate=bool(pending and pending[0] == 'kujiale_0234'))
            if pending and selected and available_kib >= 64 * 1024**2 * (groups + 1):
                scene = pending[0]
                gpu, sim_gpu = selected
                logfile = CAMPAIGN / 'worker_logs' / (scene + '.log')
                logfile.parent.mkdir(exist_ok=True)
                with logfile.open('a') as log:
                    process = subprocess.Popen([sys.executable, '-u', __file__, 'worker', '--scene', scene, '--gpu', str(gpu), '--sim-gpu', str(sim_gpu)],
                                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                active[scene] = {'process': process, 'pid': process.pid, 'gpu': gpu, 'sim_gpu': sim_gpu, 'log': str(logfile)}
        previous = snapshot
        time.sleep(30)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['prepare', 'run', 'worker', 'status'])
    p.add_argument('--scene')
    p.add_argument('--gpu', type=int)
    p.add_argument('--sim-gpu', type=int)
    a = p.parse_args()
    if a.command == 'prepare': prepare()
    elif a.command == 'worker': worker(a.scene, a.gpu, a.sim_gpu)
    elif a.command == 'run': supervise()
    else: print(json.dumps(status()))
