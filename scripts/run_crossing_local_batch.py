"""Run one registered local batch, then clean its exact process sessions and export."""
import argparse, fcntl, json, os, signal, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from test_crossing_single_gpu import gpu_snapshot, process, owned_processes, now, write
ROOT=Path(__file__).resolve().parents[1]

def cleanup(child):
    if child is None:return []
    known=owned_processes(child);signals=[]
    def send(pid,sig):
        expected=known[pid];current=process(pid)
        if current and current['start']==expected['start'] and current['session']==child.pid and current['state']!='Z':
            try:os.kill(pid,sig);signals.append(dict(pid=pid,signal=int(sig),start=current['start']))
            except ProcessLookupError:pass
    for pid in sorted(known,reverse=True):send(pid,signal.SIGTERM)
    end=time.monotonic()+20
    while time.monotonic()<end:
        if not any((p:=process(pid)) and p['start']==row['start'] and p['state']!='Z' for pid,row in known.items()):break
        time.sleep(1)
    known.update(owned_processes(child))
    for pid in sorted(known,reverse=True):send(pid,signal.SIGKILL)
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:pass
    remaining=[p for pid,row in known.items() if (p:=process(pid)) and p['start']==row['start'] and p['state']!='Z']
    return dict(signals=signals,remaining=remaining)

