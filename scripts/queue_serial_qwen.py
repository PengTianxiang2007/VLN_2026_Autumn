"""Wait for the authorized GPUs, validate Qwen, then run the sealed 33-task batch.

No foreign process is stopped. Credentials remain in process memory only.
"""
import argparse
import getpass
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.serial_pipeline import save, sha
from scripts.run_oracle_existing_model import identity, assert_model


def resources():
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,memory.free,utilization.gpu',
                                 '--format=csv,noheader,nounits'],text=True)
    gpus={}
    for line in raw.splitlines():
        gpu,used,free,util=map(int,line.split(',')); gpus[gpu]=dict(used=used,free=free,utilization=util)
    available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
    return dict(gpus=gpus,host_available_kib=available)


def admissible(snapshot, retained_simulator_present):
    qwen=snapshot['gpus'][2]; sim=snapshot['gpus'][3]
    return (qwen['used']<1024 and qwen['utilization']<=10
            and sim['free']>=(9000 if retained_simulator_present else 12000) and sim['utilization']<=10
            and snapshot['host_available_kib']>=64*1024**2)


def alive(saved):
    proc=Path('/proc')/str(saved['pid'])
    if not proc.exists() or proc.joinpath('stat').read_text().split()[2]=='Z': return False
    assert_model(saved); return True


def stop_child(child, timeout=120):
    if child is not None and child.poll() is None:
        child.terminate()
        deadline=time.monotonic()+timeout
        while child.poll() is None and time.monotonic()<deadline: time.sleep(1)
        if child.poll() is None: raise RuntimeError('Owned supervisor did not finish cleanup')


