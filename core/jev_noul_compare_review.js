'use strict';
const B=JSON.parse(document.getElementById('payload').textContent);
const $=id=>document.getElementById(id);
const L={
  zh:{
    cases:'轨迹',all:'全部',failure:'原导航失败',success:'原导航成功',
    episodes:'轨迹数',calls:'有效调用',qwenMean:'Qwen平均分',jevMean:'JEV平均概率',concurrency:'首轮并发',
    mapProgress:'地图进度',imageProgress:'画面进度',play:'顺序回放',pause:'暂停',
    prev:'上一步',next:'下一步',reference:'参考路线',full:'完整轨迹',
    qwenMap:'Qwen4B 路线 · 1–5 分',jevMap:'JEV 路线 · P(回退点)',
    current:'当前观测',human:'人工 Crossing',highJev:'JEV ≥ 0.5 起点',
    prompt:'当前 JEV 问题（英文原文与中文翻译）',instruction:'原任务指令',
    protocol:'协议与解释边界',export:'导出复核意见',
    noScore:'未评分',notCalled:'终止/复用帧，未调用',
    qwenScore:'Qwen4B 分数',jevProbability:'JEV 回退点概率',compare:'同帧值',
    pathLegend:'路径颜色越深，数值越高；灰色表示无有效结果。',
    qwenLegend:'Qwen4B：1 分浅，5 分深',jevLegend:'JEV：概率 0 浅，概率 1 深',
    plotTitle:'同帧值',filterTitle:'折线显示与JEV概率滤波（不影响地图）',
    gaussian:'高斯滤波',ema:'指数移动平均 EMA',movingAverage:'滑动平均',
    relativeProminence:'相对突出度（离线）',streamingProminence:'流式突出度（≤5步）',
    effectiveWindow:'有效窗口 N',qwenLine:'Qwen4B分数',rawJev:'JEV原始概率',
    gaussianLine:'高斯滤波',emaLine:'EMA滤波',movingLine:'滑动平均',prominenceLine:'相对突出度（离线）',
    streamingLine:'流式突出度',maxDelay:'最大延迟 D',
    filterHint:'窗口越大越平滑；高斯使用居中σ=N/6，滑动平均使用居中N帧窗口，EMA使用α=2/(N+1)。离线相对突出度可使用完整轨迹；流式突出度仅使用过去历史及最多D步未来，输出后不再改变。',
    sampleSummary:'横轴采样节点',showSampleMapPoints:'在地图上显示采样点',
    sampleHint:'高/低局部峰阈值0.6/0.18且峰谷差≥0.03；平台阈值0.45、至少3帧；节点间距≥3帧；平台中心起每5帧采样。',
    caseStats:'有效 Qwen {q} / JEV {j}；总回放帧 {frames}',
    inputFrames:'本次实际输入',annotationList:'人工标注点',
    generated:'本页完全离线'
  },
  en:{
    cases:'Trajectories',all:'All',failure:'Native failure',success:'Native success',
    episodes:'Trajectories',calls:'Valid calls',qwenMean:'Mean Qwen score',jevMean:'Mean JEV probability',concurrency:'First-pass workers',
    mapProgress:'Map progress',imageProgress:'Image progress',play:'Play',pause:'Pause',
    prev:'Previous',next:'Next',reference:'Reference route',full:'Full trajectory',
    qwenMap:'Qwen4B route · score 1–5',jevMap:'JEV route · P(fallback)',
    current:'Current observation',human:'Human Crossing',highJev:'JEV ≥ 0.5 starts',
    prompt:'Current JEV question (English and Chinese translation)',instruction:'Original task instruction',
    protocol:'Protocol and interpretation',export:'Export review notes',
    noScore:'Unscored',notCalled:'Terminal/reused frame; not called',
    qwenScore:'Qwen4B score',jevProbability:'JEV fallback probability',compare:'Same-frame values',
    pathLegend:'Darker path color means a higher value; gray means no valid result.',
    qwenLegend:'Qwen4B: lighter = 1, darker = 5',jevLegend:'JEV: lighter = probability 0, darker = probability 1',
    plotTitle:'Same-frame values',filterTitle:'Line visibility and JEV filters (chart only)',
    gaussian:'Gaussian',ema:'Exponential moving average (EMA)',movingAverage:'Moving average',
    relativeProminence:'Relative prominence (offline)',streamingProminence:'Streaming prominence (≤5 steps)',
    effectiveWindow:'Effective window N',qwenLine:'Qwen4B score',rawJev:'Raw JEV probability',
    gaussianLine:'Gaussian filter',emaLine:'EMA filter',movingLine:'Moving average',prominenceLine:'Relative prominence (offline)',
    streamingLine:'Streaming prominence',maxDelay:'Maximum delay D',
    filterHint:'A larger window gives smoother output; Gaussian uses centered σ=N/6, moving average uses a centered N-frame window, and EMA uses α=2/(N+1). Offline prominence may use the full trajectory; streaming prominence uses only past history plus at most D future steps and is frozen after output.',
    sampleSummary:'Sampled x-axis nodes',showSampleMapPoints:'Show sampled points on maps',
    sampleHint:'High/low local-peak thresholds 0.6/0.18 with a ≥0.03 peak-to-neighbor difference; plateau threshold 0.45 for at least 3 frames; node spacing ≥3 frames; plateaus sampled every 5 frames from their center.',
    caseStats:'Valid Qwen {q} / JEV {j}; replay frames {frames}',
    inputFrames:'Actual three-frame input',annotationList:'Human annotations',
    generated:'This page is fully offline'
  }
};
let lang='zh',ci=0,index=0,timer=null;
const t=key=>L[lang][key];
const c=()=>B.cases[ci];
const row=()=>c().frames[index];
const mapCache=new Map();
const qwenColors=['#d7eee8','#a9dbce','#73c1ad','#3c9f83','#126c58'];
const jevLight=[250,224,199],jevDark=[139,29,29];
const filterColors={gaussian:'#7c3aed',ema:'#2563eb',movingAverage:'#d97706',relativeProminence:'#be185d',streamingProminence:'#0891b2'};

