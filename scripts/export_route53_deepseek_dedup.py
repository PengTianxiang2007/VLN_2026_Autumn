"""Export a completed review or a frozen subset using the route53 sampling-lab page."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from export_oracle_distance_replay import add_font

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import read, write, file_hash

PARENT = ROOT/'outputs/visualization_publishing/jev_route53_sampling_v001_web_20261118_01'
RUN = ROOT/'outputs/deviation_progress/v003/run_20261118_02_deepseek10'
BASE = ROOT/'experiments/deviation_progress/v003'/RUN.name/'exports/web_20261118_01'
DEDUP = ROOT/'experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/node_deduplication/v001_run02_all'
TEXT_SHA = '218e769e6185bfdb2701f3cc531e983103ae1ce8d730c8d1ad29d1f2456e86bd'


def replace_once(html, before, after):
    if html.count(before) != 1:
        raise ValueError('Unexpected sampling template near '+before[:65])
    return html.replace(before, after, 1)


def reviewed_cases(index, run, translations_dir, text_sha):
    records, texts = [], {}
    for i,(eid, cached) in enumerate(index.items()):
        path = run/cached['result']
        if 'sha256' in cached and file_hash(path)!=cached['sha256']:
            raise ValueError('Snapshot result changed: '+eid)
        result = read(path)
        assert result['episode_id']==eid and result['final_active_ids']==cached['retained_ids']
        record = {k:result[k] for k in ('case_number','episode_id','real_episode_id','nodes','final_active_ids','summary')}
        record.update(case_index=i, decisions=[])
        for decision in result['decisions']:
            d = {k:decision[k] for k in ('previous_id','current_id','previous_frame','current_frame','step_gap',
                 'needs_model','relation','action','active_ids_after','reason')}
            if d['needs_model']:
                d['elapsed_seconds']=decision['elapsed_seconds']
                if decision['status']=='ok':
                    answer=decision['answer']
                    assert answer['reason']==d['reason']
                    d['answer']=answer
                else:
                    response_path=path.parent/'requests'/(d['current_id']+'.response.json')
                    assert file_hash(response_path)==cached['invalid_response_sha256']
                    response=read(response_path)
                    assert response['status']=='error' and response['error']==decision['error']
                    assert decision['error']=='ValueError: Missing evidence references'
                    answer=json.loads(response['response']['choices'][0]['message']['content'])
                    d.update(validation_error=decision['error'],unvalidated_answer=answer)
                for s in [answer['reason'],*[m['description'] for m in answer['matched_branches']],*answer['a_only'],*answer['b_only']]:
                    texts.setdefault(s,None)
            record['decisions'].append(d)
        for node in record['nodes']:
            for im in node['images']:
                im.pop('path',None)
        records.append(record)
    assert hashlib.sha256(json.dumps(list(texts),ensure_ascii=False).encode()).hexdigest()==text_sha
    lines = (translations_dir/'review_en.txt').read_text().splitlines()
    assert len(lines)==len(texts)
    for i,(key,line) in enumerate(zip(texts,lines),1):
        num,translation = line.split(' ',1)
        assert num==str(i) and translation.strip()
        texts[key]=translation
    for c in records:
        for d in c['decisions']:
            if not d['needs_model']:
                gap = d['step_gap']
                texts[d['reason']] = ('First node. Establish it directly.' if gap is None else
                    f'The nodes are {gap} steps apart, exceeding 8 steps. Establish the current node directly.')
    return records,texts


def deviation_reviews(snapshot, run, cases):
    frozen = read(snapshot)
    anchors_file = run/'retained_nodes_and_terminals.json'
    assert file_hash(anchors_file) == frozen['anchors_sha256']
    anchors = read(anchors_file)
    output = {}
    for item in frozen['cases']:
        path = run/item['result']
        assert file_hash(path) == item['sha256']
        result = read(path)
        eid = result['episode_id']
        case = cases[result['case_number']-1]
        assert case['episode_id'] == eid == item['episode_id'] and eid not in output
        nodes = {n['id']: n for n in anchors[eid]}
        rows = []
        for v in result['reviews']:
            a, b = nodes[v['previous_id']], nodes[v['node_id']]
            assert v['status'] == 'ok' and (a['index'], b['index']) == (v['from_frame'],v['to_frame'])
            verdict = v['answer']['verdict']
            assert verdict in ('deviated','consistent','uncertain')
            if verdict == 'deviated':
                interval = {'from_frame': a['index'], 'to_frame': b['index']}
                assert 0 <= a['index'] < b['index'] <= len(case['frames'])
                if b['index'] == len(case['frames']):
                    assert b['terminal_node'] and b['index'] == result['terminal_frame']
                    observations = Path(v['images'][-1]['path']).parents[3]/'inputs'/eid/'observations.jsonl'
                    penultimate, terminal = map(json.loads, observations.read_text().splitlines()[-2:])
                    assert penultimate['robot_pose']['position_world_m'] == case['frames'][-1]['position']
                    assert terminal['episode_id'] == eid and terminal['step'] == b['index']
                    interval['terminal_position'] = terminal['robot_pose']['position_world_m']
                rows.append(interval)
        output[eid] = rows
    return output


def add_deviation_overlay(html):
    history = (ROOT/'experiments/deviation_progress/v003/run_20261112_05/snapshot/guard_ui.js').read_text()
    drawing = history[history.index('  function drawMap({ctx,xy})'):history.index('  window.GuardUI=')]
    drawing = drawing.replace("byId('guardOverlay')", "$('guardOverlay')")
    drawing = drawing.replace("reviews().filter(v=>v.answer?.verdict==='deviated')", "intervals()")
    drawing = drawing.replace("c().frames[f].position", "c().frames[f]?.position || r.terminal_position")
    drawing = drawing.replace("c().frames[frame].position", "c().frames[frame]?.position || r.terminal_position")
    script = ("const deviationOverlay = (() => {\n"
              "const intervals = () => B.deviationReviews[c().episode_id] || [];\n"
              "$('guardOverlay').onchange = () => draw();\n"
              + drawing + "return {drawMap,drawBands};\n})();\n")
    html = replace_once(html, 'function drawMap(state){', script+'function drawMap(state){')
    html = replace_once(html, 'class="trajectoryActions">', 'class="trajectoryActions">'
                        '<label class="eliminationShortcut"><input type="checkbox" id="guardOverlay" autocomplete="off">'
                        '<span data-i18n="showDeviation">显示偏航识别</span></label>')
    html = replace_once(html, 'function updateLanguage(){',
                        "L.zh.showDeviation='显示偏航识别'; L.en.showDeviation='Show deviation';\nfunction updateLanguage(){")
    html = replace_once(html, '\n}\nfunction drawPlot(state){',
                        '\n  deviationOverlay.drawMap({ctx,xy});\n}\nfunction drawPlot(state){')
    html = replace_once(html, 'last=Math.max(1,c().frames.length-1);',
                        "last=Math.max(1,c().frames.length-1+Number($('guardOverlay').checked && "
                        "(B.deviationReviews[c().episode_id]||[]).some(r=>r.terminal_position)));")
    return replace_once(html, '  for(let i=0;i<=4;i++){const v=i/4;',
                        '  deviationOverlay.drawBands({ctx,x,y,top:margin.top,axisY});\n  for(let i=0;i<=4;i++){const v=i/4;')


def attach_terminal_frames(cases, run, images):
    anchors = read(run/'retained_nodes_and_terminals.json')
    dataset = Path(read(ROOT/'outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/manifest.json')['dataset'])
    sources = {}
    for case in cases:
        eid = case['episode_id']
        nodes = anchors[eid]
        terminal = nodes[-1]
        index = len(case['frames'])
        assert [n for n in nodes if n['terminal_node']] == [terminal] and terminal['index'] == index
        rows = (dataset/'inputs'/eid/'observations.jsonl').read_text().splitlines()
        assert len(rows) == index+1
        before, end = map(json.loads, rows[-2:])
        assert before['robot_pose']['position_world_m'] == case['frames'][-1]['position']
        assert end['episode_id'] == eid and end['step'] == index
        front = end['native_front']
        path = dataset/front['image']
        assert path == dataset/'observations'/eid/f'{index:06d}'/'terminal_front.png' and file_hash(path)==front['sha256']
        key = front['sha256']
        filename = f'front/{key}.webp'
        images[key] = filename
        sources[filename] = path
        case['terminal_node'] = terminal
        case['frames'].append(dict(frame=index, position=end['robot_pose']['position_world_m'], image=key, jev=None))
    return sources


def add_terminal_controls(html):
    js = (ROOT/'core/jev_sampling_lab/terminal_node.js').read_text()
    html = replace_once(html, 'function drawMap(state){', js+'\nfunction drawMap(state){')
    html = replace_once(html, 'while(session.cursor<index)', 'while(session.cursor<Math.min(index,c().terminal_node.index-1))')
    assert html.count('for(const frame of c().frames){const result=') == 2
    html = html.replace('for(const frame of c().frames){const result=',
                        'for(const frame of c().frames){if(frame.frame===c().terminal_node.index)break;const result=')
    html = html.replace("c().frames.length-1+Number($('guardOverlay').checked && (B.deviationReviews[c().episode_id]||[]).some(r=>r.terminal_position))", 'c().frames.length-1')
    html = replace_once(html, 'return {values:fullCurve(),filter:filter.model.state(),versions};',
                        'return {values:fullCurve(),filter:filter.model.state(),versions,terminalNode:c().terminal_node};')
    html = replace_once(html, '\n}\nfunction drawPlot(state){',
                        '\n  drawTerminal(ctx, ...xy(c().frames[state.terminalNode.index].position), w, h);\n}\nfunction drawPlot(state){')
    html = replace_once(html, '\n}\nfunction draw(){',
                        '\n  drawTerminal(ctx,x(state.terminalNode.index),axisY,w,h);\n}\nfunction draw(){')
    html = replace_once(html, 'renderCurrentNode(state);','renderCurrentNode(state);renderTerminal(state.terminalNode);')
    html = replace_once(html, '<button id="next"', '<button type="button" id="terminalStep"></button><button id="next"')
    return replace_once(html, "['retainedCount',B.summary.retained],",
                        "['retainedCount',B.summary.retained],['effectiveCount',B.summary.retained+B.cases.length],")


def export(offline,online,snapshot=None,deviation_snapshot=None):
    if snapshot:
        summary = read(snapshot)
        run, translations_dir = ROOT/summary['run'], snapshot.parent
    else:
        summary = read(RUN/'dedup_resume_01/summary.json')
        summary.update(tag=RUN.name+'_dedup',model=read(RUN/'manifest.json')['settings']['model'],
                       display_model='DeepSeek',model_detail='DeepSeek-V4.1-Flash',text_sha256=TEXT_SHA,
                       phase_note_zh='偏航识别已暂停',phase_note_en='Deviation review paused')
        run, translations_dir = RUN, BASE
    records, translations = reviewed_cases(summary['case_results'],run,translations_dir,summary['text_sha256'])
    parent = read(PARENT/'online_manifest.json')
    assert file_hash(PARENT/'index.html')==parent['html_sha256']
    html = (PARENT/'index.html').read_text()
    match = re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
    payload = json.loads(match.group(1))
    parent_cases = {c['episode_id']:c for c in payload['cases']}
    cases = [parent_cases[c['episode_id']] for c in records]
    maps = {c['scene']:payload['maps'][c['scene']] for c in cases}
    frames = [f for c in cases for f in c['frames']]
    keys = {f['image'] for f in frames} | {m['image'] for m in maps.values()}
    images = {k:payload['images'][k] for k in sorted(keys)}
    payload.update(tag=summary['tag'],cases=cases,maps=maps,images=images,
                   summary=dict(valid_calls=len(frames),candidates=summary['dedup']['candidates'],
                                retained=summary['dedup']['retained'],comparisons=summary['dedup']['model_calls']))
    payload['dedup'] = dict(model=summary['model'], cases=records,
                            source_tag=payload['tag'], sampler_version='v001',
                            sampler_config=read(ROOT/'core/jev_online_sampling_v001.json'),
                            prompt_zh=(DEDUP/'prompt_zh.txt').read_text(),
                            prompt_en=(ROOT/'core/serial_replay_dedup_prompt_en.txt').read_text(),translations=translations,
                            display_model=summary['display_model'],model_detail=summary['model_detail'],
                            phase_note_zh=summary['phase_note_zh'],phase_note_en=summary['phase_note_en'])
    if deviation_snapshot:
        payload['deviationReviews'] = deviation_reviews(deviation_snapshot,run,cases)
    terminal_sources = attach_terminal_frames(cases,run,images) if (run/'retained_nodes_and_terminals.json').is_file() else {}
    content = json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html = html[:match.start(1)] + content + html[match.end(1):]
    html = replace_once(html, 'const D=window.JEV_NODE_DEDUP_DATA||null;', 
                        "const D=B.dedup; const wording=s=>lang==='en'?D.translations[s]:s;")
    html = replace_once(html,'#dedupControls,#eliminationControls,#nodeDeduplicationTop,#nodeEliminationTop,',
                        '#eliminationControls,#nodeEliminationTop,')
    html = replace_once(html,"D?.prompt_zh||''","lang==='zh'?D.prompt_zh:D.prompt_en")
    html = replace_once(html,"d?.reason||t('dedupEmpty')",
                        "d?(d.validation_error?t('dedupFailedReason')+' '+t('modelAnswer')+' ['+d.unvalidated_answer.relation+'] '+wording(d.unvalidated_answer.reason):wording(d.reason)):t('dedupEmpty')")
    html = html.replace("t('relation_'+d.relation)","(d.validation_error?t('dedupFailed'):t('relation_'+d.relation))")
    html = html.replace("d.answer?.matched_branches","(d.answer||d.unvalidated_answer)?.matched_branches")
    html = html.replace("d.answer?.[key]","(d.answer||d.unvalidated_answer)?.[key]")
    html = replace_once(html,'${branch.description} (','${wording(branch.description)} (')
    html = replace_once(html,'${t(label)}: ${desc}','${t(label)}: ${wording(desc)}')
    html = replace_once(html,"['calls',B.summary.valid_calls],['mean',B.summary.jev_mean_probability.toFixed(3)]",
                        "['retainedCount',B.summary.retained],['pairCount',B.summary.comparisons]")
    html = replace_once(html,'${i+1}. ${item.episode_id}',"C${String(D.cases[i].case_number).padStart(2,'0')} · ${item.episode_id}")
    html = replace_once(html,"['filterWindow','streamDelay','nodeElimination','nodeDeduplication']", 
                        "['filterWindow','streamDelay','nodeElimination']")
    html = replace_once(html,"$('nodeDeduplication').checked=false;","$('nodeDeduplication').checked=true;")
    # Apply the run labels after the two historical presentation initializers.
    labels = """
