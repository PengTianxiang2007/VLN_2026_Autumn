"""Coordinate GPU admission, local Qwen27 readiness, and the eight-trajectory development run."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from serve_crossing_vlm import gpu_rows,idle,write_json


def main():
    out=ROOT/'outputs/crossing_checkpoint/seed2_v1_20261103'
    model=ROOT/'.runtime/models/Qwen3.8-27B-FP8'
    venv=ROOT/'.runtime/crossing_vllm27'
    env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
    env.update(NO_PROXY='*',UV_CACHE_DIR=str(ROOT/'.runtime/cache'),UV_HTTP_TIMEOUT='30',UV_NATIVE_TLS='true',
               UV_CONCURRENT_DOWNLOADS='4',UV_PYTHON_DOWNLOADS='never')
    locks=[];children=[]
    state=dict(phase='gpu_admission',pid=os.getpid(),gpus=[0,3],model=str(model),
               model_choice='Qwen3.8-27B-FP8',transport='direct_no_proxy',
               reservation_scope='Project advisory locks; no claim of exclusive system-wide allocation.')
    def publish(phase,**kwargs):
        state.update(phase=phase,updated_at=datetime.now(timezone.utc).isoformat(),**kwargs)
        write_json(out/'iteration_status.json',state)
    def stop(signum,frame):
        for p in children:
            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
        publish('supervisor_stopped',signal=signum)
        raise SystemExit(0)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    for gpu in [0,3]:
        for prefix in ['peng_vlnverse_gpu_','vln_2026_gpu_']:
            f=open('/tmp/'+prefix+str(gpu)+'.lock','a')
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    for attempt in range(2):
        rows=gpu_rows()
        if any(not idle(next(r for r in rows if r['index']==g)) for g in [0,3]):
            publish('waiting_for_unoccupied_gpus',gpu_snapshot=rows)
            return
        time.sleep(3)
    publish('reserved_waiting_for_weights_and_environment',gpu_snapshot=rows)
    write_json(out/'pause.json',dict(phase='resumed_by_user',automatic_inference_resume=True,
                                   resumed_at=state['updated_at'],model=str(model)))
    requirements=['vllm==0.19.1','transformers==5.8.1','qwen-vl-utils','opencv-python-headless']
    wheelhouse=ROOT/'.runtime/crossing_wheelhouse'
    installer_options=[]
    if (wheelhouse/'pending_manifest.json').exists():
        publish('reserved_waiting_for_environment_wheels')
        while not (wheelhouse/'verified.json').exists():
            download=out/'environment_qwen27/download_status.json'
            if download.exists() and json.loads(download.read_text()).get('phase') in ['failed','stopped']:
                publish('environment_download_needs_attention');return
            time.sleep(10)
    if (wheelhouse/'verified.json').exists():
        local=[]
        for entry in json.loads((wheelhouse/'manifest.json').read_text()):
            path=wheelhouse/entry['filename']
            h=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
            if h.hexdigest()!=entry['sha256']:raise ValueError('Local wheel checksum mismatch: '+path.name)
            local.append(str(path))
        requirements=[r for r in requirements if not r.startswith('vllm==')]+local
        installer_options=['--offline','--constraint',str(wheelhouse/'constraints.txt')]
    write_json(out/'environment_qwen27/install_sources.json',dict(requirements=requirements,
               index='https://mirrors.aliyun.com/pypi/simple',transport='direct_no_proxy'))
    with (out/'environment_qwen27/install.log').open('a') as log:
        installer=subprocess.Popen([str(ROOT/'.runtime/tools/bin/uv'),'pip','install',
            '--python',str(venv/'bin/python'),'--verbose','--index-url','https://mirrors.aliyun.com/pypi/simple',
            *installer_options,*requirements],
            env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    children.append(installer)
    write_json(out/'environment_qwen27/install.pid.json',dict(pid=installer.pid))
    while True:
        if installer.poll() is not None and installer.returncode!=0:
            publish('environment_install_failed',exit_code=installer.returncode);return
        validation=model/'validation.json'
        if validation.exists() and json.loads(validation.read_text()).get('passed') and installer.poll()==0:
            break
        time.sleep(10)
    publish('starting_model')
    for f in locks:f.close()
    locks.clear()
    service=out/'service_qwen27_tp2';service.mkdir(exist_ok=True)
    with (service/'supervisor.log').open('a') as log:
        server=subprocess.Popen(['python3','-B',str(ROOT/'scripts/serve_crossing_vlm.py'),
            '--output',str(service),'--gpus','0','3','--model',str(model),
            '--python',str(venv/'bin/python'),'--served-model','crossing-qwen27b',
            '--reasoning-parser','qwen3','--max-num-seqs','4','--max-model-len','32768'],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    children.append(server)
    while True:
        status=service/'service.json'
        service_state=json.loads(status.read_text()) if status.exists() else {}
        if service_state.get('phase')=='ready' and service_state.get('supervisor_pid')==server.pid:break
        if server.poll() is not None:
            publish('model_start_failed');return
        time.sleep(5)
    publish('running_eight_development_trajectories')
    with (out/'qwen27_development.log').open('a') as log:
        replay=subprocess.Popen([str(ROOT/'benchmarks/vlnverse/.venv/bin/python'),'-B',
            str(ROOT/'scripts/replay_crossing_checkpoint.py'),'run','--output',str(out),
            '--tag','qwen27_fp8_dev_v1','--service',str(service),'--workers','4',
            '--thinking','--max-tokens','8192'],cwd=ROOT,env=env,stdout=log,
            stderr=subprocess.STDOUT,start_new_session=True)
    children.append(replay)
    code=replay.wait()
    publish('development_complete' if code==0 else 'development_needs_attention',exit_code=code)


if __name__=='__main__':main()
