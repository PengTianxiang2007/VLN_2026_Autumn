"""Run a fixed cohort of previously failed fall episodes, preserving the source run."""
import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from core.seeding import episode_seed
from core.vlnverse_runtime import placement, retry_delay, worker_failure, needs_separate_gpus
from core.vlnverse_reproduction import verify_rows
from scripts.reproduce_streamvln_vlnverse import gpu_rows, available_memory_mib, can_admit_worker


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rollback_point(frames):
    actions = [r for r in frames if not r['terminal']]
    if not frames or not frames[-1]['terminal'] or len(frames) != len(actions) + 1:
        raise ValueError('Expected exactly one terminal observation after all actions')
    if [r['action_index'] for r in actions] != list(range(len(actions))):
        raise ValueError('Missing or duplicated action observations')
    if any(r['action'].get('move_by_discrete', [None])[0] not in (1, 2, 3) for r in actions):
        raise ValueError('Unexpected non-navigation action in fall prefix')
    target = len(actions) - 10 if len(actions) >= 10 else None
    return actions, target


def cohort(source):
    scores = list(csv.DictReader((source / 'episodes.csv').open()))
    falls = [r for r in scores if int(r['run_seed']) == 2 and float(r['SR']) == 0 and r['fail_reason'] == 'fall']
    assert len(falls) == len({r['episode_id'] for r in falls}) == 41
    index = [json.loads(l) for l in (source / 'visualization/index.jsonl').read_text().splitlines()]
    cases = []
    for score in falls:
        matches = [r for r in index if r['seed'] == 2 and r['episode_id'] == score['episode_id']
                   and r['run_id'] == score['run_id'] and r['status'] == 'complete']
        assert len(matches) == 1, score['episode_id']
        vis = matches[0]
        path = source / 'visualization' / vis['steps']
        frames = [json.loads(l) for l in path.read_text().splitlines()]
        actions, target = rollback_point(frames)
        assert int(score['episode_seed']) == episode_seed(2, score['episode_id'])
        # N actions were executed before the terminal fall observation. The rollback
        # observation precedes action N-10 (zero based), leaving exactly ten actions.
        cases.append(dict(episode_id=score['episode_id'], scene=score['scene'], original=score,
                          original_action_count=len(actions), rollback_action_index=target,
                          rollback_actions=min(10, len(actions)),
                          rollback_eligible=len(actions) >= 10,
                          target_position=actions[target]['position'] if target is not None else None,
                          rollback_ineligible_reason=None if len(actions) >= 10 else 'fall_before_ten_navigation_actions',
                          source_steps=str(path), source_steps_sha256=sha(path),
                          source_video=str(source / 'visualization' / vis['video']),
                          original_actions=[r['action']['move_by_discrete'][0] for r in actions]))
    return cases


def prepare(source, campaign):
    cases = cohort(source)
    original = json.loads((source / 'manifest.json').read_text())
    root = Path(original['code_root'])
    # Check before writing; never copy run data, models, environments or caches.
    for name, expected in original['code_sha256'].items():
        if sha(root / name) != expected:
            raise RuntimeError('Source snapshot no longer matches provenance: ' + name)
    campaign.mkdir(parents=True, exist_ok=False)
    code = campaign / 'code_reset'
    for name in original['code_sha256']:
        target = code / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
    # Gate on one full task. It counts as its single reset trial, not an extra pilot.
    gate_case = min((r for r in cases if r['original_action_count'] > 0),
                    key=lambda r: (r['original_action_count'], r['episode_id']))
    groups = [(gate_case['scene'], [gate_case['episode_id']])]
    for scene in sorted({r['scene'] for r in cases}):
        ids = [r['episode_id'] for r in cases if r['scene'] == scene and r is not gate_case]
        if ids:
            groups.append((scene, ids))
    units = [dict(scene=scene, episode_ids=ids, seed=2,
                  run_id=f'peng_fine_fall_reset_{campaign.name}_{i:02d}', expected=len(ids))
             for i, (scene, ids) in enumerate(groups)]
    env = dict(original['runtime_env'])
    env['VLN_OUTPUT_ROOT'] = str(campaign / 'runs_reset')
    env['VLN_SIM_CACHE_ROOT'] = str(PROJECT / 'benchmarks/vlnverse/runner')
    env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PIP_NO_INDEX='1',
               PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    (campaign / 'runs_reset').mkdir()
    write_json(campaign / 'runs_reset/visualization.json',
               dict(schema=1, seeds=[2], output_dir=str(campaign / 'visualization_reset')))
    manifest = dict(schema=1, created_at=now(), source_campaign=str(source),
                    source_scores_sha256=sha(source / 'episodes.csv'), cases=cases,
                    cohort_rule='run_seed=2 AND SR=0 AND fail_reason=fall',
                    steps_unit='navigation action: forward/left/right; not physics ticks',
                    rollback_eligible=sum(r['rollback_eligible'] for r in cases),
                    reset=dict(code_root=str(code), code_sha256=original['code_sha256'],
                               runtime_env=env, units=units, seed=2),
                    replay=dict(status='awaiting_protocol_confirmation'),
                    limitations=['One retry per condition; not an estimate of per-task failure probability.',
                                 'Old runs lack per-step orientation, joint/velocity/controller state and exact RGB.'])
    write_json(campaign / 'manifest.json', manifest)
    write_json(campaign / 'cohort.json', cases)
    shutil.copy2(source / 'model_fingerprints.json', campaign / 'model_fingerprints.json')
    print(json.dumps(dict(campaign=str(campaign), cases=len(cases), reset_units=len(units),
                          gate_episode=gate_case['episode_id'], gate_original_actions=gate_case['original_action_count'])))


