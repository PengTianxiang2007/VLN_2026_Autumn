"""Add the frozen 29-case DeepSeek layer to the terminal-complete Qwen replay."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from export_route53_deepseek_dedup import ROOT, replace_once
from core.agent_route_choice import file_hash, now, read, write

NAME = 'run_20261118_03_deepseek29'
RUN = ROOT/'outputs/deviation_progress/v003'/NAME
RECORD = ROOT/'experiments/deviation_progress/v003'/NAME/'exports/web_20261118_01'
QWEN = ROOT/'outputs/deviation_progress/v003/run_20261118_01_qwen27b'
CASES = range(1,30)

def reviewed(model_root, eid, number, anchors):
    file = model_root/'deviation/run/cases'/f'C{number:02d}'/'result.json'
    result = read(file)
    assert result['episode_id']==eid and result['case_number']==number and result['stop_reason'] in ('first_deviation','all_nodes_reviewed')
    by_id = {n['id']:n for n in anchors}
    assert result['terminal_frame']==anchors[-1]['index'] and anchors[-1]['terminal_node']
    interval = None
    errors = 0
    for review in result['reviews']:
        a,b = by_id[review['previous_id']],by_id[review['node_id']]
        assert (a['index'],b['index']) == (review['from_frame'],review['to_frame'])
        if review['status']!='ok':
            errors+=1
        elif review['answer']['verdict']=='deviated':
            assert interval is None and 0 <= a['index'] < b['index'] <= result['terminal_frame']
            interval=dict(from_frame=a['index'],to_frame=b['index'])
    assert bool(interval)==(result['stop_reason']=='first_deviation')
    return dict(interval=interval,errors=errors),file_hash(file)

def collect():
    if read(RUN/'status.json')['phase']!='complete':raise RuntimeError('The 29-case batch is not complete')
    source=read(RUN/'manifest.json')
    anchors=read(RUN/'retained_nodes_and_terminals.json')
    layers={'deepseek':{},'qwen':{}}
    digests={}
    assert [e['case_number'] for e in source['cases']]==list(CASES)
    for entry in source['cases']:
        i,eid=entry['case_number'],entry['episode_id']
        digests[eid]={}
        for key,root in [('qwen',QWEN),('deepseek',RUN)]:
            layers[key][eid],digests[eid][key]=reviewed(root,eid,i,anchors[eid])
        assert digests[eid]['qwen']==entry['qwen_result_sha256']
    return layers,digests

def export(source, dest, layers):
    html=source.read_text()
    match=re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
    bundle=json.loads(match[1])
    for eid,entry in layers['qwen'].items():
        interval=entry['interval']
        old=bundle['deviationReviews'].get(eid)
        if old is not None:
            assert [{k:v for k,v in row.items() if k in ('from_frame','to_frame')} for row in old]==([interval] if interval else [])
        else:
            bundle['deviationReviews'][eid]=[interval] if interval else []
    bundle['deepseekReviews']=layers['deepseek']
    content=json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html=html[:match.start(1)]+content+html[match.end(1):]
    html=replace_once(html,'function drawMap(state){',(ROOT/'core/jev_sampling_lab/deepseek_deviation.js').read_text()+'\nfunction drawMap(state){')
    html=replace_once(html,'class="trajectoryActions">','class="trajectoryActions"><label class="eliminationShortcut" style="border-color:#a874c9"><input type="checkbox" id="deepseekDeviation" autocomplete="off"><span data-i18n="deepseekLabel">DeepSeek偏航识别</span></label>')
    html=replace_once(html,"L.zh.showDeviation='显示偏航识别'; L.en.showDeviation='Show deviation';","L.zh.showDeviation='Qwen偏航识别'; L.en.showDeviation='Qwen deviation'; L.zh.deepseekLabel='DeepSeek偏航识别'; L.en.deepseekLabel='DeepSeek deviation';")
    html=replace_once(html,'deviationOverlay.drawMap({ctx,xy});','deviationOverlay.drawMap({ctx,xy});deepseekDeviation.map(ctx,xy);')
    html=replace_once(html,'deviationOverlay.drawBands({ctx,x,y,top:margin.top,axisY});','deviationOverlay.drawBands({ctx,x,y,top:margin.top,axisY});deepseekDeviation.plot(ctx,x,margin.top,axisY);')
    html=replace_once(html,'renderCurrentNode(state);','deepseekDeviation.updateLabel();renderCurrentNode(state);')
    with dest.open('x') as stream: stream.write(html)
    return file_hash(dest)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--online-base',type=Path,required=True);parser.add_argument('--offline-base',type=Path,required=True)
    args=parser.parse_args()
    layers,digests=collect()
    paths={}
    for key,p in [('online',args.online_base),('offline',args.offline_base)]:
        dest=p.with_name('index_deepseek29.html')
        paths[key]=dict(source=str(p),source_sha256=file_hash(p),export=str(dest),sha256=export(p,dest,layers))
    write(RECORD/'snapshot.json',dict(frozen_at=now(),inputs=digests,layers=layers,files=paths))
