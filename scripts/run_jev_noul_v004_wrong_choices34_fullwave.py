"""Score all eligible frames for the 33 episodes containing wrong choices."""
import argparse
import concurrent.futures
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
sys.path.insert(0, str(ROOT / 'scripts'))
from core.agent_route_choice import now, read, write
from core.crossing_lite import windows
from core.jev_node import (
    build_compact_fallback_noul_request,
    request_digest,
    request_without_images,
    validate_noul_response,
    call_api,
)
from run_jev_noul_five_concurrent import run_task

DATASET = (
    ROOT
    / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01'
    / 'crossing_seed2_human_v001'
)
POINT_RUN = (
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v004'
    / 'run_20261109_03_wrong_choices34_prevapi'
)
REUSE_RUNS = (
    ROOT / 'outputs/crossing_checkpoint/jev_noul_v004/run_20261108_01_two_cases',
    ROOT / 'outputs/crossing_checkpoint/jev_noul_v004/run_20261108_03_ten_final',
    POINT_RUN,
)
MODEL = 'jev-1.14.0'
ENDPOINT = 'https://api.site/v1/systemone'


def existing_rows():
    rows = {}
    for run in REUSE_RUNS:
        path = run / 'rows_v004.json'
        if not path.exists():
            path = run / 'rows.json'
        if not path.exists():
            continue
        for row in read(path):
            if row.get('phase') != 'complete':
                continue
            if row.get('question_version') != 'v004':
                continue
            key = (row['episode_id'], row['frame'])
            value = {
                **row,
                'source_run': str(run),
            }
            previous = rows.get(key)
            if previous and previous['request_sha256'] != value['request_sha256']:
                raise ValueError('Conflicting existing request hashes for %r' % (key,))
            rows[key] = value
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--concurrency', type=int, default=500)
    parser.add_argument('--attempts', type=int, default=5)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 500:
        raise ValueError('Concurrency must be between 1 and 500')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory')
    if not os.environ.get('JEV_API_KEY'):
        raise ValueError('Set JEV_API_KEY in the parent process')

    point_rows = read(POINT_RUN / 'rows.json')
    if len(point_rows) != 34:
        raise ValueError('Expected 34 point rows')
    episode_ids = sorted({row['episode_id'] for row in point_rows})
    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    scenes = {row['episode_id']: row['scene'] for row in point_rows}
    previous = existing_rows()

    cases = []
    tasks = []
    reused = []
    for episode_id in episode_ids:
        observations = read(DATASET / episodes[episode_id]['observations'])
        frame_windows = list(windows(observations))
        cases.append({
            'episode_id': episode_id,
            'scene': scenes[episode_id],
            'eligible': len(frame_windows),
        })
        for frame, images in frame_windows:
            task = {
                'episode_id': episode_id,
                'scene': scenes[episode_id],
                'group': 'failure',
                'frame': frame,
                'images': images,
                'question_version': 'v004',
            }
            old = previous.get((episode_id, frame))
            if old:
                request, image_audit = build_compact_fallback_noul_request(
                    images, DATASET, model=MODEL
                )
                digest = request_digest(request)
                if digest == old['request_sha256']:
                    reused.append({
                        'task': task,
                        'old': old,
                        'request_audit': request_without_images(request),
                        'request_sha256': digest,
                        'image_audit': image_audit,
                    })
                    continue
            tasks.append(task)
    expected_calls = len(tasks) + len(reused)

    output.mkdir(parents=True)
    for relative in (
        'scripts/run_jev_noul_v004_wrong_choices34_fullwave.py',
        'scripts/run_jev_noul_five_concurrent.py',
        'core/jev_node.py',
        'core/crossing_lite.py',
    ):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    write(output / 'cases.json', cases)
    write(output / 'tasks.json', tasks)
    write(output / 'reuse_audit.json', reused)
    write(output / 'manifest.json', {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'purpose': 'Full per-frame JEV v004 waveform for the 33 episodes.',
        'episodes': len(cases),
        'expected_calls': expected_calls,
        'new_calls': len(tasks),
        'reused_calls': len(reused),
        'concurrency': args.concurrency,
        'attempts': args.attempts,
        'timeout_seconds': args.timeout,
        'endpoint': ENDPOINT,
        'model': MODEL,
        'question_version': 'v004',
        'credential_on_disk': False,
        'protocol': (
            'Exact t-2,t-1,t RGB for every eligible frame in each source '
            'episode; one self-contained v004 Noul; exact request SHA256 for '
            'reuse; no task, action, position, map, label, outcome, reference '
            'route, or prior answer in the model input.'
        ),
    })
    write(output / 'status.json', {
        'phase': 'running',
        'started_at': now(),
        'completed': 0,
        'total': expected_calls,
        'new_calls': len(tasks),
        'reused_calls': len(reused),
        'concurrency': args.concurrency,
    })

    rows = []
    for item in reused:
        task = item['task']
        old = item['old']
        folder = output / 'cases' / task['episode_id'] / (
            'F%04d' % task['frame']
        )
        folder.mkdir(parents=True, exist_ok=True)
        write(folder / 'request.json', {
            **item['request_audit'],
            'request_sha256': item['request_sha256'],
            'question_version': 'v004',
        })
        write(folder / 'images.json', item['image_audit'])
        write(folder / 'reuse_source.json', old)
        row = {
            'phase': 'complete',
            **task,
            'image_frames': [image['frame'] for image in task['images']],
            'answer': old['answer'],
            'request_sha256': item['request_sha256'],
            'latency_seconds': old.get('latency_seconds'),
            'transport': old.get('transport'),
            'question_version': 'v004',
            'provenance': 'reused_exact_request',
            'reuse_source_run': old['source_run'],
        }
        write(folder / 'result.json', row)
        rows.append(row)

    for task in tasks:
        task.update(
            output=str(output),
            endpoint=ENDPOINT,
            model=MODEL,
            timeout=args.timeout,
            attempts=args.attempts,
        )
    context = multiprocessing.get_context('spawn')
    started = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(args.concurrency, max(1, len(tasks))),
        mp_context=context,
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
                        key: task[key]
                        for key in (
                            'episode_id', 'scene', 'group', 'frame', 'images',
                            'question_version'
                        )
                    },
                    'error': type(error).__name__ + ': ' + str(error),
                }
            rows.append(row)
            if index % 100 == 0 or index == len(tasks):
                write(output / 'status.json', {
                    'phase': 'running',
                    'updated_at': now(),
                    'completed': len(rows),
                    'total': expected_calls,
                    'new_completed': index,
                    'new_total': len(tasks),
                    'valid': sum(row.get('phase') == 'complete' for row in rows),
                    'failed': sum(row.get('phase') != 'complete' for row in rows),
                    'concurrency': args.concurrency,
                })

    rows.sort(key=lambda row: (row['episode_id'], row['frame']))
    complete = [row for row in rows if row.get('phase') == 'complete']
    summary = {
        'phase': (
            'complete'
            if len(complete) == expected_calls
            else 'complete_with_failures'
        ),
        'started_at': now(),
        'finished_at': now(),
        'elapsed_seconds': time.monotonic() - started,
        'episodes': len(cases),
        'expected_calls': expected_calls,
        'complete_calls': len(complete),
        'failed_calls': len(rows) - len(complete),
        'new_calls': len(tasks),
        'reused_calls': len(reused),
        'concurrency': args.concurrency,
        'mean_probability_yes': (
            sum(row['answer']['probability_yes'] for row in complete)
            / len(complete)
            if complete else None
        ),
        'transport_attempt_histogram': dict(Counter(
            row.get('transport', {}).get('attempts')
            for row in complete
        )),
        'credential_on_disk': False,
    }
    write(output / 'rows.json', rows)
    write(output / 'summary.json', summary)
    write(output / 'status.json', summary)
    os.environ.pop('JEV_API_KEY', None)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
