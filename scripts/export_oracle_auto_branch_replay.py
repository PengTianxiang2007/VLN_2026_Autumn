"""Adapt scored automatic-branch traces to the existing Oracle replay template."""
import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.export_oracle_distance_replay import Media, add_font, read, rows, sha, trace, deviation


def baseline_data(campaign, analysis, selection, review_translations):
    """Validate the frozen classification against the actual paired native scores."""
    assert sha(analysis / 'classification.csv') == selection['classification_sha256']
    review = read(analysis / 'review.json')
    assert sha(analysis / 'cases.json') == review['source_cases_sha256']
    assert review['classification_frozen_before_paired_outcome_join']
    annotations = {c['episode_id']: c for c in review['cases']}
    expected = {c['episode_id'] for c in review['cases'] if c['category'] == selection['category']}
    assert set(selection['selected_ids']) == expected
    cases = {c['episode_id']: c for c in read(analysis / 'cases.json')}
    status = read(campaign / 'baseline/status.json')
    validation = Path(status['validation']); assert read(validation)['passed']
    scores = {r['episode_id']: r for r in rows(validation.parent / 'episodes.jsonl')}
    translations = read(review_translations); assert set(translations) == expected
    traces = {}
    for eid in selection['selected_ids']:
        c, score = cases[eid], scores[eid]
        assert c['pred_path'] == score['pred_path'] and score['SR'] == 0
        assert all(c['score'][k] == v for k, v in score.items() if k != 'pred_path')
        path = c['trace_source']
        if path not in traces:
            grouped = {}
            for row in rows(path):
                grouped.setdefault(row['episode_id'], []).append(row)
            traces[path] = grouped
        actual = traces[path][eid]
        assert [r['step'] for r in actual] == list(range(len(c['actions'])))
        assert [r['action'] for r in actual] == c['actions']
        assert all(r['episode_reset'] == c['episode_reset'] and r['episode_seed'] == score['episode_seed'] for r in actual)
        assert len(c['pred_path']) == len(c['actions']) + 2
        assert [Path(p).name for p in c['initial_rgb']] == ['rgb_000.png', 'rgb_001.png']
        c['annotation'] = dict(annotations[eid], reason_en=translations[eid])
    audit = dict(classification_sha256=sha(analysis / 'classification.csv'),
                 review_sha256=sha(analysis / 'review.json'), cases_sha256=sha(analysis / 'cases.json'),
                 scores_sha256=sha(validation.parent / 'episodes.jsonl'), validation_sha256=sha(validation),
                 trace_sha256={path: sha(path) for path in traces},
                 review_translations_sha256=sha(review_translations),
                 all_positions_and_actions_verified=True, initial_rgb_per_task=2,
                 missing_rgb_not_reused=True, independent_runs=True)
    return cases, scores, audit


def baseline_nodes(case, media):
    # Native pred_path[0] is initialization; [1] is the first policy observation.
    # RGB filenames index service policy calls, so only [1] and [2] have images.
    images = [media.add(p) for p in case['initial_rgb']]
    nodes = []
    for index, position in enumerate(case['pred_path']):
        action_index = index - 1
        nodes.append(dict(p=position, a=max(0, action_index), yaw=None, segment=0,
                          phase='initial' if index == 0 else ('end' if index == len(case['pred_path'])-1 else 'walk'),
                          action=case['actions'][action_index] if 0 <= action_index < len(case['actions']) else -1,
                          image=images[index-1] if index in (1, 2) else None, reused=False,
                          distance=deviation(position, case['reference_path'])))
    return nodes


