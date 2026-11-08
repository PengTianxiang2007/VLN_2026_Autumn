"""Audit score-only requests and export a variant of the default dual-slider template."""
import base64
from collections import Counter
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import read, write, now
from core.crossing_lite import digest, sha, request, request_seed, validate

PAGE = '''<body>
<header><h1>Crossing · 三帧五级评分离线复核</h1><div id="runInfo"></div><div class="sub">Qwen3.5-4B · RGB t−2 / t−1 / t · 掉头计为分支</div></header>
<section class="campaign"><h2>方法版本</h2><select id="version" aria-label="同帧版本切换"></select><p>原始逐步分数，不进行平滑或存档确认。地图、导航成败与人工标注只用于本页复核。</p></section>
<div class="stats" id="stats"></div><div class="notice">蓝色 C 是人工标注点；红色 P 是达到展示阈值的连续片段起点，仅方便定位，不代表已确认存档或正确检测。未标帧没有被当作负类，不计算旧版 1 米匹配成绩。</div>
<main class="layout">
<aside class="panel"><h2>轨迹列表</h2><select id="filters"><option value="all">全部轨迹</option><option value="failure">原导航失败</option><option value="success">原导航成功</option></select><div id="cases"></div>
<p>展示阈值 <select id="threshold"><option>1</option><option>2</option><option>3</option><option selected>4</option><option>5</option></select>（不改变原始分数）</p><button id="export">导出复核意见</button><details><summary>实际英文提示词</summary><pre id="prompt"></pre></details></aside>
<section class="panel"><h2 id="title"></h2><p id="mapCounts"></p><canvas id="map" aria-label="人工C与高分片段P位置对照"></canvas>
<div id="mapPlayback" class="playbackControls"><label for="frame">回放进度 · 地图与画面同步</label><input id="frame" type="range" min="0" value="0"><div id="step"></div><div class="controls"><button id="prev">上一步</button><button id="play">顺序回放</button><button id="next">下一步</button><select id="speed"><option value="1000">1秒/步</option><option value="500" selected>0.5秒/步</option><option value="200">0.2秒/步</option></select></div></div>
<div class="legend"><span class="blue">● C 人工点</span><span class="red">◆ P 高分片段起点</span><span class="green">实际轨迹</span></div><div class="controls"><label><input id="showPrior" type="checkbox" checked>人工 C</label><label><input id="showCurrent" type="checkbox" checked>展示 P</label><label><input id="full" type="checkbox" checked>完整轨迹</label></div>
<h3>每步原始分数 · 点击曲线跳转</h3><canvas id="scorePlot" style="width:100%;height:150px"></canvas>
<div class="annotationGrid"><div class="annotationBox"><h3>人工 Crossing 点</h3><div id="priorList"></div></div><div class="annotationBox"><h3>高分片段起点</h3><div id="currentList"></div></div></div><p id="instruction" class="muted"></p><p id="caseStats"></p>
<details><summary>协议与解释边界</summary><p>每个有效观测独立评分1–5。返回方向计为分支，因此普通走廊也可能高分。约十步仅为粗略上限，不是精确距离估计。人工点为旧标注参照，定义是否一致仍需复核；无完整逐帧负标签，不报告精确率、召回率或F1。</p><p>只输入当前及过去两帧原始RGB，不输入指令、动作、未来图像、地图、坐标、标签、导航结果或先前模型回答。末尾复用图像不推理。模型没有生成或恢复实际存档。</p></details></section>
<aside class="panel" id="detail"><h2>当前观测与模型判断</h2><img id="rgb" alt="当前RGB"><div id="imagePlayback" class="playbackControls"><label for="imageFrame">回放进度 · 地图与画面同步</label><input id="imageFrame" type="range" min="0" value="0"><div id="imageStep"></div></div><div id="state"></div><p id="inputInfo"></p><pre id="answer"></pre><details open><summary>本次实际输入的三帧</summary><div id="history"></div></details><details><summary>原始模型回答与请求信息</summary><pre id="raw"></pre></details><h3>此刻存档状态</h3><div id="memory">本版仅评分，未建立存档；历史模型回答未作为输入。</div>
<h3>本帧复核意见</h3><select id="category"><option value="">未分类</option><option value="correct">判断合理</option><option value="early">远处选择过早计入</option><option value="miss">漏掉近处分支</option><option value="uturn">掉头分支判断问题</option><option value="uncertain">证据不足</option><option value="other">其他</option></select><textarea id="note" placeholder="记录本帧判断依据"></textarea><div id="notesStatus"></div></aside></main>
<div class="audit" id="footer"></div><dialog id="imageDialog"><button id="closeImage">关闭</button><img id="largeImage" alt="观测大图"></dialog>
<script id="payload" type="application/json">__DATA__</script><script>__SCRIPT__</script></body></html>'''


