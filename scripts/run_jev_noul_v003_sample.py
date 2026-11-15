"""Run all eligible observations of one episode with the near-fallback prompt."""
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
    NEAR_FALLBACK_CONTEXT_EN,
    NEAR_FALLBACK_CONTEXT_ZH,
    NEAR_FALLBACK_CRITERIA_EN,
    NEAR_FALLBACK_CRITERIA_ZH,
    NEAR_FALLBACK_INSTRUCTIONS_EN,
    NEAR_FALLBACK_INSTRUCTIONS_ZH,
    near_fallback_question_translation,
)
from run_jev_noul_five_concurrent import DATASET, sha, run_task

QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'
PREVIOUS_RUN = (
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v002/run_20261108_06_full61_final'
)


def qwen_predictions(episode_id):
    result = {}
    for path in sorted((QWEN_RUN / 'cases' / episode_id).glob('F*.response.json')):
        row = read(path)
        result[str(row['frame'])] = {
            'score': row['answer']['score'] if row.get('valid') else None,
            'valid': bool(row.get('valid')),
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--episode', default='kujiale_0123_fix_15_3')
    parser.add_argument('--concurrency', type=int, default=90)
    parser.add_argument('--attempts', type=int, default=5)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--model', default='jev-1.14.0')
    args = parser.parse_args()
    if not os.environ.get('JEV_API_KEY'):
        raise RuntimeError('Set JEV_API_KEY in the parent process')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory')

    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    episode = episodes[args.episode]
    selected_case = next(
        row for row in read(QWEN_RUN / 'evaluation_selection.json')
        if row['episode_id'] == args.episode
    )
    observations = read(DATASET / episode['observations'])
    tasks = [
        {
            'episode_id': args.episode,
            'scene': selected_case['scene'],
            'group': selected_case['group'],
            'frame': frame,
            'images': images,
            'question_version': 'v003',
        }
        for frame, images in windows(observations)
    ]
    if len(tasks) != 90:
        raise ValueError('Expected 90 eligible observations, got %d' % len(tasks))
    if args.concurrency != len(tasks):
        raise ValueError('This batch requires one worker per observation')

    previous_rows = [
        row for row in read(PREVIOUS_RUN / 'rows.json')
        if row['episode_id'] == args.episode
    ]
    if len(previous_rows) != len(tasks):
        raise ValueError('Previous version does not cover all observations')
    write(output / 'previous_predictions.json', {
        str(row['frame']): {
            'probability_yes': row['answer']['probability_yes'],
            'probability_no': row['answer']['probability_no'],
        }
        for row in previous_rows
    })
    write(output / 'qwen_predictions.json', qwen_predictions(args.episode))
    write(output / 'tasks.json', tasks)
    write(output / 'questions_zh.json', near_fallback_question_translation())
    write(output / 'prompt_en.json', {
        'state_context': NEAR_FALLBACK_CONTEXT_EN,
        'question': {
            'type': 'noul',
            'instructions': NEAR_FALLBACK_INSTRUCTIONS_EN,
            'criteria': dict(NEAR_FALLBACK_CRITERIA_EN),
        },
    })
    write(output / 'prompt_zh.json', {
        'state_context': NEAR_FALLBACK_CONTEXT_ZH,
        'question': {
            'type': 'noul',
            'instructions': NEAR_FALLBACK_INSTRUCTIONS_ZH,
            'criteria': dict(NEAR_FALLBACK_CRITERIA_ZH),
        },
    })
    for relative in (
        'scripts/run_jev_noul_v003_sample.py',
        'scripts/run_jev_noul_five_concurrent.py',
        'core/jev_node.py',
    ):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    write(output / 'manifest.json', {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'episode_id': args.episode,
        'question_version': 'v003',
        'model': args.model,
        'concurrency': args.concurrency,
        'expected_calls': len(tasks),
        'attempts': args.attempts,
        'timeout_seconds': args.timeout,
        'previous_run': str(PREVIOUS_RUN),
        'previous_run_sha256': sha(PREVIOUS_RUN / 'rows.json'),
        'qwen_run': str(QWEN_RUN),
        'credential_on_disk': False,
        'input_policy': (
            'Exact t-2,t-1,t RGB; no task, action, position, map, label, '
            'outcome, or prior answer in model input.'
        ),
    })
    write(
        output / 'workspace_status.txt',
        subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
    )
    for task in tasks:
        task.update(
            output=str(output),
            endpoint='https://api.site/v1/systemone',
            model=args.model,
            timeout=args.timeout,
            attempts=args.attempts,
        )
    write(output / 'status.json', {
        'phase': 'running',
        'started_at': now(),
        'total': len(tasks),
        'completed': 0,
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
                row = future.result()
            except BaseException as error:
                row = {
                    **{key: task[key] for key in (
                        'episode_id', 'scene', 'group', 'frame', 'images'
                    )},
                    'phase': 'failed',
                    'error': type(error).__name__ + ': ' + str(error),
                }
            rows.append(row)
            write(output / 'status.json', {
                'phase': 'running',
                'updated_at': now(),
                'completed': index,
                'total': len(tasks),
                'valid': sum(r['phase'] == 'complete' for r in rows),
                'failed': sum(r['phase'] != 'complete' for r in rows),
                'concurrency': args.concurrency,
            })
    rows.sort(key=lambda row: row['frame'])
    valid = [row for row in rows if row['phase'] == 'complete']
    previous = read(output / 'previous_predictions.json')
    probabilities = [row['answer']['probability_yes'] for row in valid]
    previous_probabilities = [
        previous[str(row['frame'])]['probability_yes']
        for row in valid
    ]
    summary = {
        'phase': 'complete' if len(valid) == len(tasks) else 'complete_with_failures',
        'episode_id': args.episode,
        'total': len(tasks),
        'valid': len(valid),
        'failed': len(tasks) - len(valid),
        'concurrency': args.concurrency,
        'mean_probability_yes': sum(probabilities) / len(probabilities) if probabilities else None,
        'previous_mean_probability_yes': (
            sum(previous_probabilities) / len(previous_probabilities)
            if previous_probabilities else None
        ),
        'increased': sum(
            row['answer']['probability_yes'] > previous[str(row['frame'])]['probability_yes']
            for row in valid
        ),
        'decreased': sum(
            row['answer']['probability_yes'] < previous[str(row['frame'])]['probability_yes']
            for row in valid
        ),
        'equal': sum(
            row['answer']['probability_yes'] == previous[str(row['frame'])]['probability_yes']
            for row in valid
        ),
        'finished_at': now(),
        'credential_on_disk': False,
    }
    write(output / 'rows.json', rows)
    write(output / 'summary.json', summary)
    write(output / 'status.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
