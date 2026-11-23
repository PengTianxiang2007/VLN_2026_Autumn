"""Run a prepared v006 campaign with an owned StreamVLN and a borrowed Qwen service."""
import argparse
import getpass
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from types import SimpleNamespace
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from core.paths import model_environment, model_python, resource_root
from core.serial_pipeline import save
from core.vlnverse_runtime import wait_for_model_ready
from scripts.evaluate import check_gpu
from scripts.run_oracle_existing_model import stop_simulator
from scripts.run_serial_pipeline import admit_simulator_gpu, check_semantic_service, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--model-gpu', type=int, required=True)
    parser.add_argument('--sim-gpu', type=int, required=True)
    args = parser.parse_args()
    out = args.campaign.resolve()
    manifest = json.loads((out/'manifest.json').read_text())
    code = Path(manifest['code_root'])
    if ROOT != code:
        os.execv(sys.executable, [sys.executable, '-Bu', str(code/'scripts/run_serial_v006.py'), *sys.argv[1:]])
    cfg = json.loads((out/'config.json').read_text())
    if cfg['version'] != 'serial_recovery_v002' or (out/'launch.json').exists():
        raise ValueError('Use a fresh prepared v002 run')
    if not os.environ.get('JEV_API_KEY'):
        os.environ['JEV_API_KEY'] = getpass.getpass('EasyJEV key: ')
    if not os.environ['JEV_API_KEY']:
        raise ValueError('Missing JEV_API_KEY')
    qwen = json.loads((out/'semantic_service.json').read_text())
    check_semantic_service(qwen, urllib.request.build_opener(urllib.request.ProxyHandler({})))
    checks = []
    for i in range(2):
        if i:
            time.sleep(2)
        check = admit_simulator_gpu(args.model_gpu)
        check_gpu(args.model_gpu, 32000 if args.sim_gpu == args.model_gpu else 25000, allow_shared=True)
        checks.append(dict(model=check, simulator=admit_simulator_gpu(args.sim_gpu)))
    directory = out/'navigation_model'
    directory.mkdir()
    os.environ.update(manifest['runtime_env'])
    env = model_environment('streamvln', args.model_gpu)
    for key in ('JEV_API_KEY', 'DEEPSEEK_API_KEY', 'PENG_SMOKE_BACKEND'):
        env.pop(key, None)
    env.update(VLN_BRANCH_ROOT=str(directory), VLN_EVAL_SEED=str(cfg['seed']), PYTHONHASHSEED=str(cfg['seed']))
    cmd = [str(model_python('streamvln')), '-u', str(code/'benchmarks/vlnverse/runner/service.py'),
           '--method', 'StreamVLN', '--checkpoint', str(resource_root()/'models/StreamVLN_R2R_v1_3'),
           '--output', str(directory), '--smoke-steps', '0', '--compact-trace', '--save-rgb', '2']
    def interrupted(*_):
        raise KeyboardInterrupt('Stop requested')
    signal.signal(signal.SIGTERM, interrupted)
    server = None
    ready_timeout = float(os.environ.get('VLN_MODEL_READY_TIMEOUT', '900'))
    try:
        with (directory/'agent.log').open('x') as log:
            server = subprocess.Popen(cmd, cwd=code, env=env, stdout=log, stderr=subprocess.STDOUT,
                                      start_new_session=True)
        save(directory/'launch.json', dict(pid=server.pid, gpu=args.model_gpu, sim_gpu=args.sim_gpu,
                                           prepared_checks=checks, seed=cfg['seed'], command=cmd,
                                           model_ready_timeout_seconds=ready_timeout))
        save(out/'status.json', dict(phase='loading_navigation_model', model_pid=server.pid))
        ready = wait_for_model_ready(server, directory, timeout=ready_timeout)
        run(SimpleNamespace(campaign=out, model_pid=server.pid, port=ready['port'], gpu=args.sim_gpu,
                            keys_stdin=False, detach=False, allow_active_shared_gpu=False,
                            release_semantic_service=False))
    except BaseException as exc:
        state = json.loads((out/'status.json').read_text())
        state.update(phase='failed', error=repr(exc).replace(os.environ['JEV_API_KEY'], '[REDACTED]'))
        save(out/'status.json', state)
        raise
    finally:
        stop_simulator(server)
        state = json.loads((out/'status.json').read_text())
        state.update(model_retained=False, qwen_borrowed=True)
        save(out/'status.json', state)
        save(directory/'cleanup.json', dict(pid=server.pid if server else None, released=True))


if __name__ == '__main__':
    main()
