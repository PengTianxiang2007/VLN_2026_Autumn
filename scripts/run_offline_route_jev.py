"""Score native front observations and replay the frozen sampler per episode."""
import argparse
import fcntl
import getpass
import hashlib
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import now, read
from core.crossing_lite import windows
from core.offline_route_dataset import OfflineRouteDataset
from run_jev_noul_five_concurrent import run_task

POINTER = 'experiments/crossing_checkpoint/current_jev_version.json'
WORKERS = 300
ENDPOINT = 'https://api.easyjev.online/v1/systemone'
MODEL = 'jev-1.14.0'


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_sources(out, dataset):
    versions = read(ROOT / POINTER)['fixed_pipeline']
    paths = [POINTER, 'scripts/run_offline_route_jev.py',
             'scripts/run_jev_noul_five_concurrent.py', 'scripts/replay_jev_online_sampling.cjs',
             'core/agent_route_choice.py', 'core/crossing_lite.py', 'core/offline_route_dataset.py']
    for name in ('scorer', 'sampler', 'config'):
        path = versions[name]
        if sha(ROOT / path) != versions[name + '_sha256']:
            raise ValueError('Changed fixed source: ' + path)
        paths.append(path)
    version = dict(files={p: sha(ROOT / p) for p in paths}, dataset=str(dataset),
                   dataset_manifest_sha256=sha(dataset / 'manifest.json'),
                   selection_sha256=sha(dataset / 'subsets/all_selected.txt'),
                   git_head=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
                   endpoint=ENDPOINT, model=MODEL, workers=WORKERS)
    path = out / 'manifest.json'
    if path.exists():
        old = read(path)
        # A scheduler-only recovery reuses saved requests. Preserve both
        # drivers and require every scoring, sampling and input hash to match.
        driver = 'scripts/run_offline_route_jev.py'
        original_hash = old['files'][driver]
        old['files'][driver] = version['files'][driver]
        if old != version:
            raise ValueError('Existing run uses different sources, input or configuration')
        if original_hash != version['files'][driver]:
            recovery = out / 'recovery' / version['files'][driver]
            recovery.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / driver, recovery / Path(driver).name)
            save(recovery/'manifest.json', version)
        return
    for p in paths:
        dest = out / 'source' / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / p, dest)
    save(path, version)


def episode_tasks(ds, eid, output):
    with (ds.root/'inputs'/eid/'observations.jsonl').open() as stream:
        last = sum(1 for line in stream if line.strip()) - 1
    task = ds.task(eid)
    frames = []
    for t, obs in enumerate(ds.iter_observations(eid, through_step=last, mode='front')):
        if obs['step'] != t or len(obs['views']) != 1:
            raise ValueError('Invalid front observation: ' + eid)
        image = obs['views'][0]
        frames.append(dict(frame=t, rgb=str(Path(image['image']).relative_to(ds.root)),
                           rgb_sha256=image['sha256'], terminal=t==last,
                           eligible_for_inference=t<last, rgb_reused=False))
    return [dict(episode_id=eid, scene=task['scene'], group='failure', frame=t, images=images,
                 question_version='v004', dataset=str(ds.root), output=str(output),
                 endpoint=ENDPOINT, model=MODEL, attempts=3, timeout=120) for t, images in windows(frames)]


def task_key(task):
    return task['episode_id'], task['frame']


