"""Export one bilingual StreamVLN + live-JEV VLNVerse review page."""
import base64
import gzip
import hashlib
import io
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.agent_route_choice import now, write
from core.jev_node import (
    COMPACT_FALLBACK_CONTEXT_EN,
    COMPACT_FALLBACK_CONTEXT_ZH,
    COMPACT_FALLBACK_CRITERIA_EN,
    COMPACT_FALLBACK_CRITERIA_ZH,
    COMPACT_FALLBACK_INSTRUCTIONS_EN,
    COMPACT_FALLBACK_INSTRUCTIONS_ZH,
)


RUN = (
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v004/'
    / 'vlnverse_live_0272_40/run_20261109_01'
)
NAV_RUN = (
    ROOT
    / 'outputs/vlnverse/streamvln/results/'
    / 'peng_fine_streamvln_physical_20261109_01_0272jev'
)
DATASET = (
    Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng')
    / 'assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz'
)
OUTPUT = (
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v004/'
    / 'vlnverse_live_0272_40/exports/run_20261109_04_template'
)
MAP_DIR = (
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v004/'
    / 'vlnverse_live_0272_40/maps_cpu/run_20261109_01/'
    / 'scenes/kujiale_0272'
)
INSTRUCTION_ZH = (
    ROOT
    / 'experiments/crossing_checkpoint/jev_live_vlnverse/'
    / 'run_20261109_01_0272_40/instructions_zh.json'
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prompt_text(language):
    if language == 'en':
        return '\n'.join([
            'State context: ' + COMPACT_FALLBACK_CONTEXT_EN,
            '',
            'Question type: noul',
            'Question: ' + COMPACT_FALLBACK_INSTRUCTIONS_EN,
            '',
            'true: ' + COMPACT_FALLBACK_CRITERIA_EN['true'],
            'false: ' + COMPACT_FALLBACK_CRITERIA_EN['false'],
        ])
    return '\n'.join([
        '状态上下文：' + COMPACT_FALLBACK_CONTEXT_ZH,
        '',
        '问题类型：noul',
        '问题：' + COMPACT_FALLBACK_INSTRUCTIONS_ZH,
        '',
        'true：' + COMPACT_FALLBACK_CRITERIA_ZH['true'],
        'false：' + COMPACT_FALLBACK_CRITERIA_ZH['false'],
    ])


def actual_episode_id(path_key, known):
    matches = [episode_id for episode_id in known if episode_id in path_key]
    if not matches:
        raise ValueError('Cannot map path key: ' + path_key)
    return max(matches, key=len)


def image_data(path):
    with Image.open(path) as source:
        image = source.convert('RGB')
        image.thumbnail((640, 480), Image.Resampling.LANCZOS)
        stream = io.BytesIO()
        try:
            image.save(stream, format='WEBP', quality=82, method=4)
            mime = 'image/webp'
        except Exception:
            stream = io.BytesIO()
            image.save(stream, format='JPEG', quality=82, subsampling=0)
            mime = 'image/jpeg'
    raw = stream.getvalue()
    return hashlib.sha256(raw).hexdigest(), (
        'data:' + mime + ';base64,' + base64.b64encode(raw).decode()
    )


def map_data(path):
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), (
        'data:image/png;base64,' + base64.b64encode(raw).decode()
    )


def percentiles(values):
    ordered = sorted(values)
    return {
        str(q): ordered[
            min(len(ordered) - 1, int(math.ceil(q / 100 * len(ordered))) - 1)
        ]
        for q in (50, 90, 95, 99)
    }


