"""Export the 34 human wrong-choice points as a bilingual review page."""
import argparse
import base64
import hashlib
import io
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import read, write
from core.jev_node import (
    COMPACT_FALLBACK_CONTEXT_EN,
    COMPACT_FALLBACK_CONTEXT_ZH,
    COMPACT_FALLBACK_CRITERIA_EN,
    COMPACT_FALLBACK_CRITERIA_ZH,
    COMPACT_FALLBACK_INSTRUCTIONS_EN,
    COMPACT_FALLBACK_INSTRUCTIONS_ZH,
)

DATASET = (
    ROOT
    / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01'
    / 'crossing_seed2_human_v001'
)
QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'


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


def image_data(path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        image.thumbnail((640, 480), Image.Resampling.LANCZOS)
        stream = io.BytesIO()
        try:
            image.save(stream, format='WEBP', quality=82, method=4)
            mime = 'image/webp'
        except Exception:
            stream = io.BytesIO()
            image.save(stream, format='JPEG', quality=82, subsampling=0)
            mime = 'image/jpeg'
    payload = stream.getvalue()
    return hashlib.sha256(payload).hexdigest(), (
        'data:' + mime + ';base64,' + base64.b64encode(payload).decode()
    )


def map_data(path):
    payload = Path(path).read_bytes()
    return hashlib.sha256(payload).hexdigest(), (
        'data:image/png;base64,' + base64.b64encode(payload).decode()
    )


def raw_result(run, row):
    folder = run / 'events' / row['event_id']
    if row['provenance'] == 'new_call':
        return read(folder / 'response.json')
    stored = read(folder / 'reuse_source.json')
    return {
        'result_source': 'reused_exact_request',
        'source_run': stored['source_run'],
        'source_answer': stored['answer'],
        'source_request_sha256': stored['request_sha256'],
        'source_transport': stored['transport'],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new export directory')

    manifest = read(run / 'manifest.json')
    summary_run = read(run / 'summary.json')
    rows = read(run / 'rows.json')
    prepared = read(run / 'prepared_events.json')
    if len(rows) != 34 or len(prepared) != 34:
        raise ValueError('Expected exactly 34 events')
    if any(row.get('phase') != 'complete' for row in rows):
        raise ValueError('Cannot export incomplete JEV results')
    if len({row['event_id'] for row in rows}) != 34:
        raise ValueError('Duplicate event IDs')

    rows_by_id = {row['event_id']: row for row in rows}
    prepared_by_id = {row['event_id']: row for row in prepared}
    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    maps_source = read(DATASET / 'evaluation/maps.json')
    images = {}
    maps = {}
    trajectories = {}
    events = []

    for event_id in [row['event_id'] for row in prepared]:
        row = rows_by_id[event_id]
        item = prepared_by_id[event_id]
        episode = episodes[row['episode_id']]
        map_row = maps_source[row['scene']]
        map_key = map_row['sha256']
        if map_key not in images:
            key, uri = map_data(DATASET / map_row['image'])
            if key != map_key:
                raise ValueError('Map hash changed: ' + row['scene'])
            images[key] = uri
        maps[row['scene']] = {
            'image': map_key,
            'geometry': map_row['geometry'],
        }

        if row['episode_id'] not in trajectories:
            trajectory = read(
                DATASET / 'evaluation/trajectories' / (row['episode_id'] + '.json')
            )
            trajectories[row['episode_id']] = [
                [pose['position'][0], pose['position'][2]]
                for pose in trajectory['frames']
            ]

        input_frames = []
        for frame in item['images']:
            path = DATASET / frame['rgb']
            key, uri = image_data(path)
            source_key = frame['rgb_sha256']
            if key not in images:
                images[key] = uri
            input_frames.append({
                'frame': frame['frame'],
                'image': key,
                'source_rgb_sha256': source_key,
            })
        if not input_frames or input_frames[-1]['frame'] != row['frame']:
            raise ValueError('Current input frame mismatch')

        events.append({
            'event_id': row['event_id'],
            'episode_id': row['episode_id'],
            'scene': row['scene'],
            'frame': row['frame'],
            'position': [row['position'][0], row['position'][2]],
            'qwen_score': row['qwen_score'],
            'jev_probability': row['jev_probability_yes'],
            'jev_probability_no': row['jev_probability_no'],
            'request_sha256': row['request_sha256'],
            'model': row['model'],
            'latency_seconds': row['latency_seconds'],
            'provenance': row['provenance'],
            'input_frames': input_frames,
            'current_image': input_frames[-1]['image'],
            'instruction_en': episode['instruction'],
            'instruction_zh': episode['instruction_zh'],
            'raw_result': raw_result(run, row),
        })

    complete = [row for row in rows if row['phase'] == 'complete']
    summary = {
        **summary_run,
        'events': len(events),
        'complete_events': len(complete),
        'expected_events': 34,
        'high_jev_count': sum(
            row['jev_probability_yes'] >= 0.75 for row in complete
        ),
    }
    prompt_en = prompt_text('en')
    prompt_zh = prompt_text('zh')
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        'tag': 'jev_noul_v004_wrong_choices34_prevapi',
        'generated_at': generated_at,
        'summary': summary,
        'events': events,
        'maps': maps,
        'trajectories': trajectories,
        'images': images,
        'prompt_en': prompt_en,
        'prompt_zh': prompt_zh,
    }
    template = (ROOT / 'scripts/templates/jev_wrong_choices34.html').read_text()
    script = (ROOT / 'core/jev_wrong_choices34_review.js').read_text()
    rendered = template.replace(
        '__DATA__',
        json.dumps(
            payload, ensure_ascii=False, separators=(',', ':')
        ).replace('<', '\\u003c'),
    ).replace('__SCRIPT__', script)

    from fontTools import subset
    from fontTools.ttLib import TTFont

    font_config = read(ROOT / 'core/crossing_visualization_template.json')
    font = TTFont(font_config['font'], fontNumber=0)
    subsetter = subset.Subsetter()
    subsetter.populate(text=rendered)
    subsetter.subset(font)
    buffer = io.BytesIO()
    font.save(buffer)
    rendered = rendered.replace(
        '</head>',
        '<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,'
        + base64.b64encode(buffer.getvalue()).decode()
        + ')}body,button,select,input,textarea{font-family:CrossingSans,sans-serif}'
        + '</style></head>',
    )

    output.mkdir(parents=True)
    html = output / 'jev_noul_v004_wrong_choices34.html'
    html.write_text(rendered)
    shutil.copy2(font_config['font_license'], output / 'FONT_LICENSE.txt')
    write(output / 'export_manifest.json', {
        'created_at': generated_at,
        'run': str(run),
        'html': html.name,
        'html_sha256': sha(html),
        'events': len(events),
        'episodes': len(trajectories),
        'valid_results': len(complete),
        'new_calls': summary['new_calls_requested'],
        'reused_results': summary['reused_events'],
        'qwen_scores_sha256': sha(
            QWEN_RUN / 'annotated_point_scores.json'
        ),
        'prompt_en_sha256': hashlib.sha256(prompt_en.encode()).hexdigest(),
        'prompt_zh_sha256': hashlib.sha256(prompt_zh.encode()).hexdigest(),
    })
    print(json.dumps({
        'html': str(html),
        'html_sha256': sha(html),
        'bytes': html.stat().st_size,
        'events': len(events),
        'episodes': len(trajectories),
        'images': len(images),
        'summary': summary,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
