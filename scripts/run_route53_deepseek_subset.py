"""Review a repeatable, scene-balanced subset with the archived DeepSeek protocols."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import getpass
import importlib.util
import multiprocessing
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

import httpx
import run_route53_qwen_review as route
from core.agent_route_choice import file_hash, now, read, write

ROOT = route.ROOT
NAME = 'run_20261118_02_deepseek10'
RUN = ROOT / 'outputs/deviation_progress/v003' / NAME
RECORD = ROOT / 'experiments/deviation_progress/v003' / NAME
API = 'https://api.deepseek.com'
DEDUP = ROOT / route.DEDUP
DEVIATION = ROOT / route.PROMPTS['deviation']
SCENE_SEED = 2
WORKERS = 10


def selection():
    groups = defaultdict(list)
    for case in route.load_cases():
        groups[case['scene']].append(case)
    rng = random.Random(SCENE_SEED)
    scenes = sorted(rng.sample(sorted(groups), WORKERS))
    return [rng.choice(sorted(groups[s], key=lambda c: c['episode_id'])) for s in scenes]


def case_info(case):
    nodes = case['nodes']
    return dict(case_number=case['case_number'], episode_id=case['episode_id'], scene=case['scene'],
                candidates=len(nodes), comparisons=sum(b['index']-a['index'] <= 8 for a,b in zip(nodes,nodes[1:])))


def prepare():
    cases = selection()
    entries = [case_info(c) for c in cases]
    paths = [Path(__file__), Path(route.__file__), Path(route.deviation.__file__),
             ROOT/'core/agent_route_choice.py', ROOT/'core/serial_pipeline.py', DEDUP/'run_dedup.py',
             DEDUP/'prompt_zh.txt', DEDUP/'manifest.json', DEVIATION, DEVIATION.parent/'manifest.json']
    settings = read(DEDUP/'manifest.json')['request_settings']
    assert settings == read(DEVIATION.parent/'manifest.json')['settings']
    for folder,prompt in [(DEDUP, DEDUP/'prompt_zh.txt'),(DEVIATION.parent,DEVIATION)]:
        # Historical Windows snapshots may store the original text with CRLF.
        from hashlib import sha256
        assert sha256(prompt.read_text().encode()).hexdigest() == read(folder/'manifest.json')['prompt_sha256']
    RUN.mkdir(parents=True, exist_ok=False)
    sources = {}
    for path in paths:
        relative = path.relative_to(ROOT)
        target = RUN/'source'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        sources[str(relative)] = file_hash(target)
    manifest = dict(created_at=now(), git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    selection_seed=SCENE_SEED, episode_seed=2, workers=WORKERS, cases=entries, api=API,
                    settings=settings, sources=sources, dataset_manifest_sha256=file_hash(route.DATA/'manifest.json'),
                    upstream_candidates_sha256=file_hash(route.UPSTREAM/'candidates.json'))
    write(RUN/'manifest.json',manifest)
    write(RECORD/'selection.json',entries)
    write(RUN/'status.json',dict(phase='prepared',episodes=len(cases),updated_at=now()))
    print(entries,flush=True)


def require_http_ok(response):
    if response.get('http_status') != 200:
        raise RuntimeError(response.get('error','DeepSeek request failed'))


def worker(stage, case):
    number = case['case_number']
    if stage == 'dedup':
        spec = importlib.util.spec_from_file_location('frozen_dedup',DEDUP/'run_dedup.py')
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        engine.RUN, engine.SITE = RUN/'dedup', route.DATA
        assert engine.API == API
        compare = engine.compare
        def checked(*args):
            result = compare(*args)
            require_http_ok(result)
            return result
        engine.compare = checked
        fields = ('case_number','case_index','episode_id','real_episode_id','scene','nodes')
        result = engine.run_case({k:case[k] for k in fields},KEY,(DEDUP/'prompt_zh.txt').read_text(),SETTINGS)
        assert result['summary']['model_calls'] == case_info(case)['comparisons']
        return number,result['summary']

    engine = route.deviation
    assert engine.API == API
    call = engine.call_model
    def checked_call(*args):
        meta, result = call(*args)
        require_http_ok(result)
        return meta, result
    engine.call_model = checked_call
    try:
        result = engine.run_case(case,str(RUN/'deviation'),KEY,DEVIATION.read_text(),SETTINGS)
    finally:
        engine.call_model = call
    counts = Counter(r.get('answer',{}).get('verdict','format_error') for r in result['reviews'])
    return number,dict(calls=len(result['reviews']),flagged=int(bool(result['stop_node'])),**counts)


def supervise():
    global KEY, SETTINGS
    KEY = sys.stdin.readline().strip()
    sys.stdin.close()
    if not KEY:
        sys.exit('Missing DeepSeek credential')
    state = dict(pid=os.getpid(),started_at=now(),workers=WORKERS,dedup_completed=0,deviation_completed=0)
    def update(**changes):
        state.update(changes, updated_at=now())
        write(RUN/'status.json',state)
    try:
        update(phase='checking_model')
        manifest = read(RUN/'manifest.json')
        cases = selection()
        if [case_info(c) for c in cases] != manifest['cases']:
            raise ValueError('Frozen subset changed')
        if any(file_hash(ROOT/path) != digest for path,digest in manifest['sources'].items()):
            raise ValueError('Frozen source changed')
        SETTINGS = manifest['settings']
        with httpx.Client(trust_env=False,timeout=30) as client:
            response = client.get(API+'/models',headers={'Authorization':'Bearer '+KEY})
            response.raise_for_status()
            catalog = response.json()
        write(RUN/'model_catalog.json',catalog)
        model = next((m for m in catalog['data'] if m['id']==SETTINGS['model']),None)
        if not model or 'image' not in model.get('input_modalities',['image']):
            raise ValueError('Archived visual model unavailable in current DeepSeek catalog')
        totals = {}
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('fork')) as pool:
            for stage in ('dedup','deviation'):
                update(phase=stage)
                futures = [pool.submit(worker,stage,c) for c in cases]
                counts = Counter()
                for index,future in enumerate(as_completed(futures),1):
                    _,summary = future.result()
                    counts.update(summary)
                    update(**{stage+'_completed':index,stage+'_counts':dict(counts)})
                totals[stage] = dict(counts)
                if stage == 'dedup':
                    retained = []
                    for c in cases:
                        result = read(RUN/'dedup'/'cases'/f"C{c['case_number']:02d}"/'result.json')
                        retained.append(route.retained_case(c,result))
                    write(RUN/'retained_nodes_and_terminals.json',{c['episode_id']:c['nodes'] for c in retained})
                    cases = retained
        assert totals['dedup']['candidates'] == totals['dedup']['retained'] + totals['dedup']['removed']
        assert totals['dedup']['candidates'] == sum(e['candidates'] for e in manifest['cases'])
        write(RUN/'summary.json',totals)
        write(RECORD/'completion.json',dict(finished_at=now(),cases=len(cases),**totals))
        update(phase='complete',finished_at=now())
    except BaseException as exc:
        update(phase='failed',error=str(exc).replace(KEY,'[redacted]')[:1200])
        raise


def launch():
    if read(RUN/'status.json')['phase'] != 'prepared':
        raise RuntimeError('Run already started')
    key = getpass.getpass('DeepSeek API key (hidden): ')
    if not key:
        raise ValueError('Missing DeepSeek credential')
    env = {k:v for k,v in os.environ.items() if 'proxy' not in k.lower() and not any(
           word in k.upper() for word in ('TOKEN','SECRET','API_KEY'))}
    env['CUDA_VISIBLE_DEVICES'] = ''
    cmd = [sys.executable,'-u','-B',str(Path(__file__).resolve()),'--worker']
    with (RUN/'supervisor.log').open('x') as log:
        process = subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,
                                   env=env,cwd=ROOT,start_new_session=True)
    with process.stdin as stream:
        stream.write((key+'\n').encode())
    write(RUN/'launcher.json',dict(pid=process.pid,command=cmd,started_at=now()))
    print('Supervisor PID',process.pid,flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    for command in ('prepare','launch','worker'):
        group.add_argument('--'+command,action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.launch:
        launch()
    else:
        supervise()