def main():
    if OUTPUT.exists():
        raise ValueError('Use a new export directory')
    with gzip.open(DATASET, 'rt') as stream:
        dataset_rows = json.load(stream)['episodes']
    dataset = {row['episode_id']: row for row in dataset_rows}
    known = [
        row['episode_id'] for row in dataset_rows
        if row['scan'] == 'kujiale_0272'
    ]
    if len(known) != 40:
        raise ValueError('Expected 40 kujiale_0272 episodes')
    translated_instructions = json.loads(INSTRUCTION_ZH.read_text())
    if set(translated_instructions) != set(known):
        raise ValueError('Chinese instruction mapping is incomplete or changed')
    official = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (NAV_RUN / 'episodes.jsonl').read_text().splitlines(),
        )
        if row
    }
    episodes = []
    for path in RUN.glob('seed_0/kujiale_0272/*/attempt_*/episode.json'):
        data = json.loads(path.read_text())
        episode_id = actual_episode_id(data['path_key'], known)
        episodes.append((episode_id, data, path.parent))
    episodes.sort(key=lambda item: item[0])
    if len(episodes) != 40 or len({row[0] for row in episodes}) != 40:
        raise ValueError('Live JEV episode set is incomplete or duplicated')

    images = {}
    map_path = MAP_DIR / 'floorplan.png'
    map_geometry = json.loads((MAP_DIR / 'geometry.json').read_text())
    map_key, map_uri = map_data(map_path)
    images[map_key] = map_uri
    cases = []
    all_latency = []
    all_probability = []
    all_lag = []
    frame_count = 0
    for episode_id, data, directory in episodes:
        actions = data.get('actions', [])
        calls = {
            row['stream_index']: row
            for row in data.get('calls', [])
            if row.get('stream_index') is not None
        }
        frames = []
        for index, action in enumerate(actions):
            image_path = directory / 'frames' / ('F%06d.jpg' % index)
            if not image_path.exists():
                raise FileNotFoundError(image_path)
            image_key, image_uri = image_data(image_path)
            images[image_key] = image_uri
            call = calls.get(index)
            probability = None
            if call and call.get('phase') == 'complete':
                probability = float(call['answer']['probability_yes'])
                all_probability.append(probability)
                all_latency.append(float(call['latency_seconds']))
                if call.get('unresolved_step_lag') is not None:
                    all_lag.append(int(call['unresolved_step_lag']))
            frames.append({
                'frame': index,
                'image': image_key,
                'action': action.get('action'),
                'position': action.get('position'),
                'jev': None if call is None else {
                    'probability_yes': probability,
                    'latency_seconds': call.get('latency_seconds'),
                    'unresolved_step_lag': call.get('unresolved_step_lag'),
                    'image_frames': call.get('image_frames', []),
                    'phase': call.get('phase'),
                },
            })
        truth = dataset[episode_id]
        metrics = official[episode_id]
        case = {
            'episode_id': episode_id,
            'scene': 'kujiale_0272',
            'group': 'success' if metrics['SR'] == 1 else 'failure',
            'instruction_en': truth['instruction']['instruction_text'],
            'instruction_zh': translated_instructions[episode_id],
            'reference_path': truth.get('reference_path', []),
            'pred_path': metrics.get('pred_path', []),
            'metrics': {
                key: metrics[key]
                for key in ('SR', 'SPL', 'NE', 'OS', 'TL', 'FR', 'StR', 'steps')
            },
            'fail_reason': metrics.get('fail_reason'),
            'frames': frames,
            'streaming': {
                'raw': data['streaming']['raw'],
                'filtered': data['streaming']['filtered'],
                'nodes': data['streaming']['nodes'],
                'window_n': data['streaming']['window_n'],
                'max_delay_steps': data['streaming']['max_delay_steps'],
            },
        }
        cases.append(case)
        frame_count += len(frames)

    if frame_count != sum(len(case['frames']) for case in cases):
        raise ValueError('Frame count mismatch')
    navigation = json.loads((NAV_RUN / 'result.json').read_text())
    nav = navigation['official_result']['val_unseen']
    nodes = sum(len(case['streaming']['nodes']) for case in cases)
    summary = {
        'episodes': len(cases),
        'success': sum(case['group'] == 'success' for case in cases),
        'frames': frame_count,
        'valid_calls': len(all_probability),
        'failed_calls': 0,
        'mean_probability': statistics.mean(all_probability),
        'mean_latency': statistics.mean(all_latency),
        'max_latency': max(all_latency),
        'latency_percentiles': percentiles(all_latency),
        'max_step_lag': max(all_lag),
        'streaming_nodes': nodes,
        'window_n': 11,
        'max_delay_steps': 5,
        'navigation': nav,
        'groups': dict(Counter(case['group'] for case in cases)),
    }
    payload = {
        'tag': 'streamvln_isaacsim_live_jev_kujiale_0272_40',
        'summary': summary,
        'cases': cases,
        'images': images,
        'map': {
            'image': map_key,
            'geometry': map_geometry,
        },
        'prompt_en': prompt_text('en'),
        'prompt_zh': prompt_text('zh'),
    }
    page = (ROOT / 'scripts/templates/jev_live_vlnverse_v2.html').read_text()
    script = (ROOT / 'core/jev_live_vlnverse_review_v2.js').read_text()
    rendered = page.replace(
        '__DATA__',
        json.dumps(
            payload, ensure_ascii=False, separators=(',', ':')
        ).replace('<', '\\u003c'),
    ).replace('__SCRIPT__', script)
    OUTPUT.mkdir(parents=True)
    html = OUTPUT / 'streamvln_live_jev_0272_40.html'
    html.write_text(rendered)
    write(OUTPUT / 'export_manifest.json', {
        'created_at': now(),
        'run': str(RUN),
        'navigation_run': str(NAV_RUN),
        'html': str(html),
        'html_sha256': sha(html),
        'cases': len(cases),
        'frames': frame_count,
        'calls': len(all_probability),
        'images': len(images),
        'nodes': nodes,
        'map_image': str(map_path),
        'map_sha256': sha(map_path),
        'summary': summary,
        'source_sha256': {
            'core/jev_live_vlnverse_review_v2.js': sha(
                ROOT / 'core/jev_live_vlnverse_review_v2.js'
            ),
            'scripts/templates/jev_live_vlnverse_v2.html': sha(
                ROOT / 'scripts/templates/jev_live_vlnverse_v2.html'
            ),
            str(NAV_RUN / 'episodes.jsonl'): sha(NAV_RUN / 'episodes.jsonl'),
            str(NAV_RUN / 'result.json'): sha(NAV_RUN / 'result.json'),
            str(MAP_DIR / 'geometry.json'): sha(MAP_DIR / 'geometry.json'),
            str(map_path): sha(map_path),
        },
    })
    print(json.dumps({
        'html': str(html),
        'html_sha256': sha(html),
        'cases': len(cases),
        'frames': frame_count,
        'calls': len(all_probability),
        'images': len(images),
        'nodes': nodes,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
