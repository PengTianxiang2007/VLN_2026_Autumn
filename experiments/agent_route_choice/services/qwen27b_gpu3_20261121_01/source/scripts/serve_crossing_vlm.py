"""Serve the existing local Qwen3-VL weights without changing backbone environments."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODELS = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models')


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def gpu_rows():
    result = subprocess.check_output([
        'nvidia-smi', '--query-gpu=index,memory.used,memory.free,utilization.gpu,uuid',
        '--format=csv,noheader,nounits'], text=True)
    apps = subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid',
                                    '--format=csv,noheader'],text=True).splitlines()
    rows=[]
    for line in result.splitlines():
        parts=[p.strip() for p in line.split(',')]
        row=dict(zip(('index','used_mib','free_mib','utilization'),map(int,parts[:4])))
        row['compute_process_present']=parts[4] in apps
        rows.append(row)
    return rows


def idle(row):
    return (row['used_mib'] < 1024 and row['free_mib'] >= 46000 and
            row['utilization'] <= 10 and not row['compute_process_present'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--gpus', nargs='+', type=int, required=True)
    parser.add_argument('--model', type=Path, default=MODELS / 'Qwen3-VL-32B-Instruct')
    parser.add_argument('--python', type=Path, default=MODELS / 'qwen3vl-vllm/bin/python')
    parser.add_argument('--served-model', default='crossing-qwen32b')
    parser.add_argument('--quantization', choices=['fp8'])
    parser.add_argument('--reasoning-parser')
    parser.add_argument('--cpu-offload-gb', type=float, default=0)
    parser.add_argument('--max-model-len', type=int, default=16384)
    parser.add_argument('--max-num-seqs', type=int, default=2)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    locks = []
    for gpu in sorted(set(args.gpus)):
        for name in [f'peng_vlnverse_gpu_{gpu}.lock', f'vln_2026_gpu_{gpu}.lock']:
            handle = (Path('/tmp') / name).open('a')
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locks.append(handle)
    for sample in range(2):
        rows = gpu_rows()
        for gpu in args.gpus:
            row = next(r for r in rows if r['index'] == gpu)
            if not idle(row):
                raise RuntimeError(f'GPU admission rejected: {row}')
        if sample == 0:
            time.sleep(5)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    model = args.model.resolve()
    python = args.python
    if not (model / 'config.json').is_file() or not python.is_file():
        raise ValueError('Missing local model configuration or interpreter')
    command = [str(python), '-B', '-m', 'vllm.entrypoints.openai.api_server',
               '--model', str(model), '--served-model-name', args.served_model,
               '--host', '127.0.0.1', '--port', str(port), '--dtype', 'bfloat16',
               '--tensor-parallel-size', str(len(args.gpus)),
               '--cpu-offload-gb', str(args.cpu_offload_gb),
               '--gpu-memory-utilization', '0.90',
               '--max-model-len', str(args.max_model_len),
               '--max-num-seqs', str(args.max_num_seqs),
               '--max-num-batched-tokens', '4096',
               '--limit-mm-per-prompt', '{"image":8,"video":0}',
               '--mm-processor-kwargs', '{"max_pixels":307200}',
               '--enforce-eager', '--disable-log-requests', '--seed', '20261103']
    if args.quantization:
        command.extend(['--quantization', args.quantization])
    if args.reasoning_parser:
        command.extend(['--reasoning-parser', args.reasoning_parser])
    cache = ROOT / '.runtime/crossing_vlm'
    env = {k: v for k, v in os.environ.items() if 'proxy' not in k.lower()}
    env.update(CUDA_VISIBLE_DEVICES=','.join(map(str, args.gpus)),
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
               HF_HUB_DISABLE_TELEMETRY='1', VLLM_NO_USAGE_STATS='1', DO_NOT_TRACK='1',
               TOKENIZERS_PARALLELISM='false', PYTHONDONTWRITEBYTECODE='1',
               OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
               HF_HOME=str(cache / 'huggingface'), XDG_CACHE_HOME=str(cache / 'cache'),
               VLLM_CACHE_ROOT=str(cache / 'vllm'),
               TORCHINDUCTOR_CACHE_DIR=str(cache / 'torchinductor'),
               TRITON_CACHE_DIR=str(cache / 'triton'))
    cache.mkdir(parents=True, exist_ok=True)
    state = dict(schema=1, phase='starting', created_at=now(), supervisor_pid=os.getpid(),
                 model_path=str(model), served_model=args.served_model, gpus=args.gpus,
                 quantization_override=args.quantization,
                 cpu_offload_gb=args.cpu_offload_gb, dtype='bfloat16', port=port,
                 base_url=f'http://127.0.0.1:{port}/v1', command=command,
                 gpu_admission=rows, offline=True)
    version_probe = "import importlib.metadata as m,json;print(json.dumps({p:m.version(p) for p in ['vllm','torch','transformers','tokenizers']}))"
    state['environment_versions'] = json.loads(subprocess.check_output(
        [str(python), '-B', '-c', version_probe], env=env, text=True))
    if tuple(map(int,state['environment_versions']['vllm'].split('.')[:2])) >= (0,19):
        command[command.index('--disable-log-requests')]='--no-enable-log-requests'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with (args.output / 'server.log').open('a') as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        state['server_pid'] = child.pid
        write_json(args.output / 'service.json', state)

        def stop(signum, frame):
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        start = time.monotonic()
        while child.poll() is None:
            if state['phase'] == 'starting':
                try:
                    with opener.open(state['base_url'] + '/models', timeout=2) as response:
                        models = json.load(response)
                    if any(m['id'] == state['served_model'] for m in models['data']):
                        state.update(phase='ready', ready_at=now())
                        write_json(args.output / 'service.json', state)
                        print(json.dumps({'phase': 'ready', 'base_url': state['base_url']}), flush=True)
                except (OSError, ValueError, KeyError):
                    pass
                if time.monotonic() - start > 1800:
                    state['error'] = 'server_startup_timeout'
                    stop(None, None)
            time.sleep(5)
        state.update(phase='stopped' if child.returncode == 0 else 'failed',
                     exit_code=child.returncode, finished_at=now())
        write_json(args.output / 'service.json', state)
        if child.returncode != 0:
            raise SystemExit(child.returncode if child.returncode > 0 else 1)


if __name__ == '__main__':
    main()
