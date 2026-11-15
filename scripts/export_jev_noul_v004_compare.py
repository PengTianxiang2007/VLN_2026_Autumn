"""Export two-case JEV v003 versus v004 fallback-probability comparison."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import read, write
from core.jev_node import (
    COMPACT_FALLBACK_CONTEXT_EN,
    COMPACT_FALLBACK_CONTEXT_ZH,
    COMPACT_FALLBACK_CRITERIA_EN,
    COMPACT_FALLBACK_CRITERIA_ZH,
    COMPACT_FALLBACK_INSTRUCTIONS_EN,
    COMPACT_FALLBACK_INSTRUCTIONS_ZH,
    NEAR_FALLBACK_CONTEXT_EN,
    NEAR_FALLBACK_CONTEXT_ZH,
    NEAR_FALLBACK_CRITERIA_EN,
    NEAR_FALLBACK_CRITERIA_ZH,
    NEAR_FALLBACK_INSTRUCTIONS_EN,
    NEAR_FALLBACK_INSTRUCTIONS_ZH,
)
from export_jev_noul_v003_compare import PAGE, sha, uri

DATASET=ROOT/'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'


def prompt_text(version, language):
    if version == 'v003':
        context=NEAR_FALLBACK_CONTEXT_EN if language=='en' else NEAR_FALLBACK_CONTEXT_ZH
        instructions=NEAR_FALLBACK_INSTRUCTIONS_EN if language=='en' else NEAR_FALLBACK_INSTRUCTIONS_ZH
        criteria=NEAR_FALLBACK_CRITERIA_EN if language=='en' else NEAR_FALLBACK_CRITERIA_ZH
    else:
        context=COMPACT_FALLBACK_CONTEXT_EN if language=='en' else COMPACT_FALLBACK_CONTEXT_ZH
        instructions=COMPACT_FALLBACK_INSTRUCTIONS_EN if language=='en' else COMPACT_FALLBACK_INSTRUCTIONS_ZH
        criteria=COMPACT_FALLBACK_CRITERIA_EN if language=='en' else COMPACT_FALLBACK_CRITERIA_ZH
    prefix='State context' if language=='en' else '状态上下文'
    type_label='Question type' if language=='en' else '问题类型'
    question_label='Question' if language=='en' else '问题'
    colon=':' if language=='en' else '：'
    return '\n'.join([prefix+colon+' '+context,'',type_label+colon+' noul',question_label+colon+' '+instructions,'','true'+colon+' '+criteria['true'],'false'+colon+' '+criteria['false']])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    run=args.run.resolve();out=args.output.resolve()
    if out.exists():raise ValueError('Use a new export directory')
    out.mkdir(parents=True)
    selection=read(run/'selection.json')
    episodes={r['episode_id']:r for r in map(json.loads,(DATASET/'inputs/episodes.jsonl').read_text().splitlines())}
    maps_data=read(DATASET/'evaluation/maps.json')
    v004={(r['episode_id'],r['frame']):r for r in read(run/'rows_v004.json') if r.get('phase')=='complete'}
    v003={(r['episode_id'],r['frame']):r for r in read(run/'rows_v003.json') if r.get('phase')=='complete'}
    summary_run=read(run/'summary.json');images={};cases=[];maps={}
    case_summary={}
    for selected in selection['episodes']:
        episode_id=selected['episode_id'];episode=episodes[episode_id]
        observations=read(DATASET/episode['observations']);trajectory=read(DATASET/selected['trajectory'])
        map_row=maps_data[selected['scene']];map_key=map_row['sha256'];images.setdefault(map_key,uri(DATASET/map_row['image']));maps[selected['scene']]={'geometry':map_row['geometry'],'image':map_key}
        frames=[];paired=[]
        for observation,pose in zip(observations,trajectory['frames']):
            if observation['frame']!=pose['frame']:raise ValueError('frame mismatch')
            image_key=observation['rgb_sha256'];images.setdefault(image_key,uri(DATASET/observation['rgb']))
            previous=v003.get((episode_id,observation['frame']));current=v004.get((episode_id,observation['frame']))
            if previous and current:paired.append((previous,current))
            frames.append({'frame':observation['frame'],'position':pose['position'],'image':image_key,'eligible':observation['eligible_for_inference'],'terminal':observation['terminal'],
                'previous':({'probability_yes':previous['answer']['probability_yes'],'probability_no':previous['answer']['probability_no'],'image_frames':previous['image_frames']} if previous else None),
                'current':({'probability_yes':current['answer']['probability_yes'],'probability_no':current['answer']['probability_no'],'image_frames':current['image_frames']} if current else None)})
        cases.append({'episode_id':episode_id,'scene':selected['scene'],'group':selected['group'],'instruction_zh':episode['instruction_zh'],'instruction_en':episode['instruction'],'frames':frames,'reference_path':trajectory.get('reference_path',[])})
        cm=summary_run['v004'][episode_id]
        case_summary[episode_id]={'previous_mean':cm['v003_mean_probability'],'current_mean':cm['mean_probability'],'increased':cm['increased'],'decreased':cm['decreased'],'equal':cm['equal']}
    all_prev=[r['answer']['probability_yes'] for r in v003.values()];all_cur=[r['answer']['probability_yes'] for r in v004.values()]
    paired=[(v003[k],v004[k]) for k in v003.keys()&v004.keys()]
    summary={'valid':len(v004),'total':summary_run['overall']['expected_v004'],'previous_mean_probability_yes':sum(all_prev)/len(all_prev),'mean_probability_yes':sum(all_cur)/len(all_cur),
      'increased':sum(b['answer']['probability_yes']>a['answer']['probability_yes'] for a,b in paired),
      'decreased':sum(b['answer']['probability_yes']<a['answer']['probability_yes'] for a,b in paired),
      'equal':sum(b['answer']['probability_yes']==a['answer']['probability_yes'] for a,b in paired),
      'concurrency':summary_run['max_workers'],'by_case':case_summary,'replay_frames':sum(len(c['frames']) for c in cases)}
    prompts={'v002_en':prompt_text('v003','en'),'v002_zh':prompt_text('v003','zh'),'v003_en':prompt_text('v004','en'),'v003_zh':prompt_text('v004','zh')}
    payload={'tag':'jev_noul_v004_two_cases_vs_v003','summary':summary,'cases':cases,'maps':maps,'map':maps[cases[0]['scene']],'images':images,'prompts':prompts}
    page=PAGE.replace('<title>JEV 回退点 · v002 vs v003</title>','<title>JEV 回退点 · v003 vs v004</title>')
    page=page.replace('JEV 回退点 · 上一版 v002 / 新版 v003','JEV 回退点 · 上一版 v003 / 新版 v004')
    page=page.replace('<h2 id="title"></h2>','<h2 id="title"></h2><select id="caseSelect" aria-label="轨迹"></select><p id="caseStats" class="muted"></p>')
    page=page.replace('v002 · English','上一版 v003 · English').replace('v002 · 中文翻译','上一版 v003 · 中文翻译')
    page=page.replace('v003 · English','新版 v004 · English').replace('v003 · 中文翻译','新版 v004 · 中文翻译')
    page=page.replace('kujiale_0123_fix_15_3 · 90个有效观测 · 90进程同时提交','每条轨迹全部有效观测 · 286个任务一次性提交')
    page=page.replace('__DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')).replace('__SCRIPT__',(ROOT/'core/jev_noul_version_compare.js').read_text())
    from fontTools import subset
    from fontTools.ttLib import TTFont
    cfg=read(ROOT/'core/crossing_visualization_template.json');font=TTFont(cfg['font'],fontNumber=0);sub=subset.Subsetter();sub.populate(text=page);sub.subset(font)
    buffer=io.BytesIO();font.save(buffer);page=page.replace('</head>','<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,'+base64.b64encode(buffer.getvalue()).decode()+')}body,button,select,input,textarea{font-family:CrossingSans,sans-serif}</style></head>')
    html=out/'jev_noul_v003_vs_v004.html';html.write_text(page);shutil.copy2(cfg['font_license'],out/'FONT_LICENSE.txt')
    write(out/'export_manifest.json',{'run':str(run),'html_sha256':sha(html),'cases':len(cases),'frames':summary['replay_frames'],'valid':summary['valid'],'prompt_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in prompts.items()}})
    print(json.dumps({'html':str(html),'bytes':html.stat().st_size,'sha256':sha(html),'summary':summary},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
