"""Launch one frozen ten-case arm; clean up owned workers on completion or exit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'outputs/oracle_crossing/seed2_10_multi_20261103'


def write(p, obj):
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    tmp.replace(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--campaign', type=Path, default=DEFAULT)
    ap.add_argument('--arm', choices=['control','oracle'], required=True)
    ap.add_argument('--gpu', type=int, required=True)
    ap.add_argument('--sim-gpu', type=int, required=True)
    ap.add_argument('--after-control', action='store_true',help='Wait for verified control completion and cleanup before GPU admission')
    args = ap.parse_args()
    campaign = args.campaign.resolve()
    manifest = json.loads((campaign/'manifest.json').read_text())
    if args.arm=='oracle' and manifest.get('requires_complete_campaign'):
        predecessor=Path(manifest['requires_complete_campaign'])/'status_oracle.json'
        assert predecessor.exists() and json.loads(predecessor.read_text())['phase']=='complete', 'Finish the authorized early-intervention ten cases first'
    conf = manifest[args.arm]
    code = Path(conf['code_root'])
    for name, expected in conf['code_sha256'].items():
        if hashlib.sha256((code/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen code changed: '+name)
    for f in json.loads((campaign/'model_fingerprints.json').read_text())['files']:
        s = Path(f['path']).stat()
        assert (s.st_size,s.st_mtime_ns,s.st_ino)==(f['bytes'],f['mtime_ns'],f['inode'])
    if args.after_control:
        assert args.arm=='oracle'
        while True:
            p=campaign/'status_control.json'
            status=json.loads(p.read_text()) if p.exists() else {}
            if status.get('phase')=='complete':break
            if status.get('phase') in ('failed','stopped'):
                raise RuntimeError('Control did not complete; inspect its results before starting Oracle')
            time.sleep(5)
    # No process eviction and no broad GPU sharing. Two current resource samples.
    admission=[]
    for sample in range(2):
        rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True)
        found={int(v[0]):list(map(int,v[1:])) for line in rows.splitlines() if (v:=line.split(','))}
        for g in {args.gpu,args.sim_gpu}:
            used,free,util=found[g]
            assert used<1024 and free>=46000 and util<=10,(g,found[g])
        admission.append(found)
        if sample==0:time.sleep(5)
    env={k:v for k,v in dict(os.environ,**conf['runtime_env']).items() if not k.lower().endswith('_proxy')}
    run=Path(env['VLN_OUTPUT_ROOT'])/'vlnverse/streamvln/results'/conf['run_id']
    command=[sys.executable,'-B',str(code/'benchmarks/vlnverse/runner/run_full.py'),
             '--method','StreamVLN','--mode','physical','--seed','2',
             '--gpu',str(args.gpu),'--sim-gpu',str(args.sim_gpu),
             '--episode-ids',*conf['episode_ids'],
             '--resume' if (run/'run.json').exists() else '--run-id',conf['run_id']]
    state=dict(phase='starting',arm=args.arm,pid=os.getpid(),gpu=args.gpu,sim_gpu=args.sim_gpu,
               run=str(run),command=command,started_at=time.time(),admission=admission)
    status=campaign/f'status_{args.arm}.json'
    child=None
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        with (campaign/f'{args.arm}.log').open('a') as log:
            child=subprocess.Popen(command,cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            state.update(phase='running',launcher_pid=child.pid);write(status,state)
            while child.poll() is None:
                state['updated_at']=time.time();write(status,state)
                time.sleep(5)
            state.update(phase='complete' if child.returncode==0 else 'failed',exit_code=child.returncode)
    except BaseException as e:
        state.update(phase='stopped' if isinstance(e,KeyboardInterrupt) else 'failed',error=str(e))
        raise
    finally:
        if child is not None and child.poll() is None:
            # Launcher handles SIGTERM and its independently grouped service/sim children.
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=55)
            except subprocess.TimeoutExpired:
                raise RuntimeError('Owned launcher did not clean up; inspect its owned_processes.json')
        state['finished_at']=time.time()
        state['gpu_after']=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,memory.free,utilization.gpu','--format=csv'],text=True)
        write(status,state)
    if state['phase']!='complete':
        raise SystemExit(1)


if __name__=='__main__':main()
