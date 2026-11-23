"""Run each Oracle condition through the original multi-episode reproduction entry."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate import check_gpu


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def load_campaign(campaign):
    root = Path(campaign).resolve()
    seal = json.loads((root / 'seal.json').read_text())
    for name in ('manifest', 'cohort'):
        if sha(root / (name + '.json')) != seal[name + '_sha256']:
            raise RuntimeError('Frozen ' + name + ' changed; prepare a new campaign')
    manifest = json.loads((root / 'manifest.json').read_text())
    if manifest['protocol'] not in ('distance_oracle_v001', 'auto_route_oracle_v001', 'auto_branch_oracle_v001', 'step_multiview_v001'):
        raise ValueError('Not a distance Oracle campaign')
    for name, expected in manifest['code_sha256'].items():
        if sha(Path(manifest['code_root']) / name) != expected:
            raise RuntimeError('Frozen source changed: ' + name)
    geometry = manifest.get('landing_geometry_audit')
    if geometry is not None:
        if geometry['mode'] != 'audit_only':
            raise ValueError('Unexpected geometry behavior')
        for name, expected in geometry['files_sha256'].items():
            if sha(Path(geometry['root']) / name) != expected:
                raise RuntimeError('Frozen geometry changed: ' + name)
    return manifest


def job_plan(campaign, manifest, arms, episodes, gpu, sim_gpu, inherited=(), allow_shared_gpu=False):
    if not arms or len(set(arms)) != len(arms) or not set(arms) <= set(manifest['arms']):
        raise ValueError('Unknown or duplicate arms')
    if not episodes or len(set(episodes)) != len(episodes) or not set(episodes) <= set(manifest['episode_ids']):
        raise ValueError('Unknown or duplicate episodes')
    if gpu < 0 or sim_gpu < 0:
        raise ValueError('GPU indices must be nonnegative')
    tag = hashlib.sha256(str(campaign).encode()).hexdigest()[:10]
    jobs = []
    done = {(row['arm'], row['episode_id']) for row in inherited}
    for arm in arms:
        remaining = [eid for eid in episodes if (arm, eid) not in done]
        if not remaining:
            continue
        run_id = 'peng_fine_distance_native_' + tag + '_' + arm
        command = [sys.executable, '-B', str(Path(manifest['code_root']) / 'benchmarks/vlnverse/runner/run_full.py'),
                   '--method', 'StreamVLN', '--mode', 'physical', '--seed', str(manifest['seed']),
                   '--gpu', str(gpu), '--sim-gpu', str(sim_gpu), '--episode-ids', *remaining,
                   '--run-id', run_id]
        if allow_shared_gpu:
            command.append('--allow-shared-gpu')
        jobs.append({'arm': arm, 'episode_ids': remaining, 'run_id': run_id, 'command': command,
                     'threshold_m': manifest['arms'][arm]['threshold_m']})
    return jobs


def admission(gpu, sim_gpu, allow_shared_gpu=False):
    samples = []
    for n in range(2):
        # Query all cards; selected cards must be idle. Never stop or evict a process.
        rows = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.used,memory.free,utilization.gpu',
                                        '--format=csv,noheader,nounits'], text=True)
        cards = {int(v[0]): {'used_mib': int(v[1]), 'free_mib': int(v[2]), 'utilization': int(v[3])}
                 for line in rows.splitlines() if (v := line.split(','))}
        for card in {gpu, sim_gpu}:
            if not allow_shared_gpu and (cards[card]['utilization'] > 10 or cards[card]['used_mib'] >= 1024):
                raise RuntimeError('Selected GPU is busy: ' + str(card))
        check_gpu(gpu, 32000 if gpu == sim_gpu else 25000, allow_shared=allow_shared_gpu)
        if sim_gpu != gpu:
            check_gpu(sim_gpu, 12000, allow_shared=allow_shared_gpu)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
        if available < 64 * 1024**2:
            raise RuntimeError('Less than 64 GiB MemAvailable')
        samples.append({'gpus': cards, 'available_kib': available})
        if n == 0:
            time.sleep(5)
    return samples


def idle_pair(preferred_gpu, preferred_sim_gpu):
    rows = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.used,memory.free,utilization.gpu',
                                    '--format=csv,noheader,nounits'], text=True)
    occupied = {line.split(',')[0].strip() for line in subprocess.check_output(
        ['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'], text=True).splitlines()}
    cards = [int(v[0]) for line in rows.splitlines() if (v := [x.strip() for x in line.split(',')])
             if v[1] not in occupied and int(v[2]) < 1024 and int(v[3]) >= 32000 and int(v[4]) <= 10]
    if not cards:
        raise RuntimeError('No idle GPU with at least 32000 MiB free')
    order = list(dict.fromkeys([preferred_gpu, preferred_sim_gpu, *sorted(cards)]))
    available = [g for g in order if g in cards]
    return available[0], available[1] if len(available) > 1 else available[0]


def wait_for_resources(campaign, state, gpu, sim_gpu, timeout_seconds, auto_gpu=False, allow_shared_gpu=False):
    if auto_gpu and allow_shared_gpu:
        raise ValueError('Shared placement requires explicit GPU selection')
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            selected = idle_pair(gpu, sim_gpu) if auto_gpu else (gpu, sim_gpu)
            samples = admission(*selected, allow_shared_gpu=True) if allow_shared_gpu else admission(*selected)
            state['selected_gpus'] = {'model': selected[0], 'simulation': selected[1]}
            return samples
        except RuntimeError as error:
            if time.monotonic() >= deadline:
                raise RuntimeError('Resource waiting expired: ' + str(error)) from error
            state.update(phase='waiting_for_resources', resource_reason=str(error), updated_at=time.time())
            write(campaign / 'status.json', state)
            time.sleep(min(30, max(0, deadline - time.monotonic())))


def inherited_results(manifest, sources):
    if sources and manifest['protocol'] in ('auto_route_oracle_v001', 'auto_branch_oracle_v001'):
        raise ValueError('Automatic-route comparisons require a new independent run; no inherited results')
    results = {}
    for source in sources:
        source = Path(source).resolve()
        old = load_campaign(source)
        for field in ('protocol', 'config', 'cases', 'official_split_sha256'):
            if old[field] != manifest[field]:
                raise ValueError('Cannot combine different protocols/cohorts: ' + field)
        for complete in source.glob('*.complete.json'):
            proof = json.loads(complete.read_text())
            job = proof['job']
            arm, eid = job['arm'], job['episode_id']
            path = source / 'oracle_records' / arm / eid / 'result.json'
            if sha(path) != proof['result_sha256']:
                raise RuntimeError('Inherited result hash mismatch: ' + str(path))
            result = json.loads(path.read_text())
            if (result['status'], result['arm'], result['episode_id'], result['threshold_m']) != (
                    'complete', arm, eid, manifest['arms'][arm]['threshold_m']):
                raise RuntimeError('Inherited completion identity mismatch')
            key = (arm, eid)
            if key in results:
                raise RuntimeError('Duplicate inherited job')
            results[key] = dict(arm=arm, episode_id=eid, triggered=result['triggered'],
                                inherited_from=str(source), result=str(path),
                                result_sha256=proof['result_sha256'],
                                completion_sha256=sha(complete), seal_sha256=sha(source / 'seal.json'))
    return list(results.values())


def verify_arm(campaign, manifest, job):
    run = campaign / 'runs/vlnverse/streamvln/results' / job['run_id']
    proof = json.loads((run / 'validation.json').read_text())
    result = json.loads((run / 'result.json').read_text())
    if not proof['passed'] or proof['episodes'] != len(job['episode_ids']) or result['status'] != 'complete':
        raise RuntimeError('Native reproduction/export did not complete')
    rows = {row['episode_id']: row for row in map(json.loads, (run / 'episodes.jsonl').read_text().splitlines())}
    if set(rows) != set(job['episode_ids']):
        raise RuntimeError('Official episode set differs from requested arm')
    completed = []
    for eid in job['episode_ids']:
        if manifest['arms'][job['arm']]['mode'] == 'baseline':
            # Baseline deliberately has no Oracle hook or invented interventions.
            entry = dict(arm=job['arm'], episode_id=eid, threshold_m=None, native_run=str(run))
            write(campaign / (job['arm'] + '_' + eid + '.complete.json'),
                  dict(job=entry, native_episodes_sha256=sha(run/'episodes.jsonl'),
                       validation_sha256=sha(run/'validation.json'), oracle_enabled=False))
            completed.append(dict(arm=job['arm'], episode_id=eid, triggered=False))
            continue
        case = campaign / 'oracle_records' / job['arm'] / eid
        path = case / 'result.json'
        oracle = json.loads(path.read_text())
        if (oracle['status'], oracle['arm'], oracle['episode_id'], oracle['threshold_m']) != (
                'complete', job['arm'], eid, job['threshold_m']):
            raise RuntimeError('Oracle result differs from requested task')
        if not list(case.glob('attempt_*/native_scoring_complete.json')):
            raise RuntimeError('Native scoring completion evidence missing')
        for original, exported in (('success','SR'), ('spl','SPL'), ('NE','NE'), ('TL','TL'), ('steps','steps')):
            if abs(oracle['metrics'][original] - rows[eid][exported]) > 1e-5:
                raise RuntimeError('Oracle differs from native official metrics: ' + eid)
        entry = dict(arm=job['arm'], episode_id=eid, threshold_m=job['threshold_m'], native_run=str(run))
        write(campaign / (job['arm'] + '_' + eid + '.complete.json'),
              dict(job=entry, result_sha256=sha(path), validation_sha256=sha(run/'validation.json')))
        completed.append(dict(arm=job['arm'], episode_id=eid, triggered=oracle['triggered']))
    return completed


def native_progress(campaign, manifest, job):
    score = Path(manifest['code_root']) / 'benchmarks/vlnverse/upstream/logs' / job['run_id'] / 'kujiale_result.json'
    try:
        count = json.loads(score.read_text())['val_unseen']['Count'] if score.exists() else 0
    except (json.JSONDecodeError, KeyError):
        # Native ResultLogger rewrites this file in place. Partial polling is not
        # a navigation failure; final verification still requires complete JSON.
        count = None
    proofs = []
    for eid in job['episode_ids']:
        case = campaign / 'oracle_records' / job['arm'] / eid
        for path in case.glob('attempt_*/native_scoring_complete.json'):
            proof = json.loads(path.read_text())
            proofs.append(dict(episode_id=eid, pid=proof['pid'], path=str(path)))
    same_process = any(sum(r['pid'] == p['pid'] for r in proofs) >= 2 for p in proofs)
    if same_process and count is not None and count >= 2 and not (campaign / 'first_native_continuation_verified.json').exists():
        write(campaign / 'first_native_continuation_verified.json', dict(
            arm=job['arm'], native_official_count=count, proofs=proofs,
            verification='Native scoring returned for at least two tasks in one simulator process; full-arm export pending',
            checked_at=time.time()))
    return dict(official_scored=count, expected=len(job['episode_ids']),
                scoring_hooks_completed=len(proofs), full_arm_export_pending=True)


def job_environment(campaign, manifest, job, inherited_env=None):
    source = os.environ if inherited_env is None else inherited_env
    env = {k:v for k,v in source.items()
           if not k.startswith(('VLN_', 'STREAMVLN_', 'JANUSVLN_', 'PENG_')) and not k.lower().endswith('_proxy')}
    env.update(manifest['runtime_env'])
    if manifest['arms'][job['arm']]['mode'] == 'baseline':
        for key in list(env):
            if key.startswith(('VLN_ORACLE_', 'VLN_BRANCH_', 'VLN_DISTANCE_')):
                del env[key]
    else:
        env.update(VLN_DISTANCE_ARM=job['arm'],
                   VLN_ORACLE_RECORDS=str(campaign/'oracle_records'/job['arm']),
                   VLN_BRANCH_ROOT=str(campaign/'checkpoints'/job['arm']))
    return env


def execute(campaign, manifest, jobs, inherited, args):
    if manifest.get('execution_backend') != 'native_reproduction':
        raise RuntimeError('Prepare a new native-reproduction campaign; do not use historical runtimes')
    original_runner = 'benchmarks/vlnverse/runner/run_full.py'
    if manifest['source_sha256'][original_runner] != manifest['code_sha256'][original_runner]:
        raise RuntimeError('The original reproduction launcher must remain byte-identical')
    lock = (campaign / 'campaign.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if json.loads((campaign / 'status.json').read_text())['phase'] != 'prepared':
        raise RuntimeError('Preserve the existing attempt and prepare a new run')
    state = dict(phase='prepared', pid=os.getpid(), started_at=time.time(), completed=inherited,
                 expected_jobs=len(inherited) + sum(len(j['episode_ids']) for j in jobs),
                 inherited_count=len(inherited), execution='native_reproduction', simulation_started=False)
    state['requested_placement'] = dict(model=args.gpu, simulation=args.sim_gpu,
                                       auto=args.auto_gpu, allow_shared_gpu=args.allow_shared_gpu)
    write(campaign / 'inherited_results.json', inherited)
    write(campaign / 'arm_plan.json', jobs)
    child = None
    def stop(signum, frame):
        raise KeyboardInterrupt('Termination requested')
    handlers = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        for original_job in jobs:
            if (campaign / 'stop_after_arm').exists():
                state['phase'] = 'stopped_at_arm_boundary'
                break
            job = dict(original_job, command=list(original_job['command']))
            state['current_job'] = job
            state['admission'] = wait_for_resources(campaign, state, args.gpu, args.sim_gpu,
                args.resource_wait_hours * 3600, args.auto_gpu, args.allow_shared_gpu)
            selected = state['selected_gpus']
            job['command'][job['command'].index('--gpu')+1] = str(selected['model'])
            job['command'][job['command'].index('--sim-gpu')+1] = str(selected['simulation'])
            env = job_environment(campaign, manifest, job)
            # No RSS override, scene batching, simulator cache override or custom
            # process management: run_full owns the original lifecycle unchanged.
            with (campaign / (job['arm'] + '.log')).open('x') as log:
                child = subprocess.Popen(job['command'], cwd=manifest['code_root'], env=env,
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            state.update(phase='running', launcher_pid=child.pid, simulation_started=True,
                         current_arm_progress={'official_scored': 0})
            state.pop('resource_reason', None)
            write(campaign/'status.json', state)
            while child.poll() is None:
                progress = native_progress(campaign, manifest, job)
                if progress['official_scored'] is None:
                    progress['official_scored'] = state.get('current_arm_progress', {}).get('official_scored', 0)
                    progress['score_write_in_progress'] = True
                state.update(current_arm_progress=progress, updated_at=time.time())
                write(campaign/'status.json', state)
                time.sleep(5)
            if child.returncode:
                raise RuntimeError('Original reproduction launcher failed; inspect ' + job['arm'] + '.log')
            state['completed'].extend(verify_arm(campaign, manifest, job))
            state['current_arm_progress']['full_arm_export_pending'] = False
            child = None
            write(campaign/'status.json', state)
        else:
            state['phase'] = 'complete'
    except BaseException as error:
        state.update(phase='stopped' if isinstance(error, KeyboardInterrupt) else 'failed',
                     error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=55)
            except subprocess.TimeoutExpired:
                state['cleanup_error'] = 'Original launcher still exiting; inspect owned_processes.json'
        state['finished_at'] = time.time()
        state['gpu_after'] = subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu','--format=csv'],text=True)
        write(campaign/'status.json', state)
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
        lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--reuse-from', type=Path, action='append', default=[])
    parser.add_argument('--arms', nargs='+', choices=['early','short','medium','long','checkpoint','baseline','auto_route','auto_branch'])
    parser.add_argument('--episodes', nargs='+')
    parser.add_argument('--gpu', type=int, default=2)
    parser.add_argument('--sim-gpu', type=int, default=3)
    parser.add_argument('--auto-gpu', action='store_true')
    parser.add_argument('--allow-shared-gpu', action='store_true',
                        help='Explicitly authorized shared placement; forwarded to the original launcher')
    parser.add_argument('--resource-wait-hours', type=float, default=24)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.resource_wait_hours <= 168:
        parser.error('Resource wait must be in [0,168] hours')
    if args.auto_gpu and args.allow_shared_gpu:
        parser.error('Shared placement requires explicit GPU selection, without --auto-gpu')
    campaign = args.campaign.resolve()
    manifest = load_campaign(campaign)
    inherited = inherited_results(manifest, args.reuse_from)
    arms, episodes = args.arms or list(manifest['arms']), args.episodes or manifest['episode_ids']
    inherited = [row for row in inherited if row['arm'] in arms and row['episode_id'] in episodes]
    jobs = job_plan(campaign, manifest, arms, episodes, args.gpu, args.sim_gpu, inherited, args.allow_shared_gpu)
    if not args.execute:
        print(json.dumps(dict(phase='plan_only', inherited=len(inherited),
            pending=sum(len(j['episode_ids']) for j in jobs), native_launcher_invocations=len(jobs),
            arms={j['arm']:len(j['episode_ids']) for j in jobs},
            first_command=jobs[0]['command'] if jobs else None), indent=2))
        return
    execute(campaign, manifest, jobs, inherited, args)


if __name__ == '__main__':
    main()

