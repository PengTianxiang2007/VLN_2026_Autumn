"""Merge completed full-set JEV results and retry only failed frames."""
import argparse
import concurrent.futures
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from core.agent_route_choice import now, read, write
from run_jev_noul_five_concurrent import run_task, sha


def load_completed(source, tasks):
    rows = {}
    missing = []
    failures = []
    for task in tasks:
        folder = (
            source / 'cases' / task['episode_id'] / ('F%04d' % task['frame'])
        )
        result_path = folder / 'result.json'
        error_path = folder / 'error.json'
        if result_path.is_file():
            row = read(result_path)
            if row.get('phase') != 'complete':
                missing.append(task)
                failures.append({'task': task, 'error': 'Result is not complete'})
                continue
            rows[(task['episode_id'], task['frame'])] = row
        else:
            missing.append(task)
            failures.append(read(error_path) if error_path.is_file() else {
                'episode_id': task['episode_id'],
                'frame': task['frame'],
                'error': 'No result or error file',
            })
    return rows, missing, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--concurrency', type=int, default=100)
    parser.add_argument('--attempts', type=int, default=5)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    source = args.source_run.resolve()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory')
    if not os.environ.get('JEV_API_KEY'):
        raise RuntimeError('Set JEV_API_KEY in the parent process')

    tasks = read(source / 'tasks.json')
    rows, retry_tasks, initial_failures = load_completed(source, tasks)
    if len(rows) + len(retry_tasks) != len(tasks):
        raise ValueError('Incomplete task accounting')
    output.mkdir(parents=True)
    for name in (
        'selection.json',
        'baseline_predictions.json',
        'questions_zh.json',
        'manifest.json',
    ):
        shutil.copy2(source / name, output / name)
    write(output / 'tasks.json', tasks)
    for relative in (
        'scripts/retry_jev_noul_full.py',
        'scripts/run_jev_noul_full_concurrent.py',
        'scripts/run_jev_noul_five_concurrent.py',
        'core/jev_node.py',
    ):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    write(output / 'retry_audit.json', {
        'created_at': now(),
        'source_run': str(source),
        'reused_successes': len(rows),
        'initial_failures': len(retry_tasks),
        'initial_failure_examples': initial_failures[:20],
        'retry_concurrency': args.concurrency,
        'retry_attempts': args.attempts,
        'credential_on_disk': False,
    })
    write(output / 'status.json', {
        'phase': 'retrying',
        'started_at': now(),
        'reused': len(rows),
        'retry_total': len(retry_tasks),
        'retry_completed': 0,
    })

    for task in retry_tasks:
        task.update(
            output=str(output),
            endpoint='https://api.site/v1/systemone',
            model='jev-1.14.0',
            timeout=args.timeout,
            attempts=args.attempts,
        )
    retry_results = []
    context = multiprocessing.get_context('spawn')
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(args.concurrency, len(retry_tasks)),
        mp_context=context,
    ) as executor:
        futures = {executor.submit(run_task, task): task for task in retry_tasks}
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
            retry_results.append(record)
            if record.get('phase') == 'complete':
                rows[(task['episode_id'], task['frame'])] = record
            if index % 10 == 0 or index == len(retry_tasks):
                write(output / 'status.json', {
                    'phase': 'retrying',
                    'updated_at': now(),
                    'reused': len(rows) - sum(
                        row.get('phase') == 'complete' for row in retry_results
                    ),
                    'retry_completed': index,
                    'retry_valid': sum(
                        row.get('phase') == 'complete' for row in retry_results
                    ),
                    'retry_failed': sum(
                        row.get('phase') != 'complete' for row in retry_results
                    ),
                    'retry_total': len(retry_tasks),
                })

    final_rows = sorted(
        rows.values(),
        key=lambda row: (row['episode_id'], row['frame']),
    )
    selection = read(source / 'selection.json')['cases']
    summary = {
        'phase': (
            'complete'
            if len(final_rows) == len(tasks)
            else 'complete_with_failures'
        ),
        'finished_at': now(),
        'cases': len(selection),
        'expected_calls': len(tasks),
        'valid_calls': len(final_rows),
        'failed_calls': len(tasks) - len(final_rows),
        'initial_successes_reused': len(rows) - sum(
            row.get('phase') == 'complete' for row in retry_results
        ),
        'retry_attempted': len(retry_results),
        'retry_valid': sum(row.get('phase') == 'complete' for row in retry_results),
        'retry_failed': sum(row.get('phase') != 'complete' for row in retry_results),
        'groups': {
            group: sum(case['group'] == group for case in selection)
            for group in ('failure', 'success')
        },
        'mean_probability_yes': (
            sum(row['answer']['probability_yes'] for row in final_rows)
            / len(final_rows)
            if final_rows else None
        ),
        'probability_decile_histogram': {
            str(bucket): sum(
                bucket / 10 <= row['answer']['probability_yes'] < (bucket + 1) / 10
                for row in final_rows
            )
            for bucket in range(10)
        },
        'transport_attempt_histogram': {
            str(attempts): sum(
                row.get('transport', {}).get('attempts') == attempts
                for row in final_rows
            )
            for attempts in range(1, args.attempts + 1)
        },
        'credential_on_disk': False,
    }
    write(output / 'rows.json', final_rows)
    write(output / 'summary.json', summary)
    write(output / 'retry_results.json', retry_results)
    write(output / 'status.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
