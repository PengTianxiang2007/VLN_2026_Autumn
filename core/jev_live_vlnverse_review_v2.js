'use strict';
const B=JSON.parse(document.getElementById('payload').textContent),$=id=>document.getElementById(id);
const L={zh:{
  cases:'轨迹',all:'全部',success:'原导航成功',failure:'原导航失败',export:'导出复核意见',caseHint:'点击轨迹会同步切换两张俯视图、RGB、曲线和逐帧结果。',
  rawMap:'原始 JEV 概率路线',streamMap:'N=11 流式突出度与采样节点',mapProgress:'地图进度',imageProgress:'画面进度',prev:'上一步',next:'下一步',play:'顺序回放',pause:'暂停',reference:'参考路线',full:'完整轨迹',showSampleMapPoints:'显示采样节点',
  plotTitle:'原始概率与流式突出度',rawLine:'JEV原始概率',streamLine:'流式突出度',fixedFilter:'固定 N=11，D=5',prompt:'JEV提示词（英文请求与中文翻译）',current:'当前观测与JEV判断',probability:'JEV回退点概率',latency:'API延迟',lag:'实际step滞后',rawResult:'逐帧原始结果',review:'人工复核',likely:'像回退点',uncertain:'不确定',unlikely:'不像回退点',notePlaceholder:'记录本帧判断依据',noteHint:'意见仅保存在当前浏览器。',instruction:'原任务指令',noScore:'无评分',frame:'帧',nodes:'节点',runInfo:'40条episode · StreamVLN H1 physical · JEV 1.14 · N=11/D=5',notice:'JEV是旁路评分，不改变StreamVLN动作和官方成绩。左图为原始概率路线，右图为流式突出度路线；底图来自场景USD几何正交投影。',episodes:'轨迹',navSR:'导航SR',calls:'JEV回答',meanProb:'平均概率',meanLatency:'平均API延迟',p95Latency:'P95 API延迟',streamNodes:'流式节点',caseStats:'{frames}帧 · {calls}次JEV',sampleHint:'节点由N=11流式突出度生成；阈值0.6/0.18，平台0.45，间距≥3帧。',footer:'本地离线页面 · 数据来自一次完整运行',generated:'生成于'
},en:{
  cases:'Trajectories',all:'All',success:'Native success',failure:'Native failure',export:'Export review notes',caseHint:'Clicking a trajectory updates both maps, RGB, chart, and frame result.',
  rawMap:'Raw JEV probability route',streamMap:'N=11 streaming prominence and sampled nodes',mapProgress:'Map progress',imageProgress:'Image progress',prev:'Previous',next:'Next',play:'Play',pause:'Pause',reference:'Reference route',full:'Full trajectory',showSampleMapPoints:'Show sampled nodes',
  plotTitle:'Raw probability and streaming prominence',rawLine:'Raw JEV probability',streamLine:'Streaming prominence',fixedFilter:'Fixed N=11, D=5',prompt:'JEV prompt (English request and Chinese translation)',current:'Current observation and JEV decision',probability:'JEV fallback probability',latency:'API latency',lag:'Actual step lag',rawResult:'Raw per-frame result',review:'Human review',likely:'Likely checkpoint',uncertain:'Uncertain',unlikely:'Unlikely',notePlaceholder:'Record the evidence for this frame',noteHint:'Notes are stored only in this browser.',instruction:'Original task instruction',noScore:'No score',frame:'Frame',nodes:'nodes',runInfo:'40 episodes · StreamVLN H1 physical · JEV 1.14 · N=11/D=5',notice:'JEV is a side-channel score and does not alter StreamVLN actions or the official result. The left map shows raw probability and the right map streaming prominence; both use an orthographic floorplan from scene USD geometry.',episodes:'Trajectories',navSR:'Navigation SR',calls:'JEV answers',meanProb:'Mean probability',meanLatency:'Mean API latency',p95Latency:'P95 API latency',streamNodes:'Streaming nodes',caseStats:'{frames} frames · {calls} JEV calls',sampleHint:'Nodes come from N=11 streaming prominence; thresholds 0.6/0.18, plateau 0.45, spacing >=3 frames.',footer:'Local offline page · data from one complete run',generated:'Generated'
}};
let lang='zh',ci=0,index=0,timer=null;
const t=k=>L[lang][k]||k,c=()=>B.cases[ci],row=()=>c().frames[index];
const mapImage=new Image();mapImage.onload=()=>{if(window.JEV_LIVE_V2)draw()};mapImage.src=B.images[B.map.image];
function jev(r){const p=r?.jev?.probability_yes;return Number.isFinite(p)&&p>=0&&p<=1?p:null}
function rawColor(v){if(v===null)return '#9aa5b1';const a=[244,217,199],b=[139,29,29];return `rgb(${a.map((x,i)=>Math.round(x+(b[i]-x)*v)).join(',')})`}
function streamColor(v){if(v===null)return '#9aa5b1';const a=[204,235,231],b=[7,95,102];return `rgb(${a.map((x,i)=>Math.round(x+(b[i]-x)*v)).join(',')})`}
function stop(){if(timer!==null)clearInterval(timer);timer=null;$('play').textContent=t('play')}
function canvas(id){const el=$(id),box=el.getBoundingClientRect(),dpr=devicePixelRatio||1;el.width=Math.max(1,Math.round(box.width*dpr));el.height=Math.max(1,Math.round(box.height*dpr));const ctx=el.getContext('2d');ctx.scale(dpr,dpr);return{ctx,w:box.width,h:box.height}}
function projectFactory(w,h){const g=B.map.geometry,scale=Math.min(w/g.width,h/g.height),ox=(w-g.width*scale)/2,oy=(h-g.height*scale)/2;return{p:p=>[ox+(p[0]-g.low[0])/g.resolution*scale,oy+(g.high[1]-p[1])/g.resolution*scale],scale,ox,oy}}
function drawMap(id,mode,nodes){
  const {ctx,w,h}=canvas(id),{p,scale,ox,oy}=projectFactory(w,h),g=B.map.geometry;
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#f3f6f9';ctx.fillRect(0,0,w,h);
  if(mapImage.complete&&mapImage.naturalWidth)ctx.drawImage(mapImage,ox,oy,g.width*scale,g.height*scale);
  const frames=$('full').checked?c().frames:c().frames.slice(0,index+1);
  if($('reference').checked&&c().reference_path?.length){
    ctx.strokeStyle='#d19a2c';ctx.lineWidth=3;ctx.setLineDash([7,5]);ctx.beginPath();
    c().reference_path.forEach((q,i)=>{const z=p(q);i?ctx.lineTo(...z):ctx.moveTo(...z)});ctx.stroke();ctx.setLineDash([]);
  }
  ctx.lineCap='round';ctx.lineJoin='round';ctx.lineWidth=5;
  for(let i=0;i<frames.length-1;i++){
    const value=mode==='raw'?jev(frames[i]):c().streaming.filtered[frames[i].frame];
    ctx.strokeStyle=mode==='raw'?rawColor(value):streamColor(value);ctx.setLineDash(value===null?[5,4]:[]);
    ctx.beginPath();const a=p(frames[i].position),b=p(frames[i+1].position);ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();
  }
  ctx.setLineDash([]);
  if(mode==='stream'&&$('showSampleMapPoints').checked&&nodes.length){
    ctx.font='bold 10px sans-serif';ctx.textBaseline='middle';
    nodes.forEach((node,i)=>{const q=c().frames[node.index],z=p(q.position);ctx.beginPath();ctx.arc(z[0],z[1],4,0,Math.PI*2);ctx.fillStyle='#075f66';ctx.fill();ctx.lineWidth=1.5;ctx.strokeStyle='#fff';ctx.stroke();ctx.lineWidth=2.5;ctx.strokeStyle='#fff';ctx.strokeText('S'+String(i+1).padStart(2,'0'),z[0]+5,z[1]-6);ctx.fillStyle='#075f66';ctx.fillText('S'+String(i+1).padStart(2,'0'),z[0]+5,z[1]-6)});
    ctx.textBaseline='alphabetic';
  }
  const q=p(row().position);ctx.beginPath();ctx.arc(q[0],q[1],7,0,Math.PI*2);ctx.fillStyle='#e11d48';ctx.fill();ctx.lineWidth=2;ctx.strokeStyle='#fff';ctx.stroke();
}
function drawPlot(){
  const {ctx,w,h}=canvas('scorePlot'),m={left:38,right:12,top:16,bottom:25},n=Math.max(1,c().frames.length-1),x=i=>m.left+i/n*(w-m.left-m.right),y=v=>h-m.bottom-v*(h-m.top-m.bottom);
  ctx.clearRect(0,0,w,h);ctx.font='11px sans-serif';
  for(const v of [0,.25,.5,.75,1]){const yy=y(v);ctx.strokeStyle='#e3e9ef';ctx.beginPath();ctx.moveTo(m.left,yy);ctx.lineTo(w-m.right,yy);ctx.stroke();ctx.fillStyle='#52677a';ctx.fillText(v.toFixed(2),4,yy+4)}
  const line=(values,color)=>{ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();let active=false;for(let i=0;i<values.length;i++){const v=values[i];if(v===null||v===undefined){active=false;continue}const qx=x(i),qy=y(v);active?ctx.lineTo(qx,qy):ctx.moveTo(qx,qy);active=true}ctx.stroke()};
  if($('showRawLine').checked)line(c().frames.map(jev),'#b33a3a');
  if($('showStreamLine').checked)line(c().streaming.filtered,'#0793ad');
  if($('showStreamLine').checked)c().streaming.nodes.forEach((node,i)=>{const qx=x(node.index),qy=y(node.value);ctx.strokeStyle='#0793ad';ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(qx,qy);ctx.lineTo(qx,h-m.bottom);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#0793ad';ctx.beginPath();ctx.arc(qx,h-m.bottom,3,0,Math.PI*2);ctx.fill();ctx.font='10px sans-serif';ctx.fillText('S'+String(i+1).padStart(2,'0'),Math.max(2,qx-9),h-8)});
  ctx.strokeStyle='#111';ctx.beginPath();ctx.moveTo(x(index),m.top);ctx.lineTo(x(index),h-m.bottom);ctx.stroke();
  $('sampleSummary').textContent=t('sampleHint')+' '+(c().streaming.nodes.map((n,i)=>'S'+String(i+1).padStart(2,'0')+'=F'+n.index).join(', ')||'—');
}
function draw(){drawMap('rawMap','raw',[]);drawMap('streamMap','stream',c().streaming.nodes);drawPlot()}
function renderCases(){
  const filter=$('filters').value;$('cases').replaceChildren();
  B.cases.forEach((item,i)=>{if(filter!=='all'&&item.group!==filter)return;const b=document.createElement('button');b.dataset.index=i;b.className=i===ci?'active':'';b.textContent=`${item.episode_id}\n原导航${item.group==='success'?'成功':'失败'} · ${item.frames.length} 个观测`;b.onclick=()=>select(i);$('cases').append(b)});
}
function updateInstruction(){$('instruction').textContent=`${t('instruction')}：\n中文：${c().instruction_zh}\nEnglish: ${c().instruction_en}`}
function seek(n){
  index=Math.max(0,Math.min(c().frames.length-1,Number(n)));const r=row();$('frame').max=c().frames.length-1;$('imageFrame').max=c().frames.length-1;$('frame').value=index;$('imageFrame').value=index;$('step').textContent=`F${r.frame} · ${index+1}/${c().frames.length}`;$('imageStep').textContent=$('step').textContent;$('rgb').src=B.images[r.image];
  const p=jev(r);$('probValue').textContent=p===null?'—':(p*100).toFixed(1)+'%';$('latencyValue').textContent=r.jev?.latency_seconds==null?'—':Number(r.jev.latency_seconds).toFixed(2)+' s';$('lagValue').textContent=r.jev?.unresolved_step_lag==null?'—':r.jev.unresolved_step_lag+' step';$('inputInfo').textContent=`${t('frame')} ${r.frame} · ${t('nodes')} ${c().streaming.nodes.length}`;$('raw').textContent=JSON.stringify({episode_id:c().episode_id,frame:r.frame,action:r.action,position:r.position,jev:r.jev},null,2);
  $('history').replaceChildren();for(const f of r.jev?.image_frames||[]){const b=document.createElement('button'),im=document.createElement('img'),s=document.createElement('span');im.src=B.images[c().frames[f].image];s.textContent='F'+f;b.append(im,s);b.onclick=()=>{stop();seek(f)};$('history').append(b)}
  try{const q=JSON.parse(localStorage.getItem(`jev-live-v2:${B.tag}:${c().episode_id}:${r.frame}`)||'{}');$('note').value=q.note||'';$('category').value=q.category||'uncertain'}catch{$('note').value=''}
  draw();
}
function select(n){
  stop();ci=n;index=0;const item=c();$('episodeTitle').textContent=item.episode_id;$('caseStats').textContent=t('caseStats').replace('{frames}',item.frames.length).replace('{calls}',item.frames.filter(f=>f.jev).length);updateInstruction();renderCases();if(mapImage.complete)draw();seek(0);
}
function renderStats(){
  const s=B.summary,items=[[t('episodes'),s.episodes],[t('navSR'),(100*s.navigation.SR).toFixed(1)+'%'],[t('calls'),s.valid_calls],[t('meanProb'),(100*s.mean_probability).toFixed(1)+'%'],[t('meanLatency'),s.mean_latency.toFixed(2)+' s'],[t('p95Latency'),s.latency_percentiles['95'].toFixed(2)+' s'],[t('streamNodes'),s.streaming_nodes]];$('stats').replaceChildren();for(const [label,value] of items){const b=document.createElement('div'),x=document.createElement('strong'),y=document.createElement('span');b.className='metric';x.textContent=value;y.textContent=label;b.append(x,y);$('stats').append(b)}
}
function updateLanguage(){
  document.documentElement.lang=lang==='zh'?'zh-CN':'en';document.querySelectorAll('[data-i18n]').forEach(n=>{if(n.tagName==='OPTION')n.textContent=t(n.dataset.i18n);else n.textContent=t(n.dataset.i18n)});
  $('runInfo').textContent=t('runInfo');$('notice').textContent=t('notice');$('promptEnglish').textContent=B.prompt_en;$('promptChinese').textContent=B.prompt_zh;$('footer').textContent=t('footer');
  $('note').placeholder=t('notePlaceholder');
  renderStats();renderCases();updateInstruction();seek(index);
}
$('filters').onchange=()=>{renderCases();const first=B.cases.findIndex(x=>$('filters').value==='all'||x.group===$('filters').value);if(first>=0&&!B.cases.some((x,i)=>i===ci&&($('filters').value==='all'||x.group===$('filters').value)))select(first)};
for(const id of ['frame','imageFrame'])$(id).oninput=e=>{stop();seek(Number(e.target.value))};
for(const id of ['prev','next'])$(id).onclick=()=>{stop();seek(index+(id==='prev'?-1:1))};
$('play').onclick=()=>{if(timer!==null){stop();return}if(index>=c().frames.length-1)seek(0);$('play').textContent=t('pause');timer=setInterval(()=>{if(index>=c().frames.length-1)stop();else seek(index+1)},500)};
for(const id of ['reference','full','showSampleMapPoints','showRawLine','showStreamLine'])$(id).onchange=draw;
$('language').onchange=()=>{lang=$('language').value;updateLanguage()};
$('category').onchange=$('note').oninput=()=>{try{localStorage.setItem(`jev-live-v2:${B.tag}:${c().episode_id}:${row().frame}`,JSON.stringify({note:$('note').value,category:$('category').value}))}catch{}};
$('export').onclick=()=>{const notes=[];for(const item of B.cases)for(const f of item.frames){try{const q=JSON.parse(localStorage.getItem(`jev-live-v2:${B.tag}:${item.episode_id}:${f.frame}`)||'{}');if(q.note||q.category)notes.push({episode_id:item.episode_id,frame:f.frame,...q})}catch{}}const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({tag:B.tag,notes},null,2)],{type:'application/json'}));a.download='jev_live_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
window.JEV_LIVE_V2={bundle:B,select,seek,draw,state:()=>({episode_id:c().episode_id,frame:index})};
updateLanguage();select(0);
