"""Export one-trajectory JEV v002 versus v003 probability comparison."""
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
    FALLBACK_CRITERIA_EN,
    FALLBACK_CRITERIA_ZH,
    FALLBACK_INSTRUCTIONS_EN,
    FALLBACK_INSTRUCTIONS_ZH,
    NEAR_FALLBACK_CONTEXT_EN,
    NEAR_FALLBACK_CONTEXT_ZH,
    NEAR_FALLBACK_CRITERIA_EN,
    NEAR_FALLBACK_CRITERIA_ZH,
    NEAR_FALLBACK_INSTRUCTIONS_EN,
    NEAR_FALLBACK_INSTRUCTIONS_ZH,
    STATE_CONTEXT_EN,
    STATE_CONTEXT_ZH,
)

DATASET=ROOT/'outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001'

PAGE=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>JEV 回退点 · v002 vs v003</title>
<style>
:root{--ink:#17344e;--muted:#65788a;--line:#d9e2eb;--bg:#edf2f6;--blue:#3156a3;--red:#b33a3a}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif}header{background:linear-gradient(115deg,#17344e,#1d5a68);color:#fff;padding:22px 26px}header h1{margin:0 0 5px;font-size:24px}.sub{font-size:12px;opacity:.84}.stats{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;padding:14px 16px 0}.metric,.panel{background:#fff;border:1px solid var(--line);border-radius:10px}.metric{padding:11px 14px}.metric strong{display:block;font-size:23px;font-variant-numeric:tabular-nums}.metric span{font-size:12px;color:var(--muted)}.notice{margin:12px 16px;padding:10px 14px;border-left:4px solid #c58317;background:#fff7e8}.layout{display:grid;grid-template-columns:minmax(700px,1fr) 380px;gap:14px;padding:0 16px 18px}.panel{padding:14px;min-width:0}h2{font-size:18px;margin:0 0 10px}h3{font-size:15px;margin:14px 0 7px}p{margin:7px 0}.muted{color:var(--muted);font-size:12px}button,select,input,textarea{font:inherit}button,select{border:1px solid #c5d2de;border-radius:6px;padding:6px 8px;background:#fff;color:var(--ink)}button{cursor:pointer}button:hover{background:#e6eef8}.mapGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.mapTitle{font-weight:700;margin:0 0 5px}.evidenceMap{display:block;width:100%;height:440px;background:#f3f6f9;border-radius:7px}.legend{display:flex;gap:12px;font-size:12px}.swatch{display:inline-block;width:26px;height:5px;margin-right:5px;vertical-align:middle}.playback{margin:9px 0}input[type=range]{width:100%;accent-color:#2377bb}.controls{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:7px 0}#scorePlot{display:block;width:100%;height:190px;background:#fff}#rgb{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#122432;border-radius:7px}.values{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin:10px 0}.value{border:1px solid var(--line);border-radius:7px;padding:8px}.value b{display:block;font-size:18px}.value span{font-size:11px;color:var(--muted)}#history{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}#history button{padding:3px;font-size:11px}#history img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain}pre{white-space:pre-wrap;word-break:break-word;background:#f3f6fa;padding:10px;border-radius:6px;max-height:320px;overflow:auto;font:12px/1.55 ui-monospace,monospace}details{margin:10px 0}summary{cursor:pointer;font-weight:700}textarea{width:100%;min-height:72px;border:1px solid #c5d2de;border-radius:6px;padding:8px}.footer{padding:0 18px 20px;color:var(--muted);font-size:12px}
@media(max-width:1000px){.layout{display:block}.panel{margin-bottom:12px}.stats{grid-template-columns:repeat(3,1fr)}}@media(max-width:720px){.mapGrid{grid-template-columns:1fr}.evidenceMap{height:340px}.stats{grid-template-columns:repeat(2,1fr)}.values{grid-template-columns:1fr}header{padding:18px}h1{font-size:20px}}
</style></head><body><header><select id="language"><option value="zh">中文</option><option value="en">English</option></select><h1>JEV 回退点 · 上一版 v002 / 新版 v003</h1><div class="sub" id="runInfo"></div></header>
<div class="stats" id="stats"></div><div class="notice"><span data-i18n="pathHint"></span></div>
<main class="layout"><section class="panel"><h2 id="title"></h2><p class="muted">kujiale_0123_fix_15_3 · 90个有效观测 · 90进程同时提交</p><div class="mapGrid"><div><p class="mapTitle" data-i18n="prevMap"></p><canvas class="evidenceMap" id="previousMap"></canvas><div class="legend"><span><i class="swatch" style="background:rgb(219,234,254)"></i>0</span><span><i class="swatch" style="background:rgb(124,146,196)"></i>.5</span><span><i class="swatch" style="background:rgb(30,58,138)"></i>1</span></div></div><div><p class="mapTitle" data-i18n="newMap"></p><canvas class="evidenceMap" id="newMap"></canvas><div class="legend"><span><i class="swatch" style="background:rgb(253,226,202)"></i>0</span><span><i class="swatch" style="background:rgb(196,127,115)"></i>.5</span><span><i class="swatch" style="background:rgb(139,29,29)"></i>1</span></div></div></div>
<div class="playback"><label for="frame" data-i18n="mapProgress"></label><input id="frame" type="range" min="0" value="0"><div id="step"></div></div><div class="controls"><button id="prev" data-i18n="prev"></button><button id="play" data-i18n="play"></button><button id="next" data-i18n="next"></button><label><input id="reference" type="checkbox"> <span data-i18n="reference"></span></label><label><input id="full" type="checkbox" checked> <span data-i18n="full"></span></label></div>
<h3>同帧概率 / Same-frame probability</h3><canvas id="scorePlot"></canvas>
<details><summary data-i18n="prompt"></summary><h3>v002 · English</h3><pre id="v002Prompt"></pre><h3>v002 · 中文翻译</h3><pre id="v002PromptZh"></pre><h3>v003 · English</h3><pre id="v003Prompt"></pre><h3>v003 · 中文翻译</h3><pre id="v003PromptZh"></pre></details>
<details><summary data-i18n="protocol"></summary><p>两版输入均为严格 t-2,t-1,t 三帧RGB。没有输入任务、动作、位置、地图、标签、参考路线或旧回答。Qwen轨迹仅用于地图几何，不作为两版判断输入。</p><p>v002与v003均返回单个Noul概率；不存在1–5映射。颜色只表示原始概率，不平滑、不设确认阈值。</p></details></section>
<aside class="panel"><h2 data-i18n="current"></h2><img id="rgb" alt="current RGB"><div class="playback"><label for="imageFrame" data-i18n="imageProgress"></label><input id="imageFrame" type="range" min="0" value="0"><div id="imageStep"></div></div><div class="values"><div class="value"><b id="previousValue"></b><span data-i18n="previous"></span></div><div class="value"><b id="newValue"></b><span data-i18n="newVersion"></span></div><div class="value"><b id="delta"></b><span data-i18n="delta"></span></div></div><p class="muted" id="inputInfo"></p><div id="history"></div><h3>复核</h3><select id="category"><option value="">未分类</option><option value="v003_high">新版偏高</option><option value="v003_low">新版偏低</option><option value="both_ok">两版合理</option><option value="other">其他</option></select><textarea id="note" placeholder="记录本帧判断依据"></textarea><button id="export" data-i18n="export"></button><p class="muted" id="instruction"></p></aside></main><div class="footer" id="footer"></div><script id="payload" type="application/json">__DATA__</script><script>__SCRIPT__</script></body></html>'''

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def uri(path):
    suffix=Path(path).suffix.lower();mime='image/jpeg' if suffix in ('.jpg','.jpeg') else 'image/webp'
    return 'data:'+mime+';base64,'+base64.b64encode(Path(path).read_bytes()).decode()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    run=args.run.resolve();out=args.output.resolve()
    if out.exists():raise ValueError('Use a new export directory')
    out.mkdir(parents=True)
    manifest=read(run/'manifest.json');episode_id=manifest['episode_id']
    cases=read(ROOT/'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01/evaluation_selection.json')
    selected=next(x for x in cases if x['episode_id']==episode_id)
    episodes={x['episode_id']:x for x in map(json.loads,(DATASET/'inputs/episodes.jsonl').read_text().splitlines())}
    episode=episodes[episode_id];observations=read(DATASET/episode['observations']);trajectory=read(DATASET/selected['trajectory'])
    rows={r['frame']:r for r in read(run/'rows.json')};previous=read(run/'previous_predictions.json');qwen=read(run/'qwen_predictions.json')
    images={};frames=[]
    for obs,pose in zip(observations,trajectory['frames']):
        if obs['frame']!=pose['frame']:raise ValueError('frame mismatch')
        key=obs['rgb_sha256'];images.setdefault(key,uri(DATASET/obs['rgb']))
        row=rows.get(obs['frame'])
        frames.append({'frame':obs['frame'],'position':pose['position'],'image':key,'eligible':obs['eligible_for_inference'],'terminal':obs['terminal'],
          'previous':previous.get(str(obs['frame'])),'current':({'probability_yes':row['answer']['probability_yes'],'probability_no':row['answer']['probability_no'],'image_frames':row['image_frames']} if row else None),
          'qwen':qwen.get(str(obs['frame']))})
    maps=read(DATASET/'evaluation/maps.json')[selected['scene']];map_key=maps['sha256'];images.setdefault(map_key,uri(DATASET/maps['image']))
    summary=read(run/'summary.json');summary['replay_frames']=len(frames)
    prompts={
      'v002_en':'State context: '+STATE_CONTEXT_EN+'\n\nQuestion type: noul\nQuestion: '+FALLBACK_INSTRUCTIONS_EN+'\n\ntrue: '+FALLBACK_CRITERIA_EN['true']+'\nfalse: '+FALLBACK_CRITERIA_EN['false'],
      'v002_zh':'状态上下文：'+STATE_CONTEXT_ZH+'\n\n问题类型：noul\n问题：'+FALLBACK_INSTRUCTIONS_ZH+'\n\ntrue：'+FALLBACK_CRITERIA_ZH['true']+'\nfalse：'+FALLBACK_CRITERIA_ZH['false'],
      'v003_en':'State context: '+NEAR_FALLBACK_CONTEXT_EN+'\n\nQuestion type: noul\nQuestion: '+NEAR_FALLBACK_INSTRUCTIONS_EN+'\n\ntrue: '+NEAR_FALLBACK_CRITERIA_EN['true']+'\nfalse: '+NEAR_FALLBACK_CRITERIA_EN['false'],
      'v003_zh':'状态上下文：'+NEAR_FALLBACK_CONTEXT_ZH+'\n\n问题类型：noul\n问题：'+NEAR_FALLBACK_INSTRUCTIONS_ZH+'\n\ntrue：'+NEAR_FALLBACK_CRITERIA_ZH['true']+'\nfalse：'+NEAR_FALLBACK_CRITERIA_ZH['false'],
    }
    payload={'tag':'jev_noul_v003_kujiale_0123_fix_15_3','summary':summary,'caseData':{'episode_id':episode_id,'scene':selected['scene'],'group':selected['group'],'instruction_zh':episode['instruction_zh'],'instruction_en':episode['instruction'],'frames':frames,'reference_path':trajectory.get('reference_path',[])},'map':{'geometry':maps['geometry'],'image':map_key},'images':images,'prompts':prompts}
    page=PAGE.replace('__DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')).replace('__SCRIPT__',(ROOT/'core/jev_noul_version_compare.js').read_text())
    from fontTools import subset
    from fontTools.ttLib import TTFont
    cfg=read(ROOT/'core/crossing_visualization_template.json');font=TTFont(cfg['font'],fontNumber=0);sub=subset.Subsetter();sub.populate(text=page);sub.subset(font)
    buffer=io.BytesIO();font.save(buffer);page=page.replace('</head>','<style>@font-face{font-family:CrossingSans;src:url(data:font/ttf;base64,'+base64.b64encode(buffer.getvalue()).decode()+')}body,button,select,input,textarea{font-family:CrossingSans,sans-serif}</style></head>')
    html=out/'jev_noul_v002_vs_v003.html';html.write_text(page);shutil.copy2(cfg['font_license'],out/'FONT_LICENSE.txt')
    write(out/'export_manifest.json',{'run':str(run),'html_sha256':sha(html),'frames':len(frames),'valid':summary['valid'],'concurrency':summary['concurrency'],'prompt_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in prompts.items()}})
    print(json.dumps({'html':str(html),'bytes':html.stat().st_size,'sha256':sha(html),'summary':summary},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
