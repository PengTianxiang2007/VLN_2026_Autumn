"""Thirty independent RxR processes: fresh DeepSeek dedup, then v006 on its nodes."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import httpx
import run_rxr_offline_semantics as rxr
import run_deviation_progress_v004 as deviation
from core.agent_route_choice import read, write, now, file_hash

ROOT = rxr.ROOT
UPSTREAM = ROOT/'outputs/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout'
OUT = ROOT/'outputs/deviation_progress/rxr30_v006/run_20261123_03_mistral30'
RECORD = ROOT/'experiments/deviation_progress/rxr30_v006/run_20261123_03_mistral30'
API = 'https://api.mistral.ai/v1'
PROXY = 'http://127.0.0.1:7892'
MODEL = 'deepseek-v4-1-flash-1017'
SETTINGS = dict(model=MODEL, reasoning_effort='high', max_tokens=32768,
                response_format={'type':'json_object'}, stream=False)
WORKERS = 30
DEDUP_SOURCE = ROOT/rxr.DEDUP/'run_dedup.py'
DEDUP_PROMPT = ROOT/rxr.PROMPTS['dedup']
KEY = None
STOP = None


def final_text(value):
    """Decode provider content chunks, preserving the original response on disk."""
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        raise ValueError('Unsupported provider content type')
    texts = []
    for part in value:
        if not isinstance(part, dict):
            raise ValueError('Invalid provider content chunk')
        if part.get('type') == 'thinking':
            continue
        if part.get('type') != 'text' or not isinstance(part.get('text'), str):
            raise ValueError('Unsupported provider answer chunk')
        texts.append(part['text'])
    if not texts:
        raise ValueError('Provider response has no final answer text')
    return ''.join(texts)


class ProviderJSON:
    """Only list-valued message.content needs adaptation; JSON storage is unchanged."""
    dumps = staticmethod(json.dumps)

    @staticmethod
    def loads(value, *args, **kwargs):
        return json.loads(final_text(value) if isinstance(value, list) else value, *args, **kwargs)


def client(**kwargs):
    kwargs.update(trust_env=False, proxy=PROXY,
                  timeout=httpx.Timeout(600, connect=30, write=60, pool=30))
    return httpx.Client(**kwargs)


def load_dedup():
    source = OUT/'source'/DEDUP_SOURCE.relative_to(ROOT)
    spec = importlib.util.spec_from_file_location('rxr_mistral_frozen_dedup', source)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    engine.RUN, engine.SITE, engine.API = OUT/'dedup', rxr.SOURCE, API
    # These are module-local adapters; no global httpx/json library is modified.
    engine.httpx = SimpleNamespace(Client=client, Timeout=httpx.Timeout)
    engine.json = ProviderJSON
    return engine


def prompt(name):
    source = DEDUP_PROMPT if name=='dedup' else rxr.DEVIATION_PROMPT
    return (OUT/'source'/source.relative_to(ROOT)).read_text()


def prepare():
    if (OUT/'manifest.json').exists():
        raise RuntimeError('Run already prepared; do not overwrite history')
    catalog = read(OUT/'model_catalog_entry.json')
    if catalog['id'] != MODEL or not catalog['capabilities']['vision']:
        raise ValueError('Requested image model is unavailable')
    if read(UPSTREAM/'jev/status.json')['phase'] != 'complete':
        raise ValueError('Upstream JEV is incomplete')
    candidates = read(UPSTREAM/'jev/candidates.json')
    ids = read(UPSTREAM/'dataset/index.json')['episode_ids']
    if ids != read(rxr.SAMPLE)['episode_ids'] or len(ids) != WORKERS:
        raise ValueError('Unexpected RxR sample')
    cases = [read(UPSTREAM/'dataset'/(eid+'.json')) for eid in ids]
    for case in cases:
        case['image_paths'] = {f['image']:str(rxr.SOURCE/f['path']) for f in case['frames']}
        rxr.node_inputs(case, candidates[case['episode_id']])
    write(OUT/'inputs/cases.json', cases)
    write(OUT/'inputs/candidates.json', candidates)
    paths = [Path(__file__).resolve(),Path(rxr.__file__),Path(deviation.__file__),
             Path(deviation.review.__file__), DEDUP_SOURCE, DEDUP_PROMPT, rxr.DEVIATION_PROMPT,
             ROOT/'experiments/deviation_progress/v006/prompt_en.txt']
    hashes = {}
    for source in paths:
        rel = source.relative_to(ROOT); dest = OUT/'source'/rel
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        hashes[str(rel)] = file_hash(dest)
    manifest = dict(created_at=now(),provider='mistral',endpoint=API,proxy=PROXY,settings=SETTINGS,
        workers=WORKERS,source_sha256=hashes,git_head=subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        trajectory_seed=2,model_seed=None,upstream=str(UPSTREAM.relative_to(ROOT)),
        candidates_sha256=file_hash(UPSTREAM/'jev/candidates.json'),
        settings_note='reasoning_effort explicitly high; Mistral defaults for sampling; no DeepSeek-specific thinking field',
        protocol='fresh v001 dedup on JEV candidates; freeze all 30; fresh v006 on these nodes only',
        transport_retries=6,request_timeout_seconds=600,
        cases=[dict(case_number=c['case_number'],episode_id=c['episode_id'],
                    original_candidates=len(candidates[c['episode_id']])) for c in cases])
    write(OUT/'manifest.json',manifest);write(RECORD/'manifest.json',manifest)
    write(OUT/'status.json',dict(phase='prepared',dedup_complete=0,deviation_complete=0,
                               workers=WORKERS,target_episodes=WORKERS,updated_at=now()))
    print(json.dumps(dict(prepared=WORKERS,candidates=sum(len(v) for v in candidates.values()),
                          model=MODEL,reasoning_effort='high')),flush=True)


def checked(call, folder, stem, *args):
    """Retry transport only; preserve malformed semantic answers without retrying."""
    for attempt in range(7):
        if STOP is not None and STOP.is_set():
            raise RuntimeError('Batch stop requested')
        result = call(*args)
        response = result[1] if isinstance(result,tuple) else result
        status = response.get('http_status')
        if status == 200:
            return result
        archive = folder/'transport_attempts'/f'{stem}_attempt{attempt+1:02d}'
        archive.mkdir(parents=True,exist_ok=True)
        for suffix in ['request','response']:
            source = folder/f'{stem}.{suffix}.json'
            if source.exists():shutil.copy2(source,archive/source.name)
        retryable = status in (None,408,429,500,502,503,504)
        if not retryable or attempt==6:
            if status in (400,401,402,403,404,422) and STOP is not None:STOP.set()
            raise RuntimeError(response.get('error','Mistral transport failure'))
        delay=min(60,5*2**attempt)+random.uniform(0,5)
        print(json.dumps(dict(transport_retry=stem,http_status=status,attempt=attempt+1,delay=round(delay,1))),flush=True)
        if STOP is None:time.sleep(delay)
        elif STOP.wait(delay):raise RuntimeError('Batch stop requested')


def preflight():
    global KEY
    KEY = credential()
    case = read(OUT/'inputs/cases.json')[0]
    nodes = rxr.node_inputs(case,read(OUT/'inputs/candidates.json')[case['episode_id']])
    a,b = nodes[:2]
    folder=OUT/'preflight';folder.mkdir(exist_ok=True)
    if (folder/(b['id']+'.response.json')).exists():
        raise RuntimeError('Preflight already attempted; inspect its preserved response')
    engine=load_dedup()
    result=checked(engine.compare,folder,b['id'],a,b,KEY,prompt('dedup'),SETTINGS,folder,lambda *args,**kwargs:None)
    if result['status']!='ok':
        raise RuntimeError(result.get('error','Invalid first comparison'))
    write(folder/'accepted.json',dict(case_number=case['case_number'],node=b['id'],at=now(),
          response_sha256=file_hash(folder/(b['id']+'.response.json'))))
    print(json.dumps(dict(http=result['http_status'],status=result['status'],relation=result['answer']['relation'],
          elapsed_seconds=result['elapsed_seconds'],reused_in_batch=True)),flush=True)


def dedup_worker(case):
    engine=load_dedup(); original=engine.compare
    def compare(a,b,key,system,settings,folder,log):
        accepted=read(OUT/'preflight/accepted.json')
        if case['case_number']==accepted['case_number'] and b['id']==accepted['node']:
            old=OUT/'preflight';meta=read(old/(b['id']+'.request.json'))
            expected=[*engine.evidence(a,'A'),*engine.evidence(b,'B')]
            if (meta['previous_candidate_id']!=a['candidate_id'] or meta['current_candidate_id']!=b['candidate_id']
                or meta['images']!=expected or meta['settings']!=settings
                or meta['prompt_sha256']!=deviation.review.sha(system.encode())):
                raise ValueError('Preflight reuse inputs differ')
            for suffix in ['request','response']:shutil.copy2(old/f'{b["id"]}.{suffix}.json',folder/f'{b["id"]}.{suffix}.json')
            log('preflight_response_reused',current_id=b['id'])
            return read(folder/(b['id']+'.response.json'))
        return checked(original,folder,b['id'],a,b,key,system,settings,folder,log)
    engine.compare=compare
    candidates=read(OUT/'inputs/candidates.json')[case['episode_id']]
    nodes=rxr.node_inputs(case,candidates)
    fields={k:case[k] for k in ['case_number','case_index','episode_id','real_episode_id','scene']}
    result=engine.run_case(dict(fields,nodes=nodes),KEY,prompt('dedup'),SETTINGS)
    frozen=rxr.freeze_nodes(case,nodes,result['final_active_ids'])
    write(OUT/'effective_nodes'/(case['episode_id']+'.json'),frozen)
    return dict(case_number=case['case_number'],episode_id=case['episode_id'],summary=result['summary'])


def deviation_worker(case):
    frozen=read(OUT/'effective_nodes'/(case['episode_id']+'.json'))
    case.update(nodes=frozen,final_active_ids=[n['id'] for n in frozen],terminal_frame=len(case['frames'])-1)
    deviation.review.json=ProviderJSON;deviation.json=ProviderJSON
    deviation.review.httpx=SimpleNamespace(Client=client,Timeout=httpx.Timeout)
    system=prompt('deviation');validator=deviation.VALIDATORS['v006']
    def invoke(*args):
        folder=args[-1]
        def call(*values):
            return deviation.review.call_model(*values,api_base=API,validate_answer=validator,request_timeout=600)
        return checked(call,folder.parent,folder.name,*args)
    site=OUT/'deviation'
    result=deviation.review.run_case(case,str(site),KEY,system,SETTINGS,model_call=invoke)
    audit=deviation.audit_case(case,site/f'run/cases/C{case["case_number"]:02d}',validator,system,SETTINGS)
    return dict(audit,worker_pid=result['worker_pid'])


def supervise():
    global KEY,STOP
    KEY=sys.stdin.readline().strip();sys.stdin.close()
    if not KEY:raise ValueError('Missing credential')
    STOP=multiprocessing.get_context('fork').Event()
    state=read(OUT/'status.json')
    if state['phase']!='prepared':raise RuntimeError('Run already started')
    state.update(pid=os.getpid(),started_at=now(),provider='mistral',settings=SETTINGS)
    def update(**kw):
        state.update(kw,updated_at=now());write(OUT/'status.json',state)
    def stop(*args):
        STOP.set();raise KeyboardInterrupt('Stop requested')
    signal.signal(signal.SIGTERM,stop)
    cases=read(OUT/'inputs/cases.json')
    try:
        for stage,worker in [('dedup',dedup_worker),('deviation',deviation_worker)]:
            results=[];counts=Counter();failures={}
            update(phase=stage,failed_cases={},active_stage_completed=0)
            with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('fork')) as pool:
                futures={pool.submit(worker,c):c['case_number'] for c in cases}
                for future in as_completed(futures):
                    number=futures[future]
                    try:r=future.result()
                    except Exception as error:
                        failures[str(number)]=str(error).replace(KEY,'[redacted]')[:800]
                    else:
                        results.append(r);counts.update(r['summary'] if stage=='dedup' else r['outcomes'])
                        write(OUT/('dedup_results.json' if stage=='dedup' else 'deviation/v006_results.json'),sorted(results,key=lambda x:x['case_number']))
                    update(**{stage+'_complete':len(results),stage+'_counts':dict(counts)},
                           active_stage_completed=len(results),failed_cases=failures)
            if failures:raise RuntimeError(f'{stage}: {len(failures)} failed cases; preserved partial outputs')
            if stage=='dedup':
                frozen={c['episode_id']:read(OUT/'effective_nodes'/(c['episode_id']+'.json')) for c in cases}
                write(OUT/'retained_nodes_and_terminals.json',frozen)
                update(frozen_nodes_sha256=file_hash(OUT/'retained_nodes_and_terminals.json'))
        timing=rxr.compare_annotations(OUT,results,frozen)
        update(phase='complete',finished_at=now(),summary=timing,workers_exited=True)
    except BaseException as error:
        STOP.set();update(phase='failed',finished_at=now(),error=str(error).replace(KEY,'[redacted]')[:800])
        raise SystemExit(1)
    finally:
        write(RECORD/'completion.json',state)
        KEY=None


def credential():
    path=ROOT/'.env.mistral_rxr30.local'
    if path.stat().st_mode & 0o077:raise ValueError('Credential file must be private')
    return path.read_text().strip().split('=',1)[1]


def launch():
    if read(OUT/'status.json')['phase']!='prepared':raise RuntimeError('Run already started')
    read(OUT/'preflight/accepted.json')
    key=credential()
    env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()
         and not any(s in k.upper() for s in ['API_KEY','TOKEN','SECRET'])}
    env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    with (OUT/'supervisor.log').open('xb') as log:
        process=subprocess.Popen([sys.executable,'-Bu',str(Path(__file__).resolve()),'supervise'],
            cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    with process.stdin as pipe:pipe.write((key+'\n').encode())
    write(OUT/'launch.json',dict(pid=process.pid,workers=WORKERS,at=now()))
    print(json.dumps(dict(pid=process.pid,workers=WORKERS,stages=['dedup','deviation'],output=str(OUT))),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','preflight','launch','supervise'])
    args=parser.parse_args()
    {'prepare':prepare,'preflight':preflight,'launch':launch,'supervise':supervise}[args.phase]()