def build(out, destination):
    destination.mkdir(parents=True, exist_ok=False)
    c = read(out / 'protocol.json')
    manifest = read(out / 'manifest.json')
    source = Path(c['dataset'])
    prompt = (out / 'prompt_en.txt').read_text()
    assert sha(out / 'prompt_en.txt') == manifest['prompt_sha256']
    selection = read(out / 'evaluation_selection.json')
    assert sha(out / 'evaluation_selection.json') == manifest['selection_sha256']
    tasks = {}
    for i in range(c['concurrency']):
        p = out / ('tasks_%d.json' % i)
        assert sha(p) == manifest['task_hashes'][p.name]
        tasks.update({r['episode_id']: r for r in read(p)})
    images = {}
    def embed(path, expected):
        raw = path.read_bytes()
        assert sha(path) == expected
        if expected not in images:
            images[expected] = 'data:image/' + path.suffix[1:] + ';base64,' + base64.b64encode(raw).decode()
        return expected
    episodes = {r['episode_id']: r for r in map(json.loads, (source / 'inputs/episodes.jsonl').read_text().splitlines())}
    events = [json.loads(s) for s in (source / 'evaluation/events.jsonl').read_text().splitlines()]
    cases = []
    audit = []
    latencies = []
    nvalid = nresponse = naudit = nattempted = 0
    for selected in selection:
        eid = selected['episode_id']
        ep = episodes[eid]
        obs = read(source / ep['observations'])
        trajectory = read(source / selected['trajectory'])['frames']
        assert len(obs) == len(trajectory)
        predictions = {}
        for task in tasks[eid]['frames']:
            t = task['frame']
            prefix = out / 'cases' / eid / ('F%04d' % t)
            reqpath, respath = prefix.with_suffix('.request.json'), prefix.with_suffix('.response.json')
            if reqpath.exists():
                req = read(reqpath)
                seed = request_seed(eid, t, c['seed'])
                assert req['images'] == task['images']
                assert req['request_sha256'] == digest(request(prompt, task['images'], source, c['model'], seed))
                assert req['preview'] == request(prompt, task['images'], source, c['model'], seed, False)
                assert req['image_frames'] == list(range(max(0, t - 2), t + 1))
                naudit += 1
            if not respath.exists():
                continue
            assert reqpath.exists()
            result = read(respath)
            assert result['frame'] == t and result['image_frames'] == req['image_frames']
            raw = result.get('response')
            nattempted += 1
            nresponse += int(raw is not None)
            if raw is not None:
                latencies.append(result['latency_seconds'])
            valid = False
            answer = None
            try:
                choice = raw['choices'][0]
                assert choice['finish_reason'] == 'stop'
                answer = validate(json.loads(choice['message']['content']))
                valid = True
            except (ValueError, TypeError, KeyError, AssertionError):
                pass
            assert valid == result['valid']
            if valid:
                assert result['answer'] == answer
                nvalid += 1
            predictions[t] = dict(score=answer['score'] if valid else None, answer=answer if valid else None,
                raw=raw, error=result.get('validation_error'), image_frames=req['image_frames'],
                request_sha256=req['request_sha256'], latency_seconds=result['latency_seconds'], valid=valid)
            audit.append(dict(episode_id=eid, frame=t, request_sha256=req['request_sha256'], response_sha256=sha(respath), valid=valid))
        frames = []
        for row, pose in zip(obs, trajectory):
            assert row['frame'] == pose['frame'] == len(frames)
            f = row['frame']
            frames.append(dict(frame=f, position=pose['position'], image=embed(source / row['rgb'], row['rgb_sha256']),
                               eligible=row['eligible_for_inference'], terminal=row['terminal'],
                               prediction=predictions.get(f)))
        marks = [dict(e, display_id='C%02d' % (i + 1)) for i, e in enumerate(sorted(
            [e for e in events if e['episode_id'] == eid], key=lambda e: e['frame']))]
        cases.append(dict(episode_id=eid, scene=selected['scene'], group=selected['group'], frames=frames,
                          marks=marks, instruction=ep['instruction_zh'], expected=len(tasks[eid]['frames'])))
    maps = {}
    for scene in {x['scene'] for x in selection}:
        m = read(source / 'evaluation/maps.json')[scene]
        maps[scene] = dict(geometry=m['geometry'], image=embed(source / m['image'], m['sha256']))
    histogram = Counter(str(f['prediction']['score']) for case in cases for f in case['frames']
                        if f['prediction'] and f['prediction']['valid'])
    point_scores = []
    for case in cases:
        for e in case['marks']:
            prediction = case['frames'][e['frame']]['prediction']
            point_scores.append(dict(episode_id=case['episode_id'], group=case['group'], event_id=e['id'], frame=e['frame'],
                                     score=prediction['score'] if prediction else None, type=e['type']))
    summary = dict(episodes=len(cases), groups=dict(Counter(x['group'] for x in selection)),
        expected_calls=c['expected_calls'], attempted_calls=nattempted, responses=nresponse, valid_calls=nvalid,
        invalid_or_missing=c['expected_calls'] - nvalid, audited_requests=naudit,
        score_histogram=dict(sorted(histogram.items())), replay_frames=sum(len(x['frames']) for x in cases),
        annotation_points=len(point_scores), mean_latency_seconds=sum(latencies) / len(latencies) if latencies else None,
        evaluation='Raw score distribution and exact annotated-point scores only. No unlabeled-frame negatives or PR/F1.',
        created_at=now())
    write(out / 'summary.json', summary)
    write(out / 'annotated_point_scores.json', point_scores)
    write(out / 'request_audit.json', dict(passed=True, audited_requests=naudit, results=audit))
    data = dict(tag=c['tag'], version=c['version'], prompt=prompt, summary=summary, cases=cases,
                maps=maps, images=images, manifest_sha256=sha(out / 'manifest.json'))
    # Preserve the approved template's CSS/layout and dual progress controls, with score-specific semantics.
    template = (ROOT / 'core/crossing_campaign_template.html').read_text()
    head = template.split('</head>', 1)[0]
    panel_style = (ROOT / 'core/crossing_campaign_panel.html').read_text().split('</style>', 1)[0] + '</style>'
    page = head + panel_style + '<style>#scorePlot{cursor:crosshair}#history{grid-template-columns:repeat(3,1fr)}#cases button{overflow-wrap:anywhere}.layout>*{min-width:0}#version{max-width:100%}</style></head>' + PAGE
    page = page.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
    page = page.replace('__SCRIPT__', (ROOT / 'core/crossing_lite_review.js').read_text())
    from fontTools import subset
    from fontTools.ttLib import TTFont
    cfg = read(ROOT / 'core/crossing_visualization_template.json')
    font = TTFont(cfg['font'], fontNumber=0)
    sub = subset.Subsetter()
    sub.populate(text=PAGE + (ROOT / 'core/crossing_lite_review.js').read_text() + json.dumps(summary, ensure_ascii=False)
                 + ''.join(case['instruction'] for case in cases) + json.dumps(audit, ensure_ascii=False)
                 + ''.join(json.dumps(f['prediction'], ensure_ascii=False) for case in cases for f in case['frames'] if f['prediction']))
    sub.subset(font)
    buffer = io.BytesIO()
    font.save(buffer)
    page = page.replace('</head>', '<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,' +
        base64.b64encode(buffer.getvalue()).decode() + ")}body,button,select,input,textarea{font-family:CrossingSans,sans-serif}</style></head>")
    html = destination / 'crossing_lite_review.html'
    html.write_text(page)
    shutil.copy2(cfg['font_license'], destination / 'FONT_LICENSE.txt')
    write(destination / 'export_audit.json', dict(passed=True, html_sha256=sha(html), summary=summary,
        template_id='crossing-review-v1-lite-score5', parent_template=cfg['template_id'],
        template_sha256=sha(ROOT / 'core/crossing_campaign_template.html'), native_rgb_preserved=True,
        causal_request_reconstruction=True, no_model_calls=True, score_only_no_checkpoint=True))
    subprocess.run(['node', str(ROOT / 'scripts/check_crossing_lite.cjs'), str(html)], check=True, timeout=600)
    write(Path(c['register']) / 'summary.json', summary)
    return dict(html=str(html), summary=summary)
