"""Build a portable HTML review of causal crossing detections and fixed map references."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_crossing_checkpoint import read_json,score


TEMPLATE='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crossing 存档点离线评审</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef2f6;color:#1c2d40;font:14px/1.6 system-ui,"Microsoft YaHei"}header{background:#18334e;color:white;padding:18px 24px}h1{font-size:22px;margin:0}main{padding:16px;display:grid;grid-template-columns:230px 1fr 430px;gap:14px}.panel{background:white;border:1px solid #d6dfe8;border-radius:10px;padding:14px;min-width:0}button,select{font:inherit;padding:6px;border:1px solid #c5d1dd;background:white;border-radius:5px;cursor:pointer}button.active{background:#deebfa;border-color:#3275bb}#cases button{display:block;width:100%;text-align:left;margin:5px 0;font-size:12px}canvas{width:100%;max-height:72vh;object-fit:contain;background:#f1f4f7}.rgb{width:100%;aspect-ratio:4/3;overflow:hidden;background:#111}.rgb video{width:150%;max-width:none;display:block}input[type=range]{width:100%}.muted{color:#627589;font-size:12px}.legend{display:flex;gap:12px;flex-wrap:wrap}.event{padding:8px;border-bottom:1px solid #e3e8ed;cursor:pointer}.event:hover{background:#f1f6fd}.good{color:#15805b}.bad{color:#cb4646}.miss{color:#b87908}pre{white-space:pre-wrap;word-break:break-word;font-size:12px;background:#f5f7fa;padding:10px;max-height:280px;overflow:auto}#events{max-height:350px;overflow:auto}#stats{margin-top:5px}details{margin-top:14px}@media(max-width:1100px){main{grid-template-columns:200px 1fr}#detail{grid-column:2}}@media(max-width:700px){main{display:block}.panel{margin-bottom:12px}}
</style><header><h1>Crossing 存档点 · 离线评审</h1><div id="stats"></div><div id="modelInfo"></div></header>
<main><aside class="panel"><div id="cases"></div><p class="muted"><span id="splitInfo"></span>每条轨迹按动作顺序识别；地图仅用于事后评分。</p></aside>
<section class="panel"><h2 id="title"></h2><canvas id="map"></canvas><div class="legend"><span style="color:#287cc3">蓝线：实际轨迹</span><span>灰圈：原地图 crossing</span><span class="good">绿点：匹配存档</span><span class="bad">红点：未匹配／重复</span><span class="miss">橙圈：未检出参照</span></div><div><label><input type="checkbox" id="full">显示完整实际轨迹</label></div><input id="frame" type="range" min="0" value="0"><div id="step"></div><button id="prev">上一步</button> <button id="play">播放 / 暂停</button> <button id="next">下一步</button><p id="instruction"></p><details><summary>评分口径与局限</summary><p>地图参照固定为此前标定的 55 个 crossing。仅统计实际轨迹进入 0.7m 邻域的访问事件，离开 1.2m 后再次进入另计一次访问；预测按确认时刻和 1.0m 空间容差一对一匹配。重复存档计入误报；另保存 0.7m 和 1.5m 容差结果。</p><p>这些统计衡量与地图几何参照的一致性。未进行独立逐帧可见性标注，因此“未匹配”仍需要人工检查；不能直接称为视觉检测金标准。最接近路口的动作步仅为时间参照，不等同于真实做出选择的时刻。预测位置是记录的机器人位置，不是模型估计出的路口中心。</p><p>模型只接收纯 RGB、历史动作和视觉存档记忆，不接收地图、GPS、参考路线、最终成败或未来画面。存档确认时间不会倒填。</p></details></section>
<aside class="panel" id="detail"><div class="rgb"><video id="video" preload="metadata" muted playsinline></video></div><p id="caseStats"></p><div id="events"></div><h3>当前动作时刻的模型判断</h3><pre id="answer"></pre><p id="inputs" class="muted"></p><textarea id="note" placeholder="此条轨迹的复核意见（保存在本机浏览器）" style="width:100%;min-height:80px"></textarea><button id="export">导出复核意见</button></aside></main>
<script id="payload" type="application/json">__DATA__</script><script>
const D=JSON.parse(document.getElementById('payload').textContent),$=id=>document.getElementById(id);let cid=Object.keys(D.cases)[0],frame=0,img=new Image();
const c=()=>D.cases[cid],s=()=>D.maps[c().scene],p=()=>D.results[cid];
$('splitInfo').textContent=D.summary.split==='validation'?'独立验证集，方法冻结后评测。':'开发集：成功、失败各 4 条。';
$('modelInfo').textContent=`模型：${D.model.name} · 后端：${D.model.backend} · ${D.model.precision} · 推理版本：${JSON.stringify(D.model.versions)}`;
const percent=x=>x==null?'—':(x*100).toFixed(1)+'%';const m=D.summary.metrics['1.0'];
$('stats').textContent=`${D.tag} · 完成 ${D.summary.completed_cases}/${D.summary.expected_cases} · 地图匹配准确率 ${percent(m.precision)} · 召回率 ${percent(m.recall)} · TP ${m.tp} / FP ${m.fp} / FN ${m.fn}`;
function xy(v){return[(v[0]-s().low[0])/s().resolution,(s().high[1]-v[1])/s().resolution]}
function draw(){let cv=$('map'),ctx=cv.getContext('2d');cv.width=s().width;cv.height=s().height;if(img.complete&&img.naturalWidth)ctx.drawImage(img,0,0,cv.width,cv.height);let steps=c().steps.filter(x=>x.position&&($('full').checked||x.frame<=frame));ctx.beginPath();steps.forEach((v,i)=>{let q=xy(v.position);i?ctx.lineTo(...q):ctx.moveTo(...q)});ctx.strokeStyle='#287cc3';ctx.lineWidth=2.1;ctx.stroke();let missed=new Set(p().metrics['1.0'].missed_encounters.map(id=>id.split(':')[0]));
for(let cross of s().crossings){let q=xy(cross.position);ctx.beginPath();ctx.arc(...q,.7/s().resolution,0,2*Math.PI);ctx.strokeStyle=missed.has(cross.id)?'#d39525':'#8091a0';ctx.lineWidth=1.4;ctx.stroke();ctx.fillStyle='#263f53';ctx.font='bold 11px sans-serif';ctx.fillText(cross.id,q[0]+5,q[1]-5)}
for(let event of p().events.filter(e=>e.confirmation_frame!==null&&($('full').checked||e.confirmation_frame<=frame))){let q=xy(c().steps[event.confirmation_frame].position),match=p().metrics['1.0'].predictions.find(x=>x.prediction_id===event.id);ctx.fillStyle=match.label==='matched'?'#169e70':'#dc5151';ctx.beginPath();ctx.arc(...q,4.5,0,2*Math.PI);ctx.fill();ctx.font='10px sans-serif';ctx.fillText(event.id,q[0]+5,q[1]+12)}let st=c().steps[frame];if(st&&st.position){let q=xy(st.position);ctx.fillStyle='#19394e';ctx.beginPath();ctx.arc(...q,5,0,2*Math.PI);ctx.fill()}}
function seek(n,fromVideo=false){frame=Math.min(c().frames-1,Math.max(0,n));$('frame').value=frame;$('step').textContent=`动作画面 ${frame} / ${c().frames-1}`;if(!fromVideo)$('video').currentTime=frame/c().fps;let r=(D.predictions[cid]||[]).find(x=>x.frame===frame);$('answer').textContent=r?JSON.stringify(r.prediction,null,2):'本帧没有模型判断（终止帧、复用帧或尚未处理）。';$('inputs').textContent=r?`仅提供历史画面：${r.image_frames.join(', ')}；历史动作 ${r.executed_actions.length} 个。`:'';draw()}
function select(id){cid=id;frame=0;document.querySelectorAll('#cases button').forEach(b=>b.classList.toggle('active',b.dataset.id===id));$('title').textContent=id;$('instruction').textContent=c().instruction;$('video').src=c().video;$('frame').max=c().frames-1;img=new Image();img.onload=()=>seek(0);img.src=s().floorplan;$('note').value=localStorage.getItem('crossing:'+D.tag+':'+id)||'';let met=p().metrics['1.0'];$('caseStats').textContent=`原导航：${c().success?'成功':'失败'} · 匹配 ${met.tp} / 未匹配 ${met.fp} / 未检出 ${met.fn}`;$('events').replaceChildren();for(let e of p().events){let div=document.createElement('div');div.className='event';let label=e.confirmation_frame===null?'候选，未确认':p().metrics['1.0'].predictions.find(x=>x.prediction_id===e.id).label;label=({matched:'匹配存档',unmatched_prediction:'未匹配存档',duplicate_prediction:'重复存档'})[label]||label;div.textContent=`${e.id} · ${label} · 首见 ${e.first_seen_frame} → 确认 ${e.confirmation_frame??'—'} · ${(e.confirmation_observation||{}).description||e.description}`;div.onclick=()=>seek(e.confirmation_frame??e.first_seen_frame);$('events').append(div)}for(let id of met.missed_encounters){let e=c().encounters.find(x=>x.id===id),div=document.createElement('div');div.className='event miss';let cross=s().crossings.find(x=>x.id===e.crossing_id);div.textContent=`参照未检出 ${id} · 最近步 ${e.closest_frame} · ${cross.kind==='obstacle_route'?'家具形成的分岔':'通道／房间分岔'} · ${cross.note||''}`;div.onclick=()=>seek(e.closest_frame);$('events').append(div)}}
for(let [id,v]of Object.entries(D.cases)){let b=document.createElement('button');b.dataset.id=id;b.textContent=`${v.success?'成功':'失败'} · ${id}`;b.onclick=()=>select(id);$('cases').append(b)}$('frame').oninput=e=>seek(+e.target.value);$('prev').onclick=()=>seek(frame-1);$('next').onclick=()=>seek(frame+1);$('full').onchange=draw;$('play').onclick=()=>{$('video').paused?$('video').play():$('video').pause()};$('video').ontimeupdate=()=>seek(Math.floor($('video').currentTime*c().fps),true);$('note').oninput=()=>localStorage.setItem('crossing:'+D.tag+':'+cid,$('note').value);$('export').onclick=()=>{let notes=Object.fromEntries(Object.keys(D.cases).map(id=>[id,localStorage.getItem('crossing:'+D.tag+':'+id)||'']));let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({tag:D.tag,notes},null,2)],{type:'application/json'}));a.download='crossing_review_notes.json';a.click();URL.revokeObjectURL(a.href)};if(cid)select(cid);
</script></html>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tag',required=True)
    args=parser.parse_args();score(args.output,args.tag)
    results=read_json(args.output/'runs'/args.tag/'scores.json')
    if not results['cases']:
        print('No completed trajectories; no report with fabricated results generated.');return
    cases=read_json(args.output/'evaluation/cases.json');inputs=read_json(args.output/'inputs.json')
    maps=read_json(args.output/'evaluation/maps.json');dest=args.output/'reports'/args.tag
    (dest/'videos').mkdir(parents=True,exist_ok=True);selected={};predictions={}
    for episode in results['cases']:
        selected[episode]=cases[episode]
        target=dest/cases[episode]['video']
        if not target.exists():shutil.copy2(inputs[episode]['video'],target)
        log=args.output/'runs'/args.tag/'cases'/episode/'predictions.jsonl'
        predictions[episode]=[json.loads(line) for line in log.read_text().splitlines()]
    manifest=read_json(args.output/'runs'/args.tag/'manifest.json')
    model=dict(name=Path(manifest['model_path']).name,backend=manifest.get('inference_backend','vllm'),
               precision='FP8 权重还原为 BF16 计算' if manifest.get('inference_backend')=='transformers' else '原生 FP8 推理',
               versions=manifest.get('environment_versions'))
    data=dict(tag=args.tag,model=model,summary=results['summary'],results=results['cases'],cases=selected,
              maps={s:maps[s] for s in {c['scene'] for c in selected.values()}},predictions=predictions)
    encoded=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    (dest/'index.html').write_text(TEMPLATE.replace('__DATA__',encoded))
    print(dest/'index.html')


if __name__=='__main__':main()
