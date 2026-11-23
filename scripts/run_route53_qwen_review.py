"""Apply the recorded dedup v001 and deviation v003 case runners to native RGB."""
import fcntl
import importlib.util
import os
import signal
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import read, write, file_hash, now
from core.serial_pipeline import DEDUP, PROMPTS, semantic_settings
import run_deviation_progress_review as deviation

RUN = ROOT / 'outputs/deviation_progress/v003/run_20261118_01_qwen27b'
RECORD = ROOT / 'experiments/deviation_progress/v003/run_20261118_01_qwen27b'
UPSTREAM = ROOT / 'outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01'
DATA = Path(read(UPSTREAM/'manifest.json')['dataset'])
# vLLM accepts the OpenAI-compatible local placeholder. No external credentials.
LOCAL_AUTH = 'LOCAL-VLLM-NO-AUTH'


def assert_local_service(launch, state):
    if state['supervisor_pid'] != launch['supervisor_pid'] or state['gpu'] != 3:
        raise RuntimeError('Service ownership changed')
    if state['model'] != read(RECORD/'service_config.json')['model']:
        raise RuntimeError('Unexpected served model')
    address = urlparse(state['base_url'])
    if (address.scheme, address.hostname, address.path) != ('http', '127.0.0.1', '/v1'):
        raise RuntimeError('Qwen endpoint is not the local service')


def release_service(launch):
    service = Path(launch['service'])
    pid = launch['supervisor_pid']
    proc = Path('/proc') / str(pid)
    if not proc.is_dir():
        return
    try:
        handle = os.pidfd_open(pid)
    except ProcessLookupError:
        return
    try:
        actual = (proc/'cmdline').read_bytes().split(b'\0')
        if actual[:-1] != [arg.encode() for arg in launch['command']]:
            raise RuntimeError('Qwen supervisor command changed')
        state = read(service/'service.json')
        if state['supervisor_pid'] != pid or state['gpu'] != 3:
            raise RuntimeError('Qwen supervisor identity changed')
        signal.pidfd_send_signal(handle, signal.SIGTERM)
    finally:
        os.close(handle)


def prepare():
    paths = [Path(__file__), ROOT/'scripts/serve_qwen27b_standby.py', ROOT/'scripts/run_human_route_choice.py',
             ROOT/'core/serial_pipeline.py', Path(deviation.__file__), ROOT/DEDUP/'run_dedup.py',
             ROOT/PROMPTS['dedup'], ROOT/PROMPTS['deviation'], RECORD/'service_config.json']
    frozen = {}
    for p in paths:
        rel = p.relative_to(ROOT)
        frozen[str(rel)] = file_hash(p)
        dest = RUN/'source'/rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
        elif file_hash(dest) != frozen[str(rel)]:
            raise ValueError('Different code in existing run: '+str(rel))
    manifest = dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    sources=frozen, upstream_candidates_sha256=file_hash(UPSTREAM/'candidates.json'),
                    dataset_manifest_sha256=file_hash(DATA/'manifest.json'), seed=2)
    write(RUN/'manifest.json',manifest)
    return load_cases()


def load_cases():
    ids = (DATA/'subsets/all_selected.txt').read_text().splitlines()
    if len(set(ids)) != 53 or len(ids) != 53:
        raise ValueError('Unexpected episode set')
    indexed = {eid:[] for eid in ids}
    for node in read(UPSTREAM/'candidates.json'):
        indexed[node['episode_id']].append(node)
    if sum(map(len,indexed.values())) != 494:
        raise ValueError('Candidate count mismatch')
    cases = []
    import json
    for i,eid in enumerate(ids):
        task = read(DATA/'inputs'/eid/'task.json')
        with (DATA/'inputs'/eid/'observations.jsonl').open() as stream:
            rows = [json.loads(line) for line in stream]
        frames, image_paths = [], {}
        for t,row in enumerate(rows):
            if row['step']!=t or row['episode_id']!=eid:
                raise ValueError('Frame order changed')
            im = row['native_front']
            path = im['image']
            filename = 'terminal_front.png' if t == len(rows)-1 else 'policy_front.png'
            if path != f'observations/{eid}/{t:06d}/{filename}':
                raise ValueError(f'Unexpected native image path in {eid} at step {t}: {path}')
            frames.append(dict(frame=t,image=im['sha256'],path=path,terminal=t==len(rows)-1))
            image_paths[im['sha256']] = str(DATA/path)
        nodes = []
        for j,n in enumerate(indexed[eid],1):
            t=n['index']
            if (n['id']!=f'S{j:02d}' or frames[t]['path']!=n['front_image'] or n['emittedAt']!=t+5
                    or n['emittedAt']>=len(frames)-1 or (nodes and t<=nodes[-1]['index'])):
                raise ValueError('Misaligned candidate '+eid)
            node = dict(id=n['id'], index=t, emittedAt=n['emittedAt'], ready_at_frame=n['emittedAt'],
                        candidate_id=f"C{i+1:02d}:{n['id']}:F{t}", images=[])
            for offset in range(-2,3):
                f=t+offset
                ref=dict(frame=f,label='F0' if offset==0 else f'F{offset:+d}')
                if f<0:
                    ref['missing']=True
                else:
                    ref.update(image_id=frames[f]['image'],path=frames[f]['path'])
                node['images'].append(ref)
            nodes.append(node)
        cases.append(dict(case_index=i,case_number=i+1,episode_id=eid,real_episode_id=eid,scene=task['scene'],
                          instruction_en=task['instruction'],nodes=nodes,frames=frames,image_paths=image_paths))
    return cases


