"""Export only completed original score streams, never splice in a different trajectory."""
import io
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from run import RUN, ROOT, HERE, read, save

def main(tag):
    data=read(RUN/'dataset.json');scores=read(RUN/'scores.json')
    complete=[];skipped=[]
    for c in data['cases']:
        eid=c['episode_id']
        if set(scores.get(eid,{}))=={str(i) for i in range(len(c['frames']))}:complete.append(c)
        else:skipped.append(eid)
    if not complete or (tag=='full' and skipped):raise ValueError('Full original scores required')
    sequences={c['episode_id']:[scores[c['episode_id']][str(i)]['prob'] for i in range(len(c['frames']))] for c in complete}
    points=json.loads(subprocess.check_output(['node',HERE/'replay.cjs'],input=json.dumps(sequences).encode()))
    dest=RUN/tag
    dest.mkdir(exist_ok=False)
    save(dest/'points.json',points)
    summary={}
    for mode in ['v001','coverage','active']:
        matches=[];count=0
        for c in complete:
            nodes=points[c['episode_id']][mode];count+=len(nodes)
            frames=[n['index'] for n in nodes if abs(n['index']-c['wrong_frame'])<=3]
            if frames:matches.append([c['episode_id'],min(frames,key=lambda v:abs(v-c['wrong_frame'])),c['wrong_frame']])
        summary[mode]=dict(candidates=count,hits=len(matches),references=len(complete),matches=matches)
    save(dest/'summary.json',dict(completed=len(complete),skipped=skipped,modes=summary))
    html=(ROOT/'outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/front_candidates_01/index.html').read_text()
    m=re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
    bundle=json.loads(m[1]);bundle.update(cases=[],images={},maps={},tag='early48_'+tag,missing=skipped)
    all_probs=[]
    for c in complete:
        eid=c['episode_id'];probs=sequences[eid];all_probs+=probs
        case=dict(c,case_id=f"C{c['number']:02}",real_episode_id=eid,group='failure',initial_index=c['wrong_frame'],points=points[eid].copy())
        k=c['wrong_frame']
        case['points']['wrong']=[dict(id='W',index=k,emittedAt=k,value=probs[k],kind='wrong')]
        for i,f in enumerate(case['frames']):
            f['jev']=dict(probability_yes=probs[i],image_frames=list(range(max(0,i-2),i+1)))
            bundle['images'][f['image']]='images/'+f['image']+'.webp'
        scene=c['scene'];bundle['maps'][scene]=dict(image=scene,geometry=data['maps'][scene]);bundle['images'][scene]='images/'+scene+'.png'
        bundle['cases'].append(case)
    bundle['summary']=dict(candidates=len(complete),valid_calls=len(all_probs),jev_mean_probability=sum(all_probs)/len(all_probs))
    html=html[:m.start(1)]+json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')+html[m.end(1):]
    start=html.index('const SAMPLING_VERSIONS=');end=html.index('let lang=',start)
    colors={'v001':'#007680','coverage':'#334aa6','active':'#c93c76','wrong':'#54218b'}
    defs=[dict(id=k,title='name_'+k,description='name_'+k,color=v) for k,v in colors.items()]
    html=html[:start]+'const SAMPLING_VERSIONS='+json.dumps(defs)+';\n'+html[end:]
    start=html.index('function fullSampling(version)');end=html.index('function eliminationCase',start)
    html=html[:start]+"function fullSampling(v){return {nodes:c().points[v.id],model:{state:()=>({})}};}\n"+html[end:]
    painter=(HERE.parent/'run_20261124_01/exports/map_layers_20261125_01/map_layers.js').read_text().replace("'Astra'","'wrong'")
    html=html.replace('function drawMap(state){',painter+'\nfunction drawMap(state){')
    a=html.index('  ctx.setLineDash([]);ctx.font=',html.index('function drawMap(state){'));b=html.index('\n}',a)
    html=html[:a]+"""  ctx.setLineDash([]); const [x,y]=xy(row().position);ctx.beginPath();ctx.arc(x,y,12,0,Math.PI*2);ctx.strokeStyle='#e11d48';ctx.lineWidth=2;ctx.stroke();paintMapLayers(ctx,xy,state);"""+html[b:]
    html=html.replace("${i+1}. ${item.episode_id}","${item.case_id} · ${item.episode_id}")
    token="stop();renderCases();seek(index);\n}"
    assert html.count(token)==1
    html=html.replace(token,"stop();renderCases();seek(index);if($('metrics48'))render48();\n}")
    html=html.replace("p.textContent=version.id+' · '+","p.textContent=version.id==='wrong'?t('name_wrong')+' F'+c().wrong_frame:version.id+' · '+")
    html=html.replace('</head>','<style>#metrics48{margin:12px clamp(8px,3vw,36px);padding:12px;background:white;overflow-x:auto}#metrics48 table{border-collapse:collapse;width:100%}#metrics48 th,#metrics48 td{padding:6px;border-bottom:1px solid #dce3eb;text-align:left}#metrics48>div{display:flex;align-items:center;gap:12px}#mapLayers #samplingVersions{display:flex;flex-wrap:wrap;gap:6px}#mapLayers .samplingCopy .muted{display:none}#mapLayers label{border-left:4px solid var(--sample-color)}</style></head>')
    # Supersede the old one-version startup script but keep its disabled frozen parameters.
    html=html.replace("$('sample_v001').checked=true; updateLanguage();",(HERE/'view.js').read_text())
    (dest/'index.html').write_text(html)
    assets=set(bundle['images'].values())
    with zipfile.ZipFile(io.BytesIO((RUN/'images.zip').read_bytes())) as src,zipfile.ZipFile(dest/'early48.zip','x') as archive:
        archive.write(dest/'index.html','index.html',zipfile.ZIP_DEFLATED)
        archive.write(ROOT/'outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/front_candidates_01/FONT_LICENSE.txt','FONT_LICENSE.txt')
        for name in sorted(assets):archive.writestr(name,src.read(name))
    from standalone import embed
    embed(dest)
    print(tag,len(complete),len(skipped),[(k,v['hits'],v['candidates']) for k,v in summary.items()],flush=True)


if __name__=='__main__':main(sys.argv[1])
