"""Export actual paired results and compact standalone replay without inference."""
import argparse,base64,html,json,hashlib,io,math
from PIL import Image
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
 out=a.campaign.resolve();dest=a.destination.resolve();dest.mkdir(parents=True,exist_ok=False)
 m=json.loads((out/'manifest.json').read_text());cases=[];images={};image_paths={}
 for case in m['cases']:
  d=out/'oracle_records'/case['episode_id'];record={'episode_id':case['episode_id'],'instruction':case['instruction'],'reference':case['reference_path'],'arms':{}}
  for arm in ['trunk','streamvln','oracle_actions']:
   folder=d/arm;result=folder/'result.json';observations=folder/'observations.jsonl'
   rows=[json.loads(l) for l in observations.read_text().splitlines()] if observations.exists() else []
   for row in rows:
    path=Path(row.pop('frame',''))
    row['image_id']=''
    if path.is_file():
     if str(path) not in image_paths:
      raw=path.read_bytes();key=hashlib.sha256(raw).hexdigest();image_paths[str(path)]=key
      if key not in images:
       im=Image.open(io.BytesIO(raw));im.thumbnail((480,360));buf=io.BytesIO();im.convert('RGB').save(buf,format='JPEG',quality=55)
       images[key]='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
     row['image_id']=image_paths[str(path)]
   record['arms'][arm]={'result':json.loads(result.read_text()) if result.exists() else None,'frames':rows}
  failure=d/'technical_failure.json'
  record['technical_failure']=json.loads(failure.read_text()) if failure.exists() else None
  record['checkpoint']=json.loads((d/'snapshot_checkpoint.json').read_text()) if (d/'snapshot_checkpoint.json').exists() else None
  record['actual_error']=json.loads((d/'actual_error.json').read_text()) if (d/'actual_error.json').exists() else None
  cases.append(record)
 for c in cases:
  d=out/'oracle_records'/c['episode_id'];proofs=[]
  for arm in ['streamvln','oracle_actions']:
   p=d/arm/'restore_proof.json'
   if p.exists():proofs.append(json.loads(p.read_text()))
  c['audit']={}
  if len(proofs)==2:
   c['audit']={'same_saved_pose':proofs[0]['saved_world_pose']==proofs[1]['saved_world_pose'],'same_policy_hash':proofs[0]['policy']['content_sha256']==proofs[1]['policy']['content_sha256'],'stabilized_pair_gap_m':math.dist(proofs[0]['actual_position'][:2],proofs[1]['actual_position'][:2])}
   snap=json.loads((d/'snapshot_checkpoint.json').read_text());frame=next(r for r in c['arms']['trunk']['frames'] if r['action_index']==snap['action_index'])
   c['audit']['saved_goal_distance_m']=math.dist(frame['position'][:2],c['reference'][-1][:2])
  for arm in c['arms'].values():
   r=arm['result']
   if r:r['metrics']={k:v for k,v in r['metrics'].items() if k in ['success','NE','spl','osr','TL','steps','fail_reason']}
 summary=[{'episode_id':c['episode_id'],'audit':c['audit'],'technical_failure':c['technical_failure'],**{arm:c['arms'][arm]['result'] for arm in ['streamvln','oracle_actions']}} for c in cases]
 (dest/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 paired=[c for c in cases if all(c['arms'][arm]['result'] and c['arms'][arm]['result'].get('triggered') for arm in ['streamvln','oracle_actions'])]
 counts={'requested_cases':len(cases),'valid_pairs':len(paired),'technical_failures':sum(bool(c['technical_failure']) for c in cases),'untriggered':sum(bool(c['arms']['streamvln']['result']) and not c['arms']['streamvln']['result'].get('triggered') for c in cases),'paired_final_success':{arm:sum(c['arms'][arm]['result']['metrics'].get('success',0) for c in paired) for arm in ['streamvln','oracle_actions']},'paired_local_correct':{arm:sum((c['arms'][arm]['result'].get('local_choice') or {}).get('choice')=='correct' for c in paired) for arm in ['streamvln','oracle_actions']}}
 counts['pending']=len(cases)-counts['valid_pairs']-counts['technical_failures']-counts['untriggered']
 (dest/'counts.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2))

 data=json.dumps(cases,ensure_ascii=False).replace('</','<\\/')
 page='''<!doctype html><meta charset="utf-8"><title>真实存档点：StreamVLN / Oracle动作对照</title><style>body{font:16px system-ui;margin:24px;background:#f5f7fa;color:#142034}section{display:flex;gap:16px}article{flex:1;min-width:0;background:white;padding:14px;border-radius:10px}img,canvas{width:100%;max-height:360px;object-fit:contain}input{width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px system-ui;line-height:1.6}select{padding:8px}button{padding:7px 10px;border:1px solid #cad3df;background:#eef4fc;border-radius:6px;cursor:pointer;margin:3px}.events{min-height:76px}article{box-shadow:0 2px 10px #1526400c}canvas{background:#fafbfd}h1{margin-bottom:8px}@media(max-width:900px){section{flex-direction:column}}small{display:block}</style><h1>真实存档点恢复与动作接管</h1><p>Oracle可看参考路线，但只执行导航动作；两组唯一姿态设置是返回相同实际存档。共同站姿稳定不等于PhysX位级回滚。局部选路与任务成功分别统计，未触发不是纠正失败。</p><pre id="counts"></pre><select id="cases"></select><p id="instruction"></p><section id="panels"></section><script>const DATA=__DATA__;const COUNTS=__COUNTS__;document.getElementById('counts').textContent=`任务 ${COUNTS.requested_cases} 条｜有效配对 ${COUNTS.valid_pairs}｜未触发 ${COUNTS.untriggered}｜技术失败 ${COUNTS.technical_failures}｜待完成 ${COUNTS.pending}\n有效配对最终成功：StreamVLN ${COUNTS.paired_final_success.streamvln}/${COUNTS.valid_pairs}，Oracle ${COUNTS.paired_final_success.oracle_actions}/${COUNTS.valid_pairs}\n有效配对局部选对：StreamVLN ${COUNTS.paired_local_correct.streamvln}/${COUNTS.valid_pairs}，Oracle ${COUNTS.paired_local_correct.oracle_actions}/${COUNTS.valid_pairs}`;const IMAGES=__IMAGES__;const arms=['trunk','streamvln','oracle_actions'];const names=['走错前主干','恢复后 StreamVLN','恢复后 Oracle 实际动作'];const menu=document.getElementById('cases');DATA.forEach((c,i)=>menu.add(new Option(c.episode_id,i)));function show(){let c=DATA[menu.value];document.getElementById('instruction').textContent=c.instruction+(c.technical_failure?' [技术失败] '+c.technical_failure.reason:'');let panels=document.getElementById('panels');panels.replaceChildren();arms.forEach((arm,j)=>{let a=c.arms[arm],box=document.createElement('article');box.innerHTML='<h2></h2><div class="events"></div><canvas width="500" height="400"></canvas><input class="map-progress" type="range" min="0" value="0"><img><input type="range" min="0" value="0"><small></small><pre></pre>';box.querySelector('h2').textContent=names[j];let r=a.result;box.querySelector('pre').textContent=r?`${r.triggered?'有效恢复配对':'未触发：沿用同一主干自然结果'}\n最终：${r.metrics.success?'成功':'失败'}｜NE ${Number(r.metrics.NE).toFixed(3)} m\n局部：${({correct:'选对',wrong:'选错',uncertain:'不确定'})[r.local_choice?.choice]||'未干预'}\n总动作：${r.actions}｜Oracle动作：${r.external_actions||0}\n${r.local_choice?.reason||''}`:(arm==='trunk'?'主干轨迹：先存档，再观察实际错误。':c.technical_failure?'恢复技术失败，无有效配对结果。':'无独立恢复轨迹。');let slider=box.querySelector('img+input'),mapSlider=box.querySelector('.map-progress');slider.max=Math.max(0,a.frames.length-1);mapSlider.max=slider.max;let events=box.querySelector('.events');function jump(label,action){if(action==null)return;let b=document.createElement('button');b.textContent=label+' · '+action;b.onclick=()=>{slider.value=a.frames.findIndex(f=>f.action_index>=action);draw()};events.append(b)}jump('存档',c.checkpoint?.action_index);if(arm==='trunk')jump('确认走错',c.actual_error?.action_index);jump(arm==='oracle_actions'?'交回模型':'选路判定',r?.local_choice?.action_index);let play=document.createElement('button');play.textContent='播放 / 暂停';let timer=null;play.onclick=()=>{if(timer){clearInterval(timer);timer=null}else timer=setInterval(()=>{if(!box.isConnected||+slider.value>=+slider.max){clearInterval(timer);timer=null;return}slider.value=+slider.value+1;draw()},250)};events.append(play);function draw(){mapSlider.value=slider.value;let idx=+slider.value,f=a.frames[idx];box.querySelector('img').src=IMAGES[f?.image_id]||'';box.querySelector('small').textContent=f?`action ${f.action_index} / physics ${f.physics_ticks}`:'无观测';let cv=box.querySelector('canvas'),ctx=cv.getContext('2d');ctx.clearRect(0,0,500,400);let points=[...c.reference,...Object.values(c.arms).flatMap(a=>a.frames.map(f=>f.position))];if(!points.length)return;let xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),xmin=Math.min(...xs)-1,ymin=Math.min(...ys)-1,scale=Math.min(460/(Math.max(...xs)-xmin+1),360/(Math.max(...ys)-ymin+1));let xy=p=>[20+(p[0]-xmin)*scale,380-(p[1]-ymin)*scale];function line(ps,color){ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=3;ps.forEach((p,i)=>{let q=xy(p);i?ctx.lineTo(...q):ctx.moveTo(...q)});ctx.stroke()}line(c.reference,'#b5bcc6');let cp=c.arms.trunk.frames.find(f=>f.action_index===c.checkpoint?.action_index),er=c.arms.trunk.frames.find(f=>f.action_index===c.actual_error?.action_index);for(let [node,color,label] of [[cp,'#17804a','存档'],[er,'#d54938','走错']])if(node){let q=xy(node.position);ctx.fillStyle=color;ctx.fillRect(q[0]-5,q[1]-5,10,10);ctx.font='14px sans-serif';ctx.fillText(label,q[0]+8,q[1]-8)}line(a.frames.slice(0,idx+1).map(f=>f.position),'#2877cf');if(f){ctx.beginPath();ctx.fillStyle='#db3928';ctx.arc(...xy(f.position),6,0,7);ctx.fill()}}slider.oninput=draw;mapSlider.oninput=()=>{slider.value=mapSlider.value;draw()};panels.append(box);draw()})}menu.onchange=show;show();</script>'''.replace('__COUNTS__',json.dumps(counts)).replace('__DATA__',data).replace('__IMAGES__',json.dumps(images))
 (dest/'checkpoint_pair_offline.html').write_text(page)
 print(json.dumps({'destination':str(dest),'complete_results':sum(bool(c['arms'][arm]['result']) for c in cases for arm in ['streamvln','oracle_actions'])}))
if __name__=='__main__':main()
