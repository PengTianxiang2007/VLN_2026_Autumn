"""Finish approximately N scored cases, then run the same cases with baseline.

The running evaluator and its sealed sources stay unchanged. At a scored task
boundary this controller stops only the identified old supervisor/simulator.
Completed native LMDB results are exported in a separate derived run, preserving
the original 400-case manifest and all original evidence.
"""
import argparse
from collections import Counter
import copy
import gzip
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
from scripts.run_oracle_existing_model import identity, assert_model, collect_trace
from scripts.run_oracle_distance import write, load_campaign
from scripts.watch_oracle_comparison import final_report
from core.vlnverse_reproduction import digest_json


def read(path):
    return json.loads(Path(path).read_text())


def alive(pid):
    path = Path('/proc') / str(pid) / 'stat'
    return path.exists() and path.read_text().rsplit(')', 1)[1].split()[0] not in ('Z', 'X')


def safe_signal(saved, sig):
    if not alive(saved['pid']):
        return
    if identity(saved['pid']) != saved:
        raise RuntimeError('Process identity changed; refusing to signal')
    os.kill(saved['pid'], sig)


def pause(saved):
    safe_signal(saved, signal.SIGSTOP)
    for _ in range(100):
        if not alive(saved['pid']):
            return
        state = (Path('/proc') / str(saved['pid']) / 'stat').read_text().rsplit(')', 1)[1].split()[0]
        if state in ('T', 't'):
            return
        time.sleep(.01)
    raise RuntimeError('Owned process did not pause')


def selected_episodes(episodes, completed):
    ids = {e['episode_id'] for e in episodes}
    if not completed or not completed <= ids:
        raise ValueError('Completed IDs must be a nonempty subset of the original cohort')
    return [e for e in episodes if e['episode_id'] in completed]


def boundary_safe(count, completed, latest_started, target):
    # The most recent policy reset must belong to a fully scored episode.
    # A later reset indicates an in-flight case: resume and let it finish.
    return count >= target and count == len(completed) and latest_started in completed


def completed_ids(run, episodes):
    import lmdb
    expected = {f"{e['trajectory_id']}_{e['episode_id']}": e['episode_id'] for e in episodes}
    db = lmdb.open(str(run / 'storage/samples/sample_data.lmdb'), readonly=True, lock=False)
    try:
        with db.begin() as txn:
            keys = {k.decode() for k, _ in txn.cursor() if k not in (b'timestamp_', b'eval_rank_0')}
        if not keys <= set(expected):
            raise RuntimeError('Unexpected native LMDB keys')
        return {expected[k] for k in keys}
    finally:
        db.close()


def stop_at_boundary(plan, state, score, episodes):
    old = Path(plan['source'])
    run = Path(state['launch']).parent
    supervisor = plan['source_supervisor']
    sim = None
    stopped = False
    try:
        pause(supervisor)
        # Read direct children after the supervisor is stopped, including the
        # brief interval between Popen and its status-file update.
        children = (Path('/proc') / str(supervisor['pid']) / 'task' / str(supervisor['pid']) / 'children').read_text().split()
        live = [int(pid) for pid in children if alive(int(pid))]
        if len(live) > 1:
            raise RuntimeError('Unexpected multiple supervisor children')
        if live:
            sim = identity(live[0])
            if str(old / 'auto_branch') not in sim['command'] or 'python' not in sim['command']:
                raise RuntimeError('Not the authorized simulator')
            pause(sim)
        completed = completed_ids(run, episodes)
        try:
            count = read(score)['val_unseen']['Count']
        except json.JSONDecodeError:
            # The native logger writes in place. If paused during a write,
            # release both processes and retry after the write finishes.
            return None
        resets = list((old / 'auto_branch/oracle_records/auto_branch').glob('*/attempt_*/native_reset_proof.json'))
        latest = read(max(resets, key=lambda p: p.stat().st_mtime_ns))['episode_id']
        if not boundary_safe(count, completed, latest, plan['target_per_arm']):
            return None
        proof = dict(time=time.time(), count=count, completed_ids=sorted(completed),
                     latest_started=latest, supervisor=supervisor, simulator=sim,
                     no_unfinished_policy_episode=True, original_score=read(score))
        write(Path(plan['destination']) / 'boundary_stop.json', proof)
        # Queue TERM before continuing the stopped simulator: it cannot start
        # another navigation action between verification and cancellation.
        if sim:
            safe_signal(sim, signal.SIGTERM)
            safe_signal(sim, signal.SIGCONT)
        safe_signal(supervisor, signal.SIGTERM)
        safe_signal(supervisor, signal.SIGCONT)
        stopped = True
        for _ in range(90):
            if not alive(supervisor['pid']) and (sim is None or not alive(sim['pid'])):
                assert_model(plan['model_identity'])
                return completed
            time.sleep(1)
        raise RuntimeError('Old supervisor/simulator did not exit; model retained')
    finally:
        if not stopped:
            if sim:
                safe_signal(sim, signal.SIGCONT)
            safe_signal(supervisor, signal.SIGCONT)


