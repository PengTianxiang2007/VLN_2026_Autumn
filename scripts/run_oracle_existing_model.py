"""Run the native evaluator with an explicitly retained, already loaded model.

No model service is started/stopped here. Native episode/scene/RSS behavior is
unchanged. The last simulator is retained after complete scoring, as requested.
"""
import argparse
import fcntl
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_oracle_distance import load_campaign, write
from scripts.evaluate import check_gpu
from core.vlnverse_reproduction import digest_json
from core.seeding import SEED_SCHEME
from core.paths import simulation_python
from core.vlnverse_reproduction import verify_resume


def execution_code(manifest, revision):
    if revision is None:
        return Path(manifest['code_root'])
    record=json.loads((revision/'revision.json').read_text())
    if record['base_code_sha256']!=manifest['code_sha256']:
        raise RuntimeError('Code revision has a different frozen base')
    hashes=record['code_sha256']
    if set(hashes)!=set(manifest['code_sha256']):
        raise RuntimeError('Code revision changed the source inventory')
    allowed={'scripts/run_oracle_existing_model.py','core/oracle_distance_runtime.py',
             'tests/test_oracle_existing_model.py'}
    for name,expected in hashes.items():
        if expected!=manifest['code_sha256'][name] and name not in allowed:
            raise RuntimeError('Unexpected resume source change: '+name)
        if hashlib.sha256((revision/'code'/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Resume source changed: '+name)
    return revision/'code'


def validate_resume(output, manifest, args, saved, selected):
    meta=json.loads((output/'run.json').read_text())
    borrowed=json.loads((output/'borrowed_model.json').read_text())
    verify_resume(meta,selected,manifest['seed'])
    model_gpu=args.gpu if getattr(args,'model_gpu',None) is None else args.model_gpu
    if (meta['run_id']!=args.run_id or meta['gpu']!=model_gpu or
            meta.get('sim_gpu',args.gpu)!=args.gpu or meta['borrowed_model_port']!=args.port):
        raise RuntimeError('Resume changed run ID, GPU or model port')
    if borrowed['identity']!=saved or meta['borrowed_model']!=saved:
        raise RuntimeError('Resume must use the same retained model process')
    if Path(borrowed['trace']).resolve()!=args.model_trace.resolve():
        raise RuntimeError('Resume changed the model evidence log')
    if args.model_trace.stat().st_size<borrowed['trace_offset']:
        raise RuntimeError('Model evidence log was truncated')
    owned=json.loads((output/'owned_processes.json').read_text())
    pid=owned['evaluator_pid'];proc=Path('/proc')/str(pid)
    if proc.exists() and proc.joinpath('stat').read_text().split()[2]!='Z':
        raise RuntimeError('Previous simulator PID is still live; do not start another')
    return meta,borrowed


def retry_failures(previous, start, completed):
    # Same progress rule as native run_full.py, including nonzero simulator exits.
    failures=previous+1 if completed<=start else 0
    if failures>=3:
        raise RuntimeError('Three native simulator chunks made no progress')
    return failures


class NativeScoreCounter:
    """The native logger rewrites JSON in place; polling may see a partial write.

    Keep the last fully parsed count. Completion/export still require the native
    simulator's marker and a complete, independently validated result file.
    """
    def __init__(self,path):
        self.path=path;self.completed=0

    def __call__(self):
        if not self.path.exists():return self.completed
        try:result=json.loads(self.path.read_text())
        except json.JSONDecodeError:return self.completed
        completed=result.get('val_unseen',{}).get('Count',0)
        if type(completed) is not int or completed<self.completed:
            raise RuntimeError('Native scoring count regressed or is invalid')
        self.completed=completed
        return completed


def identity(pid):
    p=Path('/proc')/str(pid)
    return dict(pid=pid,start_ticks=p.joinpath('stat').read_text().split()[21],
                command=p.joinpath('cmdline').read_bytes().replace(b'\x00',b' ').decode())


def assert_model(saved):
    current=identity(saved['pid'])
    if current!=saved:
        raise RuntimeError('Retained model PID identity changed')


def stop_simulator(child):
    """Only the directly owned simulator process group is ever cleaned up."""
    if child is not None and child.poll() is None:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)


def collect_trace(source,offset,destination):
    with Path(source).open('rb') as f:
        f.seek(offset);data=f.read()
    if data and not data.endswith(b'\n'):
        raise RuntimeError('Model trace ended in an incomplete record')
    destination.write_bytes(data)
    return dict(offset=offset,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def run(args):
    campaign=args.campaign.resolve();manifest=load_campaign(campaign)
    model_gpu=args.gpu if getattr(args,'model_gpu',None) is None else args.model_gpu
    if list(manifest['arms'])!=[args.arm]:
        raise ValueError('This retained-service campaign must contain only the requested arm')
    saved=identity(args.model_pid)
    model_project=Path(manifest['runtime_env']['STREAMVLN_VENV']).parents[2]
    if '/service.py ' not in saved['command'] or str(model_project) not in saved['command']:
        raise RuntimeError('Not this project model service')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f'http://127.0.0.1:{args.port}/oracle/state',timeout=15) as f:initial_policy=json.load(f)
    check_gpu(args.gpu,12000,allow_shared=True)
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
    if available<64*1024**2:raise RuntimeError('Less than 64 GiB host memory available')
    os.environ.update(manifest['runtime_env'])
    code=execution_code(manifest,args.code_revision);runner=code/'benchmarks/vlnverse/runner'
    spec=importlib.util.spec_from_file_location('original_run_full',runner/'run_full.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    output=campaign/'runs/vlnverse/streamvln/results'/args.run_id
    output.mkdir(parents=True,exist_ok=args.resume)
    lock=(output/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    dataset=output/'dataset/fine'
    prepared=campaign/'prepared/dataset/fine/val_unseen/val_unseen.json.gz'
    with gzip.open(prepared,'rt') as f:selected=json.load(f)['episodes']
    assert {e['episode_id'] for e in selected}==set(manifest['episode_ids'])
    if args.resume:
        previous_meta,borrowed=validate_resume(output,manifest,args,saved,selected)
        with gzip.open(dataset/'val_unseen/val_unseen.json.gz','rt') as f:
            if json.load(f)['episodes']!=selected:raise RuntimeError('Resume dataset changed')
    else:
        (dataset/'val_unseen').mkdir(parents=True)
        with gzip.open(dataset/'val_unseen/val_unseen.json.gz','wt') as f:json.dump({'episodes':selected},f)
    samples=output/'storage/samples';samples.mkdir(parents=True,exist_ok=args.resume)
    link=code/'benchmarks/vlnverse/upstream/data/sample_episodes'/args.run_id
    link.parent.mkdir(parents=True,exist_ok=True)
    if link.is_symlink():
        if link.resolve()!=samples.resolve():raise RuntimeError('Wrong resume LMDB link')
    else:link.symlink_to(samples,target_is_directory=True)
    score=Path(manifest['code_root'])/'benchmarks/vlnverse/upstream/logs'/args.run_id/'kujiale_result.json'
    if code!=Path(manifest['code_root']):
        score.parent.mkdir(parents=True,exist_ok=True)
        score_link=code/'benchmarks/vlnverse/upstream/logs'/args.run_id
        score_link.parent.mkdir(parents=True,exist_ok=True)
        if score_link.is_symlink():
            if score_link.resolve()!=score.parent.resolve():raise RuntimeError('Wrong score link')
        else:score_link.symlink_to(score.parent,target_is_directory=True)
    expected=len(selected)
    meta=dict(method='StreamVLN',mode='physical',run_id=args.run_id,dataset=str(dataset),
              episode_ids=[e['episode_id'] for e in selected],gpu=model_gpu,sim_gpu=args.gpu,
              model_action_cap=None,physics_tick_cap=25000,camera_resolution=[640,480],warm_up_step=500,
              seed=manifest['seed'],seed_scheme=SEED_SCHEME,scenes=sorted({e['scan'] for e in selected}),
              complete_scenes=False,dataset_sha256=digest_json(selected),code_commit=manifest['git_head'],
              review_visualization=None,borrowed_model=saved,borrowed_model_port=args.port)
    if not args.resume:write(output/'run.json',meta)
    attempt=output/('launch_'+str(time.time_ns()));attempt.mkdir()
    for name,path in [('previous_status',campaign/'status.json'),('previous_owned',output/'owned_processes.json')]:
        if path.exists():write(attempt/(name+'.json'),json.loads(path.read_text()))
    count=NativeScoreCounter(score)
    if count()>=expected:raise RuntimeError('Campaign already complete; do not restart simulation')
    state=dict(phase='starting_simulator',pid=os.getpid(),arm=args.arm,expected=expected,
               run_id=args.run_id,model_pid=args.model_pid,model_retained=True,model_reloaded=False,
               gpu=args.gpu,model_gpu=model_gpu,sim_gpu=args.gpu,started_at=time.time(),completed=count(),resume=args.resume,
               code_revision=str(args.code_revision) if args.code_revision else None,launch=str(attempt))
    write(attempt/'launch.json',dict(**state,command=sys.argv,model_identity=saved))
    write(campaign/'status.json',state)
    env={k:v for k,v in os.environ.items() if not k.startswith(('VLN_','STREAMVLN_','PENG_','JANUSVLN_')) and not k.lower().endswith('_proxy')}
    env.update(manifest['runtime_env'],VLN_DISTANCE_ARM=args.arm,
               VLN_ORACLE_RECORDS=str(campaign/'oracle_records'/args.arm),
               VLN_BRANCH_ROOT=str(campaign/'checkpoints'/args.arm),VLN_EVAL_SEED=str(manifest['seed']),
               VLN_SIM_CACHE_ROOT=str(Path(manifest['code_root'])/'benchmarks/vlnverse/runner'),
               PYTHONHASHSEED=str(manifest['seed']),CUDA_VISIBLE_DEVICES=str(args.gpu),VLN_SIM_RENDER_GPU=str(args.gpu),
               VLN_RSS_BUDGET_MIB='24000',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',
               NO_PROXY='127.0.0.1,localhost',no_proxy='127.0.0.1,localhost')
    if manifest['arms'][args.arm]['mode']=='baseline':
        env={k:v for k,v in env.items() if not k.startswith(('VLN_ORACLE_','VLN_DISTANCE_','VLN_BRANCH_'))}
    tmp=output/'tmp';tmp.mkdir(exist_ok=args.resume);env.update(TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp))
    trace_start=borrowed['trace_offset'] if args.resume else args.model_trace.stat().st_size
    if not args.resume:
        write(output/'borrowed_model.json',dict(identity=saved,trace=str(args.model_trace),trace_offset=trace_start,initial_policy=initial_policy))
    child=None;retained=False;failures=0
    def stop(signum,frame):raise KeyboardInterrupt('Stop requested; borrowed model is retained')
    handlers={s:signal.signal(s,stop) for s in (signal.SIGINT,signal.SIGTERM)}
    try:
        for _ in range(1000):
            assert_model(saved)
            chunk=output/('chunk_'+str(time.time_ns()));chunk.mkdir()
            marker=chunk/'simulator_retained.json';config=chunk/'eval_config.py'
            native.write_config(config,'StreamVLN',args.port,args.run_id,dataset,'physical')
            env.update(VLN_SIM_RETAIN_FILE=str(marker),VLN_NATIVE_RESULT_FILE=str(score),VLN_EXPECTED_EPISODES=str(expected))
            start=count()
            print(f'CHUNK_START {chunk.name} completed={start}/{expected}',flush=True)
            with (chunk/'evaluator.log').open('x') as log:
                child=subprocess.Popen(['bash',str(runner/'run_eval.sh'),str(config)],env=env,cwd=code,
                                       stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            owned=dict(agent_pid=args.model_pid,evaluator_pid=child.pid,gpu=model_gpu,sim_gpu=args.gpu,
                       launcher_pid=os.getpid(),chunk=str(chunk),borrowed_model=True)
            write(output/'owned_processes.json',owned)
            state.update(phase='running',simulator_pid=child.pid,chunk=str(chunk),simulation_started=True)
            write(campaign/'status.json',state)
            while child.poll() is None:
                assert_model(saved)
                if manifest['protocol']=='step_multiview_v001' and (campaign/'capture_failure.json').exists():
                    raise RuntimeError('Per-step capture failed; see capture_failure.json')
                state.update(completed=count(),updated_at=time.time());write(campaign/'status.json',state)
                if marker.exists():
                    if count()!=expected:raise RuntimeError('Retained marker before complete scoring')
                    retained=True;break
                newest=max((chunk/'evaluator.log').stat().st_mtime,args.model_trace.stat().st_mtime)
                if time.time()-newest>900:
                    write(chunk/'timeout.json',dict(reason='Native 900-second no-progress timeout',time=time.time()))
                    stop_simulator(child);break
                time.sleep(5)
            if manifest['protocol']=='step_multiview_v001' and (campaign/'capture_failure.json').exists():
                raise RuntimeError('Per-step capture failed; see capture_failure.json')
            if retained or count()==expected:break
            completed=count()
            write(chunk/'exit.json',dict(exit_code=child.returncode,completed_before=start,completed_after=completed,
                                        no_progress_failures=failures+1 if completed<=start else 0,time=time.time()))
            print(f'CHUNK_END rc={child.returncode} completed={completed}/{expected}',flush=True)
            failures=retry_failures(failures,start,completed)
            child=None
        if count()!=expected:raise RuntimeError('Incomplete native evaluation')
        trace_dir=output/'chunk_model_evidence';trace_dir.mkdir()
        proof=collect_trace(args.model_trace,trace_start,trace_dir/'agent_trace.jsonl')
        write(trace_dir/'source.json',proof)
        evidence=output/'storage/chunks/borrowed_model_evidence'
        evidence.parent.mkdir(parents=True,exist_ok=True);evidence.symlink_to(trace_dir,target_is_directory=True)
        subprocess.run([str(simulation_python()),str(code/'scripts/export_vlnverse_results.py'),'--run',str(output)],
                       cwd=code,env=dict(env,CUDA_VISIBLE_DEVICES='',PYTHONPATH=str(code)),check=True)
        write(output/'result.json',dict(status='complete',expected_episodes=expected,official_result=json.loads(score.read_text()),
                                        official_result_path=str(score),run_id=args.run_id,model_gpu=model_gpu,sim_gpu=args.gpu))
        if manifest['protocol']=='step_multiview_v001':
            subprocess.run([str(simulation_python()),str(code/'scripts/verify_step_multiview.py'),
                            '--campaign',str(campaign),'--run',str(output)],
                           cwd=code,env=dict(env,CUDA_VISIBLE_DEVICES='',PYTHONPATH=str(code)),check=True)
        state.update(phase='complete_services_retained',completed=expected,simulator_retained=retained,
                     model_retained=True,finished_at=time.time(),validation=str(output/'validation.json'))
        write(campaign/'status.json',state)
    except BaseException as e:
        state.update(phase='stopped' if isinstance(e,KeyboardInterrupt) else 'failed',error=repr(e),model_retained=True)
        write(campaign/'status.json',state);raise
    finally:
        if not retained:stop_simulator(child)
        write(campaign/'status.json',state)
        for s,h in handlers.items():signal.signal(s,h)
        lock.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--campaign',type=Path,required=True);p.add_argument('--arm',required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--gpu',type=int,required=True)
    p.add_argument('--model-pid',type=int,required=True);p.add_argument('--port',type=int,required=True)
    p.add_argument('--model-gpu',type=int,help='Retained model GPU; --gpu selects the simulator GPU')
    p.add_argument('--model-trace',type=Path,required=True)
    p.add_argument('--resume',action='store_true',help='Continue the existing LMDB; keep all attempts and the original trace offset')
    p.add_argument('--code-revision',type=Path,help='Separately sealed maintenance snapshot; original campaign is immutable')
    run(p.parse_args())