<script>
Object.assign(L.zh,{title:D.display_model+' 回退点去重',subtitle:B.cases.length+' 条轨迹 · '+Object.keys(B.maps).length+' 个场景',source:'原生前视 · '+D.model_detail,
dedupFailed:'校验失败，保留两点',dedupFailedReason:'回答缺少证据帧引用，校验失败。两个节点均已保留。',modelAnswer:'未经校验的模型原答',
retainedCount:'去重后保留',pairCount:'模型比较',samplingHint:'地图与波形同步显示节点。关闭“节点去重”可查看所有原始候选。',
dedupUnavailable:'这组节点与本批去重输入不匹配。',footer:'JEV 采样 v001 · '+D.display_model+' 去重 v001 · '+D.phase_note_zh});
Object.assign(L.en,{title:D.display_model+' checkpoint deduplication',subtitle:B.cases.length+' trajectories · '+Object.keys(B.maps).length+' scenes',source:'Native front view · '+D.model_detail,
dedupFailed:'Validation failed; both kept',dedupFailedReason:'The answer lacks evidence frame references. Validation failed. Both nodes were kept.',modelAnswer:'Unvalidated model answer',
retainedCount:'Retained nodes',pairCount:'Model comparisons',samplingHint:'The map and waveform show the same nodes. Turn off deduplication to see all original candidates.',
dedupUnavailable:'These nodes do not match the reviewed inputs.',dedupPrompt:'Deduplication prompt (English translation)',
footer:'JEV sampling v001 · '+D.display_model+' deduplication v001 · '+D.phase_note_en});
updateLanguage();
</script>"""
    html = replace_once(html,'</body>',labels+'</body>')
    if summary['dedup'].get('errors'):
        # The saved fallback relation for an invalid answer is not a model verdict.
        counts=summary['verdicts']
        details = dict(zh=f"相同 {counts['same']} 对，不同 {counts['different']} 对，不确定 {counts['uncertain']} 对，校验失败 {counts['validation_error']} 对。",
                       en=f"{counts['same']} same, {counts['different']} different, {counts['uncertain']} uncertain, {counts['validation_error']} failed validation.")
        info='<script>for(const [k,msg] of Object.entries('+json.dumps(details,ensure_ascii=False)+')) L[k].notice=msg+" "+L[k].notice; updateLanguage();</script>'
        html=replace_once(html,'</body>',info+'</body>')
    if deviation_snapshot:
        html = add_deviation_overlay(html)
    if terminal_sources:
        html = add_terminal_controls(html)
    html,nfonts = re.subn(r'<style id="embedded-font">.*?</style>','',html,flags=re.S)
    assert nfonts==1
    if offline.exists() or online.exists():
        raise FileExistsError('Choose unused export directories')
    offline.mkdir(parents=True)
    page = offline/'index.html'
    page.write_text(html)
    add_font(page)
    page.write_text(page.read_text().replace('font-family:OracleSans','font-family:CrossingSans'))
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/prepare_online_visualization.py'),
                    '--html',str(page),'--destination',str(online)],check=True)
    pkg = read(online/'online_manifest.json')
    def copy_asset(name):
        dest = offline/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        if name in terminal_sources:
            from PIL import Image
            with Image.open(terminal_sources[name]) as image:
                image.convert('RGB').save(dest, format='WEBP', quality=85, method=3)
            checksum = file_hash(dest)
        else:
            src = PARENT/name
            checksum = parent['assets'][name]
            assert file_hash(src)==checksum
            shutil.copyfile(src,dest)
        link = online/name
        link.parent.mkdir(parents=True,exist_ok=True)
        try:
            os.link(dest,link)
        except OSError:
            shutil.copyfile(dest,link)
        return name,checksum
    with ThreadPoolExecutor(max_workers=8) as workers:
        pkg['assets'].update(workers.map(copy_asset,sorted(set(images.values())|{'font_license.zip'})))
    pkg.update(html_sha256=file_hash(online/'index.html'),release=online.name,scored_frames=len(frames),
               maps=len(maps),native_front_images=len(images)-len(maps),terminal_nodes=len(cases) if terminal_sources else 0)
    write(online/'online_manifest.json',pkg)
    print({k:pkg[k] for k in ('html_sha256','scored_frames','maps','native_front_images')})


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--offline',type=Path,required=True)
    parser.add_argument('--online',type=Path,required=True)
    parser.add_argument('--snapshot',type=Path)
    parser.add_argument('--deviation-snapshot',type=Path)
    args=parser.parse_args()
    export(args.offline.resolve(),args.online.resolve(),args.snapshot,args.deviation_snapshot)
