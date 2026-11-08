"""Prepare or supervise a fixed three-RGB, 1..5 scoring batch on a local vLLM service."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from core.agent_route_choice import now, read, write
from core.crossing_lite import digest, sha, select_cases, windows, request, request_seed, validate
from run_crossing_local_batch import cleanup
from test_crossing_single_gpu import gpu_snapshot, process

DATASET = ROOT / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
MODEL = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/Qwen3.5-4B')
SOURCES = ['core/crossing_lite.py', 'scripts/run_crossing_lite.py',
           'scripts/export_crossing_lite.py', 'core/crossing_lite_review.js',
           'scripts/check_crossing_lite.cjs', 'scripts/export_crossing_iteration.py',
           'core/crossing_campaign_template.html', 'core/crossing_campaign_panel.html',
           'core/crossing_visualization_template.json', 'core/agent_route_choice.py',
           'scripts/run_crossing_local_batch.py', 'scripts/test_crossing_single_gpu.py']


def prepare(out, reg):
    if (out / 'manifest.json').exists():
        raise ValueError('Use a new run directory')
    out.mkdir(parents=True, exist_ok=True)
    seed = 20261107
    selected = select_cases([json.loads(x) for x in (DATASET / 'evaluation/episodes.jsonl').read_text().splitlines()],
                            {'failure': 10, 'success': 20}, seed)
    index = {e['episode_id']: e for e in map(json.loads, (DATASET / 'inputs/episodes.jsonl').read_text().splitlines())}
    tasks = []
    inputs = []
    for case in selected:
        eid = case['episode_id']
        obs_path = DATASET / index[eid]['observations']
        obs = read(obs_path)
        frames = []
        for t, images in windows(obs):
            for im in images:
                assert sha(DATASET / im['rgb']) == im['rgb_sha256']
            frames.append(dict(frame=t, images=images))
        tasks.append(dict(episode_id=eid, frames=frames))
        inputs.append(dict(episode_id=eid, observations_sha256=sha(obs_path), calls=len(frames)))
    write(out / 'evaluation_selection.json', selected)
    write(reg / 'selection.json', selected)
    write(out / 'input_audit.json', dict(passed=True, cases=inputs, exact_three_frame_windows=True))
    for i in range(4):
        write(out / ('tasks_%d.json' % i), tasks[i::4])
    shutil.copy2(reg / 'prompt_en.txt', out / 'prompt_en.txt')
    config = dict(kind='crossing_lite', version='lite_v001', tag='qwen35_4b_rgb3_score5',
                  dataset=str(DATASET), dataset_id=read(DATASET / 'dataset.json')['dataset_id'],
                  model_path=str(MODEL), model='crossing-lite-qwen35-4b', gpu=0,
                  concurrency=4, gpu_memory_utilization=0.50, max_model_len=8192,
                  max_images=3, max_tokens=256, temperature=0, thinking=False, seed=seed,
                  selection_rule='Seeded shuffled per-scene round-robin within failure/success; no prediction-based selection',
                  groups={'failure': 10, 'success': 20}, expected_calls=sum(len(t['frames']) for t in tasks),
                  request_timeout_seconds=180, network_attempts=2, batch_timeout_seconds=28800,
                  structured_output='json_schema', score_range=[1, 5], uturn_counts=True,
                  input_policy='Exact t-2,t-1,t RGB only; no instruction/actions/history answers/labels/maps/future',
                  evaluation_policy='Point annotations are references; unlabeled frames are not negative. No PR/F1 or old 1m matching. Display threshold >=4 is not a checkpoint rule.',
                  register=str(reg), documentation=[str(reg / 'README.md'), str(reg.parent / 'README.md'),
                  str(ROOT / 'experiments/README.md'), str(ROOT / 'docs/STATUS.md')])
    write(out / 'protocol.json', config)
    write(reg / 'protocol.json', config)
    model_config = read(MODEL / 'config.json')
    idx = MODEL / 'model.safetensors.index.json'
    shards = sorted(set(read(idx)['weight_map'].values()))
    assert all((MODEL / s).is_file() and (MODEL / s).stat().st_size > 0 for s in shards)
    write(out / 'model_audit.json', dict(config=model_config, config_sha256=sha(MODEL / 'config.json'),
          index_sha256=sha(idx), shards=[dict(name=s, bytes=(MODEL / s).stat().st_size) for s in shards], offline=True))
    hashes = {}
    for rel in SOURCES:
        dest = out / 'source' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
        hashes[rel] = sha(dest)
    manifest = dict(created_at=now(), git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    source_hashes=hashes, prompt_sha256=sha(out / 'prompt_en.txt'), protocol_sha256=sha(out / 'protocol.json'),
                    task_hashes={('tasks_%d.json' % i): sha(out / ('tasks_%d.json' % i)) for i in range(4)},
                    selection_sha256=sha(out / 'evaluation_selection.json'), expected_calls=config['expected_calls'])
    write(out / 'manifest.json', manifest)
    write(reg / 'registration.json', manifest)
    (out / 'workspace_status.txt').write_bytes(subprocess.check_output(['git', 'status', '--short'], cwd=ROOT))
    (out / 'tracked_worktree.diff').write_bytes(subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT))
    write(out / 'status.json', dict(phase='prepared', created_at=now(), **config))
    print(json.dumps(dict(prepared=True, expected_calls=config['expected_calls'], scenes=len({c['scene'] for c in selected}), groups=config['groups'])))


def verify(out):
    m = read(out / 'manifest.json')
    assert sha(out / 'prompt_en.txt') == m['prompt_sha256']
    assert sha(out / 'protocol.json') == m['protocol_sha256']
    for name, expected in m['task_hashes'].items():
        assert sha(out / name) == expected
    for rel, expected in m['source_hashes'].items():
        assert sha(ROOT / rel) == expected, 'Registered source changed: ' + rel


def worker(out, wid):
    verify(out)
    c = read(out / 'protocol.json')
    prompt = (out / 'prompt_en.txt').read_text()
    base = read(out / 'service/service.json')['base_url']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    progress = dict(worker=wid, pid=os.getpid(), phase='running', completed_calls=0, valid_calls=0, completed_episodes=0)
    status_path = out / 'workers' / ('worker_%d.json' % wid)
    write(status_path, progress)
    for task in read(out / ('tasks_%d.json' % wid)):
        eid = task['episode_id']
        folder = out / 'cases' / eid
        folder.mkdir(parents=True, exist_ok=False)
        case = dict(phase='running', worker=wid, expected=len(task['frames']), processed=0, valid=0)
        write(folder / 'status.json', case)
        network_streak = 0
        for frame in task['frames']:
            t, images = frame['frame'], frame['images']
            prefix = folder / ('F%04d' % t)
            seed = request_seed(eid, t, c['seed'])
            wire = request(prompt, images, c['dataset'], c['model'], seed)
            write(prefix.with_suffix('.request.json'), dict(frame=t, image_frames=[im['frame'] for im in images],
                  images=images, request_sha256=digest(wire), preview=request(prompt, images, c['dataset'], c['model'], seed, False)))
            started = time.monotonic()
            record = dict(frame=t, image_frames=[im['frame'] for im in images], started_at=now(), attempts=[], valid=False)
            raw = None
            for attempt in range(c['network_attempts']):
                try:
                    req = urllib.request.Request(base + '/chat/completions', data=json.dumps(wire).encode(), headers={'Content-Type': 'application/json'})
                    with opener.open(req, timeout=c['request_timeout_seconds']) as response:
                        raw = json.load(response)
                    record['attempts'].append(dict(attempt=attempt + 1, status='response', at=now()))
                    break
                except (OSError, ValueError) as exc:
                    record['attempts'].append(dict(attempt=attempt + 1, error=str(exc), at=now()))
                    if attempt + 1 < c['network_attempts']:
                        time.sleep(2)
            record.update(response=raw, finished_at=now(), latency_seconds=time.monotonic() - started)
            if raw is not None:
                network_streak = 0
                try:
                    choice = raw['choices'][0]
                    if choice['finish_reason'] != 'stop':
                        raise ValueError('Non-stop finish reason')
                    record['answer'] = validate(json.loads(choice['message']['content']))
                    record['valid'] = True
                except (KeyError, ValueError, TypeError) as exc:
                    record['validation_error'] = str(exc)
            else:
                network_streak += 1
                record['validation_error'] = 'No model response'
            write(prefix.with_suffix('.response.json'), record)
            case['processed'] += 1
            case['valid'] += int(record['valid'])
            progress['completed_calls'] += 1
            progress['valid_calls'] += int(record['valid'])
            progress.update(episode_id=eid, frame=t, updated_at=now())
            write(folder / 'status.json', case)
            write(status_path, progress)
            if network_streak >= 3:
                raise RuntimeError('Three consecutive transport failures; stopping worker')
        case.update(phase='complete' if case['valid'] == case['expected'] else 'complete_with_invalid', finished_at=now())
        write(folder / 'status.json', case)
        progress['completed_episodes'] += 1
        write(status_path, progress)
    progress.update(phase='complete', finished_at=now())
    write(status_path, progress)


def supervise(out):
    verify(out)
    c = read(out / 'protocol.json')
    svcdir = out / 'service'
    svcdir.mkdir(exist_ok=False)
    state = dict(phase='admission', supervisor_pid=os.getpid(), started_at=now(), gpu=c['gpu'], concurrency=c['concurrency'], expected_calls=c['expected_calls'])
    server = None
    workers = []
    locks = []
    error = None
    def update(phase, **kw):
        state.update(phase=phase, updated_at=now(), **kw)
        write(out / 'status.json', state)
        print(json.dumps(state), flush=True)
    def stop(*_):
        raise KeyboardInterrupt('Termination requested')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    update('admission')
    try:
        for prefix in ('peng_vlnverse_gpu_', 'vln_2026_gpu_'):
            handle = (Path('/tmp') / (prefix + str(c['gpu']) + '.lock')).open('a')
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locks.append(handle)
        admission = []
        for i in range(3):
            snap = gpu_snapshot()
            admission.append(snap)
            row = next(r for r in snap['gpus'] if r['index'] == c['gpu'])
            # Shared GPU0 explicitly requested; leave foreign processes and ample free memory.
            if row['free_mib'] < row['total_mib'] * c['gpu_memory_utilization'] + 4096 or row['utilization'] > 10:
                raise RuntimeError('GPU0 admission failed; foreign workload left untouched')
            available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
            if available < 64 * 1024 ** 2:
                raise RuntimeError('Host available memory below 64 GiB')
            if i < 2:
                time.sleep(5)
        write(svcdir / 'admission.json', admission)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = 'http://127.0.0.1:%d/v1' % port
        py = ROOT / '.runtime/crossing_vllm27/bin/python'
        cmd = [str(py), '-B', '-m', 'vllm.entrypoints.openai.api_server', '--model', c['model_path'],
               '--served-model-name', c['model'], '--host', '127.0.0.1', '--port', str(port),
               '--dtype', 'bfloat16', '--tensor-parallel-size', '1', '--cpu-offload-gb', '0',
               '--gpu-memory-utilization', str(c['gpu_memory_utilization']), '--max-model-len', str(c['max_model_len']),
               '--max-num-seqs', str(c['concurrency']), '--max-num-batched-tokens', '4096',
               '--limit-mm-per-prompt', '{"image":3,"video":0}', '--mm-processor-kwargs', '{"max_pixels":307200}',
               '--enforce-eager', '--no-enable-log-requests', '--seed', str(c['seed']), '--reasoning-parser', 'qwen3']
        env = {k: v for k, v in os.environ.items() if 'proxy' not in k.lower()}
        cache = ROOT / '.runtime/crossing_vlm'
        env.update(CUDA_VISIBLE_DEVICES=str(c['gpu']), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                   HF_DATASETS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', VLLM_NO_USAGE_STATS='1', DO_NOT_TRACK='1',
                   TOKENIZERS_PARALLELISM='false', PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4',
                   OPENBLAS_NUM_THREADS='4', HF_HOME=str(cache / 'huggingface'), XDG_CACHE_HOME=str(cache / 'cache'),
                   VLLM_CACHE_ROOT=str(cache / 'vllm'), TORCHINDUCTOR_CACHE_DIR=str(cache / 'torchinductor'), TRITON_CACHE_DIR=str(cache / 'triton'))
        versions = json.loads(subprocess.check_output([str(py), '-B', '-c', 'import importlib.metadata as m,json;print(json.dumps({p:m.version(p) for p in ["vllm","torch","transformers"]}))'], env=env, text=True))
        with (svcdir / 'server.log').open('x') as log:
            server = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        service = dict(phase='loading', base_url=base, command=cmd, environment_versions=versions, server_pid=server.pid, process=process(server.pid), model=c['model'])
        write(svcdir / 'service.json', service)
        update('loading', base_url=base, server_pid=server.pid)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 2700
        while True:
            if server.poll() is not None:
                raise RuntimeError('vLLM exited while loading')
            try:
                with opener.open(base + '/models', timeout=2) as response:
                    if any(r['id'] == c['model'] for r in json.load(response)['data']):
                        break
            except (OSError, ValueError, KeyError):
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError('vLLM loading exceeded 2700 seconds')
            time.sleep(2)
        service.update(phase='ready', ready_at=now())
        write(svcdir / 'service.json', service)
        for i in range(c['concurrency']):
            with (out / ('worker_%d.log' % i)).open('x') as log:
                child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--output', str(out), '--worker', str(i)],
                                         cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            workers.append(child)
            write(out / ('worker_%d_process.json' % i), process(child.pid))
        update('running', worker_pids=[p.pid for p in workers])
        deadline = time.monotonic() + c['batch_timeout_seconds']
        while any(w.poll() is None for w in workers):
            if server.poll() is not None:
                raise RuntimeError('vLLM exited during scoring')
            if any(w.poll() not in (None, 0) for w in workers):
                raise RuntimeError('Worker failed; inspect worker logs')
            if time.monotonic() >= deadline:
                raise TimeoutError('Eight-hour inference limit')
            time.sleep(3)
        if any(w.returncode for w in workers):
            raise RuntimeError('Worker failed')
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        # Repeated signals must not interrupt cleanup of our own sessions.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        clean = dict(workers=[cleanup(w) for w in workers], server=cleanup(server))
        clean['gpu_after'] = gpu_snapshot()
        write(out / 'cleanup.json', clean)
        for handle in locks:
            handle.close()
        remaining = any(x.get('remaining') for x in clean['workers'] + [clean['server']] if isinstance(x, dict))
        write(svcdir / 'stopped.json', dict(at=now(), released=not remaining))
        if (svcdir / 'service.json').exists():
            service = read(svcdir / 'service.json')
            service.update(phase='stopped', finished_at=now(), gpu_released=not remaining)
            write(svcdir / 'service.json', service)
    if remaining:
        error = (error or '') + ' Owned processes remain after cleanup'
    update('exporting', inference_error=error, gpu_released=not remaining)
    try:
        verify(out)
        with (out / 'export.log').open('x') as log:
            subprocess.run([str(ROOT / 'backbone/streamvln/.venv/bin/python'), '-B', str(ROOT / 'scripts/export_crossing_iteration.py'),
                            '--output', str(out), '--tag', c['tag'], '--destination', str(out / 'exports/final')],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1800)
        summary = read(out / 'summary.json')
        phase = 'complete' if summary['valid_calls'] == c['expected_calls'] and not error else 'failed_partial' if error else 'complete_with_invalid'
        update(phase, finished_at=now(), error=error, summary=summary, html=str(out / 'exports/final/crossing_lite_review.html'))
    except BaseException as exc:
        update('failed', finished_at=now(), error=error, export_error=type(exc).__name__ + ': ' + str(exc))
    note = '\n' + now() + '：三帧Crossing五级评分 ' + str(out.relative_to(ROOT)) + ' 自动收尾：' + json.dumps(state, ensure_ascii=False) + '。未标帧不视为负类，语义准确性待复核。\n'
    for path in c['documentation']:
        with Path(path).open('a') as stream:
            stream.write(note)
    return 0 if state['phase'] in ('complete', 'complete_with_invalid') else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prepare', type=Path, help='Registration directory; prepare only')
    parser.add_argument('--worker', type=int)
    args = parser.parse_args()
    out = args.output.resolve()
    if args.prepare:
        prepare(out, args.prepare.resolve())
    elif args.worker is not None:
        worker(out, args.worker)
    else:
        sys.exit(supervise(out))
