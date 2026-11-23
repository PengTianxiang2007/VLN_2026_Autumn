"""Export a frozen, bilingual RxR dedup snapshot without invoking inference."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'outputs/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout'
REL = Path('deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/snapshot4_20261123_01')
OUT = ROOT/'outputs'/REL
RECORD = ROOT/'experiments'/REL
MEDIA = ROOT/'outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/exports/random30_20261123_01'
DEDUP = ROOT/'experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/node_deduplication/v001_run02_all'


def read(p):
    return json.loads(p.read_text())


def encoded(x):
    return json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def save(p,x):
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
    OUT.mkdir(parents=True,exist_ok=False)
    text=(MEDIA/'cases.js').read_text()
    cases=json.loads(text.removeprefix('const CASES = ').rstrip().removesuffix(';'))
    strings={}; totals=Counter(); inputs={}; chosen=[]
    for i,c in enumerate(cases,1):
        c['scores']=read(RUN/'jev/episodes'/c['id']/'scores.json')
        assert len(c['scores'])==len(c['pose'])-1
        c['dedup']=None
        if i>4:
            continue
        folder=RUN/f'dedup/cases/C{i:02d}'
        result=read(folder/'result.json'); nodes=read(RUN/'effective_nodes'/(c['id']+'.json'))
        assert str(result['episode_id'])==c['id']
        assert [n['source_id'] for n in nodes if not n['terminal_node']]==result['final_active_ids']
        rows=[]
        for d in result['decisions']:
            row=dict(d)
            if d['needs_model']:
                req=folder/'requests'/(d['current_id']+'.request.json')
                resp=folder/'requests'/(d['current_id']+'.response.json')
                row['request']=read(req); row['response']=read(resp)
                assert row['response']['status']=='ok'
                row['raw_content']=row['response']['response']['choices'][0]['message']['content']
                inputs[str(req.relative_to(ROOT))]=sha(req); inputs[str(resp.relative_to(ROOT))]=sha(resp)
            a=d.get('answer',{})
            for s in [d['reason'],*[m['description'] for m in a.get('matched_branches',[])],*a.get('a_only',[]),*a.get('b_only',[])]:
                strings.setdefault(s,len(strings)+1)
            rows.append(row)
        c['dedup']=dict(case_number=i,nodes=nodes,decisions=rows,summary=result['summary'],started_at=result['started_at'],completed_at=result['completed_at'])
        totals.update(result['summary']);chosen.append(c['id'])
        inputs[str((folder/'result.json').relative_to(ROOT))]=sha(folder/'result.json')
    assert totals['candidates']==139 and totals['retained']==71 and totals['model_calls']==134
    payload=dict(cases=cases,created_at=datetime.now(timezone.utc).isoformat(),completed_ids=chosen,
                 summary=dict(totals),deviation_complete=0,source_run=str(RUN.relative_to(ROOT)),
                 prompts=dict(dedup_zh=(DEDUP/'prompt_zh.txt').read_text(),dedup_en=(ROOT/'core/serial_replay_dedup_prompt_en.txt').read_text()))
    save(OUT/'snapshot.json',payload);save(OUT/'source_hashes.json',inputs)
    save(RECORD/'translation_source.json',list(strings))
    print(encoded(dict(cases=len(cases),completed=chosen,summary=dict(totals),translation_strings=len(strings))))


def build():
    data=read(OUT/'snapshot.json'); tr=data.get('translations',{})
    if not tr:
        strings=read(RECORD/'translation_source.json')
        lines=(RECORD/'review_en.txt').read_text().splitlines()
        assert len(lines)==len(strings)
        for i,(source,line) in enumerate(zip(strings,lines),1):
            n,value=line.split(' ',1);assert n==str(i) and value.strip();tr[source]=value
    data['translations']=tr
    (OUT/'cases.js').write_text('const SNAPSHOT = '+encoded(data).replace('</','<\\/')+';\nconst CASES = SNAPSHOT.cases;\n')
    html=(ROOT/'core/rxr_branch_replay.html').read_text()
    n=len(data['completed_ids']); dev=data.get('deviation_complete',0)
    html=html.replace('RxR-CE 错选支路回放','RxR30 有效节点与偏航识别').replace('RxR-CE wrong-branch replay','RxR30 effective nodes and deviation reviews')
    model=data.get('model_label','Qwen')
    html=html.replace('原版 StreamVLN · 80 条明确错选中随机抽取 30 条',f'JEV → {model} 去重 → v006 偏航识别 · 去重 {n}/30，偏航 {dev}/30').replace('Original StreamVLN · 30 randomly sampled from 80 confirmed wrong-branch failures',f'JEV → {model} deduplication → v006 deviation review · Dedup {n}/30; deviation {dev}/30')
    html=html.replace('</style>','\n'+(ROOT/'core/rxr_offline_snapshot.css').read_text()+'\n</style>',1)
    html=html.replace('<main>','<main><section id="snapshotSummary" class="panel snapshot"></section>',1)
    html=html.replace('<div class="notes">',(ROOT/'core/rxr_offline_snapshot_panel.html').read_text()+'<div class="notes">',1)
    html=html.replace('<p class="small" id="mapNote">','<label><input id="effectiveLayer" type="checkbox" checked><i class="legend" style="background:#853ba5"></i><span data-zh="有效节点" data-en="Effective nodes"></span></label><label><input id="deviationLayer" type="checkbox"><i class="legend" style="background:#e02032"></i><span data-zh="显示偏航区间（红色）" data-en="Show deviation intervals (red)"></span></label><p class="small" id="deviationMapNote"></p><p class="small" id="mapNote">',1)
    html=html.replace('  const pos=item.pose[step];','  window.RxRSnapshot?.drawNodes({ctx,px,pz});\n  const pos=item.pose[step];',1)
    html=html.replace('  rgb();map();','  rgb();map();window.RxRSnapshot?.render();',1)
    html=html.replace('  document.title=L("RxR-CE · 错选支路回放","RxR-CE · Wrong-branch replay");','  document.title=L("RxR30 · 有效节点与偏航识别","RxR30 · Effective nodes and deviation reviews");')
    html=html.replace('select(CASES[0]);','select(CASES[0]);\nwindow.RXR_REPLAY={state:()=>({id:item.id,step,lang}),jump,select,drawMap:map};\n')
    html=html.replace('</body>','<script src="snapshot.js"></script></body>')
    html=html.replace('rxr30_dedup_snapshot4_offline.zip',data.get('archive','rxr30_dedup_snapshot4_offline.zip'))
    (OUT/'index.html').write_text(html);shutil.copy2(ROOT/'core/rxr_offline_snapshot.js',OUT/'snapshot.js')
    font_script = '''
import json,sys,shutil
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
root,out=map(Path,sys.argv[1:])
config=json.loads((root/'core/crossing_visualization_template.json').read_text())
font=TTFont(config['font'],fontNumber=0)
subsetter=subset.Subsetter()
subsetter.populate(text=''.join((out/name).read_text() for name in ['index.html','snapshot.js','cases.js']))
subsetter.subset(font)
(out/'assets').mkdir(exist_ok=True)
font.save(out/'assets/snapshot_cjk.ttf')
shutil.copy2(config['font_license'],out/'FONT_LICENSE.txt')
'''
    subprocess.run([str(ROOT/'backbone/streamvln/.venv/bin/python'),'-B','-c',font_script,str(ROOT),str(OUT)],check=True)
    html=html.replace('</head>','<style>@font-face{font-family:SnapshotSans;src:url("assets/snapshot_cjk.ttf")}body,button,select,input,textarea,pre{font-family:SnapshotSans,system-ui,sans-serif}</style></head>')
    (OUT/'index.html').write_text(html)
    save(OUT/'font_license.json',dict(license=(OUT/'FONT_LICENSE.txt').read_text()))
    assets=['cases.js','snapshot.js','assets/snapshot_cjk.ttf','font_license.json',*data.get('extra_assets',[])]
    for c in data['cases']:
        folder=OUT/'assets'/c['id'];folder.mkdir(parents=True,exist_ok=True)
        for name in ['floor.png',*[f'{i}.jpg' for i in range(math.ceil(len(c['pose'])/9))]]:
            rel=Path('assets')/c['id']/name;dest=OUT/rel
            if not dest.exists():os.link(MEDIA/rel,dest)
            assets.append(str(rel))
    save(OUT/'snapshot_public.json',data);assets.append('snapshot_public.json')
    archive=data.get('archive','rxr30_dedup_snapshot4_offline.zip')
    # The draft package is rebuilt during this export; published versions use a new OUT.
    with zipfile.ZipFile(OUT/archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for name in ['index.html','FONT_LICENSE.txt',*assets]:z.write(OUT/name,name)
    assets.append(archive)
    save(OUT/'online_manifest.json',dict(html='index.html',assets=assets))
    sources=[Path(__file__),ROOT/'core/rxr_offline_snapshot.js',ROOT/'core/rxr_offline_snapshot.css',ROOT/'core/rxr_offline_snapshot_panel.html']
    save(OUT/'build.json',dict(completed_cases=n,effective_nodes=data['summary']['retained'],terminal_nodes=n,
         original_candidates=data['summary']['candidates'],model_calls=data['summary']['model_calls'],translations=len(tr),frames=sum(len(c['pose']) for c in data['cases']),
         deviation_complete=dev,deviation_summary=data.get('deviation_summary',{}),
         html_sha256=sha(OUT/'index.html'),archive_sha256=sha(OUT/archive),archive_bytes=(OUT/archive).stat().st_size,
         sources={str(p.relative_to(ROOT)):sha(p) for p in sources}))
    print(encoded(read(OUT/'build.json')))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','build']);args=parser.parse_args()
    {'prepare':prepare,'build':build}[args.phase]()
