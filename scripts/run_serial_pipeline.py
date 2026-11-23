"""Run a sealed serial recovery pipeline on a retained model and native simulator."""
import argparse
import fcntl
import getpass
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from core.serial_pipeline import save, sha
from core.serial_batch import batch_progress, record_episode_failure, write_retry_manifest
from scripts.run_oracle_existing_model import identity, assert_model, stop_simulator, NativeScoreCounter, retry_failures
from scripts.evaluate import check_gpu


def validate_run(out, score, identity_proof):
    results=[json.loads(p.read_text()) for p in (out/'episodes').glob('*/attempt_*/result.json')]
    expected=json.loads((out/'config.json').read_text())['episode_ids']
    progress=write_retry_manifest(out)
    marker = out/'scored_cycle.json'
    stopped_at_cycle = marker.is_file() and json.loads((out/'config.json').read_text()).get('stop_after_scored_cycle')
    if stopped_at_cycle:
        accepted = json.loads(marker.read_text())['episode_id']
        if not any(r['episode_id']==accepted and r['full_chain_observed'] for r in results):
            raise RuntimeError('Scored cycle does not match a completed recovery')
    if progress['pending'] and not stopped_at_cycle: raise RuntimeError('Incomplete episode records')
    official=json.loads(score.read_text()) if score.exists() else {}
    if official.get('val_unseen',{}).get('Count',0)!=len(results): raise RuntimeError('Native scoring incomplete')
    events=[json.loads(line) for p in (out/'episodes').glob('*/attempt_*/events.jsonl') for line in p.read_text().splitlines()]
    counts={k:sum(e['kind']==k for e in events) for k in sorted({e['kind'] for e in events})}
    proofs=[json.loads(p.read_text()) for result in (out/'episodes').glob('*/attempt_*/result.json')
            for p in result.parent.glob('recovery_*/memory_restore.json')]
    if not all(p['equal'] and p['restored']['content_sha256']==p['saved']['content_sha256'] for p in proofs):
        raise RuntimeError('Memory restoration evidence failed')
    assert_model(identity_proof)
    full=any(r['full_chain_observed'] for r in results)
    evidence=dict(native_scoring_complete=True,all_requested_scored=not (progress['skipped'] or progress['pending']),
                  remaining_unrun=progress['pending'],
                  skipped_episode_ids=progress['skipped_ids'],skipped_count=progress['skipped'],
                  full_chain_observed=full,episode_count=len(results),stage_counts=counts,
                  episodes_with_full_recovery=sum(bool(r['full_chain_observed']) for r in results),
                  all_episodes_had_full_recovery=bool(results) and all(r['full_chain_observed'] for r in results),
                  memory_restores=len(proofs),model_identity_unchanged=True,results=results,
                  limitation='Technical execution check; semantic correctness and navigation benefit are not established.')
    save(out/'validation.json',evidence); save(out/'official_result.json',official)
    return evidence


def check_semantic_service(service, opener):
    for key in ('supervisor_identity','server_identity'): assert_model(service[key])
    with opener.open(service['base_url']+'/models',timeout=15) as response:
        if service['model'] not in [m['id'] for m in json.load(response)['data']]:
            raise RuntimeError('Local semantic model is not ready')


def stop_owned_semantic_service(service, out):
    """Signal only the verified supervisor, which cleans up its own vLLM group."""
    saved=service['supervisor_identity']; assert_model(saved)
    if ('scripts/serve_qwen27b_standby.py ' not in saved['command']
            or Path(service['source_service_json']).parent.name not in saved['command']):
        raise RuntimeError('Refusing to stop an unrecognized semantic service')
    os.kill(saved['pid'],signal.SIGTERM)
    deadline=time.monotonic()+55
    source=Path(service['source_service_json'])
    while time.monotonic()<deadline:
        current=json.loads(source.read_text())
        if current['phase'] in ('stopped','failed') and 'cleanup' in current:
            save(out/'semantic_cleanup.json',current)
            return
        time.sleep(1)
    raise RuntimeError('Qwen supervisor did not confirm cleanup; inspect its service.json')