def prepare_replay(campaign):
    manifest = json.loads((campaign / 'manifest.json').read_text())
    if manifest['replay'].get('code_root'):
        raise RuntimeError('Replay already prepared; preserving existing experiment')
    base = manifest['reset']
    code = campaign / 'code_replay'
    code.mkdir(exist_ok=False)
    for name, expected in base['code_sha256'].items():
        source = Path(base['code_root']) / name
        if sha(source) != expected:
            raise RuntimeError('Reset source changed: ' + name)
        target = code / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(PROJECT / 'core/fall_replay.py', code / 'core/fall_replay.py')
    evaluator = code / 'benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py'
    source = evaluator.read_text()
    edits = [
        ('        self.data_collector = DataCollector(self.dataloader.lmdb_path)\n',
         '        self.data_collector = DataCollector(self.dataloader.lmdb_path)\n'
         '        from core.fall_replay import FallReplay\n'
         '        self.fall_replay = FallReplay.from_environment()\n'),
        ('            review_observations = obs if self.review else None\n',
         '            review_observations = obs\n'),
        ('            obs, action = self.get_action(obs, action)\n',
         '            obs, action = self.get_action(obs, action)\n'
         '            if self.fall_replay:\n'
         '                for index, (ob, info, act) in enumerate(zip(review_observations, reset_info, action)):\n'
         '                    if info is not None and self.runner_status[index] == runner_status_code.NORMAL:\n'
         '                        chosen = self.fall_replay.choose(info.data["episode_id"], ob, act[self.robot_name])\n'
         '                        action[index] = {self.robot_name: chosen}\n'),
        ('                self.data_collector.save_eval_result(\n',
         '                if self.fall_replay:\n'
         '                    self.fall_replay.finish(reset_info.data["episode_id"], obs,\n'
         '                                            obs["metrics"][list(obs["metrics"])[0]][0])\n'
         '                self.data_collector.save_eval_result(\n'),
    ]
    for before, after in edits:
        if source.count(before) != 1:
            raise RuntimeError('Unexpected evaluator version; not applying replay patch')
        source = source.replace(before, after)
    evaluator.write_text(source)
    eligible = {c['episode_id'] for c in manifest['cases'] if c['rollback_eligible']}
    units = []
    for unit in base['units']:
        ids = [eid for eid in unit['episode_ids'] if eid in eligible]
        if ids:
            units.append(dict(unit, episode_ids=ids, expected=len(ids), run_id=unit['run_id'].replace('_reset_', '_replay_')))
    env = dict(base['runtime_env'], VLN_OUTPUT_ROOT=str(campaign / 'runs_replay'),
               VLN_FALL_REPLAY_MANIFEST=str(campaign / 'manifest.json'),
               VLN_FALL_REPLAY_RECORD_DIR=str(campaign / 'replay_records'))
    (campaign / 'runs_replay').mkdir()
    write_json(campaign / 'runs_replay/visualization.json',
               dict(schema=1, seeds=[2], output_dir=str(campaign / 'visualization_replay')))
    hashes = {name: sha(code / name) for name in [*base['code_sha256'], 'core/fall_replay.py']}
    manifest['replay'] = dict(status='prepared', code_root=str(code), code_sha256=hashes,
                              runtime_env=env, units=units, seed=2,
                              protocol='original_action_prefix_then_native_streamvln_v1',
                              checkpoint_xy_quality_threshold_m=0.5,
                              excluded=[dict(episode_id=c['episode_id'], reason=c['rollback_ineligible_reason'])
                                        for c in manifest['cases'] if not c['rollback_eligible']],
                              model_history='Native model runs on new observations during forced action replay; '
                                            'native pending actions and caches remain intact at handover. '
                                            'Proposed vs executed action mismatches are reported.',
                              exact_original_state_restored=False)
    write_json(campaign / 'manifest.json', manifest)
    print(json.dumps(dict(replay_prepared=True, eligible=len(eligible), excluded=manifest['replay']['excluded'])))