def static_map(case, geometry, floorplan, output):
    """Draw the same measured XY data as the interactive SVG, without a simulator."""
    from PIL import Image, ImageDraw, ImageFont
    g = geometry
    scale = 1200 / max(g['width'], g['height'])
    margin, top = 50, 65
    w, h = round(g['width'] * scale), round(g['height'] * scale)
    canvas = Image.new('RGB', (w + 2 * margin, h + top + margin), 'white')
    floor = Image.open(floorplan).convert('RGB').resize((w, h), Image.Resampling.LANCZOS)
    canvas.paste(floor, (margin, top))
    draw = ImageDraw.Draw(canvas)
    font_path = read(ROOT / 'core/crossing_visualization_template.json')['font']
    font = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 15)
    def xy(p):
        return (margin + (p[0] - g['low'][0]) / g['resolution'] * scale,
                top + (g['high'][1] - p[1]) / g['resolution'] * scale)
    def label(p, text, color, delta=(7, -20)):
        q = xy(p); draw.text((q[0] + delta[0], q[1] + delta[1]), text, fill=color, font=small,
                            stroke_width=2, stroke_fill='white')
    draw.text((margin, 18), case['id'] + '   SR=' + str(int(case['metrics']['success'])) +
              '   NE=' + format(case['metrics']['NE'], '.2f') + 'm', fill='#203145', font=font)
    if case['original']:
        draw.text((margin, 44), '参考 Reference / 绿 Green    原版 Baseline / 橙 Orange    纠错 Correction / 蓝 Blue    瞬移 Teleport / 紫 Purple', fill='#365267', font=small)
    draw.line([xy(p) for p in case['reference']], fill='#12846a', width=5)
    if case['original']:
        draw.line([xy(n['p']) for n in case['original']], fill='#d0642b', width=3)
    nodes = case['nodes']
    for a, b in zip(nodes, nodes[1:]):
        if a['segment'] == b['segment']:
            draw.line([xy(a['p']), xy(b['p'])], fill='#2374d5', width=3)
    for event in case['events']:
        a, b = xy(nodes[event['before']]['p']), xy(nodes[event['after']]['p'])
        length = math.dist(a, b)
        if length > .1:
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            for distance in range(0, math.ceil(length), 16):
                stop = min(length, distance + 9)
                draw.line([(a[0] + ux * distance, a[1] + uy * distance),
                           (a[0] + ux * stop, a[1] + uy * stop)], fill='#8848c8', width=3)
            draw.polygon([b, (b[0]-ux*14-uy*6, b[1]-uy*14+ux*6),
                          (b[0]-ux*14+uy*6, b[1]-uy*14-ux*6)], fill='#8848c8')
        c = xy(event['crossing']); t = xy(event['target'])
        draw.ellipse((c[0]-5, c[1]-5, c[0]+5, c[1]+5), fill='#e2ac29', outline='#735c16')
        draw.line((t[0]-7, t[1], t[0]+7, t[1]), fill='#8848c8', width=3)
        draw.line((t[0], t[1]-7, t[0], t[1]+7), fill='#8848c8', width=3)
        label(event['crossing'], 'C'+str(event['number']), '#956400')
        label(event['target'], 'T'+str(event['number']), '#8848c8', (7, 4))
    for p, text, color in [(case['reference'][0], 'S', '#244659'),
                            (case['reference'][-1], 'G', '#12846a'),
                            (nodes[-1]['p'], 'P', '#2374d5')]:
        q = xy(p); draw.ellipse((q[0]-5, q[1]-5, q[0]+5, q[1]+5), fill=color)
        label(p, text, color)
    if case['original']:
        label(case['original'][-1]['p'], 'B', '#d0642b', (7, 12))
    canvas.save(output)


