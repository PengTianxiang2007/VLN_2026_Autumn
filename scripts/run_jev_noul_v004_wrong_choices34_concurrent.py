"""Run the 34 human-labeled wrong choices through JEV v004.

Existing v004 answers are reused only when a freshly rebuilt request has the
same SHA256 as the stored result. All missing points are submitted together;
the requested concurrency is an upper bound and is never exceeded.
"""
import argparse
import concurrent.futures
import getpass
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import now, read, write
from core.crossing_lite import windows
from core.jev_node import (
    build_compact_fallback_noul_request,
    call_api,
    request_digest,
    request_without_images,
    validate_noul_response,
)

DATASET = (
    ROOT
    / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01'
    / 'crossing_seed2_human_v001'
)
QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'
REUSE_RUNS = (
    ROOT / 'outputs/crossing_checkpoint/jev_noul_v004/run_20261108_01_two_cases',
    ROOT / 'outputs/crossing_checkpoint/jev_noul_v004/run_20261108_03_ten_final',
)
MODEL = 'jev-1.14.0'
DEFAULT_ENDPOINT = 'https://api.site/v1/systemone'
EXPECTED_EVENTS = 34
REQUESTED_CONCURRENCY_LIMIT = 500


def sha(path):
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_events():
    rows = [
        json.loads(line)
        for line in (DATASET / 'evaluation/events.jsonl').read_text().splitlines()
        if line.strip()
    ]
    events = [row for row in rows if row.get('type') == 'wrong_choice']
    keys = [(row['episode_id'], row['frame']) for row in events]
    if len(events) != EXPECTED_EVENTS:
        raise ValueError('Expected 34 wrong choices, got %d' % len(events))
    if len(keys) != len(set(keys)):
        raise ValueError('Wrong-choice keys are not unique')
    return events


def load_qwen_scores():
    rows = read(QWEN_RUN / 'annotated_point_scores.json')
    by_event = {row['event_id']: row for row in rows}
    by_key = {(row['episode_id'], row['frame']): row for row in rows}
    if len(by_event) != 128 or len(by_key) != 128:
        raise ValueError('Expected 128 unique Qwen annotated point scores')
    return by_event, by_key


def prepare_events():
    events = load_events()
    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    qwen_by_event, qwen_by_key = load_qwen_scores()
    prepared = []
    for event in events:
        episode = episodes[event['episode_id']]
        observations = read(DATASET / episode['observations'])
        frame_windows = dict(windows(observations))
        if event['frame'] not in frame_windows:
            raise ValueError(
                '%s F%d is not eligible for inference'
                % (event['episode_id'], event['frame'])
            )
        images = frame_windows[event['frame']]
        request, image_audit = build_compact_fallback_noul_request(
            images, DATASET, model=MODEL
        )
        qwen = qwen_by_event.get(event['id']) or qwen_by_key.get(
            (event['episode_id'], event['frame'])
        )
        if not qwen or qwen.get('type') != 'wrong_choice':
            raise ValueError('Missing Qwen score for event ' + event['id'])
        prepared.append({
            'event_id': event['id'],
            'episode_id': event['episode_id'],
            'scene': event['scene'],
            'frame': event['frame'],
            'position': event['position'],
            'rgb': event['rgb'],
            'image_sha256': event['image_sha256'],
            'images': images,
            'image_frames': [row['frame'] for row in images],
            'request_sha256': request_digest(request),
            'request_audit': request_without_images(request),
            'image_audit': image_audit,
            'qwen_score': qwen['score'],
            'instruction_en': episode['instruction'],
            'instruction_zh': episode['instruction_zh'],
        })
    return prepared


def find_reusable(prepared):
    stored = {}
    for run in REUSE_RUNS:
        path = run / 'rows_v004.json'
        if not path.exists():
            continue
        for row in read(path):
            if row.get('phase') != 'complete':
                continue
            if row.get('question_version') != 'v004':
                continue
            key = (row['episode_id'], row['frame'])
            value = {
                'answer': row['answer'],
                'request_sha256': row['request_sha256'],
                'latency_seconds': row.get('latency_seconds'),
                'transport': row.get('transport'),
                'source_run': str(run),
                'source_row': row,
            }
            previous = stored.get(key)
            if previous and previous['request_sha256'] != value['request_sha256']:
                raise ValueError('Conflicting reuse request hashes for %r' % (key,))
            stored[key] = value

    reusable = {}
    for item in prepared:
        row = stored.get((item['episode_id'], item['frame']))
        if row and row['request_sha256'] == item['request_sha256']:
            reusable[item['event_id']] = row
    return reusable


