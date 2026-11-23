"""Explicitly run two independent calls per sample; default is a no-network dry run."""
import argparse
import getpass
import json
import multiprocessing
import os
from pathlib import Path
import random
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from core.agent_route_choice import (build_messages, digest, file_hash, now, payload, read,
                                     validate_choice, validate_inventory, verify_prepared, write)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Unexpected API redirect refused')


def read_stream(response, deadline):
    content, finish, usage, model = [], None, None, None
    for raw in response:
        if time.monotonic() > deadline:
            raise TimeoutError('Per-request deadline exceeded')
        line = raw.decode('utf-8').strip()
        if not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if data == '[DONE]':
            break
        chunk = json.loads(data)
        if 'error' in chunk:
            raise RuntimeError('Provider stream error')
        model = chunk.get('model', model)
        usage = chunk.get('usage') or usage
        for choice in chunk.get('choices', []):
            delta = choice.get('delta', {})
            if delta.get('content'):
                content.append(delta['content'])
            finish = choice.get('finish_reason') or finish
    if finish is None:
        raise ConnectionError('Stream ended without a finish marker')
    return {'content': ''.join(content), 'finish_reason': finish, 'usage': usage, 'model': model}


def call_model(endpoint, wire, key, config, log_path):
    # No ambient proxy or redirect may change the credential destination.
    url = urllib.parse.urlparse(endpoint)
    if config['backend'] == 'glm':
        if endpoint != 'https://open.bigmodel.cn/api/paas/v4/chat/completions' or not key:
            raise ValueError('Expected the registered GLM endpoint and an in-memory credential')
    elif url.scheme != 'http' or url.hostname != '127.0.0.1' or key:
        raise ValueError('Local model endpoint must be loopback and receive no cloud credential')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + config['request_deadline_seconds']
    for attempt in range(config['max_network_attempts']):
        started = time.monotonic()
        headers = {'Content-Type': 'application/json'}
        if key:
            headers['Authorization'] = 'Bearer ' + key
        request = urllib.request.Request(endpoint, data=json.dumps(wire, ensure_ascii=False).encode(), headers=headers)
        retryable, result, error, provider_error = True, None, None, None
        retry_after = 0
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Per-request deadline exceeded')
            with opener.open(request, timeout=min(config['request_timeout_seconds'], remaining)) as response:
                result = read_stream(response, deadline)
        except urllib.error.HTTPError as exc:
            error = 'HTTP_%d' % exc.code
            retryable = exc.code in (408, 429, 500, 502, 503, 504)
            try:
                body = json.loads(exc.read(8192)).get('error', {})
                provider_error = {k: str(body[k]).replace(key or '\0', '[redacted]')[:600]
                                  for k in ('code', 'message') if k in body}
            except (ValueError, TypeError, AttributeError):
                pass
            try:
                retry_after = max(0, float(exc.headers.get('Retry-After', 0)))
            except (ValueError, TypeError):
                pass
        except (OSError, ValueError, RuntimeError) as exc:
            error = type(exc).__name__
        record = {'at': now(), 'attempt': attempt + 1, 'request_sha256': digest(wire),
                  'elapsed_seconds': time.monotonic() - started, 'error': error,
                  'finish_reason': result['finish_reason'] if result else None,
                  'provider_error': provider_error}
        with Path(log_path).open('a') as stream:
            stream.write(json.dumps(record) + '\n')
        if result is not None:
            return result
        if error == 'HTTP_429':
            delay = max(retry_after, min(config.get('retry_backoff_cap_seconds', 10),
                        config.get('retry_backoff_base_seconds', 2) * 2 ** attempt))
            delay += random.SystemRandom().uniform(0, config.get('retry_jitter_seconds', 0))
        else:
            delay = min(10, 2 ** (attempt + 1))
        if not retryable or attempt + 1 >= config['max_network_attempts'] or time.monotonic() + delay >= deadline:
            raise RuntimeError('Bounded request failed: ' + str(error))
        time.sleep(delay)
    raise RuntimeError('No provider response')


