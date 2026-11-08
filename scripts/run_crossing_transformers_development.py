"""Start the approved direct-Transformers development path, with one complete first case."""
import json
import os
from pathlib import Path
import subprocess
import time
from serve_crossing_vlm import now, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/crossing_checkpoint/seed2_v1_20261103'


def main():
    service = OUT / 'service_qwen27_transformers'
    service.mkdir(exist_ok=True)
    env = {k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
    env.update(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4')
    state = dict(pid=os.getpid(), backend='transformers', model='Qwen3.8-27B-FP8',
                 gpus=[0,3], vllm_dependencies='Continue domestic direct downloads in background.')
    def publish(phase, **kwargs):
        state.update(phase=phase, updated_at=now(), **kwargs)
        write_json(OUT / 'iteration_status.json', state)
    with (service / 'server.log').open('a') as log:
        server = subprocess.Popen([
            '/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/qwen3vl-vllm/bin/python',
            '-B', '-u', str(ROOT/'scripts/serve_crossing_transformers.py'),
            '--output',str(service),'--gpus','0','3'],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    publish('loading_transformers_model',server_pid=server.pid)
    while server.poll() is None:
        path=service/'service.json'
        info=json.loads(path.read_text()) if path.exists() else {}
        if info.get('phase')=='ready' and info.get('server_pid')==server.pid:
            break
        time.sleep(5)
    else:
        publish('transformers_start_failed',exit_code=server.returncode)
        return
    with (OUT/'transformers_development.log').open('a') as log:
        replay=subprocess.Popen([str(ROOT/'benchmarks/vlnverse/.venv/bin/python'),'-B',
            str(ROOT/'scripts/replay_crossing_checkpoint.py'),'run','--output',str(OUT),
            '--tag','qwen27_tf_bf16_dev_v1','--service',str(service),'--workers','1',
            '--limit-cases','1','--thinking','--max-tokens','8192'],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    publish('running_transformers_first_development_case',replay_pid=replay.pid)
    code=replay.wait()
    publish('transformers_first_case_complete' if code==0 else 'transformers_replay_needs_attention',
            exit_code=code)


if __name__=='__main__':main()