def prepare_arm(source, destination, arm, selected):
    manifest = copy.deepcopy(read(source / arm / 'manifest.json'))
    cohort = copy.deepcopy(read(source / arm / 'cohort.json'))
    ids = [e['episode_id'] for e in selected]
    selected_set = set(ids)
    for obj in (manifest, cohort):
        obj['cases'] = [case for case in obj['cases'] if case['episode_id'] in selected_set]
        obj['episodes'] = len(ids)
        obj['scope_reduction'] = dict(source=str(source), rule='All native-scored cases at the requested boundary; no outcome filtering')
    manifest['episode_ids'] = ids
    target = destination / arm
    target.mkdir()
    manifest['runtime_env']['VLN_OUTPUT_ROOT'] = str(target / 'runs')
    manifest['runtime_env']['VLN_ORACLE_MANIFEST'] = str(target / 'manifest.json')
    dataset = target / 'prepared/dataset/fine/val_unseen/val_unseen.json.gz'
    dataset.parent.mkdir(parents=True)
    with gzip.open(dataset, 'wt') as stream:
        json.dump({'episodes': selected}, stream)
    manifest['scope_reduction']['prepared_dataset_sha256'] = hashlib.sha256(dataset.read_bytes()).hexdigest()
    write(target / 'manifest.json', manifest)
    write(target / 'cohort.json', cohort)
    write(target / 'episode_ids.json', ids)
    write(target / 'seal.json', {name + '_sha256': hashlib.sha256((target / (name + '.json')).read_bytes()).hexdigest()
                               for name in ('manifest', 'cohort')})
    load_campaign(target)
    return manifest