def run_case(case, prepared, output, config, endpoint, key, request_fn=call_model):
    folder = output / 'cases' / case['sample_id']
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'status.json', {'phase': 'running', 'pid': os.getpid(), 'started_at': now()})
    inventory = None
    for stage, prompt_file in [(1, '01_inventory_en.txt'), (2, '02_choose_en.txt')]:
        messages = build_messages(case, prepared, stage, (prepared / 'prompts' / prompt_file).read_text(), inventory)
        wire = payload(messages, config, case['sample_id'], stage)
        # Store the exact logical request and image hashes without duplicating image base64.
        preview = build_messages(case, prepared, stage, (prepared / 'prompts' / prompt_file).read_text(), inventory, embed_images=False)
        write(folder / ('call%d_request.json' % stage), {'request_sha256': digest(wire),
              'parameters': {k: v for k, v in wire.items() if k != 'messages'}, 'messages_image_hash_preview': preview,
              'inventory_sha256': digest(inventory) if inventory is not None else None})
        raw = request_fn(endpoint, wire, key, config, folder / ('call%d_transport.jsonl' % stage))
        write(folder / ('call%d_response.json' % stage), raw)
        if raw['finish_reason'] != 'stop':
            raise ValueError('Incomplete provider response; no automatic semantic repair')
        answer = json.loads(raw['content'])
        ids = [im['id'] for im in case['images'] if stage == 2 or im['phase'] == 'checkpoint_context']
        if stage == 1:
            inventory = validate_inventory(answer, ids)
        else:
            validate_choice(answer, inventory, ids, case['instruction'])
        write(folder / ('call%d_answer.json' % stage), answer)
        write(folder / 'status.json', {'phase': 'running', 'pid': os.getpid(), 'completed_calls': stage, 'updated_at': now()})
    write(folder / 'status.json', {'phase': 'complete_pending_semantic_review', 'model_calls': 2, 'finished_at': now()})


def case_worker(case, prepared, output, config, endpoint, key):
    def stop_worker(*_):
        raise KeyboardInterrupt('Worker termination requested')
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    failed = False
    try:
        run_case(case, prepared, output, config, endpoint, key)
    except BaseException as exc:
        failed = True
        failure = {'sample_id': case['sample_id'], 'phase': 'failed', 'pid': os.getpid(),
                   'error_type': type(exc).__name__, 'finished_at': now()}
        # Errors here are local validation messages or sanitized transport failures.
        if isinstance(exc, (ValueError, RuntimeError)):
            failure['error'] = str(exc)[:600]
        write(output / 'cases' / case['sample_id'] / 'status.json', failure)
    finally:
        key = None
    if failed:
        raise SystemExit(1)


def start_case_workers(cases, prepared, output, config, endpoint, key):
    """Exactly one process per case; both calls stay in that same worker."""
    if config['concurrency'] != len(cases):
        raise ValueError('This batch requires one independently owned process per case')
    context = multiprocessing.get_context('fork')
    workers = []
    try:
        for case in cases:
            child = context.Process(target=case_worker, args=(case, prepared, output, config, endpoint, key))
            child.start()
            workers.append((case['sample_id'], child))
        return workers
    except BaseException:
        cleanup_case_workers(workers)
        raise


def cleanup_case_workers(workers):
    """Process objects refer only to children started by this supervisor."""
    for _, child in workers:
        if child.is_alive():
            child.terminate()
    deadline = time.monotonic() + 15
    for _, child in workers:
        child.join(timeout=max(0, deadline - time.monotonic()))
    for _, child in workers:
        if child.is_alive():
            child.kill(); child.join(timeout=5)
    return [{'sample_id': sid, 'pid': child.pid, 'exitcode': child.exitcode, 'alive': child.is_alive()}
            for sid, child in workers]


