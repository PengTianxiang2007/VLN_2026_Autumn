"""Adapt one completed serial run to the existing JEV sampling-lab template.

The original template/app/filter/sampler are reused. No model or simulator calls.
"""
import argparse
import copy
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from export_oracle_distance_replay import add_font, sha

ROOT=Path(__file__).resolve().parents[1]


def encode(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')


def build(source, output):
    source=source.resolve(); output=output.resolve()
    if output.exists(): raise FileExistsError(output)
    source_build=json.loads((source.parent/'build.json').read_text())
    assert sha(source)==source_build['html_sha256']
    match=re.search(r'<script id="data" type="application/json">(.*?)</script>',source.read_text(),re.S)
    r=json.loads(match.group(1)); assert len(r['frames'])==40 and r['summary']['recoveries']==0
    campaign=ROOT/r['source']
    assert sha(ROOT/'core/jev_online_sampler_v001.js')==sha(campaign/'code/core/jev_online_sampler_v001.js')
    tag=r['run']+'_jev_template'
    frames=[]
    for frame in r['frames']:
        call=r['requests'][frame['request']]
        frames.append(dict(frame=frame['index'],image=str(frame['image']),position=frame['position'],
                           jev=dict(probability_yes=frame['probability'],image_frames=[i['frame'] for i in call['images']]),
                           action=frame['action'],physics_ticks=frame['physics_ticks']))
    def prompt(lang):
        p=r['prompts']['jev'][lang]
        labels=['状态上下文','问题','true条件','false条件'] if lang=='zh' else ['State context','Question','Criterion for true','Criterion for false']
        return '\n\n'.join(label+':\n'+value for label,value in zip(labels,[p['context'],p['instructions'],p['criteria']['true'],p['criteria']['false']]))
    case=dict(episode_id=r['id'],real_episode_id=r['id'],scene=r['scene'],group='failure' if not r['metrics']['success'] else 'success',
              frames=frames,reference_path=r['reference'],instruction_en=r['instruction']['en'],instruction_zh=r['instruction']['zh'],initial_index=0)
    payload=dict(tag=tag,cases=[case],summary=dict(valid_calls=len(frames),jev_mean_probability=sum(f['probability'] for f in r['frames'])/len(frames)),
                 images={str(i):v for i,v in enumerate(r['images'])},maps={r['scene']:dict(geometry=r['map']['geometry'],image=str(r['map']['image']))},
                 prompt_zh=prompt('zh'),prompt_en=prompt('en'))
    nodes=[]; decisions=[]; active=[]
    for n in r['nodes']:
        node={k:n[k] for k in ['id','index','value','rawScore','kind','drop','emittedAt','delay']}
        node['images']=[]
        for offset in [-2,-1,0,1,2]:
            frame=n['index']+offset; missing=not 0<=frame<len(frames)
            node['images'].append(dict(label='F'+('0' if offset==0 else '%+d'%offset),frame=frame,missing=missing,
                                       image_id=None if missing else frames[frame]['image']))
        nodes.append(node)
        call=r['requests'][n['dedup_request']] if 'dedup_request' in n else None
        d=dict(previous_id=n['previous_candidate'],current_id=n['id'],previous_frame=next((q['index'] for q in nodes if q['id']==n['previous_candidate']),None),
               current_frame=n['index'],relation='not_compared' if n['relation']=='first' else n['relation'],
               action='replace_previous' if n['replaced'] else 'append_current',needs_model=call is not None,
               active_ids_before=active,active_ids_after=n['retained_after'],status='ok')
        d['step_gap']=None if d['previous_frame'] is None else d['current_frame']-d['previous_frame']
        if call:
            d.update(answer=copy.deepcopy(call['raw_answer']),reason=call['raw_answer']['reason'],elapsed_seconds=round(call['latency_seconds'],2),
                     display_answer=call['answer'],request=call['raw_request'])
        else:
            d.update(reason='首个节点直接建立。',display_answer={'reason':{'zh':'首个节点直接建立。','en':'The first node is established directly.'}})
        active=list(n['retained_after']);decisions.append(d)
    dedup=dict(source_tag=tag,sampler_version='v001',sampler_config={'window':7,'delay':5},model='deepseek-flash',
               prompt_zh=r['prompts']['dedup']['zh'],prompt_en=r['prompts']['dedup']['en'],cases=[dict(case_index=0,episode_id=r['id'],real_episode_id=r['id'],
               nodes=nodes,decisions=decisions,final_active_ids=r['final_retained'],summary=dict(candidates=len(nodes),retained=len(active),removed=len(nodes)-len(active),model_calls=r['summary']['dedup']))])
    template=ROOT/'core/jev_sampling_lab/template.html'; app=ROOT/'core/jev_sampling_lab/app.js'; adapter=ROOT/'core/serial_jev_template_adapter.js'
    html=template.read_text().replace('@@PAYLOAD_JSON@@',encode(payload))
    # The old asset font belonged to the offline 34-case package. Embed a fresh
    # subset of the same licensed font for this standalone export instead.
    html=re.sub(r'@font-face\{font-family:CrossingSans;src:url\(assets/[^)]+\)\}', '', html)
    source_scripts={
        'online_filter.js':ROOT/'core/jev_online_filter_v001.js',
        'online_sampler_v001.js':ROOT/'core/jev_online_sampler_v001.js',
        'app.js':app,
    }
    for name,path in source_scripts.items(): html=html.replace('<script src="'+name+'"></script>','<script>\n'+path.read_text()+'\n</script>')
    html=html.replace('<script src="node_elimination_results.js"></script>','<script>window.JEV_NODE_ELIMINATION_DATA=null;</script>')
    html=html.replace('<script src="node_deduplication_results.js"></script>','<script>window.JEV_NODE_DEDUP_DATA='+encode(dedup)+';</script>')
    # Preserve all existing original-request details without loading a second page.
    serial=dict(r); serial.pop('images');serial.pop('map')
    html=html.replace('</body>','<script id="serial-evidence" type="application/json">'+encode(serial)+'</script>\n<script>\n'+adapter.read_text()+'\n</script>\n</body>')
    assert not re.search(r'<script\s+src=',html)
    assert not re.search(r'sk-[A-Za-z0-9]{20,}',html)
    output.mkdir(parents=True); page=output/'serial_jev_replay.html';page.write_text(html)
    font=add_font(page);page.write_text(page.read_text().replace('font-family:OracleSans','font-family:CrossingSans'))
    paths=[source,template,app,adapter,Path(__file__),*source_scripts.values()]
    for path in [template,app,adapter,Path(__file__),*source_scripts.values()]: shutil.copy2(path,output/path.name)
    manifest=dict(created_at=datetime.now(timezone.utc).isoformat(),source_html=str(source.relative_to(ROOT)),
                  source_build_sha256=sha(source.parent/'build.json'),git_head=source_build['git_head'],summary=r['summary'],
                  reused_template=str(template.relative_to(ROOT)),reused_app=str(app.relative_to(ROOT)),
                  reused_app_unchanged=True,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths},
                  html_sha256=sha(page),html_bytes=page.stat().st_size,font=font,model_calls=0,
                  sampling_default=False,dedup_default=False,full_waveform_and_nodes=True,
                  actual_sampler=dict(window=7,delay=5),dedup_is_saved_result=True)
    (output/'build.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(html=str(page),summary=r['summary'],bytes=page.stat().st_size),ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