def run(out, plan):
    state=dict(phase='waiting_for_resources',pid=os.getpid(),started_at=time.time(),expected=33,
               qwen_gpu=2,simulation_gpu=3,simulation_started=False)
    service=None; batch=None; probe=None
    def update(phase=None,**extra):
        state.update(extra,updated_at=time.time())
        if phase: state['phase']=phase
        save(out/'status.json',state)
    def stopped(*_): raise KeyboardInterrupt('Queue cancelled')
    signal.signal(signal.SIGTERM,stopped); signal.signal(signal.SIGINT,stopped)
    def verify_source():
        for name,digest in plan['source_sha256'].items():
            if sha(ROOT/name)!=digest: raise RuntimeError('Queued source changed; preserved snapshot requires review: '+name)
        for name,digest in plan['input_sha256'].items():
            if sha(name)!=digest: raise RuntimeError('Queued input changed: '+name)
    def wait_resources():
        consecutive=0
        while consecutive<3:
            assert_model(plan['streamvln_identity'])
            snapshot=resources(); old=alive(plan['old_simulator_identity'])
            consecutive=consecutive+1 if admissible(snapshot,old) else 0
            update('waiting_for_resources',resources=snapshot,consecutive_admissions=consecutive)
            if consecutive<3: time.sleep(10 if consecutive else 30)
    def launch(command, log, env=None):
        with Path(log).open('x') as stream:
            return subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    def wait_process(child):
        while child.poll() is None: time.sleep(3)
        if child.returncode: raise RuntimeError('Owned stage failed with exit code %s; see its log'%child.returncode)
    update()
    try:
        wait_resources(); verify_source()
        env=dict(os.environ); env.pop('DEEPSEEK_API_KEY',None)
        model_env={k:v for k,v in env.items() if not any(s in k.upper() for s in ('API_KEY','TOKEN','SECRET'))}
        service_dir=Path(plan['service_output']); service_file=service_dir/'service.json'
        service=launch([plan['qwen_python'],'-B',str(ROOT/'scripts/serve_qwen27b_standby.py'),
                        '--output',str(service_dir),'--config',plan['service_config'],'--gpu','2'],out/'service_launcher.log',model_env)
        update('loading_qwen',qwen_supervisor_pid=service.pid,service_json=str(service_file))
        while True:
            if service.poll() is not None: raise RuntimeError('Qwen startup failed; see service log')
            current=json.loads(service_file.read_text()) if service_file.exists() else {}
            if current.get('phase')=='ready' and current.get('smoke_passed'): break
            if current.get('phase')=='failed': raise RuntimeError('Qwen startup failed: '+current.get('error','unknown'))
            time.sleep(3)
        update('checking_live_image_protocol')
        probe=launch([plan['simulation_python'],'-B',str(ROOT/'scripts/check_serial_qwen.py'),
                      '--service',str(service_file),'--source',plan['preflight_source'],
                      '--output',str(out/'preflight')],out/'preflight.log',env)
        wait_process(probe)
        preflight=json.loads((out/'preflight/result.json').read_text())
        if not preflight['passed']: raise RuntimeError('Qwen protocol check failed')
        verify_source(); update('freezing_batch',preflight_passed=True,preflight_not_exercised=preflight.get('not_exercised',[]))
        probe=launch([plan['simulation_python'],'-B',str(ROOT/'scripts/prepare_serial_pipeline.py'),
                      '--output',plan['campaign'],'--cohort',plan['cohort'],
                      '--semantic-service',str(service_file),'--jev-endpoint','https://api.easyjev.online/v1/systemone'],
                      out/'prepare.log',env)
        wait_process(probe)
        old=plan['old_simulator_identity']
        if alive(old):
            marker=json.loads((Path(plan['old_campaign'])/'simulator_retained.json').read_text())
            if marker['pid']!=old['pid']: raise RuntimeError('Retained simulator marker identity changed')
            update('replacing_completed_simulator')
            (Path(plan['old_campaign'])/'simulator_retained.release').write_text('Authorized replacement for Qwen33 serial batch.\n')
            deadline=time.monotonic()+60
            while alive(old) and time.monotonic()<deadline: time.sleep(2)
            if alive(old):
                os.kill(old['pid'],signal.SIGTERM)
                deadline=time.monotonic()+30
                while alive(old) and time.monotonic()<deadline: time.sleep(2)
            if alive(old): raise RuntimeError('Owned old simulator did not exit; preserved for inspection')
        update('waiting_for_simulator_gpu')
        ready=0
        while ready<2:
            row=resources()['gpus'][3]
            ready=ready+1 if row['free']>=12000 and row['utilization']<=10 else 0
            if service.poll() is not None: raise RuntimeError('Qwen service stopped before navigation')
            if ready<2: time.sleep(5 if ready else 30)
        campaign=Path(plan['campaign'])
        batch=launch([plan['simulation_python'],'-B',str(campaign/'code/scripts/run_serial_pipeline.py'),
                      '--campaign',str(campaign),'--gpu','3','--model-pid',str(plan['streamvln_identity']['pid']),
                      '--port',str(plan['streamvln_port']),'--release-semantic-service'],out/'batch.log',env)
        update('batch_running',batch_pid=batch.pid,simulation_started=True,campaign=str(campaign))
        verified=False
        while batch.poll() is None:
            if not verified:
                requests=campaign/'episodes'
                jev=list(requests.glob('*/attempt_*/requests/*_jev/result.json'))
                semantic=[p for p in requests.glob('*/attempt_*/requests/*/answer.json') if '_jev' not in p.parent.name]
                if jev and semantic and (campaign/'live.json').exists():
                    live=json.loads((campaign/'live.json').read_text())
                    if live['action_count']>0:
                        proof=dict(time=time.time(),real_simulator_actions=live['action_count'],jev_results=len(jev),
                                   qwen_results=len(semantic),streamvln_identity=identity(plan['streamvln_identity']['pid']),
                                   full_recovery_pending=True,note='Startup validation only; no ongoing human monitoring required.')
                        save(out/'startup_verified.json',proof); save(campaign/'startup_verified.json',proof)
                        verified=True; update(startup_verified=True)
            time.sleep(5)
        batch_status=json.loads((campaign/'status.json').read_text())
        if batch.returncode or not batch_status['phase'].startswith('complete_'):
            raise RuntimeError('Batch stopped without complete results; see campaign/status.json')
        update('complete',completed=batch_status['completed'],finished_at=time.time(),batch_status=batch_status)
    except BaseException as error:
        message=str(error)
        if os.environ.get('JEV_API_KEY'): message=message.replace(os.environ['JEV_API_KEY'],'[REDACTED]')
        update('cancelled' if isinstance(error,KeyboardInterrupt) else 'failed',error=type(error).__name__+': '+message,finished_at=time.time())
    finally:
        errors=[]
        for name,child in [('batch',batch),('preflight_or_preparation',probe),('qwen',service)]:
            try: stop_child(child)
            except Exception as error: errors.append(name+': '+str(error))
        if errors: update(cleanup_errors=errors)
        save(out/'cleanup.json',dict(time=time.time(),errors=errors,resources=resources(),streamvln_retained=True))


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--queue',type=Path,required=True)
    p.add_argument('--keys-stdin',action='store_true'); p.add_argument('--detach',action='store_true')
    a=p.parse_args(); out=a.queue.resolve(); plan=json.loads((out/'plan.json').read_text())
    if (out/'status.json').exists(): raise RuntimeError('Queue already started; preserve it')
    if a.keys_stdin: os.environ['JEV_API_KEY']=getpass.getpass('JEV key: ')
    if not os.environ.get('JEV_API_KEY'): raise RuntimeError('Missing runtime JEV credential')
    if a.detach:
        pid=os.fork()
        if pid:
            print(json.dumps(dict(queue_pid=pid,queue=str(out))),flush=True); return
        os.setsid()
        with open(os.devnull,'rb') as stdin, (out/'supervisor.log').open('x') as log:
            os.dup2(stdin.fileno(),0); os.dup2(log.fileno(),1); os.dup2(log.fileno(),2)
    run(out,plan)


if __name__=='__main__': main()
