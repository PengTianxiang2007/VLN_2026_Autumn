"""Resume only unscored episodes, borrowing the two explicitly retained models."""
import csv
import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core.codex_client import now, process_start_ticks, save, sha256
from core.codex_serial_config import DEFAULTS, snapshot_source
from core.codex_serial_runtime import ReviewWorker
from core.vlnverse_runtime import ExistingModelService
from core.seeding import episode_seed

OUT = ROOT / 'outputs/serial_recovery/codex_v001' / HERE.name
PREVIOUS = ROOT / 'outputs/serial_recovery/codex_v001/run_20261126_12_scene0208_0240_after_terminalfix'
HOLD = ROOT / 'outputs/serial_recovery/codex_v001/run_20261127_01_model_hold/launch.json'
RETAINED = {1548476, 1548482}


def read(path):
    return json.loads(path.read_text())


def credentials():
    values = {}
    for line in (ROOT / '.env.easyjev.local').read_text().splitlines():
        line = line.strip().removeprefix('export ')
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        parts = shlex.split(value, comments=True)
        values[key.strip()] = parts[0] if parts else ''
    if not values.get('JEV_API_KEY') or values.get('JEV_BASE_URL', '').rstrip('/') != 'https://api.easyjev.online':
        raise RuntimeError('Missing or mismatched private JEV configuration')
    return values['JEV_API_KEY']


def admit():
    models = [ExistingModelService(HOLD, gpu, 'StreamVLN', 2, ROOT) for gpu in (0, 1)]
    rows = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.free', '--format=csv,noheader,nounits'], text=True)
    apps = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'], text=True)
    for model in models:
        gpu = model.entry['gpu']
        row, = [s.split(', ') for s in rows.splitlines() if int(s.split(',')[0]) == gpu]
        pids = {int(s.split(',')[1]) for s in apps.splitlines() if s.split(',')[0].strip() == row[1]}
        if pids - (RETAINED | {model.pid}) or int(row[2]) < 12000:
            raise RuntimeError(f'GPU {gpu} has unexpected processes or insufficient simulator memory')
        for pid in pids & RETAINED:
            proc = Path(f'/proc/{pid}')
            if proc.joinpath('cwd').resolve() != ROOT or b'run_20261126_08_five_goal120/simulate.py' not in proc.joinpath('cmdline').read_bytes():
                raise RuntimeError('Retained simulator ownership mismatch')
    available = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))
    if available < 128 * 1024**2:
        raise RuntimeError('Insufficient host memory for two simulators')