def build(campaign, selection_file, translations, output, baseline_analysis=None, review_translations=None):
    campaign = campaign.resolve(); output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    arm = campaign / 'auto_branch'
    status = read(arm / 'status.json'); manifest = read(arm / 'manifest.json')
    validation = read(status['validation'])
    assert status['phase'] == 'complete_scored_subset' and validation['passed']
    official = {r['episode_id']: r for r in rows(Path(status['validation']).parent / 'episodes.jsonl')}
    assert len(official) == validation['episodes'] == 200
    selected = read(selection_file); ids = selected['selected_ids']; zh = read(translations)
    assert 1 <= len(ids) <= 200 and len(ids) == len(set(ids)) and set(ids) <= set(official)
    assert set(zh) == set(ids) and all(zh.values())
    paired = baseline_analysis is not None
    paired_audit = None
    if paired:
        baseline_cases, baseline_scores, paired_audit = baseline_data(campaign, baseline_analysis, selected, review_translations)
    case_map = {c['episode_id']: c for c in manifest['cases']}
    geometry_source = ROOT / 'outputs/oracle_crossing/scene_annotations_v001/run_20261116_01/scenes'
    media = Media(); audits = []; scene_audits = []; geometry_data = {}
    data = dict(cases=[], maps={}, images=[], summary={}, seed=manifest['seed'],
                threshold=.75, landing_offset_m=1.25, arm='auto_branch', mode='auto_branch',
                has_original=paired, paired=paired, full_cohort=validation)
    mapdir = output.parent / 'topdown_maps'; mapdir.mkdir(exist_ok=False)
    for eid in ids:
        c = case_map[eid]; result_path = arm / 'oracle_records/auto_branch' / eid / 'result.json'
        result, nodes, events, audit = trace(result_path, c, media, 'auto_branch')
        score = official[eid]
        for key, metric in [('success', 'SR'), ('NE', 'NE'), ('spl', 'SPL'), ('osr', 'OS')]:
            assert abs(float(result['metrics'][key]) - score[metric]) < 1e-6
        assert result['metrics']['fail_reason'] == score['fail_reason']
        targets = [dict(id=e['target_id'], crossing_position=e['crossing'], target_xy=e['target']) for e in events]
        for e in events:
            assert abs(e['requested_offset_m'] - 1.25) < 1e-9
            assert abs(e['target_reference_arc_m'] - e['branch_reference_arc_m'] - e['actual_offset_m']) < 1e-8
            assert 0 <= e['actual_offset_m'] <= 1.25 + 1e-8
        scene = c['scene']; source = geometry_source / scene
        if scene not in data['maps']:
            frozen = Path(manifest['landing_geometry_audit']['root']) / scene / 'geometry.json'
            expected = manifest['landing_geometry_audit']['files_sha256'][scene + '/geometry.json']
            assert sha(frozen) == sha(source / 'geometry.json') == expected
            g = read(frozen); geometry = {k:g[k] for k in ['low', 'high', 'width', 'height', 'resolution']}
            from PIL import Image
            with Image.open(source / 'floorplan.png') as image:
                assert image.size == (g['width'], g['height'])
            data['maps'][scene] = dict(geometry=geometry, image=media.add(source / 'floorplan.png', 0))
            geometry_data[scene] = geometry
            scene_audits.append(dict(scene=scene, geometry_sha256=expected,
                                     floorplan_sha256=sha(source / 'floorplan.png'), units=g['units'], up_axis=g['up_axis']))
        metrics = {k: result['metrics'][k] for k in ['success', 'NE', 'spl', 'osr', 'fail_reason']}
        case = dict(id=eid, scene=scene, instruction=c['instruction'], instruction_zh=zh[eid],
                    reference=c['reference_path'], targets=targets, nodes=nodes, original=[],
                    historical_success=None, metrics=metrics, events=events,
                    source_run='run_20261116_03_gpu2sim_gpu3model',
                    max_distance=result['max_reference_distance_m'], actions=result['executed_actions'])
        if paired:
            base, original_score = baseline_cases[eid], baseline_scores[eid]
            assert base['instruction'] == c['instruction'] and base['reference_path'] == c['reference_path']
            assert original_score['scene'] == score['scene']
            assert original_score['run_seed'] == score['run_seed'] == manifest['seed']
            assert original_score['episode_seed'] == score['episode_seed']
            case.update(original=baseline_nodes(base, media), historical_success=original_score['SR'],
                        original_metrics={k:original_score[v] for k,v in [('success','SR'),('NE','NE'),('spl','SPL'),('osr','OS'),('fail_reason','fail_reason')]},
                        original_actions=len(base['actions']), review=base['annotation'],
                        outcome=('corrected_' if events else 'uncorrected_') + ('success' if metrics['success'] else 'failure'))
            audit['baseline_initial_rgb_sha256'] = {Path(p).name: sha(p) for p in base['initial_rgb']}
        data['cases'].append(case); audits.append(dict(episode_id=eid, **audit))
        static_map(case, geometry_data[scene], source / 'floorplan.png', mapdir / (eid + '.png'))
    cases = data['cases']; count = len(cases)
    data['summary'] = dict(tasks=count, annotations=sum(len(c['targets']) for c in cases),
                           success=sum(int(c['metrics']['success']) for c in cases),
                           normal_success=sum(c['metrics']['fail_reason']=='success' for c in cases),
                           triggered=sum(bool(c['events']) for c in cases), events=sum(len(c['events']) for c in cases),
                           mean_spl=sum(c['metrics']['spl'] for c in cases)/count,
                           mean_ne=sum(c['metrics']['NE'] for c in cases)/count,
                           oracle_frames=sum(len(c['nodes']) for c in cases), original_frames=sum(len(c['original']) for c in cases),
                           scenes=len(data['maps']), endpoint_clamps=sum(e['clamped_to_route_end'] for c in cases for e in c['events']))
    data['labels'] = {
        'title':['自动分离点纠错 · 25条回放','Automatic divergence correction · 25 episode replays'],
        'subtitle':['StreamVLN · seed 2 · 25条展示 / 11个场景 · 完整200条官方SR 78.00%',
                    'StreamVLN · seed 2 · 25 displayed episodes / 11 scenes · full 200-episode official SR 78.00%'],
        'official':['本页样本官方成功率','Official success rate of displayed cases'],
        'tasks':['本页展示任务','Displayed episodes'], 'annotations':['估计分离点','Estimated divergence points'],
        'oracle':['自动分离点纠错组','Automatic divergence correction run'],
        'oracleShort':['自动纠错实际轨迹','Actual automatic-correction trajectory'],
        'crossing':['估计分离点 C','Estimated divergence C'],
        'timelineHelp':['地图与RGB下方两条进度条同步。本页展示自动纠错组；播放速度用于浏览，不代表仿真时间。',
                        'The map and RGB sliders are synchronized. This page shows the automatic-correction run; playback speed is for viewing, not simulation time.'],
        'mapHelp':['S 起点 · G 目标 · C 运行时估计的分离点 · T 规划落点 · P 当前实际位置及朝向。绿色为正确参考路线，蓝色实线为实际导航，紫色虚线箭头为真实瞬移；浅蓝色显示完整记录。C并非人工标注路口。拖动平移、滚轮缩放；“完整场景”显示全部俯视底图。',
                   'S: start · G: goal · C: runtime-estimated divergence · T: planned landing · P: actual current position and heading. Green is the correct reference route, blue solid lines are navigation, and purple dashed arrows are real teleports; pale blue shows the complete record. C is not a manually annotated junction. Drag to pan, scroll to zoom, and use Full scene to show the entire floor plan.'],
        'branchInterval':['估计分离的动作区间','Estimated divergence action interval'],
        'actualOffset':['实际 / 请求前移距离','Actual / requested forward offset'],
        'endpointClamp':['落点截断至路线终点','Landing clamped to route end'],
        'landingError':['稳定落点误差','Settled landing error'], 'yes':['是','Yes'], 'no':['否','No'],
        'scope1':['偏航阈值为到完整正确参考路线的最短水平距离0.75米。脚本从已经走过的轨迹估计分离位置，以此为锚点沿参考路线前移1.25米，并取路线方向作为朝向；超过末端则截断到终点。等策略动作队列为空后直接瞬移，保留干预时记忆，允许重复纠正。估计不可靠则跳过，不使用人工路口或静态候选。',
                  'The trigger is a shortest horizontal distance of 0.75 m to the complete correct reference route. The script estimates divergence from the observed walked history, advances 1.25 m along the reference from that anchor, and uses the route direction as heading; landings beyond the route are clamped to its end. Teleportation waits for an empty policy action queue, preserves intervention-time memory, and allows repeated corrections. Unreliable estimates are skipped; no manually annotated junctions or static candidates are used.'],
        'scope2':['本页选取25条行为示例，覆盖全部11个已跑场景，包含成功、失败、未纠错和反复末端截断。并非随机抽样，本页样本SR不能替代完整200条的78.00%。本页不包含原版对照轨迹，不把参考路线当作原版模型运行结果。',
                  'These 25 behavioral examples cover all 11 evaluated scenes, including successes, failures, uncorrected cases, and repeated endpoint clamping. This is not a random sample; its SR does not replace the full 200-episode SR of 78.00%. No baseline run is included here, and the reference route is not a baseline model trajectory.'],
        'scope3':['官方成功沿用原版终点距离评分，实际终止原因另列。俯视底图来自场景资产几何投影，用于定位，不构成碰撞保证；轨迹坐标与底图共享同一米制坐标系。纠错前后均为实际保存图像，复用终止RGB会明确标注。终点附近瞬移可能直接满足成功距离，不能都归因于纠错后自主走对。',
                  'Official success follows the original final-distance scoring, with termination reasons listed separately. Floor plans project scene-asset geometry for localization and do not certify collision safety; trajectories and maps share the same metric coordinates. Before/after images are actual recordings, with reused terminal RGB labeled. Teleports near the goal may directly satisfy the success distance, so success is not entirely attributable to autonomous navigation after correction.'],
        'scope4':[f'来源：运行03自动纠错原始记录、运行04同200条原生评分导出。本页{count}条、{data["summary"]["events"]}次纠错；逐次核对记忆SHA256和实际跳变，纠错次数不是独立样本数。地图C/T按实际事件生成，不预先写死落点。仅导出现有记录。',
                  f'Sources: raw automatic-correction records from run03 and the matching 200 native scores exported by run04. This page has {count} episodes and {data["summary"]["events"]} corrections; each memory SHA256 and actual jump is checked. Corrections are not independent samples. Map C/T points come from recorded events, not preassigned landings. Only existing records are exported.'],
        'scoreNote':['这是选取的25条行为展示样本，官方成功与正常成功停止分别显示。完整200条：156成功，SR 78.00%，SPL 0.6030。',
                     'These are 25 selected behavioral examples, with official success and normal successful stopping shown separately. Full 200-episode cohort: 156 successes, SR 78.00%, SPL 0.6030.']}
    # Keep the original template and derive all sample-dependent labels from this export.
    scene_count = data['summary']['scenes']
    data['labels'].update(title=[f'自动分离点纠错 · {count}条回放', f'Automatic divergence correction · {count} episodes'],
        subtitle=[f'StreamVLN · seed {manifest["seed"]} · {count}条展示 / {scene_count}个场景 · 完整200条官方SR 78.00%',
                  f'StreamVLN · seed {manifest["seed"]} · {count} displayed episodes / {scene_count} scenes · full 200-episode SR 78.00%'])
    for key in ['scope2', 'scoreNote']:
        data['labels'][key] = [s.replace('25条', str(count)+'条').replace('25 ', str(count)+' ').replace('11个', str(scene_count)+'个').replace('11 evaluated', str(scene_count)+' evaluated') for s in data['labels'][key]]
    if paired:
        outcomes = Counter(c['outcome'] for c in cases)
        data['summary'].update(outcomes=dict(outcomes), baseline_success=sum(int(c['historical_success']) for c in cases))
        data['labels'].update({
            'title':[f'选错路{count}条 · 原版与自动纠错对照', f'{count} wrong-route cases · baseline vs correction'],
            'subtitle':[f'StreamVLN · seed 2 · {scene_count}场景 · 原版0/{count} → 纠错组{data["summary"]["success"]}/{count} · 实际纠错后成功{outcomes["corrected_success"]}条',
                        f'StreamVLN · seed 2 · {scene_count} scenes · baseline 0/{count} → correction arm {data["summary"]["success"]}/{count} · {outcomes["corrected_success"]} successes with intervention'],
            'original':['原版对照组（同任务 / seed 2）','Matched baseline run (same task / seed 2)'],
            'originalShort':['原版对照实际轨迹','Actual baseline trajectory'],
            'historical':['原版对照结果','Baseline result'], 'official':['自动纠错组成功率','Correction-arm success rate'],
            'timelineHelp':['切换来源查看两组独立轨迹；地图与RGB进度条同步。两组帧号不表示同一时刻。原版仅前两个策略观测保存了RGB，其余位置显示缺失提示。',
                            'Switch sources to inspect the independent runs. Map and RGB sliders stay synchronized within each run; equal indices are not matched moments across runs. Only the first two baseline policy observations have saved RGB; other positions show a missing-image notice.'],
            'mapHelp':['绿色：正确参考路线；橙色：原版对照；蓝色：自动纠错；紫色虚线：实际瞬移。C为运行时估计分离点，T为规划落点，P为当前回放位置。原版无朝向记录，不绘制朝向箭头。拖动平移、滚轮缩放。',
                       'Green: correct reference; orange: baseline; blue: correction arm; purple dashed arrows: actual teleports. C marks estimated divergence, T the planned landing, and P the playback position. Baseline headings were not recorded and are not drawn. Drag to pan and scroll to zoom.'],
            'scope2':[f'本页为原版失败离线分类中全部{count}条选错方向、分支或漏转弯任务，分类冻结后再关联纠错结果，没有按纠错成败筛选。两组同任务、同seed独立运行，并非从同一失败现场接续，不能将组间差异全部视为干预的因果效果。',
                      f'All {count} baseline failures classified offline as wrong direction, wrong branch, or missed turn are included. Classification was frozen before joining correction outcomes; no outcome-based filtering was applied. Runs use matched tasks and seeds but are independent, not continuations from the same failed state, so differences are not wholly causal intervention effects.'],
            'scope3':['官方成功采用原版终点距离评分，终止原因另列。原版提供完整位置轨迹与动作、仅起始两个策略观测RGB；缺失画面不复用、不补造。纠错组使用实际记录图像，末端复用明确标注。底图仅为资产投影，不是碰撞保证。落点在目标三米内时，成功不能全部归因于后续自主导航。',
                      'Official success uses native final-distance scoring; termination reasons are separate. Baseline positions and actions are complete, but only the first two policy RGB observations exist. Missing images are neither reused nor fabricated. Correction images are recorded, with terminal reuse labeled. Floor plans are asset projections, not collision guarantees. Landings within three meters of the goal prevent attributing success entirely to later autonomous navigation.'],
            'scope4':[f'来源：运行04两组原生成绩、原版102条失败的冻结分类、运行03纠错记录。{outcomes["corrected_success"]}条纠错后成功、{outcomes["corrected_failure"]}条纠错后失败、{outcomes["uncorrected_success"]}条未纠错成功、{outcomes["uncorrected_failure"]}条未纠错失败。逐次核验记忆SHA256与真实跳变；未启动新导航。',
                      f'Sources: run04 native scores from both arms, the frozen review of 102 baseline failures, and run03 correction records. With intervention: {outcomes["corrected_success"]} successes and {outcomes["corrected_failure"]} failures; without intervention: {outcomes["uncorrected_success"]} successes and {outcomes["uncorrected_failure"]} failures. Memory hashes and real jumps are verified per event; no new navigation was started.'],
            'scoreNote':[f'本页{count}条均为原版选错路失败，属于事后选择的子集。完整同200条：原版98/200（49%），纠错156/200（78%）。本页纠错组成功包括{outcomes["uncorrected_success"]}条未干预成功；有执行纠错且最终成功为{outcomes["corrected_success"]}条。',
                         f'These {count} baseline wrong-route failures are a retrospectively selected subset. Full matched 200: baseline 98/200 (49%), correction 156/200 (78%). Subset correction-arm successes include {outcomes["uncorrected_success"]} without intervention; {outcomes["corrected_success"]} succeeded after actual intervention.']})
    print(json.dumps(data['summary']), flush=True)
    # The exact English input is retained and bound to its display-only translation.
    write_translations = {c['id']:dict(en=c['instruction'], zh=c['instruction_zh'],
                          en_sha256=hashlib.sha256(c['instruction'].encode()).hexdigest()) for c in cases}
    (output.parent / 'translation_pairs.json').write_text(json.dumps(write_translations, ensure_ascii=False, indent=2)+'\n')
    data['images'] = media.encode()
    template = ROOT / 'core/oracle_distance_replay.html'
    html = template.read_text(); assert html.count('__PAYLOAD__') == 1
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    output.write_text(html.replace('__PAYLOAD__', payload))
    font_metadata = add_font(output)
    with zipfile.ZipFile(output.parent / f'topdown_maps_{count}.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(mapdir.glob('*.png')):
            archive.write(path, path.name)
    build_record = dict(created_at=datetime.now(timezone.utc).isoformat(), html=str(output), sha256=sha(output),
        bytes=output.stat().st_size, summary=data['summary'], images=len(data['images']), arm='auto_branch',
        threshold_m=.75, landing_offset_m=1.25, template=str(template), template_sha256=sha(template),
        exporter_sha256=sha(Path(__file__)), shared_trace_exporter_sha256=sha(ROOT/'scripts/export_oracle_distance_replay.py'),
        selection_sha256=sha(selection_file), translations_sha256=sha(translations),
        full_cohort_validation_sha256=sha(Path(status['validation'])), full_cohort=validation,
        audits=audits, maps=scene_audits, static_maps=count, self_contained=True, paired_audit=paired_audit,
        no_model_or_simulator_started=True, original_template_reused=True,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),git_dirty=True,**font_metadata)
    output.with_suffix('.build.json').write_text(json.dumps(build_record, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in build_record.items() if k not in ['audits','maps','full_cohort']},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--translations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-analysis', type=Path)
    parser.add_argument('--review-translations', type=Path)
    args = parser.parse_args()
    build(args.campaign, args.selection, args.translations, args.output, args.baseline_analysis, args.review_translations)
