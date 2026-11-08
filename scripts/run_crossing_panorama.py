"""Supervise registered scene-only capture jobs and release only owned processes."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from test_crossing_single_gpu import gpu_snapshot, process, now, write
from run_crossing_local_batch import cleanup

ROOT = Path(__file__).resolve().parents[1]


def gpu_admission_ok(row, uuid, compute_apps, allow_shared=False, min_free_mib=24576):
    if allow_shared:
        return row['free_mib'] >= min_free_mib and row['utilization'] <= 10
    return row['used_mib'] < 1024 and row['utilization'] <= 10 and uuid not in compute_apps


def wait_for_idle(gpu, uuid, admissions, output, phase, timeout=1800, allow_shared=False, min_free_mib=24576):
    """Require consecutive low-load samples, respecting explicit shared admission."""
    deadline = time.monotonic() + timeout
    consecutive = 0
    while consecutive < 2:
        snap = gpu_snapshot()
        row = next(g for g in snap['gpus'] if g['index'] == gpu)
        available = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
        idle = gpu_admission_ok(row, uuid, snap['compute_apps'], allow_shared, min_free_mib)
        enough_memory = available >= 64 * 1024 ** 2
        snap.update(target_gpu=gpu, admission_idle=idle, host_memory_available_kib=available,
                    allow_shared_gpu=allow_shared, min_free_mib=min_free_mib if allow_shared else None)
        admissions.append(snap)
        write(output / 'admission.json', admissions)
        consecutive = consecutive + 1 if idle and enough_memory else 0
        if not idle or not enough_memory:
            phase('waiting_for_resources', admission_gpu=row, host_memory_available_kib=available,
                  admission_note='Waiting without stopping any foreign process; require two idle samples.')
        if consecutive == 2:
            return
        if time.monotonic() >= deadline:
            raise TimeoutError('Resources not available after 1800 seconds; no foreign process stopped')
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--gpu', type=int, required=True)
    ap.add_argument('--allow-shared-gpu', action='store_true', help='Only with explicit authorization: allow existing processes if low-load and enough free VRAM')
    ap.add_argument('--min-free-mib', type=int, default=24576, help='Shared admission minimum free VRAM; at least 24 GiB')
    a = ap.parse_args()
    if a.min_free_mib < 24576:
        ap.error('Shared admission must retain at least 24 GiB free before launch')
    out = a.output.resolve()
    manifest = json.loads((out / 'manifest.json').read_text())
    prov = json.loads((out / 'provenance.json').read_text())
    if json.loads((out / 'status.json').read_text())['phase'] != 'prepared':
        raise RuntimeError('This capture was already started; use a new run, not an overwrite.')
    for rel, digest in prov['source_hashes'].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, f'Source changed after preparation: {rel}'
    reused_scenes = manifest.get('reused_completed_scenes', [])
    reused_images = manifest.get('reused_unique_images', 0)
    # Recheck copied RGB before launching any new simulator.
    for scene in reused_scenes:
        result = json.loads((out / 'scenes' / (scene + '.json')).read_text())
        for pano in result['results']:
            metadata = json.loads((out / pano['metadata']).read_text())
            for view in metadata['views']:
                assert hashlib.sha256((out / view['path']).read_bytes()).hexdigest() == view['sha256']
    state = dict(phase='admission', started_at=now(), supervisor=process(os.getpid()), gpu=a.gpu,
                 model_calls=0, navigation_actions=0, completed_scenes=len(reused_scenes),
                 completed_unique_images=reused_images, reused_unique_images=reused_images,
                 newly_captured_unique_images=0, allow_shared_gpu=a.allow_shared_gpu,
                 admission_min_free_mib=a.min_free_mib if a.allow_shared_gpu else None)
    def phase(name, **kwargs):
        state.update(phase=name, updated_at=now(), **kwargs)
        write(out / 'status.json', state)
        print(json.dumps(state), flush=True)
    def stop(*_):
        raise KeyboardInterrupt('Capture termination requested')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    locks, clean, admissions = [], [], []
    child = None
    error = None
    phase('admission')
    try:
        for prefix in ['peng_vlnverse_gpu_', 'vln_2026_gpu_']:
            f = Path(f'/tmp/{prefix}{a.gpu}.lock').open('a')
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locks.append(f)
        uuid = subprocess.check_output(['nvidia-smi', '-i', str(a.gpu), '--query-gpu=uuid', '--format=csv,noheader'], text=True).strip()
        env = {k: v for k, v in os.environ.items() if 'proxy' not in k.lower()
               and not k.startswith(('VLN_ORACLE_', 'CUDA_VISIBLE_DEVICES', 'PENG_SMOKE_'))}
        # Vulkan keeps physical indices; CUDA/PhysX sees only this GPU at logical index 0.
        env.update(CUDA_VISIBLE_DEVICES=uuid, VLN_SIM_CACHE_ROOT=str(out / 'runtime_cache'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                   PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4')
        for asset in manifest['scenes']:
            if asset['scene'] in reused_scenes:
                continue
            scene = asset['scene']
            phase('admission', current_scene=scene, child_pid=None)
            # Admission is repeated between scenes so a newly occupied GPU is never taken over.
            wait_for_idle(a.gpu, uuid, admissions, out, phase,
                          allow_shared=a.allow_shared_gpu, min_free_mib=a.min_free_mib)
            cmd = ['bash', str(ROOT / 'scripts/run_crossing_panorama_isaac.sh'),
                   str(ROOT / 'scripts/render_crossing_panorama.py'), '--output', str(out), '--scene', scene, '--gpu', str(a.gpu)]
            with (out / 'logs' / (scene + '.log')).open('x') as log:
                child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            write(out / 'scenes' / (scene + '.process.json'), dict(command=cmd, identity=process(child.pid), started_at=now()))
            phase('rendering', current_scene=scene, child_pid=child.pid)
            rc = child.wait(timeout=1800)
            record = dict(scene=scene, cleanup=cleanup(child), exit_code=rc)
            clean.append(record)
            child = None
            if record['cleanup'].get('remaining'):
                raise RuntimeError('Owned processes remain after scene exit')
            if rc:
                raise RuntimeError(f'Scene {scene} exited {rc}; see its log')
            result = json.loads((out / 'scenes' / (scene + '.json')).read_text())
            state['completed_scenes'] += 1
            state['completed_unique_images'] += sum(p['images'] for p in result['results'])
            state['newly_captured_unique_images'] = state['completed_unique_images'] - reused_images
            phase('scene_complete')
        assert state['completed_unique_images'] == manifest['expected_unique_images']
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        if child is not None:
            clean.append(dict(scene=state.get('current_scene'), cleanup=cleanup(child)))
        snap = gpu_snapshot()
        remaining = [p for c in clean for p in c['cleanup'].get('remaining', [])]
        write(out / 'cleanup.json', dict(records=clean, remaining_owned_processes=remaining, gpu_after_cleanup=snap))
        for f in locks:
            f.close()
        phase('capture_complete' if error is None and not remaining else 'failed', error=error,
              finished_at=now(), owned_processes_exited=not remaining)
    return 1 if error or remaining else 0


if __name__ == '__main__':
    sys.exit(main())
