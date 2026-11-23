"""DeepSeek v003 on the first 29 completed Qwen node sequences, including terminal."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import getpass
import hashlib
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import httpx
import run_route53_deepseek_subset as ds
from core.agent_route_choice import file_hash, now, read, write

NAME = 'run_20261118_03_deepseek29'
RUN = ds.ROOT/'outputs/deviation_progress/v003'/NAME
RECORD = ds.ROOT/'experiments/deviation_progress/v003'/NAME
QWEN = ds.route.RUN
WORKERS = 29

def prepare():
    anchors = read(QWEN/'retained_nodes_and_terminals.json')
    cases = ds.route.load_cases()[:WORKERS]
    entries = []
    for case in cases:
        number, eid = case['case_number'], case['episode_id']
        dedup = read(QWEN/'dedup/cases'/f'C{number:02d}'/'result.json')
        case_input = ds.route.retained_case(case, dedup)
        result_file = QWEN/'deviation/run/cases'/f'C{number:02d}'/'result.json'
        qwen = read(result_file)
        assert case_input['nodes'] == anchors[eid] and qwen['episode_id'] == eid
        assert qwen['terminal_frame'] == case_input['terminal_frame'] and case_input['nodes'][-1]['terminal_node']
        entries.append(dict(case_number=number, episode_id=eid, nodes=len(anchors[eid]), terminal_frame=qwen['terminal_frame'], qwen_result_sha256=file_hash(result_file)))
    assert [e['case_number'] for e in entries] == list(range(1,30))
    historical = read(ds.DEVIATION.parent/'manifest.json')
    assert hashlib.sha256(ds.DEVIATION.read_text().encode()).hexdigest()==historical['prompt_sha256']
    RUN.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),Path(ds.__file__),Path(ds.route.__file__),Path(ds.route.deviation.__file__),ds.DEVIATION]
    sources={}
    for p in paths:
        rel=p.relative_to(ds.ROOT)
        dest=RUN/'source'/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,dest)
        sources[str(rel)]=file_hash(dest)
    write(RUN/'manifest.json',dict(phase='prepared',created_at=now(),workers=WORKERS,episode_seed=2,api=ds.API,settings=historical['settings'],
         prompt_sha256=historical['prompt_sha256'],anchors_sha256=file_hash(QWEN/'retained_nodes_and_terminals.json'),sources=sources,
         git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cases=entries))
    write(RUN/'retained_nodes_and_terminals.json',{e['episode_id']:anchors[e['episode_id']] for e in entries})
    write(RECORD/'selection.json',entries)
    write(RUN/'status.json',dict(phase='prepared',episodes=WORKERS,workers=WORKERS,completed=0,updated_at=now()))

def supervise():
    ds.KEY=sys.stdin.readline().strip()
    sys.stdin.close()
    if not ds.KEY: raise ValueError('Missing credential')
    ds.RUN=RUN
    mf=read(RUN/'manifest.json')
    ds.SETTINGS=mf['settings']
    state=dict(phase='checking_model',started_at=now(),pid=os.getpid(),workers=WORKERS,episodes=WORKERS,completed=0)
    def update(**changes):
        state.update(changes,updated_at=now());write(RUN/'status.json',state)
    try:
        update()
        with httpx.Client(trust_env=False,timeout=30) as client:
            resp=client.get(ds.API+'/models',headers={'Authorization':'Bearer '+ds.KEY});resp.raise_for_status()
        model=next(m for m in resp.json()['data'] if m['id']==ds.SETTINGS['model'])
        assert 'image' in model.get('input_modalities',['image'])
        write(RUN/'model_catalog.json',model)
        mapping=read(RUN/'retained_nodes_and_terminals.json')
        cases=ds.route.load_cases()[:WORKERS]
        for case in cases:
            nodes=mapping[case['episode_id']]
            case.update(nodes=nodes,final_active_ids=[n['id'] for n in nodes],terminal_frame=nodes[-1]['index'])
        counts=Counter();failures={}
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('fork')) as pool:
            futures={pool.submit(ds.worker,'deviation',c):c['case_number'] for c in cases}
            update(phase='deviation')
            for future in as_completed(futures):
                try:
                    _,summary=future.result()
                    counts.update(summary)
                    state['completed']+=1
                except Exception as exc:
                    failures[str(futures[future])]=str(exc).replace(ds.KEY,'[redacted]')[:300]
                update(totals=dict(counts),failed_cases=failures)
        update(phase='incomplete' if failures else 'complete',finished_at=now())
        write(RECORD/'completion.json',state)
    except Exception as exc:
        update(phase='failed',error=str(exc).replace(ds.KEY,'[redacted]')[:400]);raise

def launch():
    if read(RUN/'status.json')['phase']!='prepared': raise RuntimeError('Run already started')
    secret=getpass.getpass('DeepSeek credential (hidden): ')
    if not secret:raise ValueError('Missing credential')
    env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower() and not any(x in k.upper() for x in ('TOKEN','SECRET','API_KEY'))}
    env['CUDA_VISIBLE_DEVICES']=''
    with (RUN/'supervisor.log').open('x') as log:
        p=subprocess.Popen([sys.executable,'-Bu',str(Path(__file__).resolve()),'--worker'],stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,cwd=ds.ROOT,env=env,start_new_session=True)
    with p.stdin as pipe:pipe.write((secret+'\n').encode())
    print('Supervisor PID',p.pid,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    op=parser.add_mutually_exclusive_group(required=True)
    for x in ('prepare','worker','launch'): op.add_argument('--'+x,action='store_true')
    a=parser.parse_args()
    if a.prepare:prepare()
    elif a.launch:launch()
    else:supervise()
