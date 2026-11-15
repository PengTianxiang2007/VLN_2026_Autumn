"""Run the complete human Crossing set through JEV Noul with 1000 workers."""
import argparse
import concurrent.futures
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from core.agent_route_choice import now, read, write
from core.crossing_lite import windows
from core.jev_node import (
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    build_noul_request,
    call_api,
    noul_question_translation,
    request_digest,
    request_without_images,
)
from run_jev_noul_five_concurrent import DATASET, run_task, sha

QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'
SOURCE_SELECTION = QWEN_RUN / 'evaluation_selection.json'


def baseline_from_qwen():
    result = {}
    for case in read(SOURCE_SELECTION):
        episode_id = case['episode_id']
        result[episode_id] = {}
        folder = QWEN_RUN / 'cases' / episode_id
        for path in sorted(folder.glob('F*.response.json')):
            row = read(path)
            result[episode_id][str(row['frame'])] = {
                'score': row['answer']['score'] if row.get('valid') else None,
                'answer': row.get('answer'),
                'valid': bool(row.get('valid')),
            }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--concurrency', type=int, default=1000)
    parser.add_argument('--attempts', type=int, default=5)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    args = parser.parse_args()
    if args.concurrency != 1000:
        raise ValueError('This run requires concurrency=1000')
    if not os.environ.get('JEV_API_KEY'):
        raise RuntimeError('Set JEV_API_KEY in the parent process')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory')

    selected = read(SOURCE_SELECTION)
    if len(selected) != 61:
        raise ValueError('Expected the frozen 61-case selection')
    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    baseline = baseline_from_qwen()
    tasks = []
    cases = []
    for case in selected:
        episode_id = case['episode_id']
        observations = read(DATASET / episodes[episode_id]['observations'])
        frames = []
        for frame, images in windows(observations):
            qwen = baseline[episode_id].get(str(frame))
            if not qwen or not qwen['valid']:
                raise ValueError('Missing Qwen baseline for %s F%d' % (
                    episode_id, frame
                ))
            frames.append({
                'episode_id': episode_id,
                'scene': case['scene'],
                'group': case['group'],
                'frame': frame,
                'images': images,
            })
        tasks.extend(frames)
        cases.append({
            **case,
            'observations': episodes[episode_id]['observations'],
            'frame_count': len(frames),
        })
    if len(tasks) != 5378:
        raise ValueError('Expected 5378 tasks, got %d' % len(tasks))

    output.mkdir(parents=True)
    for relative in (
        'scripts/run_jev_noul_full_concurrent.py',
        'scripts/run_jev_noul_five_concurrent.py',
        'core/jev_node.py',
    ):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    write(output / 'selection.json', {
        'source': str(SOURCE_SELECTION),
        'source_sha256': sha(SOURCE_SELECTION),
        'scope': 'All frozen 61 human-annotated episodes',
        'cases': cases,
    })
    write(output / 'tasks.json', tasks)
    write(output / 'baseline_predictions.json', baseline)
    write(output / 'questions_zh.json', noul_question_translation())
    manifest = {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'dataset': str(DATASET),
        'qwen_baseline_run': str(QWEN_RUN),
        'selection_sha256': sha(output / 'selection.json'),
        'tasks_sha256': sha(output / 'tasks.json'),
        'expected_calls': len(tasks),
        'cases': len(cases),
        'concurrency': args.concurrency,
        'attempts': args.attempts,
        'timeout_seconds': args.timeout,
        'endpoint': args.endpoint,
        'model': args.model,
        'credential_on_disk': False,
        'protocol': (
            'All 61 frozen cases. Exact t-2,t-1,t RGB; one self-contained '
            'fallback_point Noul; no task, action, position, map, label, '
            'outcome, or prior answer in model input.'
        ),
    }
    write(output / 'manifest.json', manifest)
    write(
        output / 'workspace_status.txt',
        subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
    )

    for task in tasks:
        task.update(
            output=str(output),
            endpoint=args.endpoint,
            model=args.model,
            timeout=args.timeout,
            attempts=args.attempts,
        )
    started_at = now()
    write(output / 'status.json', {
        'phase': 'running',
        'started_at': started_at,
        'completed': 0,
        'total': len(tasks),
        'concurrency': args.concurrency,
    })
    rows = []
    context = multiprocessing.get_context('spawn')
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=args.concurrency, mp_context=context
    ) as executor:
        futures = {executor.submit(run_task, task): task for task in tasks}
        for index, future in enumerate(
            concurrent.futures.as_completed(futures), 1
        ):
            task = futures[future]
            try:
                record = future.result()
            except BaseException as error:
                record = {
                    **{key: task[key] for key in (
                        'episode_id', 'scene', 'group', 'frame', 'images'
                    )},
                    'phase': 'failed',
                    'error': type(error).__name__ + ': ' + str(error),
                }
            rows.append(record)
            if index % 25 == 0 or index == len(tasks):
                write(output / 'status.json', {
                    'phase': 'running',
                    'started_at': started_at,
                    'updated_at': now(),
                    'completed': index,
                    'total': len(tasks),
                    'complete': sum(row['phase'] == 'complete' for row in rows),
                    'failed': sum(row['phase'] != 'complete' for row in rows),
                    'concurrency': args.concurrency,
                })

    write(output / 'rows.json', rows)
    valid = [row for row in rows if row['phase'] == 'complete']
    summary = {
        'phase': 'complete' if len(valid) == len(tasks) else 'complete_with_failures',
        'started_at': started_at,
        'finished_at': now(),
        'cases': len(cases),
        'expected_calls': len(tasks),
        'completed_calls': len(rows),
        'valid_calls': len(valid),
        'failed_calls': len(rows) - len(valid),
        'concurrency': args.concurrency,
        'groups': {
            group: sum(case['group'] == group for case in cases)
            for group in ('failure', 'success')
        },
        'by_case': {
            case['episode_id']: {
                'valid': sum(
                    row['phase'] == 'complete'
                    and row['episode_id'] == case['episode_id']
                    for row in rows
                ),
                'total': case['frame_count'],
            }
            for case in cases
        },
        'mean_probability_yes': (
            sum(row['answer']['probability_yes'] for row in valid) / len(valid)
            if valid else None
        ),
        'probability_decile_histogram': {
            str(bucket): sum(
                bucket / 10 <= row['answer']['probability_yes'] < (bucket + 1) / 10
                for row in valid
            )
            for bucket in range(10)
        },
        'transport_attempt_histogram': {
            str(attempts): sum(
                row.get('transport', {}).get('attempts') == attempts
                for row in valid
            )
            for attempts in range(1, args.attempts + 1)
        },
        'credential_on_disk': False,
    }
    write(output / 'summary.json', summary)
    write(output / 'status.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