def run_path(config, unit):
    return Path(config['runtime_env']['VLN_OUTPUT_ROOT']) / 'vlnverse/streamvln/results' / unit['run_id']


def collect(campaign, arm, config):
    rows, complete, counts = [], [], {}
    code = Path(config['code_root'])
    for unit in config['units']:
        path = run_path(config, unit)
        if (path / 'result.json').exists():
            result = json.loads((path / 'result.json').read_text())
            proof = json.loads((path / 'validation.json').read_text())
            assert result['status'] == 'complete' and proof['passed']
            group = [json.loads(l) for l in (path / 'episodes.jsonl').read_text().splitlines()]
            verify_rows(group, unit['episode_ids'], 2)
            if arm == 'replay':
                for row in group:
                    records = sorted((campaign / 'replay_records' / row['episode_id']).glob('*/result.json'))
                    if not records:
                        raise RuntimeError('Scored replay lacks diagnostic evidence: ' + row['episode_id'])
                    diagnostic = json.loads(records[-1].read_text())
                    if (diagnostic['fail_reason'] != row['fail_reason'] or diagnostic['episode_seed'] != row['episode_seed']
                            or abs(diagnostic['NE'] - row['NE']) > 1e-6 or diagnostic['SR'] != row['SR']):
                        raise RuntimeError('Replay diagnostics disagree with scored episode')
                    row['replay'] = diagnostic
            rows.extend(dict(condition=arm, **r) for r in group)
            complete.append(unit['run_id'])
            counts[unit['run_id']] = len(group)
        else:
            official = code / 'benchmarks/vlnverse/upstream/logs' / unit['run_id'] / 'kujiale_result.json'
            try:
                counts[unit['run_id']] = json.loads(official.read_text())['val_unseen']['Count']
            except (FileNotFoundError, json.JSONDecodeError):
                counts[unit['run_id']] = 0
        assert 0 <= counts[unit['run_id']] <= unit['expected']
    summary = dict(condition=arm, expected=sum(u['expected'] for u in config['units']), scored=sum(counts.values()), validated=len(rows),
                   validated_falls=sum(r['fail_reason'] == 'fall' for r in rows),
                   validated_success=sum(r['SR'] > 0 for r in rows), complete_units=complete,
                   counts=counts, updated_at=now())
    if arm == 'replay':
        diagnostics = [r['replay'] for r in rows]
        reached = [r for r in diagnostics if r['checkpoint_reached']]
        summary.update(cohort_total=41, inapplicable=1,
                       checkpoint_reached=len(reached),
                       falls_before_checkpoint=sum(r['outcome'] == 'fall_before_checkpoint' for r in diagnostics),
                       falls_after_checkpoint=sum(r['outcome'] == 'fall_after_checkpoint' for r in reached),
                       checkpoints_within_0_5m=sum(r['checkpoint']['within_0_5m'] for r in reached),
                       falls_within_10_actions_after_checkpoint=sum(r['fall_within_10_actions_after_checkpoint'] for r in reached))
    write_json(campaign / f'summary_{arm}.json', summary)
    write_json(campaign / f'results_{arm}.json', rows)
    return summary


def unlocked(gpu):
    with Path(f'/tmp/peng_vlnverse_gpu_{gpu}.lock').open('a') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


def process_alive(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] not in ('Z', 'X')
    except FileNotFoundError:
        return False


def admission_failure(failure):
    """A runner losing the GPU flock race has not executed a navigation trial."""
    text = failure.get('log_tail', '')
    if (failure.get('phase') == 'launcher' and 'fcntl.flock(lock,' in text
            and 'BlockingIOError: [Errno 11]' in text):
        return dict(failure, kind='gpu_admission', admission_reason='gpu_lock_contention')
    return failure


