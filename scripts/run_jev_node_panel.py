"""Run a small mixed JEV node panel without using labels in model input."""
import argparse
import getpass
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import now, read, write
from core.crossing_lite import windows
from core.jev_node import (
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    DIRECTION_KEYS,
    build_request,
    call_api,
    question_translation,
    request_digest,
    request_without_images,
    validate_response,
)

DATASET = (
    ROOT
    / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01'
    / 'crossing_seed2_human_v001'
)


def api_key(use_stdin):
    if use_stdin:
        value = getpass.getpass('JEV API key: ') if sys.stdin.isatty() else sys.stdin.readline()
    else:
        value = os.environ.get('JEV_API_KEY', '')
    value = value.strip()
    if not value:
        raise RuntimeError('Set JEV_API_KEY or pass --api-key-stdin')
    return value


def balanced_sample(rows, count, rng):
    """Prefer distinct episodes, then fill with remaining cases."""
    grouped = {}
    for row in sorted(rows, key=lambda item: (item['episode_id'], item['frame'])):
        grouped.setdefault(row['episode_id'], []).append(row)
    episodes = sorted(grouped)
    rng.shuffle(episodes)
    for episode in episodes:
        rng.shuffle(grouped[episode])
    result = []
    while len(result) < count:
        advanced = False
        for episode in episodes:
            if grouped[episode] and len(result) < count:
                result.append(grouped[episode].pop())
                advanced = True
        if not advanced:
            break
    if len(result) != count:
        raise ValueError('Insufficient cases for requested panel size')
    return result


def select_cases(source, annotation_count, control_count, seed):
    cases = read(source)['cases']
    rng = random.Random(seed)
    result = []
    for role, count in (
        ('annotation', annotation_count),
        ('stability_control', control_count),
    ):
        result.extend(balanced_sample(
            [row for row in cases if row['role'] == role],
            count,
            rng,
        ))
    return sorted(result, key=lambda row: (row['role'], row['episode_id'], row['frame']))


def distribution(values):
    return {str(key): value for key, value in sorted(Counter(values).items())}


