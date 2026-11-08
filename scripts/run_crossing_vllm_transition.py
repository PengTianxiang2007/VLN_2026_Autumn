"""Start vLLM after releasing the direct backend, check saved inputs, then run all eight development cases."""
import json
import os
from pathlib import Path
import subprocess
import time
from serve_crossing_vlm import now,write_json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/crossing_checkpoint/seed2_v1_20261103'


def main():
    env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
    env.update(OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
    state=dict(pid=os.getpid(),backend='vllm',model='Qwen3.8-27B-FP8',gpus=[0,3])
    def publish(phase,**kwargs):
        state.update(phase=phase,updated_at=now(),**kwargs);write_json(OUT/'iteration_status.json',state)
    service=OUT/'service_qwen27_tp2';service.mkdir(exist_ok=True)
    with (service/'supervisor.log').open('a') as log:
        server=subprocess.Popen(['python3','-B',str(ROOT/'scripts/serve_crossing_vlm.py'),
            '--output',str(service),'--gpus','0','3','--model',str(ROOT/'.runtime/models/Qwen3.8-27B-FP8'),
            '--python',str(ROOT/'.runtime/crossing_vllm27/bin/python'),'--served-model','crossing-qwen27b',
            '--reasoning-parser','qwen3','--max-num-seqs','4','--max-model-len','32768'],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    publish('starting_vllm_after_transformers',service_supervisor_pid=server.pid)
    while server.poll() is None:
        path=service/'service.json';info=json.loads(path.read_text()) if path.exists() else {}
        if info.get('phase')=='ready' and info.get('supervisor_pid')==server.pid:break
        time.sleep(5)
    else:
        publish('vllm_start_needs_attention',exit_code=server.returncode);return
    python=str(ROOT/'benchmarks/vlnverse/.venv/bin/python')
    with (OUT/'backend_comparison.log').open('a') as log:
        comparison=subprocess.Popen([python,'-B',str(ROOT/'scripts/compare_crossing_backends.py'),
            '--output',str(OUT),'--source-tag','qwen27_tf_bf16_dev_v1','--service',str(service),'--count','5'],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    publish('checking_backend_transition',comparison_pid=comparison.pid)
    code=comparison.wait()
    if code:
        publish('backend_comparison_needs_attention',exit_code=code);return
    with (OUT/'qwen27_development.log').open('a') as log:
        replay=subprocess.Popen([python,'-B',str(ROOT/'scripts/replay_crossing_checkpoint.py'),
            'run','--output',str(OUT),'--tag','qwen27_fp8_dev_v1','--service',str(service),
            '--workers','4','--thinking','--max-tokens','8192'],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    publish('running_eight_development_trajectories',replay_pid=replay.pid)
    code=replay.wait();publish('development_complete' if code==0 else 'development_needs_attention',exit_code=code)


if __name__=='__main__':main()
