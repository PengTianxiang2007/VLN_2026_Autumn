"""Probe one causal wrong-choice frame through the AnyAIGC OpenAI endpoint."""
import base64
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.jev_node import (
    COMPACT_FALLBACK_CONTEXT_EN,
    COMPACT_FALLBACK_CRITERIA_EN,
    COMPACT_FALLBACK_INSTRUCTIONS_EN,
)


DATASET = (
    ROOT
    / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01'
    / 'crossing_seed2_human_v001'
)


def main():
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
    images = [
        frames[frame] for frame in (event['frame'] - 2, event['frame'] - 1, event['frame'])
    ]
    content = []
    for image in images:
        content.append({
            'type': 'text',
            'text': 'RGB observation frame %d:' % image['frame'],
        })
        path = DATASET / image['rgb']
        suffix = path.suffix.lower()
        mime = 'image/jpeg' if suffix in ('.jpg', '.jpeg') else 'image/png'
        content.append({
            'type': 'image_url',
            'image_url': {
                'url': 'data:' + mime + ';base64,'
                       + base64.b64encode(path.read_bytes()).decode()
            },
        })
    content.append({
        'type': 'text',
        'text': '\n'.join([
            'Question type: noul',
            COMPACT_FALLBACK_INSTRUCTIONS_EN,
            '',
            'true: ' + COMPACT_FALLBACK_CRITERIA_EN['true'],
            'false: ' + COMPACT_FALLBACK_CRITERIA_EN['false'],
            '',
            'Return only the probability that the answer is yes.',
        ]),
    })
    request_value = {
        'model': 'jev-1.14.0',
        'messages': [
            {'role': 'system', 'content': COMPACT_FALLBACK_CONTEXT_EN},
            {'role': 'user', 'content': content},
        ],
        'temperature': 0,
        'max_tokens': 128,
        'response_format': {
            'type': 'json_schema',
            'json_schema': {
                'name': 'fallback_probability',
                'strict': True,
                'schema': {
                    'type': 'object',
                    'properties': {
                        'probability_yes': {
                            'type': 'number',
                            'minimum': 0,
                            'maximum': 1,
                        },
                    },
                    'required': ['probability_yes'],
                    'additionalProperties': False,
                },
            },
        },
    }
    request = urllib.request.Request(
        'https://anyaigc.ai/v1/chat/completions',
        data=json.dumps(request_value).encode(),
        headers={
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=120) as response:
            raw = json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors='replace').replace(key, '[REDACTED]')
        raise RuntimeError('HTTP %d: %s' % (error.code, body[:3000])) from None
    out = ROOT / 'outputs/crossing_checkpoint/jev_noul_v004/wrong_choices34_anyaigc_20261109_01'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'probe_response.json').write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + '\n'
    )
    print(json.dumps(raw, ensure_ascii=False, indent=2)[:6000])


if __name__ == '__main__':
    main()