def prepare():
    if DEFAULTS['reasoning_effort'] != 'high' or DEFAULTS['movement_budget'] != 180:
        raise ValueError('Protocol differs from approved high / 180')
    admit()
    previous = read(PREVIOUS / 'manifest.json')
    lanes, excluded = [], []
    for old in previous['workers']:
        completed = []
        for path in Path(old['serial_output']).glob('episodes/*/attempt_*/result.json'):
            item = read(path)
            if 'success' in item.get('metrics', {}) and 'spl' in item['metrics']:
                completed.append(item['episode_id'])
        if len(completed) != len(set(completed)):
            raise ValueError('Duplicate formal episode result')
        excluded.extend(completed)
        ids = [eid for eid in old['episode_ids'] if eid not in completed]
        gpu = old['gpu']
        run_id = f"peng_fine_codex_serial_{old['scene'].removeprefix('kujiale_')}_high_20261127_resume30_g{gpu}"
        lanes.append(dict(gpu=gpu, scene=old['scene'], episode_ids=ids, run_id=run_id,
                          serial_output=str(OUT / f'gpu{gpu}/serial'),
                          native_output=str(ROOT / 'outputs/vlnverse/streamvln/results' / run_id)))
    if [len(w['episode_ids']) for w in lanes] != [21, 9] or len(excluded) != 18:
        raise ValueError('Expected 30 remaining episodes and 18 previously scored successors')
    selected = {eid for w in lanes for eid in w['episode_ids']}
    baseline_source = HERE.parent / PREVIOUS.name / 'baseline48.csv'
    with baseline_source.open() as stream:
        baseline = [r for r in csv.DictReader(stream) if r['episode_id'] in selected and int(r['run_seed']) == 2]
    if {r['episode_id'] for r in baseline} != selected or len(baseline) != 30:
        raise ValueError('Incomplete paired baseline')
    if any(int(r['episode_seed']) != episode_seed(2, r['episode_id']) for r in baseline):
        raise ValueError('Baseline seed mismatch')
    OUT.mkdir(parents=True, exist_ok=False)
    with (HERE / 'baseline30.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(baseline[0]))
        writer.writeheader(); writer.writerows(baseline)
    manifest = dict(prepared_at=now(), workers=lanes, seed=2, protocol=DEFAULTS,
                    excluded_scored_successors=sorted(excluded), excluded_completed_scene='kujiale_0036 (all 25)',
                    model_manifest=str(HOLD), queue_sha256=sha256(Path(__file__)),
                    bridge_sha256=sha256(ROOT / 'benchmarks/vlnverse/upstream/scripts/vlnverse_robot_bridge.py'))
    save(HERE / 'manifest.json', manifest)
    save(OUT / 'manifest.json', manifest)
    snapshot_source(OUT)
    shutil.copy2(__file__, OUT / 'source/queue.py')
    shutil.copy2(ROOT / 'benchmarks/vlnverse/upstream/scripts/vlnverse_robot_bridge.py', OUT / 'source/bridge_compat.py')


def probe():
    folder = OUT / 'jev_probe'
    folder.mkdir()
    source = ROOT / 'outputs/multiview_capture/v001/run_20261117_03/capture/episodes/kujiale_0036_0_0/attempt_1794972488070620490/steps/000000/policy_front.png'
    shutil.copy2(source, folder / 'front.png')
    save(folder / 'config.json', DEFAULTS)
    save(folder / 'start.json', dict(episode_id='startup_probe', scene='kujiale_0036', instruction='Runtime connectivity probe only; no navigation.'))
    worker = ReviewWorker(folder)
    try:
        result = worker.request(dict(episode_id='startup_probe', frame=0, stop_requested=False,
                                     native_front=dict(image='front.png', sha256=sha256(folder / 'front.png'))), lambda: None)
        if result.get('decision') != 'continue':
            raise RuntimeError('JEV probe was not acknowledged')
    finally:
        worker.close()
    save(folder / 'verification.json', dict(phase='complete', time=now(), actual_jev=True, included_in_navigation=False))


def worker():
    lock = (OUT / 'queue.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state = dict(phase='checking_jev', time=now(), workers=[])
    children = []
    def persist():
        state['updated_at'] = now()
        save(OUT / 'queue_status.json', state)
    persist()
    try:
        manifest = read(OUT / 'manifest.json')
        snapshot_source(OUT)
        if sha256(Path(__file__)) != manifest['queue_sha256'] or sha256(ROOT / 'benchmarks/vlnverse/upstream/scripts/vlnverse_robot_bridge.py') != manifest['bridge_sha256']:
            raise RuntimeError('Queue/bridge source changed')
        os.environ['JEV_API_KEY'] = credentials()
        os.environ['VLN_NODE_BINARY'] = shutil.which('node') or '/etc/dsw/runtime/export_bin/node'
        probe()
        admit()
        for lane in manifest['workers']:
            dst = OUT / f"gpu{lane['gpu']}"
            dst.mkdir()
            env = {k: v for k, v in os.environ.items() if not k.startswith(('VLN_', 'PENG_', 'STREAMVLN_', 'JANUSVLN_')) and k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'VIRTUAL_ENV')}
            env.update(JEV_API_KEY=os.environ['JEV_API_KEY'], VLN_NODE_BINARY=os.environ['VLN_NODE_BINARY'],
                       VLN_MODEL_READY_TIMEOUT='3600', VLN_OUTPUT_ROOT=str(ROOT / 'outputs'),
                       VLN_SIM_CACHE_ROOT=str(dst / 'runtime_cache'),
                       VLN_CODE_COMMIT=read(OUT / 'source_manifest.json')['git_head'],
                       PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
            command = [sys.executable, '-Bu', str(ROOT / 'benchmarks/vlnverse/runner/run_full.py'),
                       '--method', 'StreamVLN', '--mode', 'physical', '--seed', '2',
                       '--gpu', str(lane['gpu']), '--sim-gpu', str(lane['gpu']), '--allow-shared-gpu',
                       '--model-service-manifest', str(HOLD), '--run-id', lane['run_id'],
                       '--codex-serial-output', lane['serial_output'], '--episode-ids', *lane['episode_ids']]
            with (dst / 'launcher.log').open('x') as log:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            children.append(child)
            entry = dict(lane, phase='launched', launcher_pid=child.pid,
                         launcher_start_ticks=process_start_ticks(child.pid), command=command, started_at=now())
            save(dst / 'launch.json', entry)
            state['workers'].append(entry)
            persist()
        state['phase'] = 'running'
        persist()
        while any(child.poll() is None for child in children):
            for child, lane in zip(children, state['workers']):
                if child.poll() is not None and lane['phase'] == 'launched':
                    lane.update(phase='complete' if child.returncode == 0 else 'failed', returncode=child.returncode, finished_at=now())
            persist()
            time.sleep(30)
        for child, lane in zip(children, state['workers']):
            lane.update(phase='complete' if child.returncode == 0 else 'failed', returncode=child.returncode, finished_at=now())
        state['phase'] = 'complete' if all(child.returncode == 0 for child in children) else 'failed'
    except Exception as error:
        state.update(phase='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    state['cleanup_pending'] = True
        state['finished_at'] = now()
        persist()


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']:
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        worker()
    elif not sys.argv[1:]:
        prepare()
        with (OUT / 'queue.log').open('x') as log:
            child = subprocess.Popen([sys.executable, '-Bu', str(Path(__file__)), '--worker'], cwd=ROOT,
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        save(OUT / 'queue_launch.json', dict(pid=child.pid, start_ticks=process_start_ticks(child.pid), time=now()))
        print(json.dumps(dict(queue_pid=child.pid, tasks=30, output=str(OUT))))
    else:
        raise SystemExit('Use no args to enqueue; --worker is internal')
