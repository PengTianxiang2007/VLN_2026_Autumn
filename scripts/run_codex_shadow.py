"""Read-only JEV and Codex consumers for live native navigation captures."""
import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.codex_client import CodexConfig, now, save
from core.codex_shadow_retry import retry_wait


def read(path):
    return json.loads(path.read_text())


def append(path, record):
    with path.open('a') as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + '\n')


def alive(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split(') ')[1][0] != 'Z'
    except FileNotFoundError:
        return False


def records(folder, filename, done, nav_pid):
    """Tail only committed lines. An atomic completion marker follows the last append."""
    path, offset = folder / filename, 0
    while True:
        finished = (folder / done).is_file()
        if path.exists():
            with path.open('rb') as stream:
                stream.seek(offset)
                for line in stream:
                    if not line.endswith(b'\n'):
                        break
                    offset += len(line)
                    yield json.loads(line)
        if finished:
            return
        if not (folder / 'navigation.json').exists() and (
            not alive(nav_pid) or any(p.name > folder.name for p in folder.parent.glob('attempt_*'))
        ):
            raise RuntimeError('Navigation attempt ended before the terminal observation was committed')
        time.sleep(0.5)


def endpoint_node(number, name, frame, ready, fronts, offsets):
    images = []
    for delta in offsets:
        i = frame + delta
        image = dict(frame=i, label='F0' if not delta else f'F{delta:+d}')
        if i < 0:
            image['missing'] = True
        else:
            image.update(path=fronts[i]['image'], image_id=fronts[i]['sha256'])
        images.append(image)
    return dict(id=name, index=frame, emittedAt=ready, ready_at_frame=ready,
                candidate_id=f'C{number:02d}:{name}:F{frame}', images=images)


def score_frame(request):
    from core.jev_request_runner import run_jev_task
    f = request['frame']
    folder = Path(request['output'])/'cases'/request['episode_id']/f'F{f:06d}'
    cache = folder/'result.json'
    log = folder/'retries.jsonl'
    folder.mkdir(exist_ok=True, parents=True)
    old_attempts = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    attempt = len(old_attempts)
    failed_seconds = sum(row['latency_seconds'] for row in old_attempts)
    while True:
        if cache.exists():
            answer = read(cache)
            if (answer['phase'] != 'complete' or answer['episode_id'] != request['episode_id']
                    or answer['frame'] != f or answer['image_frames'] != [im['frame'] for im in request['images']]):
                raise ValueError(f'Inconsistent JEV cache at F{f}')
        else:
            answer = run_jev_task(request)
        if answer['phase'] == 'complete':
            return dict(answer, failed_request_seconds=failed_seconds, failed_attempts=attempt)
        attempt += 1
        failed_seconds += answer['latency_seconds']
        retry_wait(log, attempt, answer['error'], frame=f, latency_seconds=answer['latency_seconds'])


def score(folder, number, nav_pid, requests):
    task = read(folder / 'start.json')
    fronts, pending, history = {}, deque(), deque(maxlen=3)
    # The local numerical sampler only receives scores on standard input.
    env = {key: val for key, val in os.environ.items() if key != 'JEV_API_KEY'}
    node = subprocess.Popen(['node', str(ROOT/'scripts/jev_sampler_stdio.cjs')], env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    def send(message):
        node.stdin.write(json.dumps(message)+'\n')
        node.stdin.flush()
        response = json.loads(node.stdout.readline())
        if 'error' in response:
            raise RuntimeError(response['error'])
        return response
    calls, seconds, candidates = 0, 0.0, 0
    calls_log = folder/'jev_calls.jsonl'
    points_log = folder/'candidates.jsonl'
    recorded = {r['frame']:r for r in map(json.loads,calls_log.read_text().splitlines())
                if r['phase']=='complete'} if calls_log.exists() else {}
    points = {r['id']:r for r in map(json.loads,points_log.read_text().splitlines())} if points_log.exists() else {}
    def resolve():
        nonlocal calls, seconds, candidates
        f, future = pending.popleft()
        answer = future.result()
        if f not in recorded:
            append(calls_log, answer)
        elif recorded[f]['answer'] != answer['answer']:
            raise ValueError(f'Saved JEV score differs at F{f}')
        seconds += answer['latency_seconds'] + answer.get('failed_request_seconds', 0)
        calls += 1
        raw = send(dict(value=answer['answer']['probability_yes'], frame=f)).get('node')
        if raw:
            point = endpoint_node(number, raw['id'], raw['index'], f, fronts, (-2,0,2))
            point.update(sampling=raw, published_at=now())
            if point['id'] not in points:
                append(points_log, point)
            elif points[point['id']]['sampling'] != raw:
                raise ValueError('Existing JEV candidate differs on replay')
            candidates += 1
    try:
        send(dict(reset=True, version='v002', mode='active'))
        for row in records(folder, 'observations.jsonl', 'navigation.json', nav_pid):
            f = row['step']
            if f != len(fronts):
                raise ValueError('Nonconsecutive observation stream')
            front = fronts[f] = row['native_front']
            if row['terminal']:
                break
            history.append(dict(frame=f, rgb=front['image'], rgb_sha256=front['sha256']))
            request = dict(episode_id=task['episode_id'], scene=task['scene'], group='live_shadow',
                           frame=f, images=list(history), question_version='v004', dataset=str(folder),
                           output=str(folder/'jev'), model='jev-1.14.0', attempts=1, timeout=120,
                           endpoint='https://api.easyjev.online/v1/systemone')
            pending.append((f,requests.submit(score_frame,request)))
            if len(pending) >= 5:
                resolve()
        while pending:
            resolve()
        while not (folder/'navigation.json').exists():
            if not alive(nav_pid):
                raise RuntimeError('Missing final navigation record')
            time.sleep(0.5)
        terminal = read(folder/'navigation.json').get('terminal_frame')
        if terminal is None or terminal != calls or terminal not in fronts:
            raise RuntimeError('Missing or inconsistent native terminal RGB')
        return dict(calls=calls, jev_request_seconds=seconds, candidates=candidates, terminal_frame=terminal)
    finally:
        node.stdin.close()
        node.wait(timeout=10)


def review(folder, number, nav_pid, requests):
    from core.codex_checkpoint_review import DIRECTIONAL_REVISION, MODE, run_case
    from core.codex_deviation_review import FrameGapSampler, TERMINAL_VERSION
    start = read(folder/'start.json')
    fronts = {}
    case = dict(case_number=number, episode_id=start['episode_id'], nodes=[], mode=MODE,
                instruction_en=start['instruction'], prompt_revision=DIRECTIONAL_REVISION,
                observation_offsets=[-2,0,2], deviation_review=TERMINAL_VERSION, max_frame_gap=6)
    sampler = FrameGapSampler(folder, case['episode_id'], 6, live_fronts=fronts)
    def update_fronts(through):
        with (folder/'observations.jsonl').open() as stream:
            for line in stream:
                row = json.loads(line)
                fronts[row['step']] = row['native_front']
                if row['step'] == through:
                    return
        raise ValueError(f'Missing capture F{through}')
    def candidates():
        for node in records(folder, 'candidates.jsonl', 'score.json', nav_pid):
            update_fronts(node['ready_at_frame'])
            yield node
        scoring = read(folder/'score.json')
        if scoring['status'] != 'complete':
            raise RuntimeError(scoring['error'])
        end = scoring['terminal_frame']
        update_fronts(end)
        case['terminal_node'] = endpoint_node(number, 'END', end, end, fronts, (0,))
        case['terminal_node']['terminal_node'] = True
    cfg = CodexConfig(model='gpt-6-astra', timeout_seconds=1800, proxy_url='http://127.0.0.1:17982')
    dest = folder/'review'
    result = run_case(case, folder, dest, cfg, candidate_stream=candidates(), live_sampler=sampler)
    checkpoint_time = deviation_time = 0.0
    for p in sorted((dest/'codex/turns').glob('*/response.json')):
        turn = read(p)
        if '_deviation_' in p.parent.name or 'terminal_observation' in p.parent.name:
            deviation_time += turn['elapsed_seconds']
        else:
            checkpoint_time += turn['elapsed_seconds']
    timing = dict(checkpoint_request_seconds=checkpoint_time, deviation_request_seconds=deviation_time,
                  rollback_target=result['rollback_target'], stop_reason=result['stop_reason'])
    if result['rollback_target']:
        r = result['deviation_reviews'][-1]
        turn = next((dest/'codex/turns').glob(f"turn_{r['turn']:04d}_*/response.json"))
        when = read(turn)['completed_at']
        timing.update(first_alarm_at=when, interval=[r['previous_frame'],r['current_frame']],
                      rollback_frame=r['previous_frame'], first_alarm_elapsed_seconds=(
                          datetime.fromisoformat(when)-datetime.fromisoformat(start['started_at'])).total_seconds())
    return timing


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['score','review'])
    parser.add_argument('output', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    out=args.output.resolve()
    role_lock=(out/(args.role+'.lock')).open('a')
    fcntl.flock(role_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.role == 'score':
        token = sys.stdin.readline().strip()
        if not token:
            raise ValueError('Missing JEV credential on private input pipe')
        os.environ['JEV_API_KEY'] = token
    launch=read(out/'launch.json')
    nav_pid=launch['nav_pid']
    eids=read(args.manifest)['episode_ids']
    func=score if args.role=='score' else review
    def handle(folder, pool):
        tick = time.monotonic()
        try:
            values=func(folder,eids.index(folder.parent.name)+1,nav_pid,pool)
            result=dict(status='complete',**values)
        except Exception as err:
            result=dict(status='error',error=f'{type(err).__name__}: {err}')
        result.update(finished_at=now(),wall_seconds=time.monotonic()-tick)
        save(folder/(args.role+'.json'),result)
        print(folder.parent.name, result, flush=True)
    seen=set()
    capture=out/'captures'
    with ThreadPoolExecutor(max_workers=8) as cases, ThreadPoolExecutor(max_workers=16) as requests:
        while True:
            nav_running=alive(nav_pid)
            for start in sorted(capture.glob('*/*/start.json')):
                folder=start.parent
                if folder not in seen and not (folder/(args.role+'.json')).exists():
                    cases.submit(handle,folder,requests)
                seen.add(folder)
            if not nav_running:
                break
            time.sleep(2)
        cases.shutdown(wait=True)
    finished={}; errors=[]
    for eid in eids:
        attempts=sorted((capture/eid).glob('attempt_*/navigation.json'))
        if attempts:
            result=attempts[-1].parent/(args.role+'.json')
            if result.exists() and read(result)['status']=='complete':
                finished[eid]=read(result)
                continue
        errors.append(eid)
    save(out/(args.role+'_summary.json'),dict(finished_at=now(),completed=len(finished),technical_incomplete=errors,
            batch_wall_seconds=time.time()-launch['started_unix'], episodes=finished))


if __name__=='__main__':
    main()
