"""Run v004 on two full episodes and fill missing v003 comparison observations."""
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
    NEAR_FALLBACK_CONTEXT_EN,
    NEAR_FALLBACK_CONTEXT_ZH,
    NEAR_FALLBACK_CRITERIA_EN,
    NEAR_FALLBACK_CRITERIA_ZH,
    NEAR_FALLBACK_INSTRUCTIONS_EN,
    NEAR_FALLBACK_INSTRUCTIONS_ZH,
)
from run_jev_noul_five_concurrent import DATASET, run_task, sha

QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'
V003_RUN = (
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v003/'
    / 'run_20261108_01_kujiale_0123_fix_15_3'
)
EPISODES = ('kujiale_0123_fix_15_3', 'kujiale_0257_13_4')


def text_prompt(version, language):
    if version == 'v003':
        context = NEAR_FALLBACK_CONTEXT_EN if language == 'en' else NEAR_FALLBACK_CONTEXT_ZH
        instructions = (
            NEAR_FALLBACK_INSTRUCTIONS_EN
            if language == 'en' else NEAR_FALLBACK_INSTRUCTIONS_ZH
        )
        criteria = (
            NEAR_FALLBACK_CRITERIA_EN
            if language == 'en' else NEAR_FALLBACK_CRITERIA_ZH
        )
    else:
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--concurrency', type=int, default=100)
    parser.add_argument('--attempts', type=int, default=5)
    parser.add_argument('--timeout', type=float, default=120)
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
    selection = {
        row['episode_id']: row
        for row in read(QWEN_RUN / 'evaluation_selection.json')
    }
    existing_v003 = {
        row['frame']: row
        for row in read(V003_RUN / 'rows.json')
    }
    tasks = []
    counts = {}
    for episode_id in EPISODES:
        episode = episodes[episode_id]
        observations = read(DATASET / episode['observations'])
        frame_windows = list(windows(observations))
        counts[episode_id] = {'observations': len(observations), 'eligible': len(frame_windows)}
        for frame, images in frame_windows:
            tasks.append({
                'episode_id': episode_id,
                'scene': selection[episode_id]['scene'],
                'group': selection[episode_id]['group'],
                'frame': frame,
                'images': images,
                'question_version': 'v004',
                'output': str(output / 'v004'),
            })
            if episode_id == EPISODES[1]:
                tasks.append({
                    'episode_id': episode_id,
                    'scene': selection[episode_id]['scene'],
                    'group': selection[episode_id]['group'],
                    'frame': frame,
                    'images': images,
                    'question_version': 'v003',
                    'output': str(output / 'v003'),
                })
    expected = sum(value['eligible'] for value in counts.values())
    if expected != 188:
        raise ValueError('Expected 188 v004 observations')
    if len(tasks) != expected + counts[EPISODES[1]]['eligible']:
        raise ValueError('Invalid combined task count')

    output.mkdir(parents=True)
    for relative in (
        'scripts/run_jev_noul_v004_two_cases.py',
        'scripts/run_jev_noul_five_concurrent.py',
        'core/jev_node.py',
    ):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    write(output / 'selection.json', {
        'episodes': [
            {**selection[episode_id], **counts[episode_id]}
            for episode_id in EPISODES
        ],
        'scope': 'All eligible observations in two fixed episodes',
        'v003_first_case_reused_from': str(V003_RUN),
    })
    write(output / 'qwen_predictions.json', {
        episode_id: qwen_predictions(episode_id)
        for episode_id in EPISODES
    })
    write(output / 'prompt_v003_en.txt', text_prompt('v003', 'en'))
    write(output / 'prompt_v003_zh.txt', text_prompt('v003', 'zh'))
    write(output / 'prompt_v004_en.txt', text_prompt('v004', 'en'))
    write(output / 'prompt_v004_zh.txt', text_prompt('v004', 'zh'))
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
    write(output / 'batch_tasks.json', tasks)
    write(output / 'manifest.json', {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'episode_counts': counts,
        'v004_calls': expected,
        'v003_comparison_calls': counts[EPISODES[1]]['eligible'],
        'v003_first_case_reused_rows': len(existing_v003),
        'submitted_tasks': len(tasks),
        'max_workers': args.concurrency,
        'attempts': args.attempts,
        'timeout_seconds': args.timeout,
        'model': 'jev-1.14.0',
        'credential_on_disk': False,
        'protocol': (
            'Exact t-2,t-1,t RGB; one Noul per observation; all tasks submitted '
            'together; no task/action/position/map/label/prior answer in state.'
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
                record = future.result()
            except BaseException as error:
                record = {
                    **{key: task[key] for key in (
                        'episode_id', 'scene', 'group', 'frame', 'images',
                        'question_version'
                    )},
                    'phase': 'failed',
                    'error': type(error).__name__ + ': ' + str(error),
                }
            rows.append(record)
            if index % 10 == 0 or index == len(tasks):
                write(output / 'status.json', {
                    'phase': 'running',
                    'updated_at': now(),
                    'completed': index,
                    'total': len(tasks),
                    'valid_v004': sum(
                        row['phase'] == 'complete'
                        and row.get('question_version') == 'v004'
                        for row in rows
                    ),
                    'failed_v004': sum(
                        row['phase'] != 'complete'
                        and row.get('question_version') == 'v004'
                        for row in rows
                    ),
                    'valid_v003': sum(
                        row['phase'] == 'complete'
                        and row.get('question_version') == 'v003'
                        for row in rows
                    ),
                    'failed_v003': sum(
                        row['phase'] != 'complete'
                        and row.get('question_version') == 'v003'
                        for row in rows
                    ),
                    'max_workers': args.concurrency,
                })

    v004 = {
        (row['episode_id'], row['frame']): row
        for row in rows if row.get('question_version') == 'v004'
    }
    v003_second = {
        (row['episode_id'], row['frame']): row
        for row in rows
        if row.get('question_version') == 'v003'
        and row.get('episode_id') == EPISODES[1]
    }
    v003 = {
        (EPISODES[0], frame): row for frame, row in existing_v003.items()
    }
    v003.update(v003_second)
    write(output / 'rows_v004.json', sorted(
        v004.values(), key=lambda row: (row['episode_id'], row['frame'])
    ))
    write(output / 'rows_v003.json', sorted(
        v003.values(), key=lambda row: (row['episode_id'], row['frame'])
    ))
    summary = {'episode_counts': counts, 'v004': {}, 'overall': {}}
    all_v004 = []
    all_v003 = []
    for episode_id in EPISODES:
        current = [
            row for (case, _), row in v004.items()
            if case == episode_id and row.get('phase') == 'complete'
        ]
        previous = [
            row for (case, _), row in v003.items()
            if case == episode_id and row.get('phase') == 'complete'
        ]
        current.sort(key=lambda row: row['frame'])
        previous_by_frame = {row['frame']: row for row in previous}
        paired = [
            (row, previous_by_frame[row['frame']])
            for row in current if row['frame'] in previous_by_frame
        ]
        summary['v004'][episode_id] = {
            'valid': len(current),
            'expected': counts[episode_id]['eligible'],
            'mean_probability': (
                sum(row['answer']['probability_yes'] for row in current)
                / len(current) if current else None
            ),
            'v003_mean_probability': (
                sum(old['answer']['probability_yes'] for _, old in paired)
                / len(paired) if paired else None
            ),
            'increased': sum(
                row['answer']['probability_yes']
                > old['answer']['probability_yes']
                for row, old in paired
            ),
            'decreased': sum(
                row['answer']['probability_yes']
                < old['answer']['probability_yes']
                for row, old in paired
            ),
            'equal': sum(
                row['answer']['probability_yes']
                == old['answer']['probability_yes']
                for row, old in paired
            ),
        }
        all_v004.extend(current)
        all_v003.extend(previous)
    summary['overall'] = {
        'expected_v004': expected,
        'valid_v004': len(all_v004),
        'valid_v003': len(all_v003),
        'mean_v004_probability': (
            sum(row['answer']['probability_yes'] for row in all_v004)
            / len(all_v004) if all_v004 else None
        ),
        'mean_v003_probability': (
            sum(row['answer']['probability_yes'] for row in all_v003)
            / len(all_v003) if all_v003 else None
        ),
    }
    summary.update(
        phase=(
            'complete'
            if len(all_v004) == expected and len(all_v003) == expected
            else 'complete_with_failures'
        ),
        submitted_tasks=len(tasks),
        max_workers=args.concurrency,
        finished_at=now(),
        credential_on_disk=False,
    )
    write(output / 'summary.json', summary)
    write(output / 'status.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
