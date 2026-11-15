'use strict';
const B=window.JEV_LIVE_DATA;
const $=id=>document.getElementById(id);
const I18N={
  zh:{
    title:'StreamVLN + Isaac Sim 实时 JEV',trajectory:'轨迹与实时评分',all:'全部',
    success:'成功',failure:'失败',prev:'上一帧',next:'下一帧',play:'播放',pause:'暂停',
    observation:'当前观测',probability:'JEV 回退点概率',apiLatency:'JEV API 延迟',
    stepLag:'未决 step 延迟',inputFrames:'三帧输入',result:'逐帧原始结果',prompt:'完整提示词（英文请求 / 中文翻译）',
    review:'人工复核',likely:'像回退点',uncertain:'不确定',unlikely:'不像回退点',
    export:'导出复核意见',rawLine:'原始 JEV 概率',streamLine:'N=11 流式突出度',
    mapNodes:'在俯视路线显示采样节点',refLegend:'数据集参考路线',robotLegend:'当前机器人',
    probLegend:'路线颜色越深表示 JEV 概率越高',episodes:'轨迹',navSR:'导航 SR',
    calls:'JEV 回答',meanProb:'平均概率',meanLatency:'平均 API 延迟',
    p95Latency:'P95 API 延迟',nodes:'流式节点',instruction:'指令',
    sampleNodes:'横轴采样节点',sampleHint:'N=11、D=5；阈值0.6/0.18，平台0.45，节点间距≥3帧',
    current:'当前',reviewNote:'复核意见',generated:'本地离线页面 · 数据来自一次完整运行',
    runInfo:'40条新episode · StreamVLN H1 physical · JEV 1.14 · N=11/D=5',
    noticeX:'JEV 只作为旁路评分，不改变 StreamVLN 的动作、停止或官方评分。俯视底图由场景 USD 几何正交投影生成；勾选后仅显示流式采样节点。',
    caseStats:'{n} 帧 · {c} 次JEV',noScore:'无评分',successLabel:'成功',
    failureLabel:'失败',frame:'帧'
  },
  en:{
    title:'StreamVLN + Isaac Sim Live JEV',trajectory:'Trajectories and live scores',all:'All',
    success:'Success',failure:'Failure',prev:'Previous',next:'Next',play:'Play',pause:'Pause',
    observation:'Current observation',probability:'JEV fallback-point probability',apiLatency:'JEV API latency',
    stepLag:'Unresolved step lag',inputFrames:'Three-frame input',result:'Raw per-frame result',prompt:'Complete prompt (English request / Chinese translation)',
    review:'Human review',likely:'Likely checkpoint',uncertain:'Uncertain',unlikely:'Unlikely',
    export:'Export review notes',rawLine:'Raw JEV probability',streamLine:'N=11 streaming prominence',
    mapNodes:'Show sampled nodes on top-down route',refLegend:'Dataset reference route',robotLegend:'Current robot',
    probLegend:'Darker route means higher JEV probability',episodes:'Trajectories',navSR:'Navigation SR',
    calls:'JEV answers',meanProb:'Mean probability',meanLatency:'Mean API latency',
    p95Latency:'P95 API latency',nodes:'Streaming nodes',instruction:'Instruction',
    sampleNodes:'X-axis sampled nodes',sampleHint:'N=11, D=5; thresholds 0.6/0.18, plateau 0.45, spacing >=3 frames',
    current:'Current',reviewNote:'Review note',generated:'Local offline page · data from one complete run',
    runInfo:'40 new episodes · StreamVLN H1 physical · JEV 1.14 · N=11/D=5',
    noticeX:'JEV is a side-channel score and does not alter StreamVLN actions, stopping, or the official score. The floorplan is an orthographic projection of scene USD geometry; sampled nodes appear only when enabled.',
    caseStats:'{n} frames · {c} JEV calls',noScore:'No score',successLabel:'success',
    failureLabel:'failure',frame:'Frame'
  }
};
let lang='zh',ci=0,index=0,timer=null;
const floorplan=new Image();
floorplan.onload=()=>{if(window.JEV_LIVE)draw()};
floorplan.src=B.images[B.map.image];
const t=k=>I18N[lang][k]||k;
const c=()=>B.cases[ci];
const row=()=>c().frames[index];
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const esc=s=>String(s).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
function pColor(p){
  if(p===null||p===undefined)return '#c8d2db';
  const v=clamp(Number(p),0,1);
  return `hsl(${24-18*v},${48+35*v}%,${78-43*v}%)`;
}
function renderCases(){
  const filter=$('groupFilter').value;
  $('caseList').replaceChildren();
  B.cases.forEach((item,i)=>{
    if(filter!=='all'&&item.group!==filter)return;
    const button=document.createElement('button');
    button.className=i===ci?'active':'';
    button.textContent=`${item.episode_id}\n${item.group==='success'?t('successLabel'):t('failureLabel')} · ${item.frames.length}`;
    button.onclick=()=>select(i);
    $('caseList').append(button);
  });
}
function selectCase(n){
  ci=n;index=0;
  $('frame').max=c().frames.length-1;$('imageFrame').max=c().frames.length-1;
  $('caseStats').textContent=t('caseStats').replace('{n}',c().frames.length).replace('{c}',c().frames.filter(f=>f.jev).length);
  renderCases();seek(0);
}
function seek(value){
  index=clamp(Number(value),0,c().frames.length-1);
  $('frame').value=index;$('imageFrame').value=index;
  const r=row();
  $('step').textContent=`${index+1}/${c().frames.length}`;
  $('imageStep').textContent=`${index+1}/${c().frames.length}`;
  $('frameBadge').textContent=`${t('frame')} ${r.frame}`;
  $('rgb').src=B.images[r.image];
  const p=r.jev?.probability_yes;
  $('prob').textContent=p===null||p===undefined?'—':`${(100*p).toFixed(1)}%`;
  $('latency').textContent=r.jev?.latency_seconds===null||r.jev?.latency_seconds===undefined?'—':`${r.jev.latency_seconds.toFixed(2)} s`;
  $('lag').textContent=r.jev?.unresolved_step_lag===null||r.jev?.unresolved_step_lag===undefined?'—':`${r.jev.unresolved_step_lag} step`;
  $('instruction').textContent =
    lang==='zh' ? `中文：${c().instruction_zh}\n\nEnglish: ${c().instruction_en}`
                : `English: ${c().instruction_en}\n\n中文：${c().instruction_zh}`;
  $('raw').textContent=JSON.stringify({
    episode_id:c().episode_id,frame:r.frame,action:r.action,position:r.position,
    jev:r.jev,metrics:c().metrics,fail_reason:c().fail_reason
  },null,2);
  $('history').replaceChildren();
  for(const frameId of r.jev?.image_frames||[]){
    const frameData=c().frames[frameId];if(!frameData)continue;
    const button=document.createElement('button'),image=document.createElement('img'),label=document.createElement('span');
    image.src=B.images[frameData.image];label.textContent=String(frameId);
    button.append(image,label);button.onclick=()=>{stop();seek(frameId)};$('history').append(button);
  }
  try{
    const saved=JSON.parse(localStorage.getItem(`jev-live:${B.tag}:${c().episode_id}:${r.frame}`)||'{}');
    $('note').value=saved.note||'';$('category').value=saved.category||'uncertain';
  }catch{$('note').value='';}
  draw();
}
function draw(){drawMap();drawPlot();}
function drawMap(){
  const canvas=$('map'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#f5f8fa';ctx.fillRect(0,0,w,h);
  if(!floorplan.complete||!floorplan.naturalWidth){
    ctx.fillStyle='#64788a';ctx.font='14px system-ui';ctx.fillText('Loading floorplan…',28,42);return;
  }
  const geometry=B.map.geometry;
  const scale=Math.min((w-24)/floorplan.naturalWidth,(h-24)/floorplan.naturalHeight);
  const drawW=floorplan.naturalWidth*scale,drawH=floorplan.naturalHeight*scale;
  const originX=(w-drawW)/2,originY=(h-drawH)/2;
  ctx.drawImage(floorplan,originX,originY,drawW,drawH);
  const project=p=>({
    x:originX+((Number(p[0])-geometry.low[0])/geometry.resolution)/geometry.width*drawW,
    y:originY+((geometry.high[1]-Number(p[1]))/geometry.resolution)/geometry.height*drawH
  });
  const ref=(c().reference_path||[]).filter(Boolean);
  if(ref.length>1){
    ctx.strokeStyle='#27825d';ctx.lineWidth=3;ctx.setLineDash([7,5]);ctx.beginPath();
    ref.forEach((p,i)=>{const q=project(p);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y)});ctx.stroke();ctx.setLineDash([]);
  }
  const frames=c().frames.filter(f=>f.position);
  for(let i=0;i<frames.length-1;i++){
    const a=project(frames[i].position),b=project(frames[i+1].position);
    ctx.strokeStyle=pColor(frames[i].jev?.probability_yes);ctx.lineWidth=4;ctx.lineCap='round';
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
  }
  if($('showMapNodes').checked){
    c().streaming.nodes.forEach((node,n)=>{
      const f=c().frames[node.index];if(!f?.position)return;
      const q=project(f.position);
      ctx.fillStyle='#0793ad';ctx.strokeStyle='#fff';ctx.lineWidth=2;
      ctx.beginPath();ctx.arc(q.x,q.y,5,0,Math.PI*2);ctx.fill();ctx.stroke();
      ctx.fillStyle='#075467';ctx.font='11px system-ui';ctx.fillText(`S${String(n+1).padStart(2,'0')}`,q.x+7,q.y-7);
    });
  }
  const current=row().position;
  if(current){
    const q=project(current);
    ctx.fillStyle='#111';ctx.strokeStyle='#fff';ctx.lineWidth=2.5;
    ctx.beginPath();ctx.arc(q.x,q.y,8,0,Math.PI*2);ctx.fill();ctx.stroke();
  }
  ctx.fillStyle='#ffffffe8';ctx.fillRect(16,12,Math.min(w-32,420),38);
  ctx.fillStyle='#17344e';ctx.font='bold 14px system-ui';ctx.fillText(c().episode_id,27,30);
  ctx.fillStyle='#475f73';ctx.font='12px system-ui';
  ctx.fillText(`SR ${c().metrics.SR.toFixed(2)} · SPL ${c().metrics.SPL.toFixed(3)} · NE ${c().metrics.NE.toFixed(2)} m`,27,45);
}
function drawPlot(){
  const canvas=$('plot'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height,m={l:42,r:12,t:18,b:28};
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);
  const n=c().frames.length,x=i=>m.l+(n<=1?0:i/(n-1)*(w-m.l-m.r)),y=v=>m.t+(1-clamp(v,0,1))*(h-m.t-m.b);
  ctx.strokeStyle='#dce5ec';ctx.fillStyle='#758799';ctx.font='11px system-ui';
  for(const v of [0,.25,.5,.75,1]){ctx.beginPath();ctx.moveTo(m.l,y(v));ctx.lineTo(w-m.r,y(v));ctx.stroke();ctx.fillText(v.toFixed(2),6,y(v)+4);}
  const line=(values,color,width)=>{
    ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();let active=false;
    values.forEach((value,i)=>{if(value===null||value===undefined){active=false;return;}const px=x(i),py=y(value);active?ctx.lineTo(px,py):ctx.moveTo(px,py);active=true;});
    ctx.stroke();
  };
  if($('showRaw').checked)line(c().frames.map(f=>f.jev?.probability_yes),'#b33a3a',2);
  if($('showStreaming').checked){
    line(c().streaming.filtered,'#0793ad',3);
    c().streaming.nodes.forEach((node,i)=>{
      const px=x(node.index),py=y(node.value);
      ctx.strokeStyle='#0793ad';ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(px,h-m.b);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#0793ad';ctx.beginPath();ctx.arc(px,h-m.b,3,0,Math.PI*2);ctx.fill();
      ctx.font='10px system-ui';ctx.fillText(`S${String(i+1).padStart(2,'0')}`,Math.max(2,px-10),h-8);
    });
  }
  const px=x(index);ctx.strokeStyle='#111';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(px,m.t);ctx.lineTo(px,h-m.b);ctx.stroke();
  $('sampleSummary').textContent=c().streaming.nodes.length
    ?`${t('sampleNodes')}: ${c().streaming.nodes.map((node,i)=>`S${String(i+1).padStart(2,'0')}=F${node.index}`).join(', ')} · ${t('sampleHint')}`
    :`${t('sampleNodes')}: —`;
}
function updateStats(){
  const s=B.summary,items=[
    ['episodes',s.episodes],['navSR',`${(100*s.navigation.SR).toFixed(1)}%`],
    ['calls',s.valid_calls],['meanProb',`${(100*s.mean_probability).toFixed(1)}%`],
    ['meanLatency',`${s.mean_latency.toFixed(2)} s`],['p95Latency',`${s.latency_percentiles['95'].toFixed(2)} s`],
    ['nodes',s.streaming_nodes]
  ];
  $('stats').replaceChildren();
  for(const [key,value] of items){
    const box=document.createElement('div'),b=document.createElement('b'),span=document.createElement('span');
    box.className='metric';b.textContent=value;span.textContent=t(key);box.append(b,span);$('stats').append(box);
  }
}
function updateLanguage(){
  document.documentElement.lang=lang==='zh'?'zh-CN':'en';
  document.querySelectorAll('[data-i18n]').forEach(node=>node.textContent=t(node.dataset.i18n));
  $('title').textContent=t('title');$('runInfo').textContent=t('runInfo');$('notice').textContent=t('noticeX');
  $('promptEnglish').textContent=B.prompt_en;$('promptChinese').textContent=B.prompt_zh;
  $('note').placeholder=t('reviewNote');$('footer').textContent=t('generated');
  updateStats();renderCases();seek(index);
}
function stop(){if(timer!==null){clearInterval(timer);timer=null;}$('play').textContent=t('play');}
for(const id of ['frame','imageFrame'])$(id).oninput=e=>{stop();seek(Number(e.target.value));};
for(const id of ['showRaw','showStreaming','showMapNodes'])$(id).onchange=draw;
for(const [id,delta] of [['mapPrev',-1],['imagePrev',-1]])$(id).onclick=()=>{stop();seek(index+delta)};
$('nextBtn') && ($('nextBtn').onclick=()=>{stop();seek(index+1)});
$('play').onclick=()=>{
  if(timer!==null){stop();return;}
  if(index>=c().frames.length-1)seek(0);
  $('play').textContent=t('pause');
  timer=setInterval(()=>{if(index>=c().frames.length-1){stop();return;}seek(index+1)},450);
};
$('groupFilter').onchange=()=>{const first=B.cases.findIndex(x=>$('groupFilter').value==='all'||x.group===$('groupFilter').value);if(first>=0)selectCase(first);else renderCases();};
$('language').onchange=()=>{lang=$('language').value;updateLanguage();};
$('plot').onclick=e=>{const r=$('plot').getBoundingClientRect();stop();seek(Math.round((e.clientX-r.left-42)/Math.max(1,r.width-54)*(c().frames.length-1)));};
$('frame').onchange=$('imageFrame').onchange;
$('note').oninput=$('category').onchange=()=>{try{localStorage.setItem(`jev-live:${B.tag}:${c().episode_id}:${row().frame}`,JSON.stringify({note:$('note').value,category:$('category').value}))}catch{}};
$('export').onclick=()=>{
  const notes=[];
  for(const item of B.cases)for(const frame of item.frames){
    try{const note=JSON.parse(localStorage.getItem(`jev-live:${B.tag}:${item.episode_id}:${frame.frame}`)||'{}');if(note.note||note.category)notes.push({episode_id:item.episode_id,frame:frame.frame,...note});}catch{}
  }
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({tag:B.tag,notes},null,2)],{type:'application/json'}));a.download='jev_live_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
};
window.addEventListener('resize',draw);
window.JEV_LIVE={bundle:B,select:selectCase,seek,draw,drawMap,drawPlot,state:()=>({episode_id:c().episode_id,frame:index,probability:row().jev?.probability_yes})};
updateLanguage();selectCase(0);
