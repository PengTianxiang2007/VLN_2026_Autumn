"""Export all twelve v004 trajectories against the original Qwen4B best_v001."""
import argparse
import base64
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.agent_route_choice import read,write
from export_jev_noul_compare import PAGE,data_uri,sha

DATASET=ROOT/'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'
QWEN_RUN=ROOT/'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'
V004_RUNS=[
    ROOT/'outputs/crossing_checkpoint/jev_noul_v004/run_20261108_01_two_cases',
    ROOT/'outputs/crossing_checkpoint/jev_noul_v004/run_20261108_03_ten_final',
]

def qwen_row(episode_id,frame):
    row=read(QWEN_RUN/'cases'/episode_id/('F%04d.response.json'%frame))
    return {'valid':bool(row.get('valid')),'score':row['answer']['score'] if row.get('valid') else None}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve()
    if out.exists():raise ValueError('Use a new export directory')
    out.mkdir(parents=True)
    episodes={r['episode_id']:r for r in map(json.loads,(DATASET/'inputs/episodes.jsonl').read_text().splitlines())}
    map_source=read(DATASET/'evaluation/maps.json');rows={};selections=[]
    for run in V004_RUNS:
        selection=read(run/'selection.json');cases=selection.get('cases') or selection.get('episodes');selections.extend(cases)
        for row in read(run/'rows_v004.json'):
            if row.get('phase')=='complete':rows[(row['episode_id'],row['frame'])]=row
    if len(selections)!=12 or len(rows)!=1050:raise ValueError('Unexpected merged scope')
    images={};maps={};cases=[];qwen_scores=[];jev_probs=[]
    for selected in selections:
        eid=selected['episode_id'];ep=episodes[eid];obs=read(DATASET/ep['observations']);traj=read(DATASET/selected['trajectory']);map_row=map_source[selected['scene']]
        map_key=map_row['sha256'];images.setdefault(map_key,data_uri(DATASET/map_row['image']));maps[selected['scene']]={'geometry':map_row['geometry'],'image':map_key}
        frames=[]
        for ob,pose in zip(obs,traj['frames']):
            if ob['frame']!=pose['frame']:raise ValueError('frame mismatch')
            key=ob['rgb_sha256'];images.setdefault(key,data_uri(DATASET/ob['rgb']));row=rows.get((eid,ob['frame']));q=qwen_row(eid,ob['frame']) if row else {'valid':False,'score':None}
            if row:
                p_yes=row['answer']['probability_yes'];jev_probs.append(p_yes)
                if q['valid']:qwen_scores.append(q['score'])
                jev={'probability_yes':p_yes,'probability_no':row['answer']['probability_no'],'image_frames':row['image_frames']}
            else:jev=None
            frames.append({'frame':ob['frame'],'position':pose['position'],'image':key,'eligible':ob['eligible_for_inference'],'terminal':ob['terminal'],'qwen':q,'jev':jev})
        cases.append({'episode_id':eid,'scene':selected['scene'],'group':selected['group'],'instruction_zh':ep['instruction_zh'],'instruction_en':ep['instruction'],'frames':frames,'reference_path':traj.get('reference_path',[])})
    summary={'cases':12,'groups':{'failure':sum(c['group']=='failure' for c in cases),'success':sum(c['group']=='success' for c in cases)},'valid_calls':len(rows),'expected_calls':1050,'replay_frames':sum(len(c['frames']) for c in cases),'qwen_mean_score':sum(qwen_scores)/len(qwen_scores),'jev_mean_probability':sum(jev_probs)/len(jev_probs),'qwen_score_histogram':dict(Counter(map(str,qwen_scores))),'jev_probability_decile_histogram':{str(b):sum(b/10<=v<(b+1)/10 for v in jev_probs) for b in range(10)},'concurrency':200,'comparison':'Same-frame descriptive comparison only. Qwen 1-5 score and JEV 0-1 probability have different scales; no accuracy or superiority claim.'}
    prompt_en=(V004_RUNS[1]/'prompt_v004_en.txt').read_text();prompt_zh=(V004_RUNS[1]/'prompt_v004_zh.txt').read_text()
    payload={'tag':'jev_noul_v004_vs_qwen4b_best_v001_12cases','summary':summary,'cases':cases,'maps':maps,'images':images,'prompt_en':prompt_en,'prompt_zh':prompt_zh}
    page=PAGE.replace('<title>JEV Noul vs Qwen4B · 离线轨迹对照</title>','<title>JEV Noul v004 vs 最初Qwen4B · 12条离线轨迹</title>').replace('JEV Noul × Qwen4B · 离线轨迹对照','JEV Noul v004 × 最初Qwen4B · 12条离线轨迹对照')
    page=page.replace('Qwen4B 同帧分数来自 best_v001；JEV 使用同一轨迹，仅改变逐步判断模型。','Qwen4B同帧分数来自最初best_v001；JEV为当前最好v004。地图只保留路线和机器人位置。')
    page=page.replace('__DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')).replace('__SCRIPT__',(ROOT/'core/jev_noul_compare_review.js').read_text())
    from fontTools import subset
    from fontTools.ttLib import TTFont
    cfg=read(ROOT/'core/crossing_visualization_template.json');font=TTFont(cfg['font'],fontNumber=0);sub=subset.Subsetter();sub.populate(text=page);sub.subset(font)
    buf=io.BytesIO();font.save(buf);page=page.replace('</head>','<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,'+base64.b64encode(buf.getvalue()).decode()+')}body,button,select,input,textarea{font-family:CrossingSans,sans-serif}</style></head>')
    html=out/'jev_noul_v004_vs_qwen4b.html';html.write_text(page);shutil.copy2(cfg['font_license'],out/'FONT_LICENSE.txt')
    write(out/'export_manifest.json',{'html_sha256':sha(html),'cases':12,'frames':summary['replay_frames'],'valid':len(rows),'prompt_en_sha256':hashlib.sha256(prompt_en.encode()).hexdigest(),'prompt_zh_sha256':hashlib.sha256(prompt_zh.encode()).hexdigest()})
    print(json.dumps({'html':str(html),'bytes':html.stat().st_size,'sha256':sha(html),'summary':summary},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
