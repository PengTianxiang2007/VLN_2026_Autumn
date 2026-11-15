"""Export the five-case Qwen4B versus JEV Noul comparison page."""
import argparse
import base64
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import read, write
from core.jev_node import (
    FALLBACK_CRITERIA_EN,
    FALLBACK_CRITERIA_ZH,
    FALLBACK_INSTRUCTIONS_EN,
    FALLBACK_INSTRUCTIONS_ZH,
    STATE_CONTEXT_EN,
    STATE_CONTEXT_ZH,
)

DATASET = (
    ROOT
    / 'outputs/crossing_dataset/seed2_human_v001/run_20261106_01'
    / 'crossing_seed2_human_v001'
)

PAGE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JEV Noul vs Qwen4B · 离线轨迹对照</title>
<style>
:root{--ink:#17344e;--muted:#65788a;--line:#d9e2eb;--paper:#fff;--bg:#edf2f6;--blue:#2563eb;--teal:#13845c;--red:#b33a3a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif}
header{background:linear-gradient(115deg,#17344e,#1d5a68);color:#fff;padding:22px 26px}header h1{margin:0 0 5px;font-size:24px}.sub{font-size:12px;opacity:.82}
.layout{display:grid;grid-template-columns:245px minmax(650px,1fr) 390px;gap:14px;padding:14px 16px 20px}.panel{background:#fff;border:1px solid var(--line);border-radius:11px;padding:14px;min-width:0}
h2{font-size:18px;margin:0 0 10px}h3{font-size:15px;margin:14px 0 7px}p{margin:7px 0}.muted{color:var(--muted);font-size:12px}
button,select,input,textarea{font:inherit}button,select{border:1px solid #c5d2de;border-radius:6px;padding:6px 8px;background:#fff;color:var(--ink)}button{cursor:pointer}button:hover,button.active{background:#e6f0fb;border-color:#4f8dcc}
#cases button{display:block;width:100%;text-align:left;white-space:pre-line;margin:7px 0;font-size:12px}#cases{max-height:610px;overflow:auto}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;padding:14px 16px 0}.metric,.notice{background:#fff;border:1px solid var(--line);border-radius:10px}.metric{padding:11px 14px}.metric strong{display:block;font-size:24px;font-variant-numeric:tabular-nums}.metric span{font-size:12px;color:var(--muted)}.notice{margin:12px 16px;padding:10px 14px;border-left:4px solid #c58317}
.mapGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.mapTitle{font-weight:700;margin:0 0 5px}.evidenceMap{display:block;width:100%;height:430px;background:#f3f6f9;border-radius:7px}.playback{margin:9px 0}input[type=range]{width:100%;accent-color:var(--blue)}.controls{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:7px 0}.legend{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:12px}.swatch{display:inline-block;width:26px;height:5px;margin-right:5px;vertical-align:middle}
#scorePlot{display:block;width:100%;height:220px;background:#fff}.filterBox{border:1px solid var(--line);border-radius:8px;padding:9px 11px;margin:8px 0;background:#f8fafc}.filterBox strong{display:block;margin-bottom:5px}.filterOptions{display:flex;flex-wrap:wrap;gap:9px 16px;align-items:center;font-size:12px}.filterOptions input[type=range]{width:180px;accent-color:#2563eb}.filterLegend{display:flex;flex-wrap:wrap;gap:5px 13px;font-size:11px;margin-top:6px}.filterLegend i{display:inline-block;width:23px;height:4px;margin-right:4px;vertical-align:middle}#rgb{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#122432;border-radius:7px}.values{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin:10px 0}.value{border:1px solid var(--line);border-radius:7px;padding:8px}.value b{display:block;font-size:18px}.value span{font-size:11px;color:var(--muted)}#history{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}#history button{padding:3px;font-size:11px}#history img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain}pre{white-space:pre-wrap;word-break:break-word;background:#f3f6fa;padding:10px;border-radius:6px;max-height:280px;overflow:auto;font:12px/1.55 ui-monospace,monospace}details{margin:10px 0}summary{cursor:pointer;font-weight:700}.listButton{display:block;width:100%;text-align:left;margin:5px 0;font-size:12px}textarea{width:100%;min-height:70px;border:1px solid #c5d2de;border-radius:6px;padding:8px}.footer{padding:0 18px 20px;color:var(--muted);font-size:12px}
@media(max-width:1250px){.layout{grid-template-columns:230px 1fr}.layout>aside:last-child{grid-column:2}.stats{grid-template-columns:repeat(3,1fr)}}@media(max-width:760px){.layout{display:block}.panel{margin-bottom:12px}.mapGrid{grid-template-columns:1fr}.evidenceMap{height:340px}.stats{grid-template-columns:repeat(2,1fr)}header{padding:18px}h1{font-size:20px}.values{grid-template-columns:1fr}}
</style></head><body>
<header><select id="language" aria-label="Language"><option value="zh">中文</option><option value="en">English</option></select><h1>JEV Noul × Qwen4B · 离线轨迹对照</h1><div class="sub" id="runInfo"></div></header>
<div class="stats" id="stats"></div>
<div class="notice"><span data-i18n="pathLegend"></span> Qwen4B 使用1–5分，JEV使用P(回退点)=0–1；两者量纲不同，页面只做同帧对照，不计算准确率或优劣。</div>
<main class="layout">
<aside class="panel"><h2 data-i18n="cases"></h2><select id="filters"><option value="all" data-i18n="all"></option><option value="failure" data-i18n="failure"></option><option value="success" data-i18n="success"></option></select><div id="cases"></div><button id="export" data-i18n="export"></button><p class="muted">Qwen4B 同帧分数来自 best_v001；JEV 使用同一轨迹，仅改变逐步判断模型。</p></aside>
<section class="panel"><h2 id="title"></h2><p id="caseStats"></p><div class="mapGrid"><div><p class="mapTitle" data-i18n="qwenMap"></p><canvas class="evidenceMap" id="qwenMap"></canvas><div class="legend"><span><i class="swatch" style="background:#d7eee8"></i>1</span><span><i class="swatch" style="background:#a9dbce"></i>2</span><span><i class="swatch" style="background:#73c1ad"></i>3</span><span><i class="swatch" style="background:#3c9f83"></i>4</span><span><i class="swatch" style="background:#126c58"></i>5</span></div></div><div><p class="mapTitle" data-i18n="jevMap"></p><canvas class="evidenceMap" id="jevMap"></canvas><div class="legend"><span><i class="swatch" style="background:rgb(250,224,199)"></i>0</span><span><i class="swatch" style="background:rgb(195,127,114)"></i>.5</span><span><i class="swatch" style="background:rgb(139,29,29)"></i>1</span></div></div></div>
<div class="playback"><label for="frame" data-i18n="mapProgress"></label><input id="frame" type="range" min="0" value="0"><div id="step"></div></div>
<div class="controls"><button id="prev" data-i18n="prev"></button><button id="play" data-i18n="play"></button><button id="next" data-i18n="next"></button><label><input id="reference" type="checkbox"> <span data-i18n="reference"></span></label><label><input id="full" type="checkbox" checked> <span data-i18n="full"></span></label><label><input id="showSampleMapPoints" type="checkbox"> <span data-i18n="showSampleMapPoints"></span></label></div>
<h3 data-i18n="plotTitle"></h3><div class="filterBox"><strong data-i18n="filterTitle"></strong><div class="filterOptions"><label><input id="showQwenLine" type="checkbox" checked> <span data-i18n="qwenLine"></span></label><label><input id="showRawJev" type="checkbox" checked> <span data-i18n="rawJev"></span></label><label><input id="filterGaussian" type="checkbox"> <span data-i18n="gaussian"></span></label><label><input id="filterEma" type="checkbox"> <span data-i18n="ema"></span></label><label><input id="filterMoving" type="checkbox"> <span data-i18n="movingAverage"></span></label><label><input id="filterProminence" type="checkbox"> <span data-i18n="relativeProminence"></span></label><label><input id="filterStreaming" type="checkbox"> <span data-i18n="streamingProminence"></span></label><label><span data-i18n="effectiveWindow"></span> <input id="filterWindow" type="range" min="3" max="31" step="2" value="7"> <output id="filterWindowValue">7</output></label><label><span data-i18n="maxDelay"></span> <input id="streamDelay" type="range" min="0" max="5" step="1" value="5"> <output id="streamDelayValue">5</output></label></div><div class="filterLegend"><span><i style="background:#13845c"></i><span data-i18n="qwenLine"></span></span><span><i style="background:#b33a3a"></i><span data-i18n="rawJev"></span></span><span><i style="background:#7c3aed"></i><span data-i18n="gaussianLine"></span></span><span><i style="background:#2563eb"></i><span data-i18n="emaLine"></span></span><span><i style="background:#d97706"></i><span data-i18n="movingLine"></span></span><span><i style="background:#be185d"></i><span data-i18n="prominenceLine"></span></span><span><i style="background:#0891b2"></i><span data-i18n="streamingLine"></span></span></div><p class="muted" id="filterHint"></p><p class="muted" id="sampleSummary"></p></div><canvas id="scorePlot"></canvas>
<details><summary data-i18n="prompt"></summary><h3>English · actual model input</h3><pre id="promptEnglish"></pre><h3>中文翻译</h3><pre id="promptChinese"></pre></details>
<details><summary data-i18n="protocol"></summary><p>JEV只输入严格 t-2,t-1,t 三帧RGB，并回答一个 fallback_point Noul。没有输入任务、动作、位置、地图、成败、标注、参考路线或旧回答。</p><p>Qwen4B分数来自既有 best_v001 同帧结果，不重新调用。JEV返回P(yes)，没有1–5分、理由或移动动作。路径颜色只复现原始数值，不进行平滑或阈值确认。</p></details>
</section>
<aside class="panel"><h2 data-i18n="current"></h2><img id="rgb" alt="current RGB"><div class="playback"><label for="imageFrame" data-i18n="imageProgress"></label><input id="imageFrame" type="range" min="0" value="0"><div id="imageStep"></div></div><div class="values"><div class="value"><b id="qwenValue"></b><span data-i18n="qwenScore"></span></div><div class="value"><b id="jevValue"></b><span data-i18n="jevProbability"></span></div><div class="value"><b id="delta"></b><span>normalized Δ</span></div></div><p class="muted" id="inputInfo"></p><div id="history"></div>
<h3>复核</h3><select id="category"><option value="">未分类</option><option value="jev_high">JEV概率偏高</option><option value="jev_low">JEV概率偏低</option><option value="qwen_high">Qwen分数偏高</option><option value="qwen_low">Qwen分数偏低</option><option value="both_ok">两者合理</option><option value="other">其他</option></select><textarea id="note" placeholder="记录本帧判断依据"></textarea><p class="muted">意见仅保存在当前浏览器，可通过左侧按钮导出。</p>
<p class="muted" id="instruction"></p></aside></main><div class="footer" id="footer"></div>
<script id="payload" type="application/json">__DATA__</script><script>__SCRIPT__</script></body></html>'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def data_uri(path):
    suffix = Path(path).suffix.lower()
    mime = 'image/jpeg' if suffix in ('.jpg', '.jpeg') else 'image/webp'
    return 'data:' + mime + ';base64,' + base64.b64encode(
        Path(path).read_bytes()
    ).decode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    destination = args.output.resolve()
    if destination.exists():
        raise ValueError('Use a new export directory')
    destination.mkdir(parents=True)
    selection = read(run / 'selection.json')['cases']
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
        if row['episode_id'] in {case['episode_id'] for case in selection}
    ]
    maps = read(DATASET / 'evaluation/maps.json')
    qwen = read(run / 'baseline_predictions.json')
    row_index = (
        {
            (row['episode_id'], row['frame']): row
            for row in read(run / 'rows.json')
        }
        if (run / 'rows.json').is_file()
        else {}
    )
    images = {}
    cases = []
    qwen_scores = []
    jev_probabilities = []
    for case in selection:
        episode_id = case['episode_id']
        episode = episodes[episode_id]
        observations = read(DATASET / episode['observations'])
        trajectory = read(DATASET / case['trajectory'])['frames']
        if len(observations) != len(trajectory):
            raise ValueError('Observation/trajectory mismatch')
        events_for_case = sorted(
            [
                row for row in events
                if row['episode_id'] == episode_id
            ],
            key=lambda row: row['frame'],
        )
        event_by_frame = {row['frame']: row for row in events_for_case}
        frames = []
        for observation, pose in zip(observations, trajectory):
            frame = observation['frame']
            if frame != pose['frame']:
                raise ValueError('Frame order mismatch')
            image_key = observation['rgb_sha256']
            if image_key not in images:
                images[image_key] = data_uri(DATASET / observation['rgb'])
            result_path = (
                run / 'cases' / episode_id / ('F%04d' % frame) / 'result.json'
            )
            jev = row_index.get((episode_id, frame))
            if jev is None and result_path.exists():
                jev = read(result_path)
            qwen_row = qwen[episode_id].get(str(frame))
            q = (
                {'valid': True, 'score': qwen_row['answer']['score']}
                if qwen_row and qwen_row.get('valid')
                else {'valid': False, 'score': None}
            )
            p = (
                {
                    'probability_yes': jev['answer']['probability_yes'],
                    'probability_no': jev['answer']['probability_no'],
                    'image_frames': jev['image_frames'],
                }
                if jev and jev.get('phase') == 'complete'
                else None
            )
            if p:
                jev_probabilities.append(p['probability_yes'])
            if q['valid']:
                qwen_scores.append(q['score'])
            frames.append({
                'frame': frame,
                'position': pose['position'],
                'image': image_key,
                'eligible': observation['eligible_for_inference'],
                'terminal': observation['terminal'],
                'qwen': q,
                'jev': p,
            })
        cases.append({
            'episode_id': episode_id,
            'scene': case['scene'],
            'group': case['group'],
            'instruction_zh': episode['instruction_zh'],
            'instruction_en': episode['instruction'],
            'frames': frames,
            'events': [
                {
                    'index': index,
                    'frame': event['frame'],
                    'position': trajectory[event['frame']]['position'],
                    'type': event['type'],
                }
                for index, event in enumerate(events_for_case)
            ],
            'reference_path': read(DATASET / case['trajectory']).get(
                'reference_path', []
            ),
        })
    map_data = {}
    for scene in {case['scene'] for case in cases}:
        row = maps[scene]
        key = row['sha256']
        if key not in images:
            images[key] = data_uri(DATASET / row['image'])
        map_data[scene] = {'geometry': row['geometry'], 'image': key}
    summary = read(run / 'summary.json')
    source_manifest = read(run / 'manifest.json')
    summary.update(
        qwen_mean_score=sum(qwen_scores) / len(qwen_scores),
        jev_mean_probability=sum(jev_probabilities) / len(jev_probabilities),
        qwen_score_histogram=dict(Counter(map(str, qwen_scores))),
        jev_probability_decile_histogram={
            str(bucket): sum(
                bucket / 10 <= value < (bucket + 1) / 10
                for value in jev_probabilities
            )
            for bucket in range(10)
        },
        comparison=(
            'Same-frame descriptive comparison only. Qwen score and JEV '
            'probability have different scales; no accuracy or superiority claim.'
        ),
        replay_frames=sum(len(case['frames']) for case in cases),
        concurrency=source_manifest.get('concurrency'),
        retry_concurrency=100 if len(cases) == 61 else None,
    )
    prompt_zh = '\n'.join([
        '状态上下文：' + STATE_CONTEXT_ZH,
        '',
        '问题类型：noul',
        '问题：' + FALLBACK_INSTRUCTIONS_ZH,
        '',
        'true：' + FALLBACK_CRITERIA_ZH['true'],
        'false：' + FALLBACK_CRITERIA_ZH['false'],
    ])
    prompt_en = '\n'.join([
        'State context: ' + STATE_CONTEXT_EN,
        '',
        'Question type: noul',
        'Question: ' + FALLBACK_INSTRUCTIONS_EN,
        '',
        'true: ' + FALLBACK_CRITERIA_EN['true'],
        'false: ' + FALLBACK_CRITERIA_EN['false'],
    ])
    payload = {
        'tag': (
            'jev_noul_v002_full61_vs_qwen_best_v001'
            if len(cases) == 61
            else 'jev_noul_v002_five50_vs_qwen_best_v001'
        ),
        'summary': summary,
        'cases': cases,
        'maps': map_data,
        'images': images,
        'prompt_en': prompt_en,
        'prompt_zh': prompt_zh,
    }
    html = PAGE.replace(
        '__DATA__',
        json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace(
            '<', '\\u003c'
        ),
    ).replace(
        '__SCRIPT__',
        (ROOT / 'core/jev_noul_compare_review.js').read_text(),
    )
    from fontTools import subset
    from fontTools.ttLib import TTFont
    config = read(ROOT / 'core/crossing_visualization_template.json')
    font = TTFont(config['font'], fontNumber=0)
    sub = subset.Subsetter()
    sub.populate(text=html)
    sub.subset(font)
    buffer = io.BytesIO()
    font.save(buffer)
    html = html.replace(
        '</head>',
        '<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,'
        + base64.b64encode(buffer.getvalue()).decode()
        + ')}body,button,select,input,textarea{font-family:CrossingSans,sans-serif}'
        '</style></head>',
    )
    output_html = destination / 'jev_noul_vs_qwen.html'
    output_html.write_text(html)
    shutil.copy2(config['font_license'], destination / 'FONT_LICENSE.txt')
    write(
        destination / 'export_manifest.json',
        {
            'source_run': str(run),
            'html_sha256': sha(output_html),
            'cases': len(cases),
            'scope': 'all available selected cases',
            'replay_frames': sum(len(case['frames']) for case in cases),
            'jev_calls': len(jev_probabilities),
            'qwen_frames': len(qwen_scores),
            'images': len(images),
            'prompt_en_sha256': hashlib.sha256(prompt_en.encode()).hexdigest(),
            'prompt_zh_sha256': hashlib.sha256(prompt_zh.encode()).hexdigest(),
        },
    )
    print(json.dumps(
        {
            'html': str(output_html),
            'bytes': output_html.stat().st_size,
            'sha256': sha(output_html),
            'summary': summary,
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == '__main__':
    main()