def run_task(task):
    """One event, one v004 Noul request, one isolated result directory."""
    key = os.environ.get('JEV_API_KEY', '')
    if not key:
        return dict(**task, phase='failed', error='JEV_API_KEY is missing')
    folder = Path(task['output']) / 'events' / task['event_id']
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / 'request.json', {
        **task['request_audit'],
        'request_sha256': task['request_sha256'],
        'question_version': 'v004',
    })
    write(folder / 'images.json', task['image_audit'])
    started = time.monotonic()
    try:
        request, rebuilt_audit = build_compact_fallback_noul_request(
            task['images'], DATASET, model=MODEL
        )
        if request_digest(request) != task['request_sha256']:
            raise ValueError('Request changed after task preparation')
        if rebuilt_audit != task['image_audit']:
            raise ValueError('Image audit changed after task preparation')
        raw, latency, transport = call_api(
            task['endpoint'],
            key,
            request,
            task['timeout'],
            folder / 'request_full.json',
            attempts=task['attempts'],
        )
        answer = validate_noul_response(raw)
        record = {
            'phase': 'complete',
            'event_id': task['event_id'],
            'episode_id': task['episode_id'],
            'scene': task['scene'],
            'frame': task['frame'],
            'position': task['position'],
            'rgb': task['rgb'],
            'image_frames': task['image_frames'],
            'qwen_score': task['qwen_score'],
            'jev_probability_yes': answer['probability_yes'],
            'jev_probability_no': answer['probability_no'],
            'answer': answer,
            'request_sha256': task['request_sha256'],
            'question_version': 'v004',
            'model': MODEL,
            'endpoint': task['endpoint'],
            'latency_seconds': latency,
            'transport': transport,
            'provenance': 'new_call',
        }
        write(folder / 'response.json', raw)
        write(folder / 'result.json', record)
        return record
    except Exception as error:
        record = {
            'phase': 'failed',
            'event_id': task['event_id'],
            'episode_id': task['episode_id'],
            'scene': task['scene'],
            'frame': task['frame'],
            'position': task['position'],
            'rgb': task['rgb'],
            'image_frames': task['image_frames'],
            'qwen_score': task['qwen_score'],
            'request_sha256': task['request_sha256'],
            'question_version': 'v004',
            'model': MODEL,
            'endpoint': task['endpoint'],
            'latency_seconds': time.monotonic() - started,
            'provenance': 'new_call',
            'error': str(error).replace(key, '[REDACTED]'),
        }
        write(folder / 'error.json', record)
        return record


def reused_record(item, stored, output):
    folder = Path(output) / 'events' / item['event_id']
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / 'request.json', {
        **item['request_audit'],
        'request_sha256': item['request_sha256'],
        'question_version': 'v004',
    })
    write(folder / 'images.json', item['image_audit'])
    write(folder / 'reuse_source.json', stored)
    record = {
        'phase': 'complete',
        'event_id': item['event_id'],
        'episode_id': item['episode_id'],
        'scene': item['scene'],
        'frame': item['frame'],
        'position': item['position'],
        'rgb': item['rgb'],
        'image_frames': item['image_frames'],
        'qwen_score': item['qwen_score'],
        'jev_probability_yes': stored['answer']['probability_yes'],
        'jev_probability_no': stored['answer']['probability_no'],
        'answer': stored['answer'],
        'request_sha256': item['request_sha256'],
        'question_version': 'v004',
        'model': MODEL,
        'endpoint': stored['source_row'].get('endpoint', 'https://api.site/v1/systemone'),
        'latency_seconds': stored['latency_seconds'],
        'transport': stored['transport'],
        'provenance': 'reused_exact_request',
        'reuse_source_run': stored['source_run'],
    }
    write(folder / 'result.json', record)
    return record


