"""Probe JEV local-node scoring on selected offline Crossing frames."""
import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import now, read, write
from core.crossing_lite import windows
from core.jev_node import (
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    build_request,
    build_noul_request,
    call_api,
    noul_question_translation,
    question_translation,
    request_digest,
    request_without_images,
    validate_noul_response,
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--episode', required=True)
    parser.add_argument('--frame', required=True, type=int, action='append')
    parser.add_argument('--baseline-run', required=True, type=Path)
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument(
        '--question-type',
        choices=('score', 'noul'),
        default='score',
    )
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--attempts', type=int, default=3)
    parser.add_argument('--api-key-stdin', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    out = args.output.resolve()
    if out.exists():
        raise ValueError('Use a new output directory')
    if len(set(args.frame)) != len(args.frame):
        raise ValueError('Duplicate requested frame')
    key = None if args.dry_run else api_key(args.api_key_stdin)

    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    episode = episodes[args.episode]
    observations = read(DATASET / episode['observations'])
    available = {frame: images for frame, images in windows(observations)}
    missing = sorted(set(args.frame) - set(available))
    if missing:
        raise ValueError('Frames are not eligible JEV observations: ' + str(missing))
    baseline = read(args.baseline_run.resolve() / 'baseline_predictions.json')[
        args.episode
    ]

    out.mkdir(parents=True)
    for rel in ('scripts/probe_jev_node_score.py', 'core/jev_node.py'):
        target = out / 'source' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    translation = (
        noul_question_translation()
        if args.question_type == 'noul'
        else question_translation()
    )
    write(out / 'questions_zh.json', translation)
    write(
        out / 'workspace_status.txt',
        subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
    )
    write(
        out / 'manifest.json',
        {
            'created_at': now(),
            'git_head': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
            ).strip(),
            'endpoint': args.endpoint,
            'model': args.model,
            'question_type': args.question_type,
            'dataset': str(DATASET),
            'episode': args.episode,
            'requested_frames': args.frame,
            'baseline_run': str(args.baseline_run.resolve()),
            'transport_attempts': args.attempts,
            'credential_on_disk': False,
            'scope': 'Single-frame diagnostics; not a method validation claim.',
        },
    )
    write(out / 'status.json', {'phase': 'running', 'started_at': now()})

    results = {}
    try:
        for frame in args.frame:
            images = available[frame]
            builder = (
                build_noul_request
                if args.question_type == 'noul'
                else build_request
            )
            request, image_audit = builder(images, DATASET, model=args.model)
            folder = out / ('frame_%04d' % frame)
            folder.mkdir()
            write(folder / 'request.json', request_without_images(request))
            write(folder / 'images.json', image_audit)
            write(
                folder / 'request.json',
                {
                    **request_without_images(request),
                    'request_sha256': request_digest(request),
                },
            )
            frame_manifest = {
                'frame': frame,
                'image_frames': [row['frame'] for row in images],
                'request_sha256': request_digest(request),
                'questions_zh': translation,
                'baseline_best_v001': baseline[str(frame)]['answer'],
            }
            write(folder / 'manifest.json', frame_manifest)
            if args.dry_run:
                results[str(frame)] = {
                    'phase': 'dry_run',
                    'request_sha256': frame_manifest['request_sha256'],
                }
                continue

            raw, latency, transport = call_api(
                args.endpoint,
                key,
                request,
                args.timeout,
                folder / 'request_full.json',
                attempts=args.attempts,
            )
            if args.question_type == 'noul':
                interpretation = validate_noul_response(raw)
                answer = interpretation
            else:
                interpretation = validate_response(raw)
                answer = {
                    'score': interpretation['score'],
                    'score_continuous_1_5': interpretation[
                        'score_continuous_1_5'
                    ],
                    'confidence': interpretation['confidence'],
                    'directional_probabilities': interpretation[
                        'directional_probabilities'
                    ],
                    'probabilities_1_5': interpretation['probabilities_1_5'],
                }
            result = {
                'phase': 'complete',
                'frame': frame,
                'image_frames': [row['frame'] for row in images],
                'answer': answer,
                'best_v001': baseline[str(frame)]['answer'],
                'request_sha256': frame_manifest['request_sha256'],
                'latency_seconds': latency,
                'transport': transport,
                'scope': 'Single-frame diagnostic only; not a method improvement claim.',
            }
            write(folder / 'response.json', raw)
            write(folder / 'interpretation.json', interpretation)
            write(folder / 'result.json', result)
            results[str(frame)] = result
    except Exception as error:
        detail = str(error).replace(key or '', '[REDACTED]')
        write(
            out / 'partial.json',
            {
                'phase': 'failed',
                'failed_at': now(),
                'episode': args.episode,
                'frames': args.frame,
                'results': results,
                'error': detail,
                'credential_on_disk': False,
            },
        )
        write(
            out / 'status.json',
            {'phase': 'failed', 'finished_at': now(), 'error': detail},
        )
        raise

    summary = {
        'phase': 'dry_run' if args.dry_run else 'complete',
        'finished_at': now(),
        'episode': args.episode,
        'frames': args.frame,
        'model': args.model,
        'endpoint': args.endpoint,
        'results': results,
        'credential_on_disk': False,
    }
    write(out / 'summary.json', summary)
    write(
        out / 'status.json',
        {'phase': summary['phase'], 'finished_at': summary['finished_at']},
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
