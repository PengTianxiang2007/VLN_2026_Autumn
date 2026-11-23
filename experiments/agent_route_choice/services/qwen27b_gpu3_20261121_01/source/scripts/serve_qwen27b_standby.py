"""Keep the local Qwen27B service ready under explicit user retention authorization."""
import argparse
import base64
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
from run_human_route_choice import start_local
from run_crossing_local_batch import cleanup
from test_crossing_single_gpu import process, gpu_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--gpu', type=int, required=True)
    parser.add_argument('--allow-shared-gpu', action='store_true')
    parser.add_argument('--process-only', action='store_true',
                        help='Keep the server running without a readiness probe or loading deadline')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    config = read(args.config)
    state = dict(phase='admission', gpu=args.gpu, model=config['model'],
                 supervisor_pid=os.getpid(), started_at=now(), keep_alive=True,
                 retention_authorization=config.get('retention_authorization',
                     'User explicitly requested Qwen27B on GPU%d for authorized work.' % args.gpu),
                 model_config=config)
    stop_requested = False
    child = None
    locks = []
    def stop(*_):
        nonlocal stop_requested
        stop_requested = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    def update(**values):
        state.update(values, updated_at=now())
        write(out/'service.json', state)
        print(json.dumps({k:state.get(k) for k in ('phase','server_pid','base_url','error') if k in state}), flush=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    update()
    try:
        child, base = start_local(config, args.gpu, out, locks, args.allow_shared_gpu)
        if args.process_only:
            update(phase='running', readiness='not_probed', server_pid=child.pid,
                   process=process(child.pid), base_url=base)
            while not stop_requested:
                if child.poll() is not None:
                    raise RuntimeError(f'Model service exited with code {child.returncode}')
                time.sleep(2)
            update(phase='stopping')
            return
        update(phase='loading', server_pid=child.pid, process=process(child.pid), base_url=base)
        deadline = time.monotonic() + 1800
        while not stop_requested:
            if child.poll() is not None:
                raise RuntimeError('Model service exited while loading')
            try:
                with opener.open(base+'/models', timeout=2) as response:
                    models = json.load(response)
                if any(m['id'] == config['model'] for m in models['data']):
                    break
            except (OSError, ValueError, KeyError):
                pass
            if time.monotonic() > deadline:
                raise TimeoutError('Model startup exceeded 1800 seconds')
            time.sleep(2)
        if not stop_requested:
            update(phase='checking_inference')
            image_path = ROOT/'outputs/agent_route_choice/human_v001/preparation_20261106_01/images/sample_30/F0014.png'
            request = dict(model=config['model'], messages=[dict(role='user', content=[
                dict(type='text', text='Name one visible object in this image. Answer briefly.'),
                dict(type='image_url', image_url=dict(url='data:image/png;base64,'+base64.b64encode(image_path.read_bytes()).decode()))])],
                temperature=0, max_tokens=64, stream=False, chat_template_kwargs={'enable_thinking':False})
            req = urllib.request.Request(base+'/chat/completions', data=json.dumps(request).encode(), headers={'Content-Type':'application/json'})
            with opener.open(req, timeout=180) as response:
                result = json.load(response)
            assert result['choices'][0]['message'].get('content'), 'Empty smoke response'
            write(out/'smoke.json', dict(kind='service_readiness_only_not_experiment', image=str(image_path.relative_to(ROOT)), response=result, checked_at=now()))
            update(phase='ready', ready_at=now(), smoke_passed=True, gpu_snapshot=gpu_snapshot())
            while not stop_requested:
                if child.poll() is not None:
                    raise RuntimeError('Model service exited after readiness')
                time.sleep(2)
            update(phase='stopping')
    except BaseException as exc:
        update(phase='failed', error=type(exc).__name__+': '+str(exc))
    finally:
        result = cleanup(child)
        write(out/'cleanup.json', dict(result=result, snapshot=gpu_snapshot(), at=now()))
        for handle in locks:
            handle.close()
        update(phase='failed' if state.get('error') else 'stopped', finished_at=now(), cleanup=result)


if __name__ == '__main__':
    main()