def summarize(rows, reusable_count, new_count, workers):
    complete = [row for row in rows if row.get('phase') == 'complete']
    failures = [row for row in rows if row.get('phase') != 'complete']
    probabilities = [
        row['jev_probability_yes'] for row in complete
        if row.get('jev_probability_yes') is not None
    ]
    return {
        'phase': 'complete' if len(complete) == EXPECTED_EVENTS else 'complete_with_failures',
        'events': len(rows),
        'expected_events': EXPECTED_EVENTS,
        'complete_events': len(complete),
        'failed_events': len(failures),
        'reused_events': reusable_count,
        'new_calls_requested': new_count,
        'requested_concurrency_limit': REQUESTED_CONCURRENCY_LIMIT,
        'actual_max_workers': workers,
        'model': MODEL,
        'question_version': 'v004',
        'mean_jev_probability': (
            sum(probabilities) / len(probabilities) if probabilities else None
        ),
        'mean_qwen_score': (
            sum(row['qwen_score'] for row in complete) / len(complete)
            if complete else None
        ),
        'qwen_score_counts': dict(Counter(
            str(row['qwen_score']) for row in complete
        )),
        'jev_probability_bands': {
            band: sum(
                lower <= probability < upper
                for probability in probabilities
                for lower, upper in [(
                    float(band.split('-')[0]) / 10,
                    (int(band.split('-')[1]) + 1) / 10,
                )]
            )
            for band in ('0-1', '2-3', '4-5', '6-7', '8-9')
        },
        'transport_attempt_histogram': dict(Counter(
            row.get('transport', {}).get('attempts')
            for row in complete
        )),
        'failed_event_ids': [row['event_id'] for row in failures],
        'credential_on_disk': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--concurrency', type=int, default=REQUESTED_CONCURRENCY_LIMIT)
    parser.add_argument('--attempts', type=int, default=5)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.concurrency != REQUESTED_CONCURRENCY_LIMIT:
        raise ValueError('This run requires --concurrency 500')
    if not 1 <= args.attempts <= 5:
        raise ValueError('Attempts must be from 1 to 5')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory')

    prepared = prepare_events()
    reusable = find_reusable(prepared)
    missing = [item for item in prepared if item['event_id'] not in reusable]
    workers = min(args.concurrency, len(missing)) if missing else 1

    output.mkdir(parents=True)
    for relative in (
        'scripts/run_jev_noul_v004_wrong_choices34_concurrent.py',
        'core/jev_node.py',
        'core/crossing_lite.py',
    ):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    write(output / 'prepared_events.json', prepared)
    write(output / 'reuse_audit.json', reusable)
    write(output / 'missing_event_ids.json', [row['event_id'] for row in missing])
    write(output / 'manifest.json', {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'dataset': str(DATASET),
        'dataset_events_sha256': sha(DATASET / 'evaluation/events.jsonl'),
        'qwen_run': str(QWEN_RUN),
        'qwen_scores_sha256': sha(QWEN_RUN / 'annotated_point_scores.json'),
        'events': len(prepared),
        'reused_events': len(reusable),
        'new_calls': len(missing),
        'requested_concurrency_limit': args.concurrency,
        'actual_max_workers': workers,
        'all_missing_tasks_submitted_together': True,
        'attempts': args.attempts,
        'timeout_seconds': args.timeout,
        'endpoint': args.endpoint,
        'model': MODEL,
        'question_version': 'v004',
        'credential_on_disk': False,
        'protocol': (
            'Human-labeled wrong choices only (34). Exact t-2,t-1,t RGB; one '
            'self-contained v004 Noul per location; exact request SHA256 required '
            'for reuse; no task, action, position, map, label, outcome, reference '
            'route, or prior answer in the model request.'
        ),
    })
    write(output / 'workspace_status.txt', subprocess.check_output(
        ['git', 'status', '--short'], cwd=ROOT, text=True
    ))
    write(output / 'status.json', {
        'phase': 'prepared',
        'prepared_at': now(),
        'total': EXPECTED_EVENTS,
        'reused': len(reusable),
        'to_call': len(missing),
        'actual_max_workers': workers,
    })
    print(json.dumps({
        'events': len(prepared),
        'reused': len(reusable),
        'missing': len(missing),
        'actual_max_workers': workers,
        'prepare_only': args.prepare_only,
    }, ensure_ascii=False, indent=2))
    if args.prepare_only:
        return

    key = os.environ.get('JEV_API_KEY', '')
    if not key:
        key = (
            getpass.getpass('JEV API key: ')
            if sys.stdin.isatty()
            else sys.stdin.readline()
        )
    key = key.strip()
    if not key:
        raise RuntimeError('A bearer key is required')
    os.environ['JEV_API_KEY'] = key

    rows = [
        reused_record(item, reusable[item['event_id']], output)
        for item in prepared if item['event_id'] in reusable
    ]
    tasks = []
    for item in missing:
        tasks.append({
            **item,
            'output': str(output),
            'endpoint': args.endpoint,
            'timeout': args.timeout,
            'attempts': args.attempts,
        })
    started_at = now()
    write(output / 'status.json', {
        'phase': 'running',
        'started_at': started_at,
        'completed': len(rows),
        'total': len(prepared),
        'reused': len(rows),
        'in_flight_batch': len(tasks),
        'actual_max_workers': workers,
    })

    if tasks:
        context = multiprocessing.get_context('spawn')
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=context
        ) as executor:
            futures = {executor.submit(run_task, task): task for task in tasks}
            for index, future in enumerate(
                concurrent.futures.as_completed(futures), 1
            ):
                task = futures[future]
                try:
                    row = future.result()
                except BaseException as error:
                    row = {
                        'phase': 'failed',
                        **{
                            key_name: task[key_name]
                            for key_name in (
                                'event_id', 'episode_id', 'scene', 'frame',
                                'position', 'rgb', 'image_frames', 'qwen_score',
                                'request_sha256'
                            )
                        },
                        'error': type(error).__name__ + ': ' + str(error).replace(
                            key, '[REDACTED]'
                        ),
                    }
                rows.append(row)
                write(output / 'status.json', {
                    'phase': 'running',
                    'started_at': started_at,
                    'updated_at': now(),
                    'completed': len(rows),
                    'total': len(prepared),
                    'new_completed': index,
                    'new_total': len(tasks),
                    'complete': sum(row.get('phase') == 'complete' for row in rows),
                    'failed': sum(row.get('phase') != 'complete' for row in rows),
                    'actual_max_workers': workers,
                })

    order = {row['event_id']: index for index, row in enumerate(prepared)}
    rows.sort(key=lambda row: order[row['event_id']])
    summary = summarize(rows, len(reusable), len(missing), workers)
    summary.update({
        'started_at': started_at,
        'finished_at': now(),
        'output': str(output),
    })
    write(output / 'rows.json', rows)
    write(output / 'summary.json', summary)
    write(output / 'status.json', summary)
    os.environ.pop('JEV_API_KEY', None)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