def wait_case_workers(workers, output, update, timeout):
    deadline = time.monotonic() + timeout
    while True:
        active = [child.pid for _, child in workers if child.is_alive()]
        states = [read(output / 'cases' / sid / 'status.json')
                  for sid, _ in workers if (output / 'cases' / sid / 'status.json').exists()]
        update(active_workers=active,
               completed_samples=sum(s['phase'] == 'complete_pending_semantic_review' for s in states),
               failed_samples=sum(s['phase'] == 'failed' for s in states))
        if not active:
            break
        if time.monotonic() > deadline:
            raise TimeoutError('Parallel batch deadline exceeded')
        time.sleep(2)
    failures = []
    for sid, child in workers:
        child.join()
        path = output / 'cases' / sid / 'status.json'
        result = read(path) if path.exists() else {'phase': 'failed', 'error_type': 'WorkerExitedWithoutStatus'}
        if child.exitcode != 0 or result['phase'] != 'complete_pending_semantic_review':
            result.update(sample_id=sid, phase='failed', worker_exitcode=child.exitcode)
            write(path, result); failures.append(result)
    return failures


def start_local(config, gpus, output, handles):
    import fcntl
    from serve_crossing_vlm import gpu_rows, idle
    from test_crossing_single_gpu import process
    if len(gpus) != config['tensor_parallel_size'] or len(set(gpus)) != len(gpus):
        raise ValueError('GPU count must match the registered tensor-parallel size')
    for gpu in sorted(gpus):
        for prefix in ('peng_vlnverse_gpu_', 'vln_2026_gpu_'):
            handle = (Path('/tmp') / (prefix + str(gpu) + '.lock')).open('a')
            handles.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    admission = []
    for i in range(2):
        rows = gpu_rows(); admission.append(rows)
        for gpu in gpus:
            selected = next((r for r in rows if r['index'] == gpu), None)
            if selected is None or not idle(selected):
                raise RuntimeError('Selected GPU is not empty with sufficient free memory')
        available = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
        if available < config.get('minimum_host_memory_gib', 64) * 1024 ** 2:
            raise RuntimeError('Host memory below registered admission threshold')
        if i == 0:
            time.sleep(5)
    write(output / 'gpu_admission.json', admission)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    command = [str(ROOT / config['python']), '-B', '-m', 'vllm.entrypoints.openai.api_server',
               '--model', config['model_path'], '--served-model-name', config['model'],
               '--host', '127.0.0.1', '--port', str(port), '--dtype', 'bfloat16',
               '--tensor-parallel-size', str(config['tensor_parallel_size']), '--cpu-offload-gb', '0',
               '--gpu-memory-utilization', str(config['gpu_memory_utilization']),
               '--max-model-len', str(config['max_model_len']), '--max-num-seqs', '1',
               '--max-num-batched-tokens', '4096', '--limit-mm-per-prompt', '{"image":8,"video":0}',
               '--mm-processor-kwargs', '{"max_pixels":307200}', '--enforce-eager',
               '--no-enable-log-requests', '--seed', str(config['seed'])]
    if config.get('reasoning_parser'):
        command.extend(['--reasoning-parser', config['reasoning_parser']])
    env = {k: v for k, v in os.environ.items() if 'proxy' not in k.lower() and not any(t in k.upper() for t in ('API_KEY', 'TOKEN', 'SECRET'))}
    cache = ROOT / '.runtime/crossing_vlm'
    env.update(CUDA_VISIBLE_DEVICES=','.join(map(str, gpus)), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
               HF_HUB_DISABLE_TELEMETRY='1', VLLM_NO_USAGE_STATS='1', TOKENIZERS_PARALLELISM='false',
               PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
               HF_HOME=str(cache / 'huggingface'), XDG_CACHE_HOME=str(cache / 'cache'),
               VLLM_CACHE_ROOT=str(cache / 'vllm'), TORCHINDUCTOR_CACHE_DIR=str(cache / 'torchinductor'),
               TRITON_CACHE_DIR=str(cache / 'triton'))
    with (output / 'server.log').open('x') as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    # The caller must receive the child immediately, before any fallible readiness work.
    return child, 'http://127.0.0.1:%d/v1' % port, {'command': command, 'process': process(child.pid), 'gpus': gpus}