def admit_simulator_gpu(gpu, allow_active_shared=False):
    snapshot=check_gpu(gpu,12000,allow_shared=True)
    row=subprocess.check_output(['nvidia-smi','--id='+str(gpu),'--query-gpu=utilization.gpu',
                                 '--format=csv,noheader,nounits'],text=True)
    snapshot.update(utilization=int(row.strip()),allow_active_shared=allow_active_shared)
    if snapshot['utilization']>10 and not allow_active_shared:
        raise RuntimeError('Simulator GPU has active competing work')
    return snapshot


def run(a):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    out=a.campaign.resolve(); manifest=json.loads((out/'manifest.json').read_text()); code=Path(manifest['code_root'])
    for name,digest in manifest['code_sha256'].items():
        if sha(code/name)!=digest: raise RuntimeError('Frozen source changed: '+name)
    if sha(out/'config.json')!=manifest['config_sha256']: raise RuntimeError('Frozen config changed')
    if sha(out/'dataset/fine/val_unseen/val_unseen.json.gz')!=manifest['dataset_sha256']: raise RuntimeError('Frozen data changed')
    for name,digest in manifest.get('additional_sha256',{}).items():
        if sha(out/name)!=digest: raise RuntimeError('Frozen metadata changed: '+name)
    if (out/'launch.json').exists(): raise RuntimeError('Use a new run directory; existing evidence is immutable')
    configuration=json.loads((out/'config.json').read_text())
    local=configuration.get('semantic_provider')=='qwen_local'
    service=json.loads((out/'semantic_service.json').read_text()) if local else None
    if a.keys_stdin:
        os.environ['JEV_API_KEY']=getpass.getpass('JEV key: ')
        if not local: os.environ['DEEPSEEK_API_KEY']=getpass.getpass('DeepSeek key: ')
    required=('JEV_API_KEY',) if local else ('JEV_API_KEY','DEEPSEEK_API_KEY')
    if not all(os.environ.get(k) for k in required): raise RuntimeError('Missing runtime credentials')
    if a.detach:
        pid=os.fork()
        if pid:
            print(json.dumps(dict(supervisor_pid=pid,campaign=str(out))),flush=True); return
        os.setsid()
        with open(os.devnull,'rb') as stdin, (out/'supervisor.log').open('x') as log:
            os.dup2(stdin.fileno(),0); os.dup2(log.fileno(),1); os.dup2(log.fileno(),2)
    # Keys go only to this directly owned child environment, never to metadata.
    model=identity(a.model_pid)
    if '/service.py ' not in model['command'] or '/VLN_2026_Autumn/' not in model['command']:
        raise RuntimeError('Model is not the retained project service')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    if local: check_semantic_service(service,opener)
    with opener.open('http://127.0.0.1:%d/oracle/state'%a.port,timeout=30) as f: initial_policy=json.load(f)
    admissions=[]
    for _ in range(2):
        admissions.append(admit_simulator_gpu(a.gpu,a.allow_active_shared_gpu))
        time.sleep(2)
    save(out/'gpu_admission.json',dict(checks=admissions,time=time.time()))
    available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))
    if available<64*1024**2: raise RuntimeError('Insufficient host RAM')
    lock=(out/'run.lock').open('w'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ.update(manifest['runtime_env'])
    spec=importlib.util.spec_from_file_location('serial_native_launcher',code/'benchmarks/vlnverse/runner/run_full.py')
    native=importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
    run_id='peng_fine_serial_'+out.name.lower()
    config=out/'eval_config.py'; native.write_config(config,'StreamVLN',a.port,run_id,out/'dataset/fine','physical')
    samples=out/'storage/samples'; samples.mkdir(parents=True,exist_ok=(out/'continuation.json').exists())
    link=code/'benchmarks/vlnverse/upstream/data/sample_episodes'/run_id; link.parent.mkdir(parents=True,exist_ok=True); link.symlink_to(samples,target_is_directory=True)
    score=code/'benchmarks/vlnverse/upstream/logs'/run_id/'kujiale_result.json'
    if (out/'initial_score.json').exists(): save(score,json.loads((out/'initial_score.json').read_text()))
    env={k:v for k,v in os.environ.items() if not k.startswith(('VLN_','PENG_','STREAMVLN_','JANUSVLN_')) and not k.lower().endswith('_proxy')}
    if local: env.pop('DEEPSEEK_API_KEY',None)
    env.update(manifest['runtime_env'],VLN_SERIAL_OUTPUT=str(out),VLN_EVAL_SEED='2',PYTHONHASHSEED='2',
               CUDA_VISIBLE_DEVICES=str(a.gpu),VLN_SIM_RENDER_GPU=str(a.gpu),VLN_RSS_BUDGET_MIB='24000',
               OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',NO_PROXY='127.0.0.1,localhost',no_proxy='127.0.0.1,localhost')
    tmp=out/'tmp'; tmp.mkdir(); env.update(TMPDIR=str(tmp),TEMP=str(tmp),TMP=str(tmp))
    save(out/'launch.json',dict(time=time.time(),pid=os.getpid(),model=model,model_port=a.port,gpu=a.gpu,
                                initial_policy=initial_policy,run_id=run_id,credentials_on_disk=False,
                                allow_active_shared_gpu=a.allow_active_shared_gpu,
                                semantic_provider=configuration.get('semantic_provider','deepseek'),
                                release_owned_semantic_service=a.release_semantic_service))
    state=dict(phase='starting_simulator',model_pid=a.model_pid,model_retained=True,gpu=a.gpu,
               expected=len(manifest['episode_ids']),started_at=time.time(),
               semantic_gpu=service['gpu'] if service else None)
    save(out/'status.json',state); child=None; retained=False
    def stop(*_): raise KeyboardInterrupt('Stop requested; retained model is not stopped')
    for s in (signal.SIGINT,signal.SIGTERM): signal.signal(s,stop)
    try:
        count=NativeScoreCounter(score); failures=0
        for chunk_number in range(1,1001):
            assert_model(model)
            if local: check_semantic_service(service,opener)
            chunk=out/'chunks'/('%03d'%chunk_number); chunk.mkdir(parents=True)
            save(chunk/'gpu_admission.json',admit_simulator_gpu(a.gpu,a.allow_active_shared_gpu))
            log=chunk/'evaluator.log'; start=batch_progress(out)['processed']
            if chunk_number==1: (out/'evaluator.log').symlink_to(log.relative_to(out))
            print('CHUNK_START %d processed=%d/%d'%(chunk_number,start,state['expected']),flush=True)
            with log.open('x') as stream:
                child=subprocess.Popen(['bash',str(code/'benchmarks/vlnverse/runner/run_eval.sh'),str(config)],cwd=code,env=env,
                                       stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            state.update(phase='running',simulator_pid=child.pid,simulation_started=True,chunk=chunk_number,log=str(log))
            save(out/'owned_processes.json',dict(model=model,simulator_pid=child.pid,supervisor_pid=os.getpid(),borrowed_model=True,
                                                semantic_service=service,chunk=chunk_number))
            while child.poll() is None:
                assert_model(model)
                if (out/'runtime_failure.json').exists():
                    stop_simulator(child); break
                if local:
                    assert_model(service['supervisor_identity']); assert_model(service['server_identity'])
                progress=batch_progress(out)
                state.update(completed=count(),skipped=progress['skipped'],processed=progress['processed'],
                             pending=progress['pending'],updated_at=time.time()); save(out/'status.json',state)
                if (out/'simulator_retained.json').exists():
                    evidence=validate_run(out,score,model); retained=True
                    state.update(phase='complete_with_skips' if evidence['skipped_count'] else
                                 'complete_services_retained' if evidence['full_chain_observed'] else 'complete_without_full_recovery',
                                 completed=count(),validation=str(out/'validation.json'),full_chain_observed=evidence['full_chain_observed'],
                                 episodes_with_full_recovery=evidence['episodes_with_full_recovery'],finished_at=time.time())
                    save(out/'status.json',state); print(json.dumps(state),flush=True); break
                if time.time()-log.stat().st_mtime>900:
                    save(chunk/'timeout.json',dict(reason='Native 900-second no-progress timeout',time=time.time()))
                    stop_simulator(child); break
                time.sleep(3)
            if retained: break
            # A hard simulator error still defers only its identifiable task.
            # Normal API/schema errors already continue inside the same engine.
            for name in ('runtime_failure.json','runtime_error.json'):
                if (out/name).exists(): (out/name).rename(chunk/name)
            live=json.loads((out/'live.json').read_text()) if (out/'live.json').exists() else {}
            progress=batch_progress(out); eid=live.get('episode_id')
            if eid and eid not in progress['completed_ids']+progress['skipped_ids']:
                attempts=sorted((out/'episodes'/eid).glob('attempt_*'))
                if attempts:
                    record_episode_failure(out,eid,attempts[-1],
                        'Simulator exited before scoring (code %s)'%child.returncode,'simulator_exit',chunk=chunk_number)
            progress=write_retry_manifest(out); completed=progress['processed']
            save(chunk/'exit.json',dict(exit_code=child.returncode,completed_before=start,completed_after=completed,time=time.time()))
            print('CHUNK_END %d processed=%d/%d'%(chunk_number,completed,state['expected']),flush=True)
            if not progress['pending'] or (out/'scored_cycle.json').is_file():
                evidence=validate_run(out,score,model)
                phase = ('complete_with_skips' if progress['skipped'] else
                         'complete' if evidence['full_chain_observed'] else 'complete_without_full_recovery')
                state.update(phase=phase,completed=count(),skipped=progress['skipped'],
                             full_chain_observed=evidence['full_chain_observed'], validation=str(out/'validation.json'),
                             episodes_with_full_recovery=evidence['episodes_with_full_recovery'],
                             processed=completed,pending=progress['pending'],finished_at=time.time(),simulator_retained=False)
                save(out/'status.json',state); break
            failures=retry_failures(failures,start,completed); child=None
        if not retained and batch_progress(out)['pending'] and not (out/'scored_cycle.json').exists():
            raise RuntimeError('Native evaluator did not process all tasks')
    except BaseException as e:
        message=repr(e)
        for name in ('JEV_API_KEY','DEEPSEEK_API_KEY'): message=message.replace(os.environ.get(name,'\0'),'[REDACTED]')
        state.update(phase='failed',error=message,finished_at=time.time()); save(out/'status.json',state); raise
    finally:
        if not retained: stop_simulator(child)
        if local and a.release_semantic_service:
            try:
                stop_owned_semantic_service(service,out)
                state['semantic_service_released']=True
            except Exception as cleanup_error:
                state['semantic_cleanup_error']=str(cleanup_error)
            save(out/'status.json',state)
        lock.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--gpu',type=int,default=3); p.add_argument('--model-pid',type=int,required=True)
    p.add_argument('--port',type=int,required=True); p.add_argument('--keys-stdin',action='store_true')
    p.add_argument('--release-semantic-service',action='store_true',help='Release the explicitly owned Qwen supervisor after this batch')
    p.add_argument('--allow-active-shared-gpu',action='store_true',help='Explicit user permission to share a busy GPU; still require 12000 MiB free')
    p.add_argument('--detach',action='store_true',help='Read credentials, then continue independently with a supervisor log')
    run(p.parse_args())
