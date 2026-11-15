"""Run five fixed offline episodes through JEV fallback-point Noul, 50 workers."""
import argparse
import concurrent.futures
import hashlib
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
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    build_compact_fallback_noul_request,
    build_near_fallback_noul_request,
    build_noul_request,
    call_api,
    noul_question_translation,
    request_digest,
    request_without_images,
    validate_noul_response,
)

DATASET = (
    ROOT
    / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01'
    / 'crossing_seed2_human_v001'
)
QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_v002/run_20261108_01'
SOURCE_SELECTION = QWEN_RUN / 'evaluation_selection.json'
N_SELECT = 5


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def select_five(selection):
    """Alternate outcome while preferring a new scene; no model output is read."""
    by_group = {
        group: [row for row in selection if row['group'] == group]
        for group in ('failure', 'success')
    }
    selected = []
    used_scenes = set()
    group_order = ('failure', 'success') * N_SELECT
    for group in group_order:
        if len(selected) == N_SELECT:
            break
        available = [
            row for row in by_group[group]
            if row['episode_id'] not in {item['episode_id'] for item in selected}
        ]
        if not available:
            continue
        row = next(
            (item for item in available if item['scene'] not in used_scenes),
            available[0],
        )
        selected.append(row)
        used_scenes.add(row['scene'])
    if len(selected) != N_SELECT:
        raise ValueError('Could not select five cases')
    return selected


def run_task(task):
    """Worker: one step, one JEV request, isolated output directory."""
    key = os.environ.get('JEV_API_KEY', '')
    if not key:
        return dict(**task, phase='failed', error='JEV_API_KEY is missing')
    folder = Path(task['output']) / 'cases' / task['episode_id'] / (
        'F%04d' % task['frame']
    )
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        version = task.get('question_version', 'v002')
        builder = {
            'v002': build_noul_request,
            'v003': build_near_fallback_noul_request,
            'v004': build_compact_fallback_noul_request,
        }[version]
        request, image_audit = builder(
            task['images'], task.get('dataset', DATASET), model=task['model']
        )
        write(folder / 'request.json', {
            **request_without_images(request),
            'request_sha256': request_digest(request),
            'question_version': version,
        })
        write(folder / 'images.json', image_audit)
        raw, latency, transport = call_api(
            task['endpoint'],
            key,
            request,
            task['timeout'],
            folder / 'request_full.json',
            attempts=task['attempts'],
        )
        probability = validate_noul_response(raw)
        record = {
            'phase': 'complete',
            'episode_id': task['episode_id'],
            'scene': task['scene'],
            'group': task['group'],
            'frame': task['frame'],
            'image_frames': [row['frame'] for row in task['images']],
            'answer': probability,
            'request_sha256': request_digest(request),
            'question_version': version,
            'latency_seconds': latency,
            'transport': transport,
        }
        write(folder / 'response.json', raw)
        write(folder / 'result.json', record)
        return record
    except Exception as error:
        record = {
            'phase': 'failed',
            'episode_id': task['episode_id'],
            'scene': task['scene'],
            'group': task['group'],
            'frame': task['frame'],
            'image_frames': [row['frame'] for row in task['images']],
            'latency_seconds': time.monotonic() - started,
            'error': str(error).replace(key, '[REDACTED]'),
        }
        write(folder / 'error.json', record)
        return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--concurrency', type=int, default=50)
    parser.add_argument('--attempts', type=int, default=4)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    args = parser.parse_args()
    if args.concurrency != 50:
        raise ValueError('This authorized run requires concurrency=50')
    if not os.environ.get('JEV_API_KEY'):
        raise RuntimeError('Set JEV_API_KEY in the parent process')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory')

    selection = select_five(read(SOURCE_SELECTION))
    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    baseline = read(QWEN_RUN / 'baseline_predictions.json')
    tasks = []
    cases = []
    for case in selection:
        episode_id = case['episode_id']
        observations = read(DATASET / episodes[episode_id]['observations'])
        frames = []
        for frame, images in windows(observations):
            if not baseline[episode_id].get(str(frame), {}).get('valid'):
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
    if len(tasks) != 421:
        raise ValueError('Expected 421 tasks, got %d' % len(tasks))

    output.mkdir(parents=True)
    for relative in (
        'scripts/run_jev_noul_five_concurrent.py',
        'core/jev_node.py',
    ):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    write(output / 'selection.json', {
        'source': str(SOURCE_SELECTION),
        'source_sha256': sha(SOURCE_SELECTION),
        'rule': (
            'Alternate failure/success from the frozen 20-case Qwen selection; '
            'prefer an unused scene; stop at five.'
        ),
        'cases': cases,
    })
    write(output / 'tasks.json', tasks)
    write(output / 'baseline_predictions.json', baseline)
    write(output / 'questions_zh.json', noul_question_translation())
    write(output / 'manifest.json', {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'dataset': str(DATASET),
        'qwen_baseline_run': str(QWEN_RUN),
        'selection_sha256': sha(output / 'selection.json'),
        'tasks_sha256': sha(output / 'tasks.json'),
        'expected_calls': len(tasks),
        'concurrency': args.concurrency,
        'attempts': args.attempts,
        'timeout_seconds': args.timeout,
        'endpoint': args.endpoint,
        'model': args.model,
        'credential_on_disk': False,
        'protocol': (
            'Exact t-2,t-1,t RGB; one fallback_point Noul; no task, action, '
            'position, map, label, outcome, or prior answer in model input.'
        ),
    })
    write(
        output / 'workspace_status.txt',
        subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
    )
    write(output / 'tracked_worktree.diff', {
        'binary_diff_base64': __import__('base64').b64encode(
            subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT)
        ).decode(),
    })

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
            if index % 5 == 0 or index == len(tasks):
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
            if sum(row['phase'] != 'complete' for row in rows) >= 20:
                for pending in futures:
                    pending.cancel()
                break

    write(output / 'rows.json', rows)
    summary = {
        'phase': (
            'complete'
            if len(rows) == len(tasks)
            and all(row['phase'] == 'complete' for row in rows)
            else 'complete_with_failures'
        ),
        'started_at': started_at,
        'finished_at': now(),
        'cases': len(cases),
        'expected_calls': len(tasks),
        'completed_calls': len(rows),
        'valid_calls': sum(row['phase'] == 'complete' for row in rows),
        'failed_calls': sum(row['phase'] != 'complete' for row in rows),
        'concurrency': args.concurrency,
        'by_case': {
            episode_id: dict(
                valid=sum(
                    row['phase'] == 'complete'
                    and row['episode_id'] == episode_id
                    for row in rows
                ),
                total=sum(task['episode_id'] == episode_id for task in tasks),
            )
            for episode_id in [case['episode_id'] for case in cases]
        },
        'probability_histogram': {
            str(bucket): sum(
                bucket / 10 <= row['answer']['probability_yes']
                < (bucket + 1) / 10
                for row in rows if row['phase'] == 'complete'
            )
            for bucket in range(10)
        },
        'mean_probability_yes': (
            sum(
                row['answer']['probability_yes']
                for row in rows if row['phase'] == 'complete'
            ) / sum(row['phase'] == 'complete' for row in rows)
            if any(row['phase'] == 'complete' for row in rows)
            else None
        ),
        'transport_attempt_histogram': dict(Counter(
            row.get('transport', {}).get('attempts')
            for row in rows if row['phase'] == 'complete'
        )),
        'credential_on_disk': False,
    }
    write(output / 'summary.json', summary)
    write(output / 'status.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