def run(dataset, out):
    capture_sources(out, dataset)
    ds = OfflineRouteDataset(dataset)
    ids = (dataset/'subsets/all_selected.txt').read_text().splitlines()
    if len(ids) != 53 or sorted(ids) != ds.episode_ids() or len(set(ids)) != len(ids):
        raise ValueError('Input episodes differ from registered selection')
    if not os.environ.get('JEV_API_KEY'):
        os.environ['JEV_API_KEY'] = getpass.getpass('JEV credential (hidden): ')
    status = dict(phase='preparing', started_at=now(), pid=os.getpid(), workers=WORKERS,
                  expected=4837, completed=0, failed=0)
    def report(**changes):
        status.update(changes, updated_at=now())
        save(out/'status.json',status)
    previous_status = out/'status.json'
    if previous_status.is_file():
        save(out/'recovery'/('prior_status_' + str(os.getpid())+'.json'),read(previous_status))
    report()
    rows = {}
    existing = {p.parent for p in (out/'cases').glob('*/F*/result.json')}
    def load_cached(task):
        folder = out/'cases'/task['episode_id']/('F%04d' % task['frame'])
        if folder not in existing:
            return False
        row = read(folder/'result.json')
        images = read(folder/'images.json')
        if (row['phase'] != 'complete' or task_key(row) != task_key(task)
                or [v['source_sha256'] for v in images] != [v['rgb_sha256'] for v in task['images']]):
            raise ValueError('Incompatible cached result: ' + str(folder))
        rows[task_key(task)] = row
        return True
    first = episode_tasks(ds, ids[0], out)
    probe = first[2]
    if not load_cached(probe):
        report(phase='first_request', first_episode=ids[0], first_frame=probe['frame'])
        row = run_task(probe)
        if row['phase'] != 'complete':
            raise RuntimeError('First in-scope request: ' + row['error'])
        rows[task_key(probe)] = row
    report(phase='indexing', completed=len(rows))
    print('First three-frame request verified.', flush=True)
    tasks = first[:]
    for eid in ids[1:]:
        tasks.extend(episode_tasks(ds, eid, out))
    if len(tasks) != status['expected']:
        raise ValueError('Unexpected number of eligible frames')
    pending = [t for t in tasks if task_key(t) not in rows and not load_cached(t)]
    for wave in range(1,4):
        if not pending:
            break
        target = out if wave==1 else out / ('retry_%d' % wave)
        report(phase='scoring',wave=wave,completed=len(rows),pending=len(pending),failed=0)
        failed = []
        work = {task_key(t): t for t in pending}
        jobs = (dict(t,output=str(target)) for t in pending)
        with multiprocessing.get_context('fork').Pool(min(WORKERS,len(work))) as pool:
            for i, row in enumerate(pool.imap_unordered(run_task, jobs, chunksize=1),1):
                task = work[task_key(row)]
                if row['phase']=='complete':
                    rows[task_key(task)] = row
                    if wave>1:
                        row['source_directory'] = str(target)
                        dest = out/'cases'/task['episode_id']/('F%04d' % task['frame'])
                        for name in ['images.json','request.json','response.json']:
                            shutil.copyfile(target/'cases'/task['episode_id']/dest.name/name, dest/name)
                        save(dest/'result.json', row)
                else:
                    failed.append(task)
                if i%20==0 or i==len(work):
                    report(completed=len(rows), failed=len(failed), pending=len(work)-i)
        pending = failed
    os.environ.pop('JEV_API_KEY',None)
    if pending:
        save(out/'pending_frames.json', [task_key(t) for t in pending])
        raise RuntimeError('Unscored frames after retries: %d' % len(pending))
    report(phase='sampling',completed=len(rows),failed=0,pending=0)
    grouped = defaultdict(list)
    front = {task_key(task): task['images'][-1]['rgb'] for task in tasks}
    for key,row in sorted(rows.items()):
        grouped[key[0]].append(row)
    all_nodes = []
    kind_counts = Counter()
    for eid in ids:
        entries = grouped[eid]
        if [r['frame'] for r in entries] != list(range(len(entries))):
            raise ValueError('Non-consecutive scores: ' + eid)
        folder = out/'episodes'/eid
        scores = [r['answer']['probability_yes'] for r in entries]
        save(folder/'scores.json', scores)
        result = subprocess.check_output(['node',str(out/'source/scripts/replay_jev_online_sampling.cjs'),
                                          '--input',str(folder/'scores.json')],text=True)
        sampled = json.loads(result)
        if sampled['received'] != len(scores):
            raise ValueError('Sampler input count mismatch')
        save(folder/'sampling.json',sampled)
        for node in sampled['nodes']:
            if node['emittedAt'] != node['index']+5 or node['rawScore'] != scores[node['index']]:
                raise ValueError('Candidate alignment mismatch: ' + eid)
            all_nodes.append(dict(episode_id=eid, **node, front_image=front[eid,node['index']]))
            kind_counts[node['kind']]+=1
    save(out/'candidates.json',all_nodes)
    summary = dict(episodes=len(ids), scored=len(rows), candidates=len(all_nodes),
                   kinds=dict(kind_counts), deduplication=False, finished_at=now())
    save(out/'summary.json', summary)
    report(phase='complete', **summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    with (output/'.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            run(args.dataset.resolve(),output)
        except (Exception,KeyboardInterrupt) as error:
            path=output/'status.json'
            state=read(path) if path.is_file() else {}
            save(path,dict(state,phase='stopped',error=str(error),updated_at=now()))
            raise
