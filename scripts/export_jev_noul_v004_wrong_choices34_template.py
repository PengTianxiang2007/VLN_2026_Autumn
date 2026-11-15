"""Reuse the 12-case Qwen/JEV page for the 34 human wrong-choice points."""
import argparse
import base64
import hashlib
import io
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

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
from export_jev_noul_compare import PAGE, sha

DATASET = (
    ROOT
    / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01'
    / 'crossing_seed2_human_v001'
)
QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'


def data_uri(path):
    suffix = Path(path).suffix.lower()
    mime = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
    }[suffix]
    return 'data:' + mime + ';base64,' + base64.b64encode(
        Path(path).read_bytes()
    ).decode()


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


def qwen_answer(episode_id, frame):
    path = QWEN_RUN / 'cases' / episode_id / ('F%04d.response.json' % frame)
    if not path.exists():
        return {'valid': False, 'score': None}
    row = read(path)
    return {
        'valid': bool(row.get('valid')),
        'score': row.get('answer', {}).get('score') if row.get('valid') else None,
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

    prepared = read(run / 'prepared_events.json')
    rows = read(run / 'rows.json')
    run_summary = read(run / 'summary.json')
    rows_by_event = {row['event_id']: row for row in rows}
    episodes = {
        row['episode_id']: row
        for row in map(
            json.loads,
            (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
        )
    }
    events = [
        row for row in map(
            json.loads,
            (DATASET / 'evaluation/events.jsonl').read_text().splitlines(),
        )
        if row['episode_id'] in {
            item['episode_id'] for item in prepared
        }
    ]
    maps_source = read(DATASET / 'evaluation/maps.json')
    images = {}
    maps = {}
    cases = []
    qwen_scores = []
    jev_probabilities = []

    for item in prepared:
        row = rows_by_event[item['event_id']]
        if row.get('phase') != 'complete':
            raise ValueError('Incomplete JEV result: ' + item['event_id'])
        real_episode_id = row['episode_id']
        episode = episodes[real_episode_id]
        observations = read(DATASET / episode['observations'])
        trajectory_doc = read(
            DATASET / 'evaluation/trajectories' / (real_episode_id + '.json')
        )
        trajectory = trajectory_doc['frames']
        if len(observations) != len(trajectory):
            raise ValueError('Observation/trajectory mismatch')
        if any(
            observation['frame'] != index
            for index, observation in enumerate(observations)
        ):
            raise ValueError('Observation frames are not contiguous')

        map_row = maps_source[row['scene']]
        map_key = map_row['sha256']
        if map_key not in images:
            images[map_key] = data_uri(DATASET / map_row['image'])
        maps[row['scene']] = {
            'geometry': map_row['geometry'],
            'image': map_key,
        }

        frames = []
        for observation, pose in zip(observations, trajectory):
            frame = observation['frame']
            if frame != pose['frame']:
                raise ValueError('Frame order mismatch')
            image_key = observation['rgb_sha256']
            if image_key not in images:
                images[image_key] = data_uri(DATASET / observation['rgb'])
            qwen = qwen_answer(real_episode_id, frame)
            jev = None
            if frame == row['frame']:
                jev = {
                    'probability_yes': row['jev_probability_yes'],
                    'probability_no': row['jev_probability_no'],
                    'image_frames': row['image_frames'],
                }
            frames.append({
                'frame': frame,
                'position': pose['position'],
                'image': image_key,
                'eligible': observation['eligible_for_inference'],
                'terminal': observation['terminal'],
                'qwen': qwen,
                'jev': jev,
            })

        episodes_events = sorted(
            [
                event for event in events
                if event['episode_id'] == real_episode_id
            ],
            key=lambda event: event['frame'],
        )
        display_id = '%s · F%d' % (real_episode_id, row['frame'])
        cases.append({
            'episode_id': display_id,
            'real_episode_id': real_episode_id,
            'event_id': row['event_id'],
            'initial_index': row['frame'],
            'scene': row['scene'],
            'group': 'failure',
            'instruction_zh': episode['instruction_zh'],
            'instruction_en': episode['instruction'],
            'frames': frames,
            'events': [
                {
                    'index': event['frame'],
                    'frame': event['frame'],
                    'position': trajectory[event['frame']]['position'],
                    'type': event['type'],
                }
                for event in episodes_events
            ],
            'reference_path': trajectory_doc.get('reference_path', []),
        })
        qwen_scores.append(row['qwen_score'])
        jev_probabilities.append(row['jev_probability_yes'])

    prompt_en = prompt_text('en')
    prompt_zh = prompt_text('zh')
    summary = {
        'cases': len(cases),
        'groups': {'failure': len(cases), 'success': 0},
        'valid_calls': len(rows),
        'expected_calls': len(rows),
        'replay_frames': sum(len(case['frames']) for case in cases),
        'qwen_mean_score': sum(qwen_scores) / len(qwen_scores),
        'jev_mean_probability': sum(jev_probabilities) / len(jev_probabilities),
        'qwen_score_histogram': dict(Counter(map(str, qwen_scores))),
        'jev_probability_decile_histogram': {
            str(bucket): sum(
                bucket / 10 <= value < (bucket + 1) / 10
                for value in jev_probabilities
            )
            for bucket in range(10)
        },
        'concurrency': run_summary['requested_concurrency_limit'],
        'actual_max_workers': run_summary['actual_max_workers'],
        'reused_calls': run_summary['reused_events'],
        'new_calls': run_summary['new_calls_requested'],
        'comparison': (
            'Same-frame descriptive comparison only. Qwen score and JEV '
            'probability have different scales; no accuracy or superiority claim.'
        ),
    }
    payload = {
        'tag': 'jev_noul_v004_wrong_choices34_qwen4b',
        'summary': summary,
        'cases': cases,
        'maps': maps,
        'images': images,
        'prompt_en': prompt_en,
        'prompt_zh': prompt_zh,
    }
    page = PAGE.replace(
        '<title>JEV Noul vs Qwen4B · 离线轨迹对照</title>',
        '<title>人工错误选择 34点 · JEV v004 × Qwen4B</title>',
    ).replace(
        'JEV Noul × Qwen4B · 离线轨迹对照',
        '人工错误选择 34点 · JEV v004 × Qwen4B',
    ).replace(
        'Qwen4B 同帧分数来自 best_v001；JEV 使用同一轨迹，仅改变逐步判断模型。',
        'Qwen4B逐帧分数复用最初best_v001；JEV v004只显示本批34个错误选择点。'
        '页面按错误点进入对应轨迹，折线、滤波、窗口和地图交互沿用12例版本。',
    ).replace(
        'kujiale_0123_fix_15_3 · 90个有效观测 · 90进程同时提交',
        '34个错误选择点 · 29新调用＋5精确复用 · 并发上限500 · 实际29 worker',
    )
    page = page.replace(
        '__DATA__',
        json.dumps(
            payload, ensure_ascii=False, separators=(',', ':')
        ).replace('<', '\\u003c'),
    ).replace('__SCRIPT__', (ROOT / 'core/jev_noul_compare_review.js').read_text())

    from fontTools import subset
    from fontTools.ttLib import TTFont

    font_config = read(ROOT / 'core/crossing_visualization_template.json')
    font = TTFont(font_config['font'], fontNumber=0)
    subsetter = subset.Subsetter()
    subsetter.populate(text=page)
    subsetter.subset(font)
    buffer = io.BytesIO()
    font.save(buffer)
    page = page.replace(
        '</head>',
        '<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,'
        + base64.b64encode(buffer.getvalue()).decode()
        + ')}body,button,select,input,textarea{font-family:CrossingSans,sans-serif}'
        + '</style></head>',
    )

    output.mkdir(parents=True)
    html = output / 'jev_noul_v004_vs_qwen4b.html'
    html.write_text(page)
    shutil.copy2(font_config['font_license'], output / 'FONT_LICENSE.txt')
    write(output / 'export_manifest.json', {
        'run': str(run),
        'html_sha256': sha(html),
        'cases': len(cases),
        'frames': summary['replay_frames'],
        'valid_points': len(rows),
        'qwen_frames': sum(
            frame['qwen']['valid']
            for case in cases for frame in case['frames']
        ),
        'jev_points': sum(
            frame['jev'] is not None
            for case in cases for frame in case['frames']
        ),
        'prompt_en_sha256': hashlib.sha256(prompt_en.encode()).hexdigest(),
        'prompt_zh_sha256': hashlib.sha256(prompt_zh.encode()).hexdigest(),
    })
    print(json.dumps({
        'html': str(html),
        'html_sha256': sha(html),
        'bytes': html.stat().st_size,
        'summary': summary,
        'images': len(images),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
