"""Generate local correction commands only; never launch navigation or simulation."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from core.agent_route_choice import read, write, now
from run_human_route_choice import start_local, admitted
from serve_crossing_vlm import gpu_rows
from run_agent_route_choice import wait_local
from run_crossing_local_batch import cleanup
from test_crossing_single_gpu import gpu_snapshot


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_request(case, prepared, config):
    image = prepared / case['image_path']
    if sha(image) != case['image_sha256']:
        raise ValueError('Checkpoint image changed: ' + case['sample_id'])
    prompt = (prepared / 'prompt_en.txt').read_text().format(
        selected_direction=case['selected_direction'],
        selected_entrance_description=case['selected_entrance_description'])
    return dict(model=config['model'], messages=[dict(role='user', content=[
        dict(type='text', text=prompt),
        dict(type='image_url', image_url=dict(url='data:image/png;base64,' + base64.b64encode(image.read_bytes()).decode()))])],
        temperature=0, seed=config['seed'], max_tokens=config['max_tokens'],
        stream=False, chat_template_kwargs={'enable_thinking':False})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepared', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--gpu', type=int, default=-1, help='-1 selects any eligible card')
    ap.add_argument('--resource-wait-seconds', type=int, default=86400)
    ap.add_argument('--allow-shared-gpu', action='store_true')
    args = ap.parse_args()
    prepared = args.prepared.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    config = read(prepared / 'model.json')
    manifest = read(prepared / 'manifest.json')
    cases = read(prepared / 'samples.json')
    state = dict(phase='preflight', supervisor_pid=os.getpid(), gpu=args.gpu,
                 started_at=now(), expected_calls=len(cases), completed=0,
                 navigation_executed=False, simulation_started=False)
    child = None
    locks = []
    def update(**kw):
        state.update(kw, updated_at=now())
        write(out / 'status.json', state)
        print(json.dumps(state, ensure_ascii=False), flush=True)
    def stop(*_):
        raise KeyboardInterrupt('User termination requested')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    update()
    try:
        for name, expected in manifest['source_hashes'].items():
            if sha(ROOT / name) != expected:
                raise RuntimeError('Registered source changed: ' + name)
        for name, expected in manifest['prepared_hashes'].items():
            if sha(prepared / name) != expected:
                raise RuntimeError('Registered input changed: ' + name)
        requests = [(case, build_request(case, prepared, config)) for case in cases]
        deadline = time.monotonic() + args.resource_wait_seconds
        update(phase='waiting_resources', gpu=None)
        while True:
            snapshot = gpu_snapshot()
            rows = gpu_rows()
            available = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
            totals = {r['index']:r['total_mib'] for r in snapshot['gpus']}
            eligible = [r for r in rows if (args.gpu < 0 or r['index'] == args.gpu)
                        and admitted(r, totals[r['index']], config, args.allow_shared_gpu)]
            if available < config['minimum_host_memory_gib'] * 1024 ** 2:
                eligible = []
            write(out / 'resource_wait.json', dict(checked_at=now(), rows=rows, snapshot=snapshot,
                  available_host_kib=available, eligible_gpus=[r['index'] for r in eligible]))
            for row in sorted(eligible, key=lambda r:r['free_mib'], reverse=True):
                try:
                    child, base = start_local(config, row['index'], out, locks, args.allow_shared_gpu)
                    update(phase='loading', gpu=row['index'], server_pid=child.pid, base_url=base)
                    break
                except (BlockingIOError, RuntimeError) as exc:
                    # start_local raises these before launching if admission/locks fail.
                    for handle in locks:
                        handle.close()
                    locks.clear()
                    update(phase='waiting_resources', admission_error=str(exc), gpu=None)
            if child is not None:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('No eligible GPU within the registered resource wait window')
            state['updated_at'] = now()
            write(out / 'status.json', state)
            time.sleep(60)
        wait_local(child, base, config['model'])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        rows = []
        for case, payload in requests:
            if child.poll() is not None:
                raise RuntimeError('Model service exited')
            sid = case['sample_id']
            folder = out / 'cases' / sid
            folder.mkdir(parents=True)
            update(phase='generating', current_sample=sid)
            body = json.dumps(payload, ensure_ascii=False).encode()
            (folder / 'request.json').write_bytes(body)
            write(folder / 'input_audit.json', dict(
                sample_id=sid, checkpoint_frame=case['checkpoint_frame'], image_sha256=case['image_sha256'],
                prompt_sha256=sha(prepared / 'prompt_en.txt'), request_sha256=hashlib.sha256(body).hexdigest(),
                selected_branch_id=case['selected_branch_id'], seed=config['seed']))
            request = urllib.request.Request(base + '/chat/completions', data=body, headers={'Content-Type':'application/json'})
            with opener.open(request, timeout=config['request_timeout_seconds']) as response:
                raw = response.read()
            (folder / 'response.json').write_bytes(raw)
            answer = json.loads(raw)['choices'][0]
            if answer['finish_reason'] != 'stop':
                raise RuntimeError(sid + ': incomplete response; preserve raw answer without retry')
            instruction = answer['message'].get('content')
            if not isinstance(instruction, str) or not instruction.strip():
                raise RuntimeError(sid + ': empty instruction')
            rows.append(dict(sample_id=sid, episode_id=case['episode_id'], checkpoint_frame=case['checkpoint_frame'],
                             selected_direction=case['selected_direction'], instruction=instruction))
            write(out / 'instructions.json', rows)
            update(completed=len(rows))
        update(phase='complete', semantic_review='pending', instructions_file=str(out / 'instructions.json'))
    except BaseException as exc:
        update(phase='cancelled' if isinstance(exc, KeyboardInterrupt) else 'failed', error=type(exc).__name__ + ': ' + str(exc))
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            result = cleanup(child) if child is not None else dict(signals=[], remaining=[])
            write(out / 'cleanup.json', dict(result=result, gpu_after=gpu_snapshot(), checked_at=now()))
            update(gpu_released=not result['remaining'], finished_at=now())
        finally:
            for handle in locks:
                handle.close()
        write(prepared / 'completion.json', state)
        notice = ('\n\n2026-11-07 v005七例局部纠正命令后台收尾：状态`%s`，完成%s/%s，GPU释放%s；'
                  '原答语义待复核，无导航或仿真。产物 `%s`。\n') % (
                      state['phase'], state['completed'], len(cases), state.get('gpu_released'), out.relative_to(ROOT))
        for name in [prepared / 'README.md', ROOT / 'docs/STATUS.md', ROOT / 'experiments/README.md']:
            with name.open('a') as handle:
                handle.write(notice)


if __name__ == '__main__':
    main()