def campaign_worker_pids(campaign):
    pids = set()
    for arm in ('reset', 'replay'):
        path = campaign / f'status_{arm}.json'
        if path.exists():
            pids.update(w['pid'] for w in json.loads(path.read_text()).get('workers', []))
    ledger = campaign / 'admitted_workers.json'
    if ledger.exists():
        pids.update(json.loads(ledger.read_text())['pids'])
    return {pid for pid in pids if process_alive(pid)}


def run(campaign, arm, maximum):
    manifest = json.loads((campaign / 'manifest.json').read_text())
    config = manifest[arm]
    code = Path(config['code_root'])
    for name, expected in config['code_sha256'].items():
        if sha(code / name) != expected:
            raise RuntimeError('Experiment code changed: ' + name)
    for row in json.loads((campaign / 'model_fingerprints.json').read_text())['files']:
        stat = Path(row['path']).stat()
        assert (stat.st_size, stat.st_mtime_ns, stat.st_ino) == (row['bytes'], row['mtime_ns'], row['inode'])
    lock = (campaign / f'{arm}.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = dict(os.environ, **config['runtime_env'])
    # This is entirely offline. Do not inherit proxy routing or record credentials.
    env = {k: v for k, v in env.items() if not k.lower().endswith('_proxy')}
    launches = campaign / f'launches_{arm}'
    launches.mkdir(exist_ok=True)
    active, steady, retries, delayed, blocked = {}, {}, {}, {}, {}
    separate = {'kujiale_0234'}
    status = dict(condition=arm, supervisor_pid=os.getpid(), started_at=now())
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    gate = campaign / f'gate_{arm}.json'
    try:
        while True:
            for index, worker in list(active.items()):
                if worker['process'].poll() is None:
                    continue
                worker['log'].close()
                del active[index]
                unit = config['units'][index]
                if worker['process'].returncode:
                    failure = admission_failure(worker_failure(run_path(config, unit) / 'failure.json', worker['log_path'], worker['process'].returncode))
                    retries[index] = retries.get(index, 0) + 1
                    delay = retry_delay(failure['kind'], retries[index])
                    if needs_separate_gpus(failure):
                        separate.add(unit['scene'])
                    if delay is None:
                        blocked[index] = failure
                    else:
                        delayed[index] = time.monotonic() + delay
                    print(json.dumps(dict(event='worker_failed', unit=index, retry_seconds=delay, failure=failure)), flush=True)
            summary = collect(campaign, arm, config)
            if config['units'][0]['run_id'] in summary['complete_units'] and not gate.exists():
                write_json(gate, dict(passed=True, episode_ids=config['units'][0]['episode_ids'], checked_at=now()))
            pending = [i for i, u in enumerate(config['units']) if u['run_id'] not in summary['complete_units']
                       and i not in active and i not in blocked]
            resources = gpu_rows()
            busy = {g for w in active.values() for g in (w['gpu'], w['sim_gpu'])}
            free = [r for r in resources if r['index'] not in busy and r['utilization'] <= 15 and unlocked(r['index'])]
            steady = {r['index']: steady.get(r['index'], 0) + 1 for r in free}
            ready = [r for r in free if steady[r['index']] >= 2]
            for index in pending:
                if not can_admit_worker(len(active), maximum, available_memory_mib()):
                    break
                if not gate.exists() and (index != 0 or active):
                    continue
                if time.monotonic() < delayed.get(index, 0):
                    continue
                unit = config['units'][index]
                # Serialize admission across both arms, then refresh every GPU and
                # global host-memory accounting while holding that shared lock.
                with (campaign / 'admission.lock').open('a') as admission:
                    try:
                        fcntl.flock(admission, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue
                    live_pids = campaign_worker_pids(campaign) | {w['process'].pid for w in active.values()}
                    if not can_admit_worker(len(live_pids), maximum, available_memory_mib()):
                        continue
                    ledger_path = campaign / 'admitted_workers.json'
                    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
                    reservations = [w for w in ledger.get('workers', []) if process_alive(w['pid'])]
                    reserved_gpus = {g for w in reservations for g in (w['gpu'], w['sim_gpu'])}
                    ready_ids = {r['index'] for r in ready}
                    fresh = [r for r in gpu_rows() if r['index'] in ready_ids and r['index'] not in reserved_gpus and unlocked(r['index'])]
                    pair = placement(fresh, None, busy, unit['scene'] in separate)
                    if pair is None:
                        continue
                    gpu, sim_gpu = pair
                    path = run_path(config, unit)
                    command = [sys.executable, str(code / 'benchmarks/vlnverse/runner/run_full.py'),
                               '--method', 'StreamVLN', '--mode', 'physical', '--seed', '2',
                               '--gpu', str(gpu), '--sim-gpu', str(sim_gpu), '--episode-ids', *unit['episode_ids'],
                               '--allow-shared-gpu', '--resume' if (path / 'run.json').exists() else '--run-id', unit['run_id']]
                    failure = path / 'failure.json'
                    if failure.exists():
                        failure.rename(path / f'failure_{time.time_ns()}.json')
                    log_path = launches / f'{unit["run_id"]}_{time.time_ns()}.log'
                    log = log_path.open('w')
                    worker_env = dict(env, VLN_SIM_CACHE_ROOT=str(campaign / 'sim_cache' / f'gpu_{sim_gpu}'))
                    process = subprocess.Popen(command, cwd=code, env=worker_env, stdout=log,
                                               stderr=subprocess.STDOUT, start_new_session=True)
                    active[index] = dict(process=process, log=log, log_path=str(log_path), gpu=gpu, sim_gpu=sim_gpu)
                    reservations.append(dict(pid=process.pid, gpu=gpu, sim_gpu=sim_gpu, condition=arm, unit=index))
                    write_json(ledger_path, dict(pids=sorted(live_pids | {process.pid}), workers=reservations, updated_at=now()))
                    # Keep admission serialized until the child owns its GPU locks.
                    # On slow startup, stop admitting new work instead of racing it.
                    deadline = time.monotonic() + 20
                    while process.poll() is None and any(unlocked(g) for g in set(pair)):
                        if time.monotonic() >= deadline:
                            print(json.dumps(dict(event='awaiting_worker_gpu_lock', pid=process.pid,
                                                  gpu=gpu, sim_gpu=sim_gpu)), flush=True)
                            break  # The shared ledger keeps these GPUs reserved.
                        time.sleep(0.2)
                    print(json.dumps(dict(event='started', condition=arm, unit=index, episodes=unit['episode_ids'],
                                          gpu=gpu, sim_gpu=sim_gpu, pid=process.pid)), flush=True)
                break  # Re-read every card and host RAM before each additional launch.
            if 0 in blocked and not gate.exists():
                # A failed initial gate must not leave later tasks waiting forever.
                pending = []
            status.update(status='complete' if summary['validated'] == summary['expected'] else
                          'running' if active else 'blocked' if blocked and not pending else 'waiting_for_resources',
                          **{k: summary[k] for k in ('scored', 'validated', 'validated_falls', 'validated_success')},
                          workers=[dict(unit=i, pid=w['process'].pid, gpu=w['gpu'], sim_gpu=w['sim_gpu'], log=w['log_path']) for i, w in active.items()],
                          pending_units=sum(i not in active for i in pending), blocked_units=blocked, gpu_snapshot=resources,
                          updated_at=now(), available_memory_mib=available_memory_mib())
            write_json(campaign / f'status_{arm}.json', status)
            if not pending and not active:
                break
            time.sleep(10)
    except BaseException as error:
        status.update(status='stopped' if isinstance(error, KeyboardInterrupt) else 'failed', error=str(error), updated_at=now())
        raise
    finally:
        for worker in active.values():
            if worker['process'].poll() is None:
                os.killpg(worker['process'].pid, signal.SIGTERM)
                worker['process'].wait(timeout=60)
            worker['log'].close()
        write_json(campaign / f'status_{arm}.json', status)
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'prepare-replay', 'run', 'status'])
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--arm', choices=['reset', 'replay'], default='reset')
    parser.add_argument('--max-workers', type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.max_workers <= 8:
        parser.error('max-workers must be between 1 and 8')
    if args.action == 'prepare':
        if args.source is None:
            parser.error('prepare requires source')
        prepare(args.source.resolve(), args.campaign.resolve())
    elif args.action == 'prepare-replay':
        prepare_replay(args.campaign.resolve())
    elif args.action == 'run':
        run(args.campaign.resolve(), args.arm, args.max_workers)
    else:
        print((args.campaign / f'status_{args.arm}.json').read_text())