def wait_local(child, base, model, timeout_seconds=2700):
    deadline = time.monotonic() + timeout_seconds
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError('Owned local service exited while loading')
        try:
            with opener.open(base + '/models', timeout=2) as response:
                models = json.load(response)
            if any(m['id'] == model for m in models['data']):
                return
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(2)
    raise TimeoutError(f'Local service not ready within {timeout_seconds} seconds')


def record_completion(output, state):
    """Append a credential-free completion notice without replacing concurrent edits."""
    batch = ROOT / 'experiments/agent_route_choice/v001' / output.parent.name
    if not output.is_relative_to(ROOT / 'outputs/agent_route_choice/v001') or not (batch / 'README.md').exists():
        return
    summary = {k: state.get(k) for k in ('model', 'phase', 'completed_samples', 'expected_samples',
               'request_counts', 'gpu_released', 'workers_exited', 'artifacts_ready', 'finished_at')}
    summary.update(output=str(output.relative_to(ROOT)), semantic_accuracy='pending_review')
    write(batch / (output.name + '_completion.json'), summary)
    notice = ('\n\n%s 自动收尾：Agent选路 %s/%s；状态 `%s`，完成两次调用 %s/10 条，'
              'HTML导出 %s，GPU释放 %s。结果 `%s`；语义正确率仍待复核。\n') % (
                  now(), output.parent.name, state['model'], state['phase'], state['completed_samples'],
                  state.get('artifacts_ready', False), state.get('gpu_released', '不适用'),
                  output.relative_to(ROOT))
    for path in (batch / 'README.md', batch.parent / 'README.md', batch.parent.parent / 'README.md',
                 ROOT / 'docs/STATUS.md', ROOT / 'experiments/README.md'):
        fd = os.open(path, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(fd, notice.encode('utf-8'))
        finally:
            os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--model', choices=['glm', 'qwen32b'], required=True)
    parser.add_argument('--output', type=Path, help='New run directory; required with --execute')
    parser.add_argument('--execute', action='store_true', help='Actually call a model; only after user says start')
    gpu_args = parser.add_mutually_exclusive_group()
    gpu_args.add_argument('--gpu', type=int, help='One freshly checked empty GPU; local model only')
    gpu_args.add_argument('--gpus', type=int, nargs='+', help='Freshly checked empty GPUs matching tensor parallelism')
    parser.add_argument('--key-stdin', action='store_true', help='Read cloud credential from stdin instead of non-echoing getpass')
    args = parser.parse_args(argv)
    prepared = args.prepared.resolve()
    dataset = verify_prepared(prepared, ROOT)
    config = read(prepared / 'models.json')[args.model]
    if not args.execute:
        print(json.dumps({'phase': 'dry_run_no_requests', 'model': args.model, 'samples': len(dataset['cases']),
                          'planned_calls': 20, 'model_calls': 0, 'loads_weights': False}))
        return 0
    gpus = args.gpus or ([args.gpu] if args.gpu is not None else [])
    if args.output is None or (config['backend'] == 'qwen_local' and len(gpus) != config['tensor_parallel_size']):
        parser.error('--execute needs a new --output, and local Qwen needs --gpus matching its tensor-parallel size')
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    key, child, handles, failures, workers = None, None, [], [], []
    state = {'phase': 'starting', 'model': args.model, 'started_at': now(), 'pid': os.getpid(),
             'completed_samples': 0, 'expected_samples': 10, 'credential_on_disk': False}
    def update(**fields):
        state.update(fields, updated_at=now()); write(output / 'status.json', state)
    def stop(*_):
        raise KeyboardInterrupt('Termination requested')
    old_handlers = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    write(output / 'manifest.json', {'prepared': str(prepared), 'prepared_manifest_sha256': file_hash(prepared / 'manifest.json'),
                                    'model_config': config, 'sample_order': [c['sample_id'] for c in dataset['cases']],
                                    'code_sha256': read(prepared / 'manifest.json')['code_sha256'], 'started_at': now()})
    update()
    try:
        if args.model == 'glm':
            key = sys.stdin.readline().strip() if args.key_stdin else getpass.getpass('GLM API key (not saved): ').strip()
            if not key:
                raise ValueError('Missing in-memory API credential')
            endpoint = config['endpoint']
        else:
            child, base, service = start_local(config, gpus, output, handles)
            write(output / 'service.json', service)
            update(phase='loading', gpus=gpus, server_pid=child.pid)
            wait_local(child, base, config['model'])
            endpoint = base + '/chat/completions'
        update(phase='running')
        if config['concurrency'] > 1:
            workers = start_case_workers(dataset['cases'], prepared, output, config, endpoint, key)
            key = None
            write(output / 'workers.json', [{'sample_id': sid, 'pid': process.pid} for sid, process in workers])
            update(worker_pids=[process.pid for _, process in workers], concurrency=len(workers))
            failures = wait_case_workers(workers, output, update, config.get('batch_deadline_seconds', 3600))
        else:
            deadline = time.monotonic() + config.get('batch_deadline_seconds', 14400)
            for case in dataset['cases']:
                if time.monotonic() > deadline:
                    raise TimeoutError('Sequential batch deadline exceeded')
                update(current_sample=case['sample_id'])
                try:
                    run_case(case, prepared, output, config, endpoint, key)
                    update(completed_samples=state['completed_samples'] + 1)
                except Exception as exc:
                    failure = {'sample_id': case['sample_id'], 'error_type': type(exc).__name__, 'phase': 'failed'}
                    if isinstance(exc, (ValueError, RuntimeError)):
                        failure['error'] = str(exc)[:600]
                    failures.append(failure); write(output / 'cases' / case['sample_id'] / 'status.json', failure)
        update(phase='failed_partial' if failures else 'complete_pending_semantic_review', failures=failures)
    except BaseException as exc:
        update(phase='interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed', error_type=type(exc).__name__)
    finally:
        key = None
        # Avoid a second cancellation interrupting cleanup of the owned service.
        for sig in old_handlers:
            signal.signal(sig, signal.SIG_IGN)
        try:
            if workers:
                write(output / 'worker_cleanup.json', cleanup_case_workers(workers))
                update(workers_exited=all(not process.is_alive() for _, process in workers))
            if child is not None:
                from run_crossing_local_batch import cleanup
                from test_crossing_single_gpu import gpu_snapshot
                result = cleanup(child)
                write(output / 'cleanup.json', {'server': result, 'gpu_after': gpu_snapshot()})
                update(gpu_released=not result['remaining'])
                if result['remaining']:
                    update(phase='cleanup_failed')
        finally:
            for handle in handles:
                handle.close()
            for sig, previous in old_handlers.items():
                signal.signal(sig, previous)
        counts = {'logical_requests_prepared': len(list(output.glob('cases/*/call*_request.json'))),
                  'provider_responses_saved': len(list(output.glob('cases/*/call*_response.json'))),
                  'provider_attempts_logged': sum(len(p.read_text().splitlines()) for p in output.glob('cases/*/call*_transport.jsonl'))}
        update(finished_at=now(), credential_on_disk=False, request_counts=counts)
    from scripts.report_agent_route_choice import create_review
    try:
        create_review(prepared, output, output / 'review_template.json')
        # The existing image environment provides fontTools for standalone CJK HTML.
        subprocess.run([str(ROOT / 'backbone/streamvln/.venv/bin/python'), '-B',
                        str(ROOT / 'scripts/export_agent_route_choice.py'), '--prepared', str(prepared),
                        '--destination', str(output / 'route_choice_review.html'), '--runs', str(output)],
                       check=True, timeout=600)
        update(artifacts_ready=True)
    except Exception as exc:
        update(artifacts_ready=False, export_error_type=type(exc).__name__)
        record_completion(output, state)
        return 1
    record_completion(output, state)
    return 0 if state['phase'] == 'complete_pending_semantic_review' else 1


if __name__ == '__main__':
    sys.exit(main())