def main(output):
    p=output.resolve();r=json.loads((p/'registration.json').read_text());tag=r['tag'];gpu=r['gpu']
    service=p/'service_01';service.mkdir();server=None;replay=None;locks=[];error=None;result='failed';clean={}
    state=dict(phase='preparing',tag=tag,started_at=now(),supervisor_pid=os.getpid(),gpu=gpu)
    def phase(name,**kw):
        state.update(phase=name,updated_at=now(),**kw);write(p/'status.json',state);print(json.dumps(state),flush=True)
    def stop(*args):raise KeyboardInterrupt('Termination requested')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    phase('preparing')
    try:
        for prefix in ['peng_vlnverse_gpu_','vln_2026_gpu_']:
            f=(Path('/tmp')/(prefix+str(gpu)+'.lock')).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
        admission=[]
        for i in range(2):
            snap=gpu_snapshot();admission.append(snap);row=next(x for x in snap['gpus'] if x['index']==gpu)
            # Empty-card admission; never reclaim a foreign process.
            uuid=subprocess.check_output(['nvidia-smi','-i',str(gpu),'--query-gpu=uuid','--format=csv,noheader'],text=True).strip()
            if row['used_mib']>=1024 or row['utilization']>10 or uuid in snap['compute_apps']:raise RuntimeError('GPU no longer idle')
            available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
            if available<64*1024**2:raise RuntimeError('Host memory below 64 GiB admission')
            if i==0:time.sleep(5)
        write(service/'admission.json',admission)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}/v1';model=Path(r['model_path']);python=ROOT/'.runtime/crossing_vllm27/bin/python'
        cmd=[str(python),'-B','-m','vllm.entrypoints.openai.api_server','--model',str(model),'--served-model-name',r['served_model'],
             '--host','127.0.0.1','--port',str(port),'--dtype','bfloat16','--tensor-parallel-size','1','--cpu-offload-gb','0',
             '--gpu-memory-utilization',str(r['gpu_memory_utilization']),'--max-model-len','32768','--max-num-seqs',str(r['concurrency']),
             '--max-num-batched-tokens','4096','--limit-mm-per-prompt','{"image":8,"video":0}',
             '--mm-processor-kwargs','{"max_pixels":307200}','--enforce-eager','--no-enable-log-requests','--seed','20261103','--reasoning-parser','qwen3']
        env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()};cache=ROOT/'.runtime/crossing_vlm'
        env.update(CUDA_VISIBLE_DEVICES=str(gpu),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',
                   HF_HUB_DISABLE_TELEMETRY='1',VLLM_NO_USAGE_STATS='1',DO_NOT_TRACK='1',TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1',
                   OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',HF_HOME=str(cache/'huggingface'),XDG_CACHE_HOME=str(cache/'cache'),
                   VLLM_CACHE_ROOT=str(cache/'vllm'),TORCHINDUCTOR_CACHE_DIR=str(cache/'torchinductor'),TRITON_CACHE_DIR=str(cache/'triton'))
        versions=json.loads(subprocess.check_output([str(python),'-B','-c','import json,importlib.metadata as m;print(json.dumps({x:m.version(x) for x in ["vllm","torch","transformers"]}))'],env=env,text=True))
        with (service/'server.log').open('x') as log:server=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        svc=dict(phase='loading',base_url=base,served_model=r['served_model'],model_path=str(model),dtype='bfloat16',cpu_offload_gb=0,
                 command=cmd,environment_versions=versions,gpus=[gpu],server_pid=server.pid,backend='vllm',offline=True)
        write(service/'service.json',svc);write(service/'server_process.json',process(server.pid));phase('loading',server_pid=server.pid,base_url=base)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));deadline=time.monotonic()+2700
        while True:
            if server.poll() is not None:raise RuntimeError('Model server exited during loading')
            try:
                with opener.open(base+'/models',timeout=2) as response:models=json.load(response)
                if any(m['id']==r['served_model'] for m in models['data']):break
            except (OSError,ValueError,KeyError):pass
            if time.monotonic()>deadline:raise TimeoutError('Model startup exceeded 2700 seconds')
            time.sleep(2)
        svc.update(phase='ready',ready_at=now());write(service/'service.json',svc)
        replay_cmd=[sys.executable,'-B',str(Path(r['source'])/'scripts/replay_crossing_checkpoint.py'),'run','--output',str(p),'--tag',tag,
                    '--split','development','--service',str(service),'--workers',str(r['concurrency']),'--max-tokens','8192']
        with (p/'replay.log').open('x') as log:replay=subprocess.Popen(replay_cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        phase('running',replay_pid=replay.pid,expected_calls=r['expected_model_calls'],concurrency=r['concurrency']);deadline=time.monotonic()+28800
        while replay.poll() is None:
            if server.poll() is not None:raise RuntimeError('Model server exited during replay')
            if time.monotonic()>deadline:raise TimeoutError('Eight-hour batch limit')
            time.sleep(2)
        if replay.returncode:raise RuntimeError('Replay failed; inspect per-case status')
        result='inference_complete'
    except BaseException as exc:error=type(exc).__name__+': '+str(exc)
    finally:
        clean['replay']=cleanup(replay);clean['server']=cleanup(server)
        clean['gpu_after_cleanup']=gpu_snapshot();write(p/'cleanup.json',clean)
        for f in locks:f.close()
        if (service/'service.json').exists():
            svc=json.loads((service/'service.json').read_text());svc.update(phase='stopped',finished_at=now());write(service/'service.json',svc)
    try:
        if any(v.get('remaining') for k,v in clean.items() if k!='gpu_after_cleanup' and isinstance(v,dict)):raise RuntimeError('Owned process cleanup incomplete')
        if result=='inference_complete':
            phase('exporting',gpu_released=True)
            subprocess.run([sys.executable,'-B',str(ROOT/'scripts/analyze_crossing_checkpoint.py'),'--output',str(p),'--tag',tag],check=True,timeout=600)
            subprocess.run([str(ROOT/'backbone/streamvln/.venv/bin/python'),'-B',str(ROOT/'scripts/export_crossing_iteration.py'),'--output',str(p),'--tag',tag,'--destination',str(p/'exports/final')],check=True,timeout=600)
            result='complete'
    except BaseException as exc:error=type(exc).__name__+': '+str(exc);result='failed'
    phase('complete' if result=='complete' else 'failed',error=error,finished_at=now(),gpu_released=not clean.get('server',{}).get('remaining') if isinstance(clean.get('server'),dict) else True)
    for path in r['documentation']:
        with (ROOT/path).open('a') as f:f.write('\nQwen4B三条最终状态：'+json.dumps(state,ensure_ascii=False)+'\n')
    return 0 if result=='complete' else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();sys.exit(main(args.output))