def import_native_results(plan, old_state, selected):
    old = Path(plan['source']); root = Path(plan['destination'])
    source_run = Path(old_state['launch']).parent
    target_run = root / 'auto_branch/imported_native_run'
    target_run.mkdir()
    meta = read(source_run / 'run.json')
    source_meta_sha = hashlib.sha256((source_run / 'run.json').read_bytes()).hexdigest()
    meta.update(dataset=str(root / 'auto_branch/prepared/dataset/fine'),
                episode_ids=[e['episode_id'] for e in selected],
                scenes=sorted({e['scan'] for e in selected}), dataset_sha256=digest_json(selected),
                derived_from=str(source_run), source_run_meta_sha256=source_meta_sha)
    write(target_run / 'run.json', meta)
    (target_run / 'storage/chunks').mkdir(parents=True)
    (target_run / 'storage/samples').symlink_to(source_run / 'storage/samples', target_is_directory=True)
    (root / 'auto_branch/oracle_records').symlink_to(old / 'auto_branch/oracle_records', target_is_directory=True)
    borrowed = read(source_run / 'borrowed_model.json')
    evidence = target_run / 'storage/chunks/borrowed_model_evidence'
    evidence.mkdir()
    proof = collect_trace(borrowed['trace'], borrowed['trace_offset'], evidence / 'agent_trace.jsonl')
    write(evidence / 'source.json', proof)
    manifest = read(root / 'auto_branch/manifest.json')
    code = Path(manifest['code_root'])
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONPATH=str(code))
    with (root / 'auto_branch/export.log').open('x') as log:
        subprocess.run([sys.executable, str(code / 'scripts/export_vlnverse_results.py'), '--run', str(target_run)],
                       cwd=code, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    validation = read(target_run / 'validation.json')
    assert validation['passed'] and validation['episodes'] == len(selected)
    state = dict(phase='complete_scored_subset', completed=len(selected), expected=len(selected),
                 validation=str(target_run / 'validation.json'), model_retained=True, simulator_retained=False,
                 source=str(source_run), finished_at=time.time())
    write(root / 'auto_branch/status.json', state)
    return state


def progress(plan, auto, baseline, phase='running'):
    root = Path(plan['destination'])
    report = dict(phase=phase, updated_at=time.time(), controller_pid=os.getpid(),
                  completed_total=auto.get('completed', 0) + baseline.get('completed', 0),
                  planned_total=auto.get('expected', plan['target_per_arm']) + baseline.get('expected', plan['target_per_arm']),
                  model_pid=plan['model_identity']['pid'], model_gpu=3, simulation_gpu=2,
                  arms=dict(auto_branch=auto, baseline=baseline))
    write(root / 'progress.json', report)
    return report


def run(plan):
    old = Path(plan['source']); root = Path(plan['destination'])
    state = read(old / 'auto_branch/status.json')
    source_run = Path(state['launch']).parent
    with gzip.open(source_run / 'dataset/fine/val_unseen/val_unseen.json.gz', 'rt') as stream:
        episodes = json.load(stream)['episodes']
    manifest = read(old / 'auto_branch/manifest.json')
    score = Path(manifest['code_root']) / 'benchmarks/vlnverse/upstream/logs' / state['run_id'] / 'kujiale_result.json'
    target = plan['target_per_arm']
    baseline = dict(phase='waiting_for_reduced_cohort', completed=0, expected=target)
    last_write = 0
    last_boundary_attempt_count = None
    while True:
        assert_model(plan['model_identity'])
        state = read(old / 'auto_branch/status.json')
        if state['phase'] in ('failed', 'stopped', 'cancelled'):
            raise RuntimeError('Original evaluator stopped before scope reduction: ' + repr(state))
        try:
            count = read(score)['val_unseen']['Count']
        except json.JSONDecodeError:
            time.sleep(.1); continue
        auto = dict(phase='running', completed=count, expected=target,
                    simulator_pid=state.get('simulator_pid'), source=str(old / 'auto_branch'))
        if time.time() - last_write > 5:
            progress(plan, auto, baseline); last_write = time.time()
        if count >= target and count != last_boundary_attempt_count:
            last_boundary_attempt_count = count
            completed = stop_at_boundary(plan, state, score, episodes)
            if completed is not None:
                break
        time.sleep(.1 if count >= target - 1 else 1)
    selected = selected_episodes(episodes, completed)
    for arm in ('auto_branch', 'baseline'):
        prepare_arm(old, root, arm, selected)
    write(root / 'cohort_summary.json', dict(episodes=len(selected), scenes=dict(Counter(e['scan'] for e in selected)),
                                           selection='All completed native cases at boundary; unchanged per-case inputs and seed',
                                           original_cohort=400, requested_per_arm=target))
    auto = import_native_results(plan, state, selected)
    old_final = read(old / 'auto_branch/status.json')
    old_final.update(phase='stopped_scope_reduced', scope_reduction_successor=str(root),
                     completed=len(selected), user_requested_per_arm=target)
    write(old / 'auto_branch/status.json', old_final)
    baseline = dict(phase='starting_simulator', completed=0, expected=len(selected))
    write(root / 'baseline/status.json', baseline)
    command = list(plan['baseline_command'])
    command[command.index('--campaign') + 1] = str(root / 'baseline')
    command[command.index('--run-id') + 1] = plan['baseline_run_id']
    write(root / 'baseline_command.json', command)
    # The existing launcher verifies GPU availability and model identity, and
    # retains the final simulator. No model start/stop or reload is requested.
    assert_model(plan['model_identity'])
    with (root / 'baseline/supervisor.log').open('x') as log:
        child = subprocess.Popen(command, cwd=plan['cwd'], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    write(root / 'baseline_process.json', dict(pid=child.pid, command=command, started_at=time.time()))
    while child.poll() is None:
        baseline = read(root / 'baseline/status.json')
        progress(plan, auto, baseline)
        time.sleep(5)
    baseline = read(root / 'baseline/status.json')
    if child.returncode or baseline['phase'] != 'complete_services_retained':
        raise RuntimeError('Reduced baseline did not finish: ' + repr(baseline))
    report = final_report(root, dict(auto_branch=auto, baseline=baseline))
    write(root / 'progress.json', report)
    write(root / 'controller_status.json', dict(phase='complete_services_retained', finished_at=time.time()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args(); plan = read(args.plan)
    root = Path(plan['destination'])
    write(root / 'controller_status.json', dict(phase='waiting_for_task_limit', pid=os.getpid(), started_at=time.time()))
    try:
        run(plan)
    except BaseException as error:
        # A failed limiter must not leave the cancelled 400-case scope running.
        # Only the original, identity-verified supervisor is stopped; its own
        # cleanup handles its simulator and never stops the borrowed model.
        if alive(plan['source_supervisor']['pid']):
            safe_signal(plan['source_supervisor'], signal.SIGTERM)
            safe_signal(plan['source_supervisor'], signal.SIGCONT)
        write(root / 'controller_status.json', dict(phase='failed', error=repr(error), time=time.time(), model_retained=True))
        raise


if __name__ == '__main__':
    main()
