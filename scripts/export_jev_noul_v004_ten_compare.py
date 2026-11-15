"""Export ten-case JEV v002 versus v004 fallback-probability comparison."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.agent_route_choice import read,write
from core.jev_node import (
    COMPACT_FALLBACK_CONTEXT_EN,COMPACT_FALLBACK_CONTEXT_ZH,
    COMPACT_FALLBACK_CRITERIA_EN,COMPACT_FALLBACK_CRITERIA_ZH,
    COMPACT_FALLBACK_INSTRUCTIONS_EN,COMPACT_FALLBACK_INSTRUCTIONS_ZH,
    FALLBACK_CRITERIA_EN,FALLBACK_CRITERIA_ZH,
    FALLBACK_INSTRUCTIONS_EN,FALLBACK_INSTRUCTIONS_ZH,
    STATE_CONTEXT_EN,STATE_CONTEXT_ZH,
)
from export_jev_noul_v003_compare import PAGE,sha,uri

DATASET=ROOT/'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'

def prompt_text(version,language):
    if version=='v002':
        context=STATE_CONTEXT_EN if language=='en' else STATE_CONTEXT_ZH
        instructions=FALLBACK_INSTRUCTIONS_EN if language=='en' else FALLBACK_INSTRUCTIONS_ZH
        criteria=FALLBACK_CRITERIA_EN if language=='en' else FALLBACK_CRITERIA_ZH
    else:
        context=COMPACT_FALLBACK_CONTEXT_EN if language=='en' else COMPACT_FALLBACK_CONTEXT_ZH
        instructions=COMPACT_FALLBACK_INSTRUCTIONS_EN if language=='en' else COMPACT_FALLBACK_INSTRUCTIONS_ZH
        criteria=COMPACT_FALLBACK_CRITERIA_EN if language=='en' else COMPACT_FALLBACK_CRITERIA_ZH
    prefix='State context' if language=='en' else '状态上下文'
    typ='Question type' if language=='en' else '问题类型'
    question='Question' if language=='en' else '问题'
    colon=':' if language=='en' else '：'
    return '\n'.join([prefix+colon+' '+context,'',typ+colon+' noul',question+colon+' '+instructions,'','true'+colon+' '+criteria['true'],'false'+colon+' '+criteria['false']])

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    run=a.run.resolve();out=a.output.resolve()
    if out.exists():raise ValueError('Use a new export directory')
    out.mkdir(parents=True)
    selection=read(run/'selection.json')['cases'];episodes={r['episode_id']:r for r in map(json.loads,(DATASET/'inputs/episodes.jsonl').read_text().splitlines())}
    maps_data=read(DATASET/'evaluation/maps.json');previous={(r['episode_id'],r['frame']):r for r in read(run/'rows_v002.json') if r.get('phase')=='complete'}
    current={(r['episode_id'],r['frame']):r for r in read(run/'rows_v004.json') if r.get('phase')=='complete'}
    run_summary=read(run/'summary.json');images={};maps={};cases=[];by_case={}
    for selected in selection:
        eid=selected['episode_id'];ep=episodes[eid];obs=read(DATASET/ep['observations']);traj=read(DATASET/selected['trajectory']);maprow=maps_data[selected['scene']];mk=maprow['sha256'];images.setdefault(mk,uri(DATASET/maprow['image']));maps[selected['scene']]={'geometry':maprow['geometry'],'image':mk}
        frames=[];pairs=[]
        for ob,pose in zip(obs,traj['frames']):
            if ob['frame']!=pose['frame']:raise ValueError('frame mismatch')
            key=ob['rgb_sha256'];images.setdefault(key,uri(DATASET/ob['rgb']))
            old=previous.get((eid,ob['frame']));new=current.get((eid,ob['frame']))
            if old and new:pairs.append((old,new))
            frames.append({'frame':ob['frame'],'position':pose['position'],'image':key,'eligible':ob['eligible_for_inference'],'terminal':ob['terminal'],
              'previous':({'probability_yes':old['answer']['probability_yes'],'probability_no':old['answer']['probability_no'],'image_frames':old['image_frames']} if old else None),
              'current':({'probability_yes':new['answer']['probability_yes'],'probability_no':new['answer']['probability_no'],'image_frames':new['image_frames']} if new else None)})
        cases.append({'episode_id':eid,'scene':selected['scene'],'group':selected['group'],'instruction_zh':ep['instruction_zh'],'instruction_en':ep['instruction'],'frames':frames,'reference_path':traj.get('reference_path',[])})
        item=run_summary['by_case'][eid];by_case[eid]={'previous_mean':item['previous_mean'],'current_mean':item['current_mean'],'increased':item['increased'],'decreased':item['decreased'],'equal':item['equal']}
    overall=run_summary['overall']
    summary={'valid':overall['valid'],'total':overall['total'],'previous_mean_probability_yes':overall['previous_mean'],'mean_probability_yes':overall['current_mean'],'increased':overall['increased'],'decreased':overall['decreased'],'equal':overall['equal'],'concurrency':run_summary['max_workers'],'by_case':by_case,'replay_frames':sum(len(c['frames']) for c in cases)}
    prompts={'v002_en':prompt_text('v002','en'),'v002_zh':prompt_text('v002','zh'),'v003_en':prompt_text('v004','en'),'v003_zh':prompt_text('v004','zh')}
    payload={'tag':'jev_noul_v004_ten_cases_vs_v002','summary':summary,'cases':cases,'maps':maps,'map':maps[cases[0]['scene']],'images':images,'prompts':prompts}
    page=PAGE.replace('<title>JEV 回退点 · v002 vs v003</title>','<title>JEV 回退点 · v002 vs v004</title>')
    page=page.replace('JEV 回退点 · 上一版 v002 / 新版 v003','JEV 回退点 · 上一版 v002 / 新版 v004')
    page=page.replace('<h2 id="title"></h2>','<h2 id="title"></h2><select id="caseSelect" aria-label="轨迹"></select><p id="caseStats" class="muted"></p>')
    page=page.replace('v002 · English','上一版 v002 · English').replace('v002 · 中文翻译','上一版 v002 · 中文翻译').replace('v003 · English','新版 v004 · English').replace('v003 · 中文翻译','新版 v004 · 中文翻译')
    page=page.replace('kujiale_0123_fix_15_3 · 90个有效观测 · 90进程同时提交','10条轨迹 · 862个有效观测 · 200并发worker')
    page=page.replace('__DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')).replace('__SCRIPT__',(ROOT/'core/jev_noul_version_compare.js').read_text())
    from fontTools import subset
    from fontTools.ttLib import TTFont
    cfg=read(ROOT/'core/crossing_visualization_template.json');font=TTFont(cfg['font'],fontNumber=0);sub=subset.Subsetter();sub.populate(text=page);sub.subset(font)
    buf=io.BytesIO();font.save(buf);page=page.replace('</head>','<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,'+base64.b64encode(buf.getvalue()).decode()+')}body,button,select,input,textarea{font-family:CrossingSans,sans-serif}</style></head>')
    html=out/'jev_noul_v002_vs_v004.html';html.write_text(page);shutil.copy2(cfg['font_license'],out/'FONT_LICENSE.txt')
    write(out/'export_manifest.json',{'run':str(run),'html_sha256':sha(html),'cases':len(cases),'frames':summary['replay_frames'],'valid':summary['valid'],'prompt_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in prompts.items()}})
    print(json.dumps({'html':str(html),'bytes':html.stat().st_size,'sha256':sha(html),'summary':summary},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
