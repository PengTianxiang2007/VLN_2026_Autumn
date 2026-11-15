"""Run v004 on ten fixed episodes with bounded high concurrency."""
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
    COMPACT_FALLBACK_CONTEXT_EN,
    COMPACT_FALLBACK_CONTEXT_ZH,
    COMPACT_FALLBACK_CRITERIA_EN,
    COMPACT_FALLBACK_CRITERIA_ZH,
    COMPACT_FALLBACK_INSTRUCTIONS_EN,
    COMPACT_FALLBACK_INSTRUCTIONS_ZH,
)
from run_jev_noul_five_concurrent import DATASET, run_task, sha

QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'
V002_RUN = (
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v002/run_20261108_06_full61_final'
)
EXCLUDED = {'kujiale_0123_fix_15_3', 'kujiale_0257_13_4'}


def prompt_text(language):
    context = COMPACT_FALLBACK_CONTEXT_EN if language == 'en' else COMPACT_FALLBACK_CONTEXT_ZH
    instructions = (
        COMPACT_FALLBACK_INSTRUCTIONS_EN
        if language == 'en' else COMPACT_FALLBACK_INSTRUCTIONS_ZH
    )
    criteria = (
        COMPACT_FALLBACK_CRITERIA_EN
        if language == 'en' else COMPACT_FALLBACK_CRITERIA_ZH
    )
    prefix = 'State context' if language == 'en' else '状态上下文'
    type_label = 'Question type' if language == 'en' else '问题类型'
    question_label = 'Question' if language == 'en' else '问题'
    colon = ':' if language == 'en' else '：'
    return '\n'.join([
        prefix + colon + ' ' + context,
        '',
        type_label + colon + ' noul',
        question_label + colon + ' ' + instructions,
        '',
        'true' + colon + ' ' + criteria['true'],
        'false' + colon + ' ' + criteria['false'],
    ])


def qwen_predictions(episode_id):
    result = {}
    for path in sorted((QWEN_RUN / 'cases' / episode_id).glob('F*.response.json')):
        row = read(path)
        result[str(row['frame'])] = {
            'score': row['answer']['score'] if row.get('valid') else None,
            'valid': bool(row.get('valid')),
        }
    return result


