"""Finish the frozen vLLM environment offline without allocating or waiting for GPUs."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from serve_crossing_vlm import now, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/crossing_checkpoint/seed2_v1_20261103/environment_qwen27'
WHEELS = ROOT/'.runtime/crossing_wheelhouse'


def main():
    lock=(OUT/'install_offline.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state=dict(pid=os.getpid(),gpu_allocation=False)
    def publish(phase,**kwargs):
        state.update(phase=phase,updated_at=now(),**kwargs)
        write_json(OUT/'offline_install_status.json',state)
    publish('waiting_for_verified_wheels')
    while not (WHEELS/'verified.json').exists():
        status=json.loads((OUT/'download_status.json').read_text())
        if status['phase'] in ['failed','stopped']:
            publish('download_needs_attention',download_status=status)
            return
        time.sleep(10)
    manifest=json.loads((WHEELS/'manifest.json').read_text())
    verified=json.loads((WHEELS/'verified.json').read_text())
    assert verified['passed'] and verified['files']==manifest
    for entry in manifest:
        h=hashlib.sha256()
        with (WHEELS/entry['filename']).open('rb') as f:
            for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
        assert h.hexdigest()==entry['sha256'],entry['filename']
    env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
    env.update(UV_CACHE_DIR=str(ROOT/'.runtime/cache'),UV_CONCURRENT_INSTALLS='4',
               UV_PYTHON_DOWNLOADS='never',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
    python=ROOT/'.runtime/crossing_vllm27/bin/python'
    command=[str(ROOT/'.runtime/tools/bin/uv'),'pip','install','--offline',
             '--python',str(python),'--index-url','https://mirrors.aliyun.com/pypi/simple',
             '--constraint',str(WHEELS/'constraints.txt'),
             'vllm==0.19.1','transformers==5.8.1','qwen-vl-utils','opencv-python-headless',
             *[str(WHEELS/e['filename']) for e in manifest]]
    with (OUT/'install_offline.log').open('a') as log:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    publish('installing_offline',installer_pid=child.pid,verified_wheels=len(manifest))
    code=child.wait()
    if code:
        publish('failed',exit_code=code)
        return
    code="import importlib.metadata as m,json; print(json.dumps({p:m.version(p) for p in ['vllm','torch','transformers','tokenizers']}))"
    versions=json.loads(subprocess.check_output([str(python),'-B','-c',code],env=env,text=True))
    publish('installed',environment_versions=versions,model_inference_tested=False)


if __name__=='__main__':main()