def summarize(rows):
    summary = {'total': len(rows), 'by_role': {}}
    for role in sorted({row['role'] for row in rows}):
        subset = [row for row in rows if row['role'] == role]
        scores = [row['answer']['score'] for row in subset]
        summary['by_role'][role] = {
            'total': len(subset),
            'score_histogram': distribution(scores),
            'highest_probability_histogram': distribution(
                row['interpretation']['highest_probability_score']
                for row in subset
            ),
            'score_at_least_3': sum(score >= 3 for score in scores),
            'score_at_least_4': sum(score >= 4 for score in scores),
            'mean_score': round(sum(scores) / len(scores), 4),
            'mean_continuous_score': round(sum(
                row['answer']['score_continuous_1_5'] for row in subset
            ) / len(subset), 4),
            'mean_confidence': round(sum(
                row['answer']['confidence'] for row in subset
            ) / len(subset), 4),
            'mean_directional_probabilities': {
                key: round(sum(
                    row['answer']['directional_probabilities'][key]
                    for row in subset
                ) / len(subset), 4)
                for key in DIRECTION_KEYS
            },
        }
    scores = [row['answer']['score'] for row in rows]
    summary['score_histogram'] = distribution(scores)
    summary['score_at_least_3'] = sum(score >= 3 for score in scores)
    summary['score_at_least_4'] = sum(score >= 4 for score in scores)
    summary['evaluation'] = (
        'Small mixed diagnostic panel. Annotation points are positive references; '
        'unlabeled frames are not negatives. No PR/F1 or accuracy claim.'
    )
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--panel-source', required=True, type=Path)
    parser.add_argument('--baseline-run', required=True, type=Path)
    parser.add_argument('--annotation-count', type=int, default=20)
    parser.add_argument('--control-count', type=int, default=20)
    parser.add_argument('--selection-seed', type=int, default=20261108)
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--attempts', type=int, default=3)
    parser.add_argument('--api-key-stdin', action='store_true')
    args = parser.parse_args()

    out = args.output.resolve()
    if out.exists():
        raise ValueError('Use a new output directory')
    panel_source = args.panel_source.resolve()
    baseline = args.baseline_run.resolve()
    key = api_key(args.api_key_stdin)
    cases = select_cases(
        panel_source,
        args.annotation_count,
        args.control_count,
        args.selection_seed,
    )

    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    baseline_predictions = read(baseline / 'baseline_predictions.json')
    out.mkdir(parents=True)
    for rel in ('scripts/run_jev_node_panel.py', 'core/jev_node.py'):
        target = out / 'source' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    write(out / 'questions_zh.json', question_translation())
    write(out / 'panel.json', {
        'cases': cases,
        'counts': dict(Counter(row['role'] for row in cases)),
        'selection_seed': args.selection_seed,
    })
    write(out / 'manifest.json', {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'panel_source': str(panel_source),
        'panel_source_sha256': hashlib.sha256(
            panel_source.read_bytes()
        ).hexdigest(),
        'baseline_run': str(baseline),
        'endpoint': args.endpoint,
        'model': args.model,
        'selection_seed': args.selection_seed,
        'transport_attempts': args.attempts,
        'credential_on_disk': False,
        'protocol': (
            'Exact t-2,t-1,t RGB only; no instruction, action, position, map, '
            'outcome, role, label, or prior answer in JEV input.'
        ),
    })
    write(
        out / 'workspace_status.txt',
        subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
    )
    write(out / 'status.json', {
        'phase': 'running',
        'started_at': now(),
        'completed': 0,
        'total': len(cases),
    })

    observation_cache = {}
    rows = []
    try:
        for index, case in enumerate(cases, 1):
            episode_id = case['episode_id']
            frame = case['frame']
            if episode_id not in observation_cache:
                observation_cache[episode_id] = {
                    current: images
                    for current, images in windows(
                        read(DATASET / episodes[episode_id]['observations'])
                    )
                }
            images = observation_cache[episode_id].get(frame)
            if images is None:
                raise ValueError(
                    'Ineligible frame: %s F%d' % (episode_id, frame)
                )
            request, image_audit = build_request(
                images, DATASET, model=args.model
            )
            folder = out / 'cases' / episode_id / ('F%04d' % frame)
            folder.mkdir(parents=True)
            write(folder / 'request.json', {
                **request_without_images(request),
                'request_sha256': request_digest(request),
            })
            write(folder / 'images.json', image_audit)
            baseline_answer = baseline_predictions[episode_id][str(frame)]['answer']
            write(folder / 'case.json', {
                **case,
                'image_frames': [row['frame'] for row in images],
                'request_sha256': request_digest(request),
                'baseline_best_v001': baseline_answer,
            })
            raw, latency, transport = call_api(
                args.endpoint,
                key,
                request,
                args.timeout,
                folder / 'request_full.json',
                attempts=args.attempts,
            )
            interpretation = validate_response(raw)
            answer = {
                'score': interpretation['score'],
                'score_continuous_1_5': interpretation['score_continuous_1_5'],
                'confidence': interpretation['confidence'],
                'directional_probabilities': interpretation[
                    'directional_probabilities'
                ],
                'probabilities_1_5': interpretation['probabilities_1_5'],
            }
            record = {
                **case,
                'image_frames': [row['frame'] for row in images],
                'answer': answer,
                'interpretation': interpretation,
                'baseline_best_v001': baseline_answer,
                'request_sha256': request_digest(request),
                'latency_seconds': latency,
                'transport': transport,
                'scope': 'Small mixed diagnostic panel; not independent validation.',
            }
            write(folder / 'response.json', raw)
            write(folder / 'result.json', record)
            rows.append(record)
            write(out / 'status.json', {
                'phase': 'running',
                'updated_at': now(),
                'completed': index,
                'total': len(cases),
            })
    except Exception as error:
        detail = str(error).replace(key, '[REDACTED]')
        write(out / 'partial.json', {
            'phase': 'failed',
            'failed_at': now(),
            'completed': len(rows),
            'rows': rows,
            'error': detail,
            'credential_on_disk': False,
        })
        write(out / 'status.json', {
            'phase': 'failed',
            'finished_at': now(),
            'completed': len(rows),
            'total': len(cases),
            'error': detail,
        })
        raise

    summary = summarize(rows)
    write(out / 'rows.json', rows)
    write(out / 'summary.json', summary)
    write(out / 'status.json', {
        'phase': 'complete',
        'finished_at': now(),
        'completed': len(rows),
        'total': len(cases),
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