def retained_case(case, result):
    keep = set(result['final_active_ids'])
    nodes = [dict(source_id=n['id'],index=n['index'],emittedAt=n['emittedAt'],terminal_node=False)
             for n in case['nodes'] if n['id'] in keep]
    terminal = case['frames'][-1]['frame']
    if nodes[-1]['index'] != terminal:
        nodes.append(dict(source_id=None,index=terminal,emittedAt=terminal))
    nodes[-1]['terminal_node']=True
    for j,n in enumerate(nodes,1):
        n['id']=f'S{j:02d}'
    return dict(case,nodes=nodes,final_active_ids=[n['id'] for n in nodes],terminal_frame=terminal)


def review(launch):
    cases = prepare()
    state_path=Path(launch['service'])/'service.json'
    status=dict(phase='waiting_for_qwen',pid=os.getpid(),started_at=now(),episodes=53,candidates=494,
                dedup_completed=0,deviation_completed=0)
    def update(**values):
        status.update(values,updated_at=now())
        write(RUN/'status.json',status)
    update()
    while True:
        state = read(state_path)
        if state['phase']=='ready':
            break
        if state['phase'] in ('failed','stopped') or not Path('/proc',str(launch['supervisor_pid'])).is_dir():
            raise RuntimeError('Qwen service failed: '+str(state.get('error',state['phase'])))
        time.sleep(3)
    assert_local_service(launch,state)
    spec=importlib.util.spec_from_file_location('frozen_dedup',ROOT/DEDUP/'run_dedup.py')
    dedup=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dedup)
    dedup.SITE=DATA
    dedup.RUN=RUN/'dedup'
    dedup.API=deviation.API=state['base_url']
    os.environ['no_proxy']=os.environ['NO_PROXY']='localhost,127.0.0.1'
    config=dict(semantic_provider='qwen_local',semantic_model=state['model'],semantic_seed=2)
    settings=semantic_settings(config,'dedup')
    prompts={stage:(ROOT/PROMPTS[stage]).read_text() for stage in ('dedup','deviation')}
    # Do not turn an unavailable local model into a series of semantic verdicts.
    def checked_compare(*args):
        result=original_compare(*args)
        if result.get('http_status')!=200:
            raise RuntimeError('Qwen dedup transport failed: '+result.get('error','unknown'))
        return result
    def checked_deviation(*args):
        meta,result=original_call(*args)
        if result.get('http_status')!=200:
            raise RuntimeError('Qwen deviation transport failed: '+result.get('error','unknown'))
        return meta,result
    original_compare,original_call=dedup.compare,deviation.call_model
    dedup.compare,deviation.call_model=checked_compare,checked_deviation
    write(RUN/'request_settings.json',dict(endpoint=dedup.API,settings=settings))
    counts=Counter()
    selected=[]
    for case in cases:
        update(phase='dedup',current_episode=case['episode_id'])
        fields=('case_number','case_index','episode_id','real_episode_id','scene','nodes')
        result=dedup.run_case({k:case[k] for k in fields},LOCAL_AUTH,prompts['dedup'],settings)
        counts.update(result['summary'])
        selected.append(retained_case(case,result))
        update(dedup_completed=len(selected),dedup=dict(counts))
    if counts['candidates']!=494 or counts['model_calls']!=338 or counts['retained']+counts['removed']!=494:
        raise ValueError('Dedup tally mismatch')
    mapping={c['episode_id']:c['nodes'] for c in selected}
    write(RUN/'retained_nodes_and_terminals.json',mapping)
    results=[]
    outcomes=Counter()
    for case in selected:
        update(phase='deviation',current_episode=case['episode_id'])
        result=deviation.run_case(case,str(RUN/'deviation'),LOCAL_AUTH,prompts['deviation'],settings)
        results.append(result)
        outcomes.update(r.get('answer',{}).get('verdict','format_error') for r in result['reviews'])
        update(deviation_completed=len(results),deviation_verdicts=dict(outcomes))
    summary=dict(episodes=len(results),dedup=dict(counts),deviation_verdicts=dict(outcomes),
                 deviation_calls=sum(outcomes.values()),episodes_flagged=sum(bool(c['stop_node']) for c in results),
                 terminal_nodes_added=53,finished_at=now())
    write(RUN/'summary.json',summary)
    update(phase='complete',current_episode=None,summary=summary)


if __name__=='__main__':
    launch=read(RUN/'service_launch.json')
    with (RUN/'review.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            review(launch)
        except BaseException as error:
            path=RUN/'status.json'
            state=read(path) if path.exists() else {}
            write(path,dict(state,phase='failed',error=str(error),updated_at=now()))
            raise
        finally:
            if not (RUN/'keep_service').exists():
                release_service(launch)
