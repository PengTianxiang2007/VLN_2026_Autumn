"""Run a frozen development revision against the existing local service and build reviews.

Does not start models, select new GPUs, run navigation, change methods, or unseal validation.
"""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
PYTHON=ROOT/'benchmarks/vlnverse/.venv/bin/python'


def now():return datetime.now(timezone.utc).isoformat()


def read(path):return json.loads(path.read_text())


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)


def progress(output,tag):
    protocol=read(output/'protocol.json');inputs=read(output/'inputs.json');run=output/'runs'/tag
    cases={}
    for episode in protocol['development']:
        directory=run/'cases'/episode;path=directory/'status.json'
        value=read(path) if path.exists() else dict(phase='queued')
        logs=directory/'predictions.jsonl'
        rows=[json.loads(line) for line in logs.read_bytes().splitlines(keepends=True) if line.endswith(b'\n')] if logs.exists() else []
        value['processed']=len(rows)
        value['expected']=sum(not o['terminal'] and not o['rgb_reused'] for o in inputs[episode]['observations'])
        final=directory/'result.json'
        value['complete']=bool(final.exists() and read(final).get('complete'))
        cases[episode]=value
    return dict(cases=cases,processed=sum(c['processed'] for c in cases.values()),
                expected=sum(c['expected'] for c in cases.values()),completed_cases=sum(c['complete'] for c in cases.values()),
                expected_cases=len(cases))


def main(args):
    output=args.output.resolve();service=args.service.resolve();output.mkdir(parents=True,exist_ok=True)
    lock=(output/'development_controller.lock').open('a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # Refuse an overlapping replay, including a run started outside this controller.
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:argv=path.read_bytes().split(b'\0')
        except (FileNotFoundError,PermissionError,ProcessLookupError):continue
        if str(ROOT/'scripts/replay_crossing_checkpoint.py').encode() in argv and b'run' in argv and str(output).encode() in argv:
            raise RuntimeError('Another replay for this campaign is still running')
    info=read(service/'service.json')
    if info['phase']!='ready' or not info['base_url'].startswith('http://127.0.0.1:'):
        raise ValueError('Expected an existing local model service')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(info['base_url']+'/models',timeout=10) as response:models=json.load(response)
    if info['served_model'] not in [m['id'] for m in models['data']]:raise ValueError('Model service identity differs')
    env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
    env.update(OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
    state=dict(pid=os.getpid(),backend='vllm',model=Path(info['model_path']).name,gpus=info['gpus'],tag=args.tag,
               service_supervisor_pid=info['supervisor_pid'],started_at=now(),phase='starting_development',
               thinking=args.thinking,max_tokens=args.max_tokens)
    write(output/'iteration_status.json',state)
    run=output/'runs'/args.tag;run.mkdir(parents=True,exist_ok=True)
    with (run/'replay.log').open('a') as log:
        command=[str(PYTHON),'-B',str(ROOT/'scripts/replay_crossing_checkpoint.py'),'run',
            '--output',str(output),'--tag',args.tag,'--service',str(service),'--workers',str(args.workers),
            '--max-tokens',str(args.max_tokens)]
        if args.thinking:command.append('--thinking')
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    state['replay_pid']=process.pid
    def stop(signum,frame):
        if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
        state.update(phase='interrupted',updated_at=now());write(output/'iteration_status.json',state)
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    last_preview=0;last_count=-1
    while process.poll() is None:
        current=progress(output,args.tag)
        state.update(phase='running_eight_development_trajectories',updated_at=now(),**current)
        if current['processed']>last_count and current['processed'] and time.monotonic()-last_preview>=120:
            with (run/'preview.log').open('a') as log:
                result=subprocess.run([str(PYTHON),'-B',str(ROOT/'scripts/preview_crossing_checkpoint.py'),
                    '--output',str(output),'--tag',args.tag],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
            state['preview_exit_code']=result.returncode;state['preview_updated_at']=now()
            last_preview=time.monotonic();last_count=current['processed']
        write(output/'iteration_status.json',state);time.sleep(15)
    state.update(replay_exit_code=process.returncode,updated_at=now(),**progress(output,args.tag))
    tasks=['preview_crossing_checkpoint.py']
    if state['completed_cases']:
        tasks.append('analyze_crossing_checkpoint.py')
    state['postprocessing']={}
    for script in tasks:
        with (run/'postprocess.log').open('a') as log:
            result=subprocess.run([str(PYTHON),'-B',str(ROOT/'scripts'/script),'--output',str(output),'--tag',args.tag],
                cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
        state['postprocessing'][script]=result.returncode
    if process.returncode==0 and state['completed_cases']==state['expected_cases'] and not any(state['postprocessing'].values()):
        with (run/'postprocess.log').open('a') as log:
            result=subprocess.run([str(ROOT/'backbone/streamvln/.venv/bin/python'),'-B',
                str(ROOT/'scripts/export_crossing_iteration.py'),'--output',str(output),'--tag',args.tag],
                cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
        state['postprocessing']['export_crossing_iteration.py']=result.returncode
    state.update(phase='development_ready_for_method_review' if process.returncode==0 and state['completed_cases']==state['expected_cases'] and not any(state['postprocessing'].values()) else 'development_needs_attention',updated_at=now())
    write(output/'iteration_status.json',state)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--tag',required=True)
    parser.add_argument('--service',type=Path,required=True);parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--thinking',action=argparse.BooleanOptionalAction,default=False)
    parser.add_argument('--max-tokens',type=int,default=8192)
    args=parser.parse_args()
    if not 1<=args.workers<=4:parser.error('Use 1..4 workers with the admitted existing service')
    main(args)
