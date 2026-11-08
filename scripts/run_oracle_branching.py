"""Run paired ten-case semantic Oracle, one shared trunk and three outcomes per case."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
def write(p,d):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2));tmp.replace(p)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--campaign',type=Path,required=True);ap.add_argument('--gpu',type=int,required=True)
    ap.add_argument('--episodes',nargs='+',help='Optional authorized subset for validation; never silently rerun existing outputs')
    ap.add_argument('--allow-shared-gpu',action='store_true',help='Allow a low-load card with at least 40000 MiB free; never stop existing processes')
    ap.add_argument('--attempt-tag',default='',help='New launcher/log identity after a diagnosed pre-navigation startup failure')
    ap.add_argument('--model-startup-timeout',type=int,default=900,help='Startup-only wait; does not change navigation budget')
    a=ap.parse_args();out=a.campaign.resolve();m=json.loads((out/'manifest.json').read_text())
    if not 900<=a.model_startup_timeout<=3600:ap.error('Startup wait must be between 900 and 3600 seconds')
    if a.attempt_tag and not all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in a.attempt_tag):ap.error('Invalid attempt tag')
    code=Path(m['code_root']);lock=(out/'campaign.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for n,h in m['code_sha256'].items():
        if hashlib.sha256((code/n).read_bytes()).hexdigest()!=h:raise RuntimeError('Frozen code changed: '+n)
    episodes=a.episodes or m['episode_ids']
    assert set(episodes)<=set(m['episode_ids'])
    env={k:v for k,v in dict(os.environ,**m['runtime_env']).items() if not k.lower().endswith('_proxy')}
    state=dict(phase='starting',pid=os.getpid(),gpu=a.gpu,started_at=time.time(),completed=[],expected=episodes,allow_shared_gpu=a.allow_shared_gpu,attempt_tag=a.attempt_tag,model_startup_timeout=a.model_startup_timeout)
    child=None
    def stop(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        for eid in episodes:
            case=out/'oracle_records'/eid
            if (case/'results.json').exists():
                rows=json.loads((case/'results.json').read_text());assert len(rows)==3
                state['completed'].append(eid);continue
            if case.exists():raise RuntimeError('Incomplete case exists; preserve it and explicitly diagnose before new run: '+eid)
            samples=[]
            for sample in range(2):
                rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True)
                found={int(v[0]):list(map(int,v[1:])) for line in rows.splitlines() if (v:=line.split(','))}
                used,free,util=found[a.gpu]
                assert ((free>=40000 if a.allow_shared_gpu else used<1024 and free>=46000) and util<=10),found[a.gpu]
                available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
                assert available>=64*1024**2,available
                samples.append(found)
                if sample==0:time.sleep(30 if a.allow_shared_gpu else 5)
            run_id='peng_fine_paired_'+out.name.replace('-','_').lower()+'_'+eid
            if a.attempt_tag:run_id+='_'+a.attempt_tag
            command=[sys.executable,'-B',str(code/'benchmarks/vlnverse/runner/run_full.py'),
                '--method','StreamVLN','--mode','physical','--seed','2','--gpu',str(a.gpu),'--sim-gpu',str(a.gpu),
                '--episode-ids',eid,'--run-id',run_id]
            if a.allow_shared_gpu:command.append('--allow-shared-gpu')
            if a.model_startup_timeout!=900:
                command=[sys.executable,'-B',str(ROOT/'scripts/run_oracle_branch_launcher.py'),'--code-root',str(code),
                         '--model-startup-timeout',str(a.model_startup_timeout),'--',*command[3:]]
            state.update(phase='running',episode_id=eid,command=command,admission=samples)
            log_name=eid+('_'+a.attempt_tag if a.attempt_tag else '')+'.log'
            with (out/log_name).open('x') as log:
                child=subprocess.Popen(command,cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                state['launcher_pid']=child.pid
                while child.poll() is None:
                    state['updated_at']=time.time();write(out/'status.json',state);time.sleep(5)
            if child.returncode!=0:raise RuntimeError(f'{eid} failed with {child.returncode}; inspect preserved logs')
            rows=json.loads((case/'results.json').read_text());assert len(rows)==3
            state['completed'].append(eid);child=None
            state['gpu_after']=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu','--format=csv'],text=True)
            write(out/'status.json',state)
        state['phase']='complete'
    except BaseException as error:
        state.update(phase='stopped' if isinstance(error,KeyboardInterrupt) else 'failed',error=str(error));raise
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=55)
            except subprocess.TimeoutExpired:state['cleanup_error']='Owned launcher did not exit; inspect owned_processes.json'
        state['finished_at']=time.time();write(out/'status.json',state)

if __name__=='__main__':main()
