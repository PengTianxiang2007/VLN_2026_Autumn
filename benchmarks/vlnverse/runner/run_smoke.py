"""Run a capped model smoke on an official scene, or an H1 episode when authorized assets exist."""
import argparse, fcntl, json, os, signal, subprocess, sys, time, urllib.request
from pathlib import Path
RUNNER = Path(__file__).resolve().parent
ROOT = RUNNER.parent / "upstream"
PROJECT = RUNNER.parents[2]
sys.path.insert(0,str(PROJECT))
from core.paths import output_root, model_python, resource_root, model_environment, isaac_root
RESOURCE = resource_root()
parser = argparse.ArgumentParser()
parser.add_argument('--method', choices=['StreamVLN','JanusVLN'], required=True)
parser.add_argument('--gpu', type=int, required=True)
parser.add_argument('--steps', type=int, default=8)
parser.add_argument('--backend', choices=['physical','camera'], default='physical')
args = parser.parse_args()
if not 1 <= args.steps <= 8: raise SystemExit('Smoke action cap must be 1..8')
method_dir = output_root() / 'vlnverse' / args.method.lower()
run_name = 'peng_smoke_' + args.method.lower() + '_' + time.strftime('%Y%m%d_%H%M%S')
output = method_dir / 'results' / run_name
output.mkdir(parents=True, exist_ok=False)
lock_path = Path('/tmp') / f'peng_vlnverse_gpu_{args.gpu}.lock'
lock = lock_path.open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
query = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.free', '--format=csv,noheader,nounits'], text=True)
free = {int(line.split(',')[0]): int(line.split(',')[1]) for line in query.strip().splitlines()}
required = 32000 if args.method == 'JanusVLN' else 25000
if free.get(args.gpu,0) < required: raise SystemExit(f'GPU {args.gpu} needs {required} MiB free; no other process will be stopped')
python = str(model_python(args.method.lower()))
checkpoint = RESOURCE / 'models' / ('StreamVLN_R2R_v1_3' if args.method == 'StreamVLN' else 'JanusVLN_Extra')
env = model_environment(args.method.lower(), args.gpu)
env.update(CUDA_VISIBLE_DEVICES=str(args.gpu), OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1', NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost')
server = evaluator = None
try:
    with (output/'agent.log').open('w') as log:
        server = subprocess.Popen([python,'-u',str(RUNNER/'service.py'),'--method',args.method,'--checkpoint',str(checkpoint),'--output',str(output),'--smoke-steps',str(args.steps)], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (output/'processes.json').write_text(json.dumps({'agent_pid':server.pid,'gpu':args.gpu}))
    deadline = time.time()+900
    ready = output/'ready.json'
    while not ready.exists():
        if server.poll() is not None: raise RuntimeError(f'Agent exited {server.returncode}; see {output}/agent.log')
        if time.time()>deadline: raise TimeoutError('Model loading exceeded 15 minutes')
        time.sleep(2)
    port = json.loads(ready.read_text())['port']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    # Explicitly test two resets before the real episode.
    for _ in range(2):
        request = urllib.request.Request(f'http://127.0.0.1:{port}/agent/{args.method}/reset', data=b'{"reset_index":null}', headers={'Content-Type':'application/json'})
        with opener.open(request, timeout=60) as response: assert json.load(response)['status']=='success'
    if args.backend == 'physical':
        h1 = RESOURCE / 'assets/VLNVerse/Embodiments/vln-pe/h1/h1_vln_pointcloud.usd'
        if not h1.exists(): raise RuntimeError('H1 is gated and missing: physical smoke cannot run')
    runtime = isaac_root()
    deadline = time.time() + 900
    while not (runtime / '.peng_extraction_complete').exists():
        if time.time() > deadline: raise TimeoutError('Independent Isaac extraction not ready')
        time.sleep(2)
    config = output/'eval_config.py'
    subprocess.run([sys.executable,str(RUNNER/'make_config.py'),'--method',args.method,'--port',str(port),'--task-name',run_name,'--output',str(config)], check=True)
    print(f'Agent ready; running {args.backend} evaluator, logs: {output}', flush=True)
    eval_cmd = ['bash',str(RUNNER/'run_eval.sh'),str(config)]
    if args.backend == 'camera':
        env['PENG_SMOKE_BACKEND'] = 'camera'
        eval_cmd = ['bash',str(RUNNER/'run_eval.sh'),'--port',str(port),'--method',args.method,'--output',str(output),'--steps',str(args.steps),'--gpu',str(args.gpu)]
    eval_env = env.copy()
    if args.backend == 'camera':
        eval_env.pop('CUDA_VISIBLE_DEVICES', None) # Kit/Vulkan uses physical GPU indices; explicitly selected in camera_eval.py.
    with (output/'evaluator.log').open('w') as log:
        evaluator = subprocess.Popen(eval_cmd, env=eval_env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (output/'processes.json').write_text(json.dumps({'agent_pid':server.pid,'evaluator_pid':evaluator.pid,'gpu':args.gpu}))
    try: rc=evaluator.wait(timeout=1500)
    except subprocess.TimeoutExpired: raise TimeoutError('Smoke evaluator exceeded 25 minutes')
    if rc: raise RuntimeError(f'Evaluator exited {rc}; see {output}/evaluator.log')
    trace=json.loads((output/'agent_trace.json').read_text())
    if args.backend == 'camera':
        camera_result=json.loads((output/'camera_smoke_result.json').read_text())
        assert trace['model_calls'] >= 1, 'No actual model generation'
        camera_result['agent_trace']=trace
        camera_result['gpu']=args.gpu
        (output/'smoke_result.json').write_text(json.dumps(camera_result,ensure_ascii=False,indent=2))
        (method_dir/'latest_smoke.json').write_text(json.dumps({'output':str(output),'result':str(output/'smoke_result.json')},indent=2))
        print(json.dumps({'status':'passed_camera_model_smoke','result':str(output/'smoke_result.json')}),flush=True)
        sys.exit(0)
    result_path=ROOT/'logs'/run_name/'kujiale_result.json'
    result=json.loads(result_path.read_text())
    assert trace['model_calls'] >= 1, 'No actual model generation'
    assert result['val_unseen']['Count']==1, 'Expected one scored episode'
    info={'status':'passed','method':args.method,'mode':'physical','gpu':args.gpu,'scene':'kujiale_0272','episode_id':'kujiale_0272_26_1','smoke_step_cap':args.steps,'agent_trace':trace,'benchmark_result':result,'benchmark_result_path':str(result_path)}
    (output/'smoke_result.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    (method_dir/'latest_smoke.json').write_text(json.dumps({'output':str(output),'result':str(output/'smoke_result.json')},indent=2))
    print(json.dumps({'status':'passed','result':str(output/'smoke_result.json')},ensure_ascii=False),flush=True)
finally:
    # Only this launcher's own child process groups are managed.
    for process in (evaluator,server):
        if process is not None:
            try:
                os.killpg(process.pid,signal.SIGTERM)
                process.wait(timeout=20)
            except ProcessLookupError: pass
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait(timeout=10)