def select_cases():
    rows = [
        row for row in read(QWEN_RUN / 'evaluation_selection.json')
        if row['episode_id'] not in EXCLUDED
    ]
    return (
        [row for row in rows if row['group'] == 'failure'][:5]
        + [row for row in rows if row['group'] == 'success'][:5]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--concurrency', type=int, default=200)
    parser.add_argument('--attempts', type=int, default=5)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 500:
        raise ValueError('Concurrency must be between 1 and 500')
    if not os.environ.get('JEV_API_KEY'):
        raise RuntimeError('Set JEV_API_KEY in the parent process')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory')

    selected = select_cases()
    if len(selected) != 10:
        raise ValueError('Expected ten new cases')
    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    previous = {
        (row['episode_id'], row['frame']): row
        for row in read(V002_RUN / 'rows.json')
        if row['episode_id'] in {case['episode_id'] for case in selected}
    }
    tasks = []
    cases = []
    for case in selected:
        episode_id = case['episode_id']
        observations = read(DATASET / episodes[episode_id]['observations'])
        frame_windows = list(windows(observations))
        for frame, images in frame_windows:
            if (episode_id, frame) not in previous:
                raise ValueError('Missing previous prediction for %s F%d' % (
                    episode_id, frame
                ))
            tasks.append({
                'episode_id': episode_id,
                'scene': case['scene'],
                'group': case['group'],
                'frame': frame,
                'images': images,
                'question_version': 'v004',
            })
        cases.append({
            **case,
            'observations': len(observations),
            'eligible': len(frame_windows),
        })
    if len(tasks) != 862:
        raise ValueError('Expected 862 tasks, got %d' % len(tasks))

    output.mkdir(parents=True)
    for relative in (
        'scripts/run_jev_noul_v004_ten.py',
        'scripts/run_jev_noul_five_concurrent.py',
        'core/jev_node.py',
    ):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    write(output / 'selection.json', {
        'cases': cases,
        'rule': (
            'First five failures and first five successes in the frozen 61-case '
            'order after excluding the two earlier v004 episodes.'
        ),
        'excluded': sorted(EXCLUDED),
    })
    write(output / 'tasks.json', tasks)
    write(output / 'rows_v002.json', sorted(
        previous.values(), key=lambda row: (row['episode_id'], row['frame'])
    ))
    write(output / 'qwen_predictions.json', {
        case['episode_id']: qwen_predictions(case['episode_id'])
        for case in cases
    })
    write(output / 'prompt_en.json', {
        'context': COMPACT_FALLBACK_CONTEXT_EN,
        'question': {
            'type': 'noul',
            'instructions': COMPACT_FALLBACK_INSTRUCTIONS_EN,
            'criteria': dict(COMPACT_FALLBACK_CRITERIA_EN),
        },
    })
    write(output / 'prompt_zh.json', {
        'context': COMPACT_FALLBACK_CONTEXT_ZH,
        'question': {
            'type': 'noul',
            'instructions': COMPACT_FALLBACK_INSTRUCTIONS_ZH,
            'criteria': dict(COMPACT_FALLBACK_CRITERIA_ZH),
        },
    })
    write(output / 'prompt_v004_en.txt', prompt_text('en'))
    write(output / 'prompt_v004_zh.txt', prompt_text('zh'))
    write(output / 'manifest.json', {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'cases': len(cases),
        'expected_calls': len(tasks),
        'max_workers': args.concurrency,
        'attempts': args.attempts,
        'timeout_seconds': args.timeout,
        'model': 'jev-1.14.0',
        'previous_run': str(V002_RUN),
        'qwen_run': str(QWEN_RUN),
        'credential_on_disk': False,
        'protocol': (
            'Exact t-2,t-1,t RGB; one self-contained v004 Noul per observation; '
            'all tasks submitted together; no task/action/position/map/label/'
            'prior answer in state.'
        ),
    })
    write(output / 'status.json', {
        'phase': 'running',
        'started_at': now(),
        'completed': 0,
        'total': len(tasks),
        'max_workers': args.concurrency,
    })

    for task in tasks:
        task.update(
            output=str(output),
            endpoint='https://api.site/v1/systemone',
            model='jev-1.14.0',
            timeout=args.timeout,
            attempts=args.attempts,
        )
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
                        'episode_id', 'scene', 'group', 'frame', 'images',
                        'question_version'
                    )},
                    'phase': 'failed',
                    'error': type(error).__name__ + ': ' + str(error),
                }
            rows.append(row)
            if index % 25 == 0 or index == len(tasks):
                write(output / 'status.json', {
                    'phase': 'running',
                    'updated_at': now(),
                    'completed': index,
                    'total': len(tasks),
                    'valid': sum(r['phase'] == 'complete' for r in rows),
                    'failed': sum(r['phase'] != 'complete' for r in rows),
                    'max_workers': args.concurrency,
                })

    valid = [row for row in rows if row['phase'] == 'complete']
    write(output / 'rows_v004.json', sorted(
        rows, key=lambda row: (row['episode_id'], row['frame'])
    ))
    summary = {'cases': len(cases), 'expected_calls': len(tasks), 'valid_calls': len(valid),
      'failed_calls': len(tasks) - len(valid), 'max_workers': args.concurrency, 'by_case': {}}
    for case in cases:
        episode_id = case['episode_id']
        current = [row for row in valid if row['episode_id'] == episode_id]
        old = {
            row['frame']: row for (case_id, _), row in previous.items()
            if case_id == episode_id
        }
        paired = [(row, old[row['frame']]) for row in current if row['frame'] in old]
        summary['by_case'][episode_id] = {
            'valid': len(current),
            'expected': case['eligible'],
            'previous_mean': sum(old_row['answer']['probability_yes'] for _, old_row in paired) / len(paired),
            'current_mean': sum(row['answer']['probability_yes'] for row, _ in paired) / len(paired),
            'increased': sum(row['answer']['probability_yes'] > old_row['answer']['probability_yes'] for row, old_row in paired),
            'decreased': sum(row['answer']['probability_yes'] < old_row['answer']['probability_yes'] for row, old_row in paired),
            'equal': sum(row['answer']['probability_yes'] == old_row['answer']['probability_yes'] for row, old_row in paired),
        }
    paired = [
        (row, previous[(row['episode_id'], row['frame'])])
        for row in valid if (row['episode_id'], row['frame']) in previous
    ]
    summary['overall'] = {
        'valid': len(valid), 'total': len(tasks),
        'previous_mean': sum(old['answer']['probability_yes'] for _, old in paired) / len(paired),
        'current_mean': sum(row['answer']['probability_yes'] for row, _ in paired) / len(paired),
        'increased': sum(row['answer']['probability_yes'] > old['answer']['probability_yes'] for row, old in paired),
        'decreased': sum(row['answer']['probability_yes'] < old['answer']['probability_yes'] for row, old in paired),
        'equal': sum(row['answer']['probability_yes'] == old['answer']['probability_yes'] for row, old in paired),
    }
    summary['phase'] = 'complete' if len(valid) == len(tasks) else 'complete_with_failures'
    summary['finished_at'] = now()
    write(output / 'summary.json', summary)
    write(output / 'status.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
