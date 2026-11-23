'use strict';
const $ = id => document.getElementById(id);
const esc = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const colors = {current:'#147861',original:'#416da4',reference:'#7e7066',checkpoint:'#92551d',
  flagged:'#c53e39',reviewed:'#bb790b',local:'#8529a6',jump:'#8a584b'};
const layers = {original:true,current:true,reference:true,checkpoint:true,flagged:true,local:true,jump:true,reviewed:false};
const arms=['current','original'];
let lang='zh', selected=0, filter='all', eventFilter='important', chosenEvent=null;
const frame={current:0,original:0}, timer={}, cache=new Map();
const t=(zh,en)=>lang==='zh'?zh:en;
const cc=()=>DATA.cases[selected];
const role=a=>a==='current'?t('当前版本','Current'):t('原版','Original');
const sign=n=>n>0?'+':'';
const option=(v,s,active)=>'<option value="'+esc(v)+'"'+(v===active?' selected':'')+'>'+esc(s)+'</option>';
function change(c){
  if(c.current.sr!==c.original.sr) return c.current.sr?'gain':'loss';
  return c.current.sr?'bothSuccess':'bothFail';
}
function filterName(x){
  return {all:t('全部任务','All cases'),gain:t('失败转成功','Failure → success'),loss:t('成功转失败','Success → failure'),
    bothSuccess:t('均成功','Both succeeded'),bothFail:t('均失败','Both failed'),rollback:t('实际回退','Physical rollback')}[x];
}
function matching(){
  return DATA.cases.map((c,i)=>({c,i})).filter(({c})=>filter==='all'||(filter==='rollback'?c.rollbacks>0:change(c)===filter));
}
function drawNavigation(){
  const rows=matching(), at=rows.findIndex(x=>x.i===selected);
  $('filter').innerHTML=['all','gain','loss','bothSuccess','bothFail','rollback'].map(k=>option(k,filterName(k),filter)).join('');
  $('case').innerHTML=rows.map(({c,i})=>option(i,[c.id,role('original')+' '+outcome(c.original.sr),role('current')+' '+outcome(c.current.sr)].join(' · '),selected)).join('');
  $('prev-case').disabled=at<=0;$('next-case').disabled=at<0||at===rows.length-1;
  $('matches').textContent=(at+1)+' / '+rows.length;
}
function drawHeader(){
  document.documentElement.lang=lang==='zh'?'zh-CN':'en';
  $('title').textContent=document.title=t('在线导航恢复 · 配对回放','Navigation recovery · paired replay');
  $('stamp').textContent='StreamVLN · VLNVerse fine val_unseen · seed 2  /  '+new Date(DATA.at).toLocaleString(lang==='zh'?'zh-CN':'en-GB',{timeZone:'Asia/Shanghai',hour12:false})+' UTC+8';
  $('zh').setAttribute('aria-pressed',lang==='zh');$('en').setAttribute('aria-pressed',lang==='en');
  $('csv').textContent=t('下载逐条成绩（CSV 压缩包）','Download scores (CSV in ZIP)');
  $('offline').textContent=t('下载离线回放','Download offline replay');
  $('offline').style.display=location.protocol==='file:'?'none':'';
  const n=DATA.cases.length,s=DATA.summary,deltaSR=(s.current.success-s.original.success)*100/n,deltaSPL=s.current.spl-s.original.spl;
  $('metric-head').innerHTML='<tr><th>'+t('配对成绩','Paired scores')+'</th><th>SR</th><th>'+t('平均 SPL','Mean SPL')+'</th></tr>';
  $('summary-table').innerHTML=arms.map(a=>'<tr><td>'+role(a)+'</td><td>'+s[a].success+'/'+n+' ('+(s[a].success*100/n).toFixed(2)+'%)</td><td>'+s[a].spl.toFixed(4)+'</td></tr>').join('')+
    '<tr><td>'+t('当前 − 原版','Current − original')+'</td><td>'+sign(deltaSR)+deltaSR.toFixed(2)+t(' 个百分点',' pp')+'</td><td>'+sign(deltaSPL)+deltaSPL.toFixed(4)+'</td></tr>';
  $('coverage').textContent=n+' / '+DATA.total+' '+t('条已评分','cases scored');
  $('changes').textContent=t('原版失败转成功 '+s.gains+' 条，成功转失败 '+s.losses+' 条。',s.gains+' failures became successes; '+s.losses+' successes became failures.');
  $('recovery-totals').textContent=t(s.rollbackCases+' 条发生回退，共 '+s.rollbacks+' 次回退、'+s.handoffs+' 次交还。',s.rollbackCases+' cases with rollback · '+s.rollbacks+' rollbacks · '+s.handoffs+' handoffs.');
  $('filter-label').textContent=t('筛选','Filter');$('case-label').textContent=t('任务','Case');
  $('prev-case').title=t('上一条','Previous case');$('next-case').title=t('下一条','Next case');
  $('map-title').textContent=t('轨迹与有效节点','Trajectories and retained nodes');
  drawLayerControls();
  $('map-seek-label').textContent=t('当前版本帧','Current frame');
  $('map').setAttribute('aria-label',$('map-title').textContent);
  $('wave-title').textContent=t('JEV 波形','JEV signal');
  $('wave-hint').textContent=t('原始概率 / 滤波 · 短线为有效节点','Raw / filtered · ticks are retained nodes');
  $('event-title').textContent=t('在线事件','Online events');
  $('independent').textContent=t('两侧分别按各自的观测帧播放。点击事件可定位当前版本；地图圆点跟随两侧各自的进度。','Each run has its own observation timeline. Select an event to seek the current run. Map cursors follow the two timelines independently.');
  $('skip-title').textContent=t('技术跳过 '+DATA.skips.length+' 条（单列，不计入 SR / SPL）','Technical skips: '+DATA.skips.length+' (excluded from SR / SPL)');
  $('skips').innerHTML=DATA.skips.map(s=>'<li>'+esc(s.id)+' · '+(s.reason==='http520'?t('JEV 接口返回 HTTP 520','JEV returned HTTP 520'):t('回退位姿的朝向偏差超限','Rollback yaw drift exceeded the limit'))+'</li>').join('');
}
function outcome(sr){return sr?t('成功','Success'):t('失败','Failure')}
function termination(key){return ({success:t('成功','Success'),fall:t('跌倒','Fall'),stuck:t('卡住','Stuck'),not_reach_goal:t('未到达目标','Goal not reached'),timeout:t('超时','Timeout')})[key]||key}
function drawArms(){
  $('players').innerHTML=arms.map(a=>'<article class="arm '+a+'"><h3>'+role(a)+'</h3><p class="metrics" id="metrics-'+a+'"></p><canvas class="frame" id="img-'+a+'" width="480" height="360" aria-label="'+role(a)+' RGB"></canvas><div class="controls"><button data-play="'+a+'"></button><button data-step="-1" data-arm="'+a+'" title="'+t('上一帧','Previous frame')+'">‹</button><input id="seek-'+a+'" type="range" min="0" step="1" aria-label="'+role(a)+'"><button data-step="1" data-arm="'+a+'" title="'+t('下一帧','Next frame')+'">›</button><span class="stamp" id="num-'+a+'"></span></div></article>').join('');
  for(const a of arms){
    const z=cc()[a];
    $('metrics-'+a).textContent=outcome(z.sr)+' · SPL '+z.spl.toFixed(3)+' · NE '+z.ne.toFixed(2)+' m · TL '+z.tl.toFixed(2)+' m · '+termination(z.end);
    $('seek-'+a).max=z.count-1;
    $('seek-'+a).oninput=e=>{pause(a);seek(a,Number(e.target.value))};
    document.querySelector('[data-play="'+a+'"]').onclick=()=>toggle(a);
    seek(a,frame[a]);
  }
  document.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>{const a=b.dataset.arm;pause(a);seek(a,frame[a]+Number(b.dataset.step))});
}
function pause(a){clearInterval(timer[a]);timer[a]=null;const b=document.querySelector('[data-play="'+a+'"]');if(b)b.textContent=t('播放','Play')}
function toggle(a){
  if(timer[a])return pause(a);
  if(frame[a]>=cc()[a].count-1)seek(a,0);
  timer[a]=setInterval(()=>{if(frame[a]>=cc()[a].count-1)return pause(a);seek(a,frame[a]+1)},220);
  document.querySelector('[data-play="'+a+'"]').textContent=t('暂停','Pause');
}
function rgb(a){
  const c=cc(), z=c[a], i=frame[a], slot=i%16;
  const src='media/'+c.id+'/'+z.sheets[Math.floor(i/16)];
  let image=cache.get(src);
  if(!image){
    image=new Image();cache.set(src,image);
    if(cache.size>12)cache.delete(cache.keys().next().value);
    image.src=src;
  }
  const canvas=$('img-'+a),ctx=canvas.getContext('2d');
  const paint=()=>{if(c!==cc()||i!==frame[a]||!canvas.isConnected)return;ctx.drawImage(image,(slot%4)*480,Math.floor(slot/4)*360,480,360,0,0,480,360)};
  if(image.complete&&image.naturalWidth)paint();else{ctx.clearRect(0,0,480,360);image.addEventListener('load',paint,{once:true})}
}
function seek(a,i){
  const z=cc()[a];frame[a]=Math.max(0,Math.min(i,z.count-1));
  $('seek-'+a).value=frame[a];$('num-'+a).textContent='F'+frame[a]+' / '+(z.count-1)+(a==='current'&&z.local.includes(frame[a])?' · '+t('局部纠错','Local recovery'):'');
  if(a==='current'){$('map-seek').max=z.count-1;$('map-seek').value=frame[a];$('map-frame').textContent='F'+frame[a]+' / '+(z.count-1)}
  if(!timer[a])pause(a);rgb(a);drawMap();drawWave();
}
function drawLayerControls(){
  const names={original:t('原版轨迹','Original path'),current:t('当前版本轨迹','Current path'),
    reference:t('参考路线','Reference route'),checkpoint:t('有效节点与回退点','Nodes and checkpoints'),
    flagged:t('偏航节点 → 下一节点','Flagged node → next node'),local:t('局部纠错轨迹','Local recovery path'),
    jump:t('回退跳转','Rollback jump'),reviewed:t('被判偏航的评审区间','Segment judged off-route')};
  $('layers').innerHTML='<legend>'+t('地图图层','Map layers')+'</legend>'+Object.keys(layers).map(k=>{
    const sample=k==='checkpoint'?'circle':['reference','jump','reviewed'].includes(k)?'dashed':'';
    return '<label><input type="checkbox" data-layer="'+k+'" '+(layers[k]?'checked':'')+'><i class="'+sample+'" style="--ink:'+colors[k]+'"></i>'+names[k]+'</label>';
  }).join('');
  $('map-note').textContent=t('○ 有效节点，◆ 实际回退点，□ 终止节点，★ 目标。红色从偏航节点的观测帧开始；若先回退或结束，就画到该段最后一帧。紫色显示回退后局部策略走过的路径。','○ Retained node, ◆ rollback target, □ terminal node, ★ goal. Red starts at the flagged observation and ends at the next node, rollback or termination. Purple traces motion under local control.');
}
function segments(c){
  const intervals=[], corrections=[], rollbacks=c.events.filter(e=>e.type==='rollback');
  const ends=new Map(rollbacks.map(e=>[e.leg,e.seq]));
  const nodeIndex=new Map(c.nodes.map((n,i)=>[n[2]+'/'+n[3],i]));
  const localFrames=new Set(c.current.local);
  for(const [eventIndex,e] of c.events.entries()){
    if(e.type==='rollback'&&localFrames.has(e.after)){
      let last=e.after;
      while(localFrames.has(last+1))last++;
      corrections.push({from:e.after,to:last,eventIndex});
    }
    if(e.type!=='deviation'||e.answer?.verdict!=='deviated')continue;
    const idx=nodeIndex.get(e.leg+'/'+e.node), from=c.nodes[idx][0];
    const following=c.nodes[idx+1], hasNext=following?.[2]===e.leg;
    const previous=c.nodes[nodeIndex.get(e.leg+'/'+e.previous)];
    const to=hasNext?following[0]:(ends.get(e.leg)??(c.current.count-1));
    intervals.push({from,to,previous:previous?.[0]??from,
      endKind:hasNext?'node':ends.has(e.leg)?'rollback':'end',eventIndex});
  }
  return {jumps:rollbacks.filter(e=>e.after>e.seq),targets:new Set(rollbacks.map(e=>e.target)),intervals,corrections};
}
const tracks=DATA.cases.map(segments);
function drawMap(){
  const c=cc(),g=DATA.maps[c.scene],svg=$('map'),track=tracks[selected];
  const xy=p=>[(p[0]-g.low[0])/g.resolution,(g.high[1]-p[1])/g.resolution];
  const project=p=>xy(p).map(v=>v.toFixed(2)).join(',');
  const path=(points,color,width,dash='')=>'<polyline points="'+points.map(project).join(' ')+'" fill="none" stroke="'+color+'" stroke-width="'+width+'" '+(dash?'stroke-dasharray="'+dash+'"':'')+'/>';
  const dot=(p,r,fill,stroke)=>{const [x,y]=xy(p);return '<circle cx="'+x+'" cy="'+y+'" r="'+r+'" fill="'+fill+'" stroke="'+stroke+'" stroke-width="1.5"/>'};
  const all=c.reference.concat(c.current.points,c.original.points).map(xy);
  let xs=all.map(p=>p[0]),ys=all.map(p=>p[1]),x=Math.min(...xs)-20,y=Math.min(...ys)-20;
  svg.setAttribute('viewBox',[x,y,Math.max(50,Math.max(...xs)-x+20),Math.max(50,Math.max(...ys)-y+20)].join(' '));
  let html='<image href="maps/'+c.scene+'.png" width="'+g.width+'" height="'+g.height+'" opacity=".68"/>';
  const group=(k,body)=>'<g data-map-layer="'+k+'">'+body+'</g>';
  if(layers.reference)html+=group('reference',path(c.reference,colors.reference,2,'4 3'));
  if(layers.original)html+=group('original',path(c.original.points,colors.original,2.4));
  if(layers.current){
    let start=0,body='';
    for(const e of track.jumps){
      body+=path(c.current.points.slice(start,e.seq+1),colors.current,2.5);
      start=e.after;
    }
    html+=group('current',body+path(c.current.points.slice(start),colors.current,2.5));
  }
  if(layers.jump)html+=group('jump',track.jumps.map(e=>path([c.current.points[e.seq],c.current.points[e.after]],colors.jump,2,'3 3')).join(''));
  function highlight(from,to,eventIndex,label,color,width,dash=''){
    const target=c.current.points[from], frames='F'+from+' → F'+to;
    return '<g class="annotation" data-map-event="'+eventIndex+'" data-from="'+from+'" data-to="'+to+'"><title>'+esc(label+' · '+frames)+'</title>'+
      path(c.current.points.slice(from,to+1),color,width,dash)+dot(target,4.2,'none',color)+'</g>';
  }
  if(layers.reviewed)html+=group('reviewed',track.intervals.map(r=>highlight(r.previous,r.from,r.eventIndex,t('被判偏航的评审区间','Reviewed segment'),colors.reviewed,5,'5 2')).join(''));
  if(layers.flagged)html+=group('flagged',track.intervals.map(r=>{
    const end=r.endKind==='node'?t('下一有效节点','Next retained node'):r.endKind==='rollback'?t('回退前','Before rollback'):t('本段结束','End of leg');
    return highlight(r.from,r.to,r.eventIndex,t('偏航节点','Flagged node')+' → '+end,colors.flagged,3.8);
  }).join(''));
  if(layers.local)html+=group('local',track.corrections.map(r=>highlight(r.from,r.to,r.eventIndex,t('局部纠错','Local recovery'),colors.local,3.2)).join(''));
  if(layers.checkpoint){
    html+=group('checkpoint',c.nodes.map(n=>{
      const [x,y]=xy(c.current.points[n[0]]),used=track.targets.has(n[0]);
      let symbol=dot(c.current.points[n[0]],2.5,'white',colors.checkpoint);
      if(used)symbol='<path d="M'+x+' '+(y-4)+'l4 4 -4 4 -4 -4z" fill="'+colors.checkpoint+'" stroke="white"/>';
      else if(n[4])symbol='<rect x="'+(x-2.5)+'" y="'+(y-2.5)+'" width="5" height="5" fill="white" stroke="'+colors.checkpoint+'"/>';
      const label=used?t('实际回退点','Rollback target'):n[4]?t('终止节点','Terminal node'):t('有效节点','Retained node');
      return '<g data-node="'+n[0]+'" class="annotation"><title>'+esc(label+' · '+n[3]+' · F'+n[0])+'</title>'+symbol+'</g>';
    }).join(''));
  }
  const [gx,gy]=xy(c.reference[c.reference.length-1]);
  html+='<text x="'+gx+'" y="'+(gy+4)+'" text-anchor="middle" font-size="14" fill="#991d35">★</text>';
  for(const a of ['original','current'])if(layers[a])html+='<g pointer-events="none">'+dot(c[a].points[frame[a]],a==='current'?3.8:5.2,colors[a],'white')+'</g>';
  svg.innerHTML=html;
}
function drawWave(){
  const c=cc(),x=f=>f*598/Math.max(1,c.current.count-1)+1,y=v=>65-60*v;
  let h='<path d="M0 65H600 M0 35H600" stroke="#d8e0d6" fill="none"/>';
  for(const [column,color] of [[1,'#9aa999'],[2,colors.current]]){
    let prev=-2,pts=[];
    function flush(){if(pts.length)h+='<polyline points="'+pts.join(' ')+'" fill="none" stroke="'+color+'" stroke-width="1.7"/>';pts=[]}
    for(const row of c.jev){if(row[0]!==prev+1||row[column]==null)flush();if(row[column]!=null)pts.push(x(row[0])+','+y(row[column]));prev=row[0]}
    flush();
  }
  for(const n of c.nodes)h+='<path d="M'+x(n[0])+' 57v10" stroke="'+colors.checkpoint+'" stroke-width="2"/>';
  $('wave').innerHTML=h+'<path d="M'+x(frame.current)+' 0v70" stroke="#253e39" stroke-width="2"/>';
}
function eventName(e){
  if(e.type==='rollback')return t('实际回退','Rollback')+' #'+e.number;
  if(e.type==='handoff')return t('交还','Handoff');
  if(e.type==='route_unresolved')return t('未获得局部指令','No local instruction');
  if(e.type==='pending_alarm_superseded')return t('报警已取代','Alarm superseded');
  const v=e.answer?.verdict, verdict=v==='deviated'?t('偏航','Deviation'):v==='consistent'?t('一致','Consistent'):t('无有效判断','Invalid review');
  return (e.terminal?t('终止评审','Terminal review'):e.type==='deviation_gate'?t('接管前复核','Recheck'):(e.node||''))+' · '+verdict;
}
function drawEvents(){
  const c=cc(),list=$('events');
  $('event-filter').innerHTML=[['important',t('报警与恢复','Alarms and recovery')],['all',t('全部节点与事件','All nodes and events')]].map(([v,label])=>option(v,label,eventFilter)).join('');
  list.innerHTML=c.events.map((e,i)=>{
    if(eventFilter==='important' && e.type==='deviation' && e.answer?.verdict!=='deviated')return '';
    return '<button data-event="'+i+'" class="'+(i===chosenEvent?'selected':'')+'">A'+e.action+' · '+esc(eventName(e))+'</button>';
  }).join('');
  if(!list.children.length)list.textContent=t('本条没有报警或恢复事件。','No alarms or recovery events in this run.');
  const e=c.events[chosenEvent];
  if(!e){$('detail').textContent=t('选择事件查看判定与对应画面。','Select an event to inspect its decision and frame.');return}
  let html='<b>'+esc(eventName(e))+' · A'+e.action+' · F'+e.seq+'</b>';
  const paragraph=(title,body)=>body?'<p><strong>'+title+'</strong> '+esc(body)+'</p>':'';
  if(e.type==='rollback'){
    html+=paragraph(t('已走 → 改选支路','Taken → chosen branch'),(e.tried||'—')+' → '+(e.chosen||'—'))+paragraph(t('局部指令','Local instruction'),e.instruction[lang]);
    html+='<div class="line">'+[[e.target,t('回退点','Checkpoint')],[e.seq,t('回退前','Before rollback')],[e.after,t('回退后','After rollback')]].map(([f,n])=>'<button data-frame="'+f+'">'+n+' F'+f+'</button>').join('')+'</div>';
    html+='<div class="views">'+e.views.map((v,i)=>'<figure><img src="media/'+c.id+'/'+v+'" alt="'+esc(v)+'"><figcaption>'+[t('左 70°','Left 70°'),t('正前','Front'),t('右 70°','Right 70°')][i]+'</figcaption></figure>').join('')+'</div>';
  }else if(e.type==='handoff')html+=paragraph(t('局部动作数','Local actions'),String(e.localSteps))+paragraph(t('交还原因','Handoff reason'),e.reason==='local_stop'?t('局部策略主动 STOP','Local policy emitted STOP'):t('局部动作达到预算','Local action budget reached'));
  else if(e.type==='route_unresolved')html+=paragraph(t('原因','Reason'),e.status==='no_alternative'?t('没有可选替代支路','No alternative branch'):e.status==='input_incomplete'?t('选路图像不足','Insufficient selection images'):t('模型回答未通过校验','Model output did not pass validation'));
  else if(e.answer){
    const a=e.answer;
    html+=paragraph(t('区间','Segment'),a.previous_id+' → '+a.current_id)+paragraph(t('模型描述','Model description'),a.segment_summary?.[lang])+paragraph(t('判断理由','Rationale'),a.reason?.[lang])+paragraph(t('任务进度','Task progress'),a.semantic_progress?.[lang]);
    const evidence=[...(a.instruction_evidence||[]).map(v=>v['quote_'+lang]),...(a.visual_evidence||[]).map(v=>'F'+v.frames.join(', F')+' · '+v.description[lang]),...(a.uncertainties||[]).map(v=>v[lang])].filter(Boolean);
    if(evidence.length)html+='<details><summary>'+t('指令、观测证据与不确定性','Instruction, observations and uncertainties')+'</summary><ul>'+evidence.map(v=>'<li>'+esc(v)+'</li>').join('')+'</ul></details>';
  }
  $('detail').innerHTML=html;
}
function render(){
  drawHeader();drawNavigation();const c=cc();
  $('case-title').textContent=c.id;$('case-outcome').textContent=filterName(change(c))+' · '+t('回退','Rollbacks')+' '+c.rollbacks+' · '+t('交还','Handoffs')+' '+c.handoffs;
  $('instruction').textContent=c.instruction[lang];drawArms();drawEvents();
}
function choose(i){
  arms.forEach(pause);selected=i;frame.current=frame.original=0;chosenEvent=null;render();
}
$('case').onchange=e=>choose(Number(e.target.value));
$('filter').onchange=e=>{filter=e.target.value;const rows=matching();if(rows.length)choose(rows[0].i)};
for(const [id,step] of [['prev-case',-1],['next-case',1]])$(id).onclick=()=>{const m=matching();choose(m[m.findIndex(x=>x.i===selected)+step].i)};
for(const l of ['zh','en'])$(l).onclick=()=>{arms.forEach(pause);lang=l;render()};
$('events').onclick=e=>{const b=e.target.closest('[data-event]');if(!b)return;chosenEvent=Number(b.dataset.event);pause('current');seek('current',cc().events[chosenEvent].seq);drawEvents()};
$('detail').onclick=e=>{const b=e.target.closest('[data-frame]');if(b){pause('current');seek('current',Number(b.dataset.frame))}};
$('layers').onchange=e=>{const k=e.target.dataset.layer;if(k in layers){layers[k]=e.target.checked;drawMap()}};
$('map-seek').oninput=e=>{pause('current');seek('current',Number(e.target.value))};
$('map').onclick=e=>{
  const g=e.target.closest('[data-node],[data-map-event]');if(!g)return;
  pause('current');
  if(g.dataset.node!==undefined){seek('current',Number(g.dataset.node));return}
  chosenEvent=Number(g.dataset.mapEvent);seek('current',Number(g.dataset.from));drawEvents();
};
$('event-filter').onchange=e=>{eventFilter=e.target.value;chosenEvent=null;drawEvents()};
document.addEventListener('visibilitychange',()=>{if(document.hidden)arms.forEach(pause)});
render();
