"""Run the authorized fixed v002 cohort locally; preserve raw answers and release GPU."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from core.agent_route_choice import digest, file_hash, now, payload, read, write
from core.agent_panorama_choice import build_messages, schema, validate_inventory, validate_choice, verify_prepared
from run_agent_route_choice import call_model, wait_local
from run_crossing_local_batch import cleanup
from serve_crossing_vlm import gpu_rows, idle
from test_crossing_single_gpu import gpu_snapshot, process


def start(config, gpu, out, locks):
    for prefix in ('peng_vlnverse_gpu_', 'vln_2026_gpu_'):
        f = (Path('/tmp') / f'{prefix}{gpu}.lock').open('a'); locks.append(f)
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    admissions = []
    for i in range(2):
        rows = gpu_rows(); admissions.append(rows)
        row = next(r for r in rows if r['index'] == gpu)
        if not idle(row): raise RuntimeError('GPU is not empty with sufficient free memory')
        available = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
        if available < config['minimum_host_memory_gib'] * 1024 ** 2: raise RuntimeError('Insufficient host memory')
        if i == 0: time.sleep(5)
    write(out / 'gpu_admission.json', admissions)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    command = [str(ROOT / config['python']), '-B', '-m', 'vllm.entrypoints.openai.api_server',
               '--model', config['model_path'], '--served-model-name', config['model'],
               '--host', '127.0.0.1', '--port', str(port), '--dtype', 'bfloat16',
               '--tensor-parallel-size', '1', '--cpu-offload-gb', '0',
               '--gpu-memory-utilization', str(config['gpu_memory_utilization']),
               '--max-model-len', str(config['max_model_len']), '--max-num-seqs', '1',
               '--max-num-batched-tokens', '4096', '--limit-mm-per-prompt', json.dumps({'image': config['max_images'], 'video': 0}),
               '--mm-processor-kwargs', '{"max_pixels":307200}', '--enforce-eager',
               '--no-enable-log-requests', '--seed', str(config['seed']), '--reasoning-parser', config['reasoning_parser']]
    env = {k: v for k, v in os.environ.items() if 'proxy' not in k.lower() and not any(t in k.upper() for t in ('API_KEY', 'TOKEN', 'SECRET'))}
    cache = ROOT / '.runtime/crossing_vlm'
    env.update(CUDA_VISIBLE_DEVICES=str(gpu), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
               HF_HUB_DISABLE_TELEMETRY='1', VLLM_NO_USAGE_STATS='1', TOKENIZERS_PARALLELISM='false',
               PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
               HF_HOME=str(cache / 'huggingface'), XDG_CACHE_HOME=str(cache / 'cache'), VLLM_CACHE_ROOT=str(cache / 'vllm'),
               TORCHINDUCTOR_CACHE_DIR=str(cache / 'torchinductor'), TRITON_CACHE_DIR=str(cache / 'triton'))
    write(out / 'launch.json', dict(command=command, gpu=gpu, created_at=now(), model_config_sha256=file_hash(Path(config['model_path']) / 'config.json')))
    with (out / 'server.log').open('x') as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    return child, f'http://127.0.0.1:{port}/v1'


def run_case(case, prepared, out, config, endpoint, request_fn=call_model):
    folder = out / 'cases' / case['sample_id']; folder.mkdir(parents=True, exist_ok=False)
    inventory = None; completed = 0; responses = 0
    state = dict(sample_id=case['sample_id'], phase='running', started_at=now())
    write(folder / 'status.json', state)
    try:
        for stage, filename in [(1, '01_inventory_en.txt'), (2, '02_choose_en.txt')]:
            prompt = (prepared / 'prompts' / filename).read_text()
            wire = payload(build_messages(case, prepared, stage, prompt, inventory), config, case['sample_id'], stage)
            wire['response_format'] = {'type': 'json_schema', 'json_schema': {'name': f'crossing_call{stage}', 'strict': True, 'schema': schema(stage)}}
            wire['stream_options'] = {'include_usage': True}
            preview = build_messages(case, prepared, stage, prompt, inventory, embed=False)
            write(folder / f'call{stage}_request.json', dict(request_sha256=digest(wire), parameters={k:v for k,v in wire.items() if k != 'messages'},
                  messages_image_hash_preview=preview, inventory_sha256=digest(inventory) if inventory is not None else None))
            state.update(active_call=stage, updated_at=now()); write(folder / 'status.json', state)
            raw = request_fn(endpoint, wire, None, config, folder / f'call{stage}_transport.jsonl')
            responses += 1; write(folder / f'call{stage}_response.json', raw)
            answer = json.loads(raw['content']); write(folder / f'call{stage}_parsed.json', answer)
            if raw['finish_reason'] != 'stop': raise ValueError('Incomplete response; no semantic retry')
            if stage == 1: inventory = validate_inventory(answer, case)
            else: validate_choice(answer, inventory, case)
            write(folder / f'call{stage}_answer.json', answer); completed = stage
        state.update(phase='complete_pending_semantic_review', decision=answer['status'])
    except (ValueError, RuntimeError, OSError, TypeError, KeyError) as exc:
        state.update(phase='invalid_or_failed', error_type=type(exc).__name__, error=str(exc)[:900])
    state.update(completed_valid_calls=completed, received_responses=responses, finished_at=now())
    write(folder / 'status.json', state)
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--gpu', type=int, required=True)
    a = p.parse_args(); prepared = a.prepared.resolve(); out = a.output.resolve()
    cases = verify_prepared(prepared); manifest = read(prepared / 'manifest.json')
    for rel, sha in manifest['code_sha256'].items():
        if file_hash(ROOT / rel) != sha: raise ValueError('Source changed after preparation: ' + rel)
    config = read(prepared / 'model.json'); out.mkdir(parents=True, exist_ok=False)
    state = dict(phase='preparing', supervisor_pid=os.getpid(), gpu=a.gpu, started_at=now(), expected_samples=10, expected_logical_calls=20,
                 prepared=str(prepared), prepared_manifest_sha256=file_hash(prepared / 'manifest.json'), model=config['model'], semantic_accuracy='pending_review')
    write(out / 'registration.json', dict(state, config=config, source_git_head=manifest['git_head']))
    child = None; locks = []; results = []; error = None
    def phase(name, **kw):
        state.update(phase=name, updated_at=now(), **kw); write(out / 'status.json', state); print(json.dumps(state), flush=True)
    def stop(*_): raise KeyboardInterrupt('Supervisor termination requested')
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)
    try:
        phase('admission'); child, base = start(config, a.gpu, out, locks)
        phase('loading', service=process(child.pid), endpoint=base)
        wait_local(child, base, config['model']); phase('inference')
        for case in cases:
            results.append(run_case(case, prepared, out, config, base + '/chat/completions'))
            write(out / 'case_summary.json', results)
            phase('inference', processed_samples=len(results), valid_samples=sum(r['phase'] == 'complete_pending_semantic_review' for r in results),
                  received_responses=sum(r['received_responses'] for r in results))
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:1000]); phase('failed', error=error)
    finally:
        phase('cleaning')
        clean = cleanup(child) if child is not None else dict(signals=[], remaining=[])
        write(out / 'cleanup.json', dict(clean, gpu_after=gpu_snapshot(), finished_at=now()))
        for f in locks: f.close()
        phase('complete_pending_semantic_review' if error is None and len(results) == 10 else 'failed',
              gpu_released=not clean['remaining'], finished_at=now(), selected_samples=sum(r.get('decision') == 'selected' for r in results),
              insufficient_samples=sum(r.get('decision') == 'insufficient_evidence' for r in results))
    return 0 if error is None and len(results) == 10 and not clean['remaining'] else 1


if __name__ == '__main__': raise SystemExit(main())
