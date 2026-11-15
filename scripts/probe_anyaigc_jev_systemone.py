"""Probe one error point through the native SystemOne/JEV endpoint."""
import argparse
import getpass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.agent_route_choice import write
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
OUTPUT = ROOT / 'outputs/crossing_checkpoint/jev_noul_v004/wrong_choices34_anyaigc_20261109_01'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='jev-1.14.0')
    parser.add_argument('--tag', default='probe_systemone')
    parser.add_argument(
        '--endpoint', default='https://anyaigc.ai/v1/systemone'
    )
    args = parser.parse_args()
    key = os.environ.get('JEV_API_KEY', '')
    if not key:
        key = getpass.getpass('JEV API key: ') if sys.stdin.isatty() else sys.stdin.readline()
    key = key.strip()
    if not key:
        raise RuntimeError('A bearer key is required')
    events = [
        json.loads(line)
        for line in (DATASET / 'evaluation/events.jsonl').read_text().splitlines()
        if line.strip()
    ]
    event = next(
        row for row in events
        if row['type'] == 'wrong_choice'
        and row['episode_id'] == 'kujiale_0036_0_0'
        and row['frame'] == 37
    )
    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    observations = json.loads(
        (DATASET / episodes[event['episode_id']]['observations']).read_text()
    )
    frames = {row['frame']: row for row in observations}
    images = [frames[frame] for frame in (35, 36, 37)]
    request, audit = build_compact_fallback_noul_request(
        images, DATASET, model=args.model
    )
    folder = OUTPUT / args.tag
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / 'images.json', audit)
    write(folder / 'request.json', {
        **request_without_images(request),
        'request_sha256': request_digest(request),
        'question_version': 'v004',
    })
    raw, latency, transport = call_api(
        args.endpoint,
        key,
        request,
        120,
        folder / 'request_full.json',
        attempts=5,
    )
    probability = validate_noul_response(raw)
    write(folder / 'response.json', raw)
    write(folder / 'result.json', {
        'event_id': event['id'],
        'episode_id': event['episode_id'],
        'frame': event['frame'],
        'image_frames': [35, 36, 37],
        'answer': probability,
        'model': args.model,
        'request_sha256': request_digest(request),
        'latency_seconds': latency,
        'transport': transport,
    })
    print(json.dumps({
        'probability': probability,
        'latency_seconds': latency,
        'transport': transport,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