function qwen(r){
  const q=r.qwen;
  return q&&q.valid&&Number.isInteger(q.score)&&q.score>=1&&q.score<=5?q.score:null;
}
function jev(r){
  const p=r.jev;
  return p&&Number.isFinite(p.probability_yes)&&p.probability_yes>=0&&p.probability_yes<=1?p.probability_yes:null;
}
function qwenColor(value){
  return value===null?'#9aa5b1':qwenColors[value-1];
}
function jevColor(value){
  if(value===null)return '#9aa5b1';
  const rgb=jevLight.map((start,i)=>Math.round(start+(jevDark[i]-start)*value));
  return `rgb(${rgb.join(',')})`;
}
function stop(){
  if(timer!==null)clearInterval(timer);
  timer=null;
  $('play').textContent=t('play');
}
function mapImage(scene,onload){
  const source=B.images[B.maps[scene].image];
  if(mapCache.has(scene)){
    const existing=mapCache.get(scene);
    if(existing.complete)onload();
    else existing.addEventListener('load',onload,{once:true});
    return;
  }
  const image=new Image();
  mapCache.set(scene,image);
  image.onload=onload;
  image.src=source;
}
function canvas(id){
  const el=$(id),box=el.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
  el.width=Math.max(1,Math.round(box.width*dpr));
  el.height=Math.max(1,Math.round(box.height*dpr));
  const ctx=el.getContext('2d');
  ctx.scale(dpr,dpr);
  return {ctx,w:box.width,h:box.height};
}
function drawEvidenceMap(id,mode,sampledNodes=[]){
  const {ctx,w,h}=canvas(id),geometry=B.maps[c().scene].geometry,image=mapCache.get(c().scene);
  const scale=Math.min(w/geometry.width,h/geometry.height);
  const ox=(w-geometry.width*scale)/2,oy=(h-geometry.height*scale)/2;
  const xy=position=>[
    ox+(position[0]-geometry.low[0])/geometry.resolution*scale,
    oy+(geometry.high[1]-position[1])/geometry.resolution*scale
  ];
  ctx.clearRect(0,0,w,h);
  if(image?.complete&&image.naturalWidth)ctx.drawImage(image,ox,oy,geometry.width*scale,geometry.height*scale);
  const frames=$('full').checked?c().frames:c().frames.slice(0,index+1);
  if($('reference').checked&&c().reference_path?.length){
    ctx.strokeStyle='#d19a2c';ctx.lineWidth=3;ctx.setLineDash([7,5]);ctx.beginPath();
    c().reference_path.forEach((position,i)=>{const p=xy(position);i?ctx.lineTo(...p):ctx.moveTo(...p)});
    ctx.stroke();ctx.setLineDash([]);
  }
  ctx.lineCap='round';ctx.lineJoin='round';ctx.lineWidth=5;
  for(let i=0;i<frames.length-1;i++){
    const value=mode==='qwen'?qwen(frames[i]):jev(frames[i]);
    ctx.strokeStyle=mode==='qwen'?qwenColor(value):jevColor(value);
    ctx.setLineDash(value===null?[5,4]:[]);
    ctx.beginPath();ctx.moveTo(...xy(frames[i].position));ctx.lineTo(...xy(frames[i+1].position));ctx.stroke();
  }
  ctx.setLineDash([]);
  if($('showSampleMapPoints').checked&&sampledNodes.length){
    ctx.font='bold 10px CrossingSans, sans-serif';ctx.textBaseline='middle';
    sampledNodes.forEach((node,index)=>{
      const point=xy(c().frames[node.index].position);
      ctx.beginPath();ctx.arc(point[0],point[1],4,0,2*Math.PI);
      ctx.fillStyle='#0891b2';ctx.fill();ctx.lineWidth=1.5;ctx.strokeStyle='#fff';ctx.stroke();
      ctx.lineWidth=2.5;ctx.strokeStyle='#fff';ctx.strokeText('S'+String(index+1).padStart(2,'0'),point[0]+5,point[1]-6);
      ctx.fillStyle='#0891b2';ctx.fillText('S'+String(index+1).padStart(2,'0'),point[0]+5,point[1]-6);
    });
    ctx.textBaseline='alphabetic';
  }
  const [x,y]=xy(row().position);
  ctx.beginPath();ctx.arc(x,y,7,0,2*Math.PI);
  ctx.fillStyle='#e11d48';ctx.fill();ctx.lineWidth=2;ctx.strokeStyle='#fff';ctx.stroke();
}
function draw(){
  const sampling=samplingState();
  mapImage(c().scene,()=>{
    drawEvidenceMap('qwenMap','qwen',sampling.nodes);
    drawEvidenceMap('jevMap','jev',sampling.nodes);
  });
  drawPlot(sampling);
}
function drawPlot(precomputed=null){
  const {ctx,w,h}=canvas('scorePlot'),margin={left:36,right:42,top:16,bottom:25};
  const length=Math.max(1,c().frames.length-1);
  const x=frame=>margin.left+frame/length*(w-margin.left-margin.right);
  const qy=score=>h-margin.bottom-(score-1)/4*(h-margin.top-margin.bottom);
  const py=value=>h-margin.bottom-value*(h-margin.top-margin.bottom);
  ctx.clearRect(0,0,w,h);ctx.font='11px CrossingSans, sans-serif';
  for(let i=0;i<=4;i++){
    const y=margin.top+i/4*(h-margin.top-margin.bottom);
    ctx.strokeStyle='#e3e9ef';ctx.beginPath();ctx.moveTo(margin.left,y);ctx.lineTo(w-margin.right,y);ctx.stroke();
  }
  ctx.fillStyle='#176b5a';ctx.fillText('5',6,qy(5)+4);ctx.fillText('1',6,qy(1)+4);
  ctx.fillStyle='#8b1d1d';ctx.fillText('1',w-27,py(1)+4);ctx.fillText('0',w-27,py(0)+4);
  const line=(getter,toY,color,width,dash=[])=>{
    ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.beginPath();let active=false;const points=[];
    for(const frame of c().frames){
      const value=getter(frame);
      if(value===null){active=false;continue}
      const px=x(frame.frame),vy=toY(value);
      active?ctx.lineTo(px,vy):ctx.moveTo(px,vy);active=true;
      points.push([px,vy]);
    }
    ctx.stroke();ctx.setLineDash([]);
    if(points.length<=8){
      ctx.fillStyle=color;ctx.strokeStyle='#fff';ctx.lineWidth=1.5;
      for(const [px,vy] of points){
        ctx.beginPath();ctx.arc(px,vy,4.2,0,2*Math.PI);ctx.fill();ctx.stroke();
      }
    }
  };
  if($('showQwenLine').checked)line(qwen,qy,'#13845c',2);
  if($('showRawJev').checked)line(jev,py,'#b33a3a',2);
  const rawValues=c().frames.map(jev);
  const windowSize=Number($('filterWindow').value);
  const filteredByFrame=new Map();
  for(const [kind,id] of [
    ['gaussian','filterGaussian'],
    ['ema','filterEma'],
    ['movingAverage','filterMoving']
  ]){
    if(!$(id).checked)continue;
    const series=filterSeries(kind,rawValues,windowSize);
    for(let i=0;i<c().frames.length;i++)filteredByFrame.set(kind+':'+i,series[i]);
    line(frame=>filteredByFrame.get(kind+':'+frame.frame),py,filterColors[kind],2.5);
  }
  if($('filterProminence').checked){
    const prominence=relativeProminence(rawValues,windowSize);
    for(let i=0;i<c().frames.length;i++)filteredByFrame.set('relativeProminence:'+i,prominence[i]);
    line(frame=>filteredByFrame.get('relativeProminence:'+frame.frame),py,filterColors.relativeProminence,3);
  }
  const sampling=precomputed||samplingState();
  let sampledNodes=sampling.nodes;
  if($('filterStreaming').checked){
    const streaming=sampling.streaming;
    for(let i=0;i<c().frames.length;i++)filteredByFrame.set('streamingProminence:'+i,streaming[i]);
    line(frame=>filteredByFrame.get('streamingProminence:'+frame.frame),py,filterColors.streamingProminence,3);
    const axisY=h-margin.bottom;
    ctx.strokeStyle='#0891b2';ctx.fillStyle='#0891b2';ctx.lineWidth=1;ctx.font='9px CrossingSans, sans-serif';
    sampledNodes.forEach((node,index)=>{
      const px=x(node.index);
      ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(px,py(node.value));ctx.lineTo(px,axisY);ctx.stroke();ctx.setLineDash([]);
      ctx.beginPath();ctx.arc(px,axisY,3,0,2*Math.PI);ctx.fill();
      ctx.fillText('S'+String(index+1).padStart(2,'0'),Math.max(margin.left,px-8),axisY+13);
    });
  }
  const currentX=x(row().frame);
  ctx.strokeStyle='#111';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(currentX,margin.top);ctx.lineTo(currentX,h-margin.bottom);ctx.stroke();
  $('sampleSummary').textContent=sampledNodes.length
    ?`${t('sampleSummary')}: ${sampledNodes.map(node=>'F'+c().frames[node.index].frame).join(', ')} · ${t('sampleHint')}`
    :`${t('sampleSummary')}: — · ${t('sampleHint')}`;
}
function samplingState(){
  if(!$('filterStreaming').checked)return {streaming:[],nodes:[]};
  const rawValues=c().frames.map(jev);
  const windowSize=Number($('filterWindow').value);
  const streaming=streamingProminence(rawValues,windowSize,Number($('streamDelay').value));
  return {streaming,nodes:sampleStreamingNodes(streaming,windowSize)};
}
function gaussianFilter(values,windowSize){
  const sigma=Math.max(.5,windowSize/6),radius=Math.max(1,Math.ceil(3*sigma)),out=new Array(values.length).fill(null);
  for(let i=0;i<values.length;i++){
    let sum=0,weight=0;
    for(let j=Math.max(0,i-radius);j<=Math.min(values.length-1,i+radius);j++){
      if(values[j]===null)continue;
      const distance=j-i,w=Math.exp(-(distance*distance)/(2*sigma*sigma));
      sum+=values[j]*w;weight+=w;
    }
    if(weight>0)out[i]=sum/weight;
  }
  return out;
}
function emaFilter(values,windowSize){
  const alpha=2/(windowSize+1),out=new Array(values.length).fill(null);let state=null;
  for(let i=0;i<values.length;i++){
    if(values[i]===null)continue;
    state=state===null?values[i]:alpha*values[i]+(1-alpha)*state;
    out[i]=state;
  }
  return out;
}
function movingAverageFilter(values,windowSize){
  const radius=Math.floor(windowSize/2),out=new Array(values.length).fill(null);
  for(let i=0;i<values.length;i++){
    let sum=0,count=0;
    for(let j=Math.max(0,i-radius);j<=Math.min(values.length-1,i+radius);j++){
      if(values[j]===null)continue;
      sum+=values[j];count++;
    }
    if(count)out[i]=sum/count;
  }
  return out;
}
function relativeProminence(values,windowSize){
  const smoothed=gaussianFilter(values,windowSize);
  const baseline=movingAverageFilter(smoothed,2*windowSize+1);
  const positive=smoothed.map((value,i)=>value===null||baseline[i]===null?null:Math.max(0,value-baseline[i]));
  const valid=positive.filter(value=>value!==null&&value>=0).sort((a,b)=>a-b);
  const p95=valid.length?valid[Math.min(valid.length-1,Math.floor(.95*valid.length))]:0;
  return positive.map(value=>value===null?null:(p95>0?Math.min(1,value/p95):0));
}
function streamingProminence(values,windowSize,maxDelay){
  const sigma=Math.max(.5,windowSize/6),pastRadius=Math.max(1,Math.ceil(3*sigma));
  const smoothed=new Array(values.length).fill(null);
  for(let i=0;i<values.length;i++){
    let sum=0,weight=0;
    const end=Math.min(values.length-1,i+maxDelay);
    for(let j=Math.max(0,i-pastRadius);j<=end;j++){
      if(values[j]===null)continue;
      const distance=j-i,w=Math.exp(-(distance*distance)/(2*sigma*sigma));
      sum+=values[j]*w;weight+=w;
    }
    if(weight>0)smoothed[i]=sum/weight;
  }
  const positive=new Array(values.length).fill(null),baselineWindow=2*windowSize+1;
  for(let i=0;i<smoothed.length;i++){
    if(smoothed[i]===null)continue;
    let sum=0,count=0;
    for(let j=Math.max(0,i-baselineWindow+1);j<=i;j++){
      if(smoothed[j]===null)continue;
      sum+=smoothed[j];count++;
    }
    if(count)positive[i]=Math.max(0,smoothed[i]-sum/count);
  }
  const out=new Array(values.length).fill(null),history=[];
  for(let i=0;i<positive.length;i++){
    if(positive[i]===null)continue;
    history.push(positive[i]);history.sort((a,b)=>a-b);
    const p95=history[Math.min(history.length-1,Math.floor(.95*history.length))];
    out[i]=p95>0?Math.min(1,positive[i]/p95):0;
  }
  return out;
}
function sampleStreamingNodes(series,windowSize){
  const highThreshold=.6,lowThreshold=.18,plateauThreshold=.45;
  const minDistance=3,plateauInterval=5,plateauMinimum=3,warmup=Math.max(7,windowSize);
  const peaks=[];
  for(let i=warmup;i<series.length-2;i++){
    const value=series[i];
    if(value===null||value<lowThreshold)continue;
    const look=value>=highThreshold?1:2;
    let isPeak=true;
    for(let j=Math.max(0,i-look);j<=Math.min(series.length-1,i+look);j++){
      if(j!==i&&series[j]!==null&&value<series[j]){isPeak=false;break}
    }
    if(!isPeak)continue;
    const left=Math.min(...series.slice(Math.max(0,i-minDistance),i+1).filter(value=>value!==null));
    const right=Math.min(...series.slice(i,Math.min(series.length,i+minDistance+1)).filter(value=>value!==null));
    if(Math.min(value-left,value-right)>=.03)peaks.push({index:i,value,kind:'peak'});
  }
  const regions=[];let current=[];
  for(let i=0;i<series.length;i++){
    if(series[i]!==null&&series[i]>=plateauThreshold)current.push(i);
    else if(current.length){regions.push(current);current=[]}
  }
  if(current.length)regions.push(current);
  const plateau=[];
  for(const region of regions){
    if(region.length<plateauMinimum)continue;
    for(let offset=Math.floor(plateauInterval/2);offset<region.length;offset+=plateauInterval){
      const i=region[offset];plateau.push({index:i,value:series[i],kind:'plateau'});
    }
  }
  const candidates=[...peaks,...plateau].sort((a,b)=>b.value-a.value||a.index-b.index),nodes=[];
  for(const candidate of candidates){
    if(nodes.every(node=>Math.abs(node.index-candidate.index)>=minDistance))nodes.push(candidate);
  }
  return nodes.sort((a,b)=>a.index-b.index);
}
function filterSeries(kind,values,windowSize){
  if(kind==='gaussian')return gaussianFilter(values,windowSize);
  if(kind==='ema')return emaFilter(values,windowSize);
  if(kind==='movingAverage')return movingAverageFilter(values,windowSize);
  throw new Error('Unknown filter: '+kind);
}
function syncFilterControls(){
  const value=Number($('filterWindow').value);
  $('filterWindowValue').textContent=String(value);
  $('streamDelayValue').textContent=String($('streamDelay').value);
  $('filterHint').textContent=t('filterHint').replace('{n}',String(value));
}
function seek(value){
  index=Math.max(0,Math.min(c().frames.length-1,value));
  const current=row(),q=qwen(current),p=jev(current);
  $('frame').value=index;$('imageFrame').value=index;
  $('step').textContent=`${t('current')} ${current.frame} · ${index+1}/${c().frames.length}`;
  $('imageStep').textContent=$('step').textContent;
  $('rgb').src=B.images[current.image];
  $('qwenValue').textContent=q===null?t('noScore'):`${q} / 5`;
  $('jevValue').textContent=p===null?t('noScore'):`${(p*100).toFixed(1)}%`;
  $('delta').textContent=q===null||p===null?'—':`${(((p*100)-((q-1)/4*100))).toFixed(1)} pt`;
  $('inputInfo').textContent=current.jev?`${t('inputFrames')}: ${current.jev.image_frames.join(', ')}`:'—';
  $('history').replaceChildren();
  for(const frame of current.jev?.image_frames||[]){
    const button=document.createElement('button'),image=document.createElement('img'),label=document.createElement('span');
    image.src=B.images[c().frames[frame].image];label.textContent=`${frame}`;
    button.append(image,label);button.onclick=()=>{stop();seek(frame)};$('history').append(button);
  }
  draw();
}
function renderCases(){
  const filter=$('filters').value;$('cases').replaceChildren();
  for(const [i,item] of B.cases.entries()){
    if(filter!=='all'&&item.group!==filter)continue;
    const button=document.createElement('button');button.className=i===ci?'active':'';
    button.textContent=`${item.episode_id}\n${item.group==='success'?t('success'):t('failure')} · ${item.frames.length} frames`;
    button.onclick=()=>select(i);$('cases').append(button);
  }
}
function updateLanguage(){
  for(const node of document.querySelectorAll('[data-i18n]'))node.textContent=t(node.dataset.i18n);
  $('instruction').textContent=`${t('instruction')}: ${lang==='zh'?c().instruction_zh:c().instruction_en}`;
  $('promptEnglish').textContent=B.prompt_en;
  $('promptChinese').textContent=B.prompt_zh;
  syncFilterControls();applyStats();renderRunInfo();stop();renderCases();seek(index);
}
function select(n){
  ci=n;index=Number.isInteger(c().initial_index)?c().initial_index:0;$('title').textContent=c().episode_id;
  for(const id of ['frame','imageFrame'])$(id).max=c().frames.length-1;
  const q=c().frames.filter(frame=>qwen(frame)!==null).length,p=c().frames.filter(frame=>jev(frame)!==null).length;
  $('caseStats').textContent=t('caseStats').replace('{q}',q).replace('{j}',p).replace('{frames}',c().frames.length);
  $('filters').value='all';renderCases();updateLanguage();
}
function applyStats(){
  $('stats').replaceChildren();
  const values=[['episodes',B.summary.cases],['calls',`${B.summary.valid_calls}/${B.summary.expected_calls}`],['qwenMean',B.summary.qwen_mean_score.toFixed(3)],['jevMean',B.summary.jev_mean_probability.toFixed(3)],['concurrency',B.summary.concurrency]];
  for(const [key,value] of values){
    const box=document.createElement('div'),strong=document.createElement('strong'),span=document.createElement('span');
    box.className='metric';strong.textContent=value;span.textContent=t(key);box.append(strong,span);$('stats').append(box);
  }
}
function renderRunInfo(){
  $('runInfo').textContent=lang==='zh'
    ?`${B.tag} · ${B.summary.cases}条轨迹 · ${B.summary.valid_calls}/${B.summary.expected_calls}次JEV Noul · Qwen4B同帧分数复用`
    :`${B.tag} · ${B.summary.cases} trajectories · ${B.summary.valid_calls}/${B.summary.expected_calls} JEV Noul calls · same-frame Qwen4B scores`;
  $('footer').textContent=`${t('generated')} · JEV 1.14 · no external requests`;
}
$('frame').oninput=event=>{stop();seek(Number(event.target.value))};
$('imageFrame').oninput=event=>{stop();seek(Number(event.target.value))};
$('prev').onclick=()=>{stop();seek(index-1)};
$('next').onclick=()=>{stop();seek(index+1)};
$('play').onclick=()=>{
  if(timer!==null){stop();return}
  if(index===c().frames.length-1)seek(0);
  $('play').textContent=t('pause');
  timer=setInterval(()=>{if(index===c().frames.length-1){stop();return}seek(index+1)},400);
};
for(const id of ['reference','full'])$(id).onchange=draw;
for(const id of ['showQwenLine','showRawJev','filterGaussian','filterEma','filterMoving','filterProminence'])$(id).onchange=drawPlot;
for(const id of ['filterStreaming','showSampleMapPoints'])$(id).onchange=draw;
$('filterWindow').oninput=()=>{syncFilterControls();draw()};
$('streamDelay').oninput=()=>{syncFilterControls();draw()};
$('filters').onchange=()=>{const first=B.cases.findIndex(item=>$('filters').value==='all'||item.group===$('filters').value);if(first>=0&&c().group!==$('filters').value)select(first);else renderCases()};
$('language').onchange=()=>{lang=$('language').value;document.documentElement.lang=lang==='zh'?'zh-CN':'en';updateLanguage()};
$('scorePlot').onclick=event=>{const box=$('scorePlot').getBoundingClientRect();stop();seek(Math.round((event.clientX-box.left-36)/Math.max(1,box.width-78)*(c().frames.length-1)))};
$('export').onclick=()=>{
  const notes=[];for(const item of B.cases)for(const frame of item.frames){let note={};try{note=JSON.parse(localStorage.getItem(`jev-compare:${B.tag}:${item.episode_id}:${frame.frame}`)||'{}')}catch{}
    if(note.note||note.category)notes.push({episode_id:item.episode_id,frame:frame.frame,...note});}
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({tag:B.tag,notes},null,2)],{type:'application/json'}));a.download='jev_qwen_review_notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
};
$('note').oninput=()=>{try{localStorage.setItem(`jev-compare:${B.tag}:${c().episode_id}:${row().frame}`,JSON.stringify({note:$('note').value,category:$('category').value}))}catch{}};
$('category').onchange=$('note').oninput;
window.addEventListener('resize',()=>{draw()});
document.addEventListener('keydown',event=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();stop();seek(index+(event.key==='ArrowLeft'?-1:1))}});
applyStats();
renderRunInfo();
window.JEV_COMPARE={bundle:B,select,seek,draw,drawPlot,samplingState,qwen,jev,qwenColor,jevColor,gaussianFilter,emaFilter,movingAverageFilter,relativeProminence,streamingProminence,sampleStreamingNodes,filterSeries,state:()=>({episode_id:c().episode_id,frame:index,qwen:qwen(row()),jev:jev(row())})};
select(0);
