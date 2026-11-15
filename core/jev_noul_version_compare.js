'use strict';
const B=JSON.parse(document.getElementById('payload').textContent);
const $=id=>document.getElementById(id);
const CASES=B.cases||[B.caseData];
const L={
  zh:{
    prevMap:'上一版 · P(回退点候选)',newMap:'新版 · P(回退点候选)',
    mapProgress:'地图进度',imageProgress:'画面进度',play:'顺序回放',pause:'暂停',
    prev:'上一步',next:'下一步',reference:'参考路线',full:'完整轨迹',
    current:'当前观测',previous:'上一版概率',newVersion:'新版概率',delta:'概率变化',
    prompt:'两版问题的英文原文与中文翻译',instruction:'原任务指令',
    protocol:'协议与解释边界',export:'导出复核意见',
    frames:'有效观测',prevMean:'上一版平均概率',newMean:'新版平均概率',
    increased:'新版更高',decreased:'新版更低',equal:'相同',
    pathHint:'路线颜色越深表示概率越高；地图仅保留路线和当前机器人位置。',
    v002:'上一版',v003:'新版',generated:'本页完全离线',
    inputFrames:'本次实际输入'
  },
  en:{
    prevMap:'Previous version · P(fallback candidate)',newMap:'New version · P(fallback candidate)',
    mapProgress:'Map progress',imageProgress:'Image progress',play:'Play',pause:'Pause',
    prev:'Previous',next:'Next',reference:'Reference route',full:'Full trajectory',
    current:'Current observation',previous:'Previous probability',newVersion:'New probability',delta:'Probability change',
    prompt:'English prompts and complete Chinese translations',instruction:'Original task instruction',
    protocol:'Protocol and interpretation',export:'Export review notes',
    frames:'Valid observations',prevMean:'Mean previous probability',newMean:'Mean new probability',
    increased:'New higher',decreased:'New lower',equal:'Equal',
    pathHint:'Darker route color means a higher probability; maps contain only routes and the current robot position.',
    v002:'Previous version',v003:'New version',generated:'This page is fully offline',
    inputFrames:'Actual input frames'
  }
};
let lang='zh',ci=0,index=0,timer=null;
const t=key=>L[lang][key];
const c=()=>CASES[ci],f=()=>c().frames[index];
const trajectories=new Map();
const blueStart=[219,234,254],blueEnd=[30,58,138];
const redStart=[253,226,202],redEnd=[139,29,29];
const color=(value,start,end)=>{
  if(value===null)return '#9aa5b1';
  const rgb=start.map((v,i)=>Math.round(v+(end[i]-v)*value));
  return `rgb(${rgb.join(',')})`;
};
const previousColor=value=>color(value,blueStart,blueEnd);
const newColor=value=>color(value,redStart,redEnd);
const previousValue=frame=>frame.previous?.probability_yes??null;
const newValue=frame=>frame.current?.probability_yes??null;
function stop(){if(timer!==null)clearInterval(timer);timer=null;$('play').textContent=t('play')}
function mapImage(onload){
  const scene=c().scene,mapData=B.maps?.[scene]||B.map;
  const source=B.images[mapData.image];
  if(trajectories.has(scene)){
    const image=trajectories.get(scene);
    if(image.complete)onload();else image.addEventListener('load',onload,{once:true});
    return;
  }
  const image=new Image();trajectories.set(scene,image);image.onload=onload;image.src=source;
}
function canvas(id){
  const el=$(id),box=el.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
  el.width=Math.max(1,Math.round(box.width*dpr));el.height=Math.max(1,Math.round(box.height*dpr));
  const ctx=el.getContext('2d');ctx.scale(dpr,dpr);return {ctx,w:box.width,h:box.height};
}
function drawMap(id,mode){
  const mapData=B.maps?.[c().scene]||B.map;
  const {ctx,w,h}=canvas(id),geometry=mapData.geometry,image=trajectories.get(c().scene);
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
    c().reference_path.forEach((position,i)=>{const point=xy(position);i?ctx.lineTo(...point):ctx.moveTo(...point)});
    ctx.stroke();ctx.setLineDash([]);
  }
  ctx.lineCap='round';ctx.lineJoin='round';ctx.lineWidth=5;
  for(let i=0;i<frames.length-1;i++){
    const value=mode==='previous'?previousValue(frames[i]):newValue(frames[i]);
    ctx.strokeStyle=mode==='previous'?previousColor(value):newColor(value);
    ctx.setLineDash(value===null?[5,4]:[]);
    ctx.beginPath();ctx.moveTo(...xy(frames[i].position));ctx.lineTo(...xy(frames[i+1].position));ctx.stroke();
  }
  ctx.setLineDash([]);
  const [x,y]=xy(f().position);
  ctx.beginPath();ctx.arc(x,y,7,0,2*Math.PI);
  ctx.fillStyle='#e11d48';ctx.fill();ctx.lineWidth=2;ctx.strokeStyle='#fff';ctx.stroke();
}
function draw(){
  mapImage(()=>{drawMap('previousMap','previous');drawMap('newMap','new')});
  drawPlot();
}
function drawPlot(){
  const {ctx,w,h}=canvas('scorePlot'),margin={left:34,right:18,top:14,bottom:25};
  const x=frame=>margin.left+frame/Math.max(1,c().frames.length-1)*(w-margin.left-margin.right);
  const y=value=>h-margin.bottom-value*(h-margin.top-margin.bottom);
  ctx.clearRect(0,0,w,h);ctx.font='11px CrossingSans, sans-serif';
  for(let i=0;i<=4;i++){
    const py=margin.top+i/4*(h-margin.top-margin.bottom);
    ctx.strokeStyle='#e3e9ef';ctx.beginPath();ctx.moveTo(margin.left,py);ctx.lineTo(w-margin.right,py);ctx.stroke();
  }
  ctx.fillStyle='#334155';ctx.fillText('1',5,y(1)+4);ctx.fillText('0',5,y(0)+4);
  const line=(getter,stroke)=>{
    ctx.strokeStyle=stroke;ctx.lineWidth=2;ctx.beginPath();let active=false;
    for(const frame of c().frames){
      const value=getter(frame);
      if(value===null){active=false;continue}
      const px=x(frame.frame),py=y(value);
      active?ctx.lineTo(px,py):ctx.moveTo(px,py);active=true;
    }
    ctx.stroke();
  };
  line(previousValue,'#3156a3');line(newValue,'#b33a3a');
  const currentX=x(f().frame);ctx.strokeStyle='#111';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(currentX,margin.top);ctx.lineTo(currentX,h-margin.bottom);ctx.stroke();
}
function seek(value){
  index=Math.max(0,Math.min(c().frames.length-1,value));const frame=f();
  $('frame').value=index;$('imageFrame').value=index;
  $('step').textContent=`${t('current')} ${frame.frame} · ${index+1}/${c().frames.length}`;
  $('imageStep').textContent=$('step').textContent;
  const previous=previousValue(frame),current=newValue(frame);
  $('rgb').src=B.images[frame.image];
  $('previousValue').textContent=previous===null?'—':`${(previous*100).toFixed(1)}%`;
  $('newValue').textContent=current===null?'—':`${(current*100).toFixed(1)}%`;
  $('delta').textContent=previous===null||current===null?'—':`${((current-previous)*100).toFixed(1)} pt`;
  $('inputInfo').textContent=frame.current?`${t('inputFrames')}: ${frame.current.image_frames.join(', ')}`:'—';
  $('history').replaceChildren();
  for(const frameId of frame.current?.image_frames||[]){
    const button=document.createElement('button'),image=document.createElement('img'),label=document.createElement('span');
    image.src=B.images[c().frames[frameId].image];label.textContent=String(frameId);
    button.append(image,label);button.onclick=()=>{stop();seek(frameId)};$('history').append(button);
  }
  draw();
}
function renderStats(){
  $('stats').replaceChildren();
  const values=[
    ['frames',B.summary.valid],
    ['prevMean',B.summary.previous_mean_probability_yes.toFixed(3)],
    ['newMean',B.summary.mean_probability_yes.toFixed(3)],
    ['increased',B.summary.increased],
    ['decreased',B.summary.decreased],
    ['equal',B.summary.equal]
  ];
  for(const [key,value]of values){
    const box=document.createElement('div'),strong=document.createElement('strong'),span=document.createElement('span');
    box.className='metric';strong.textContent=value;span.textContent=t(key);box.append(strong,span);$('stats').append(box);
  }
}
function updateLanguage(){
  for(const node of document.querySelectorAll('[data-i18n]'))node.textContent=t(node.dataset.i18n);
  const options=$('caseSelect').options;
  for(let i=0;i<CASES.length;i++)if(options[i])options[i].textContent=CASES[i].episode_id;
  $('caseSelect').value=String(ci);
  $('title').textContent=c().episode_id;
  $('runInfo').textContent=lang==='zh'
    ?`${CASES.length}条轨迹 · ${B.summary.valid}/${B.summary.total}个有效观测 · ${B.summary.concurrency}个并发worker`
    :`${CASES.length} trajectories · ${B.summary.valid}/${B.summary.total} valid observations · ${B.summary.concurrency} concurrent workers`;
  const caseSummary=B.summary.by_case[c().episode_id];
  $('caseStats').textContent=lang==='zh'
    ?`${c().episode_id} · 上一版均值${caseSummary.previous_mean.toFixed(3)} · 新版均值${caseSummary.current_mean.toFixed(3)} · 升高${caseSummary.increased} / 降低${caseSummary.decreased} / 相同${caseSummary.equal}`
    :`${c().episode_id} · previous mean ${caseSummary.previous_mean.toFixed(3)} · new mean ${caseSummary.current_mean.toFixed(3)} · higher ${caseSummary.increased} / lower ${caseSummary.decreased} / equal ${caseSummary.equal}`;
  $('instruction').textContent=`${t('instruction')}: ${lang==='zh'?c().instruction_zh:c().instruction_en}`;
  $('v002Prompt').textContent=B.prompts.v002_en;
  $('v002PromptZh').textContent=B.prompts.v002_zh;
  $('v003Prompt').textContent=B.prompts.v003_en;
  $('v003PromptZh').textContent=B.prompts.v003_zh;
  $('footer').textContent=`${t('generated')} · JEV 1.14 · no external requests`;
  renderStats();stop();seek(index);
}
function select(n){
  ci=Math.max(0,Math.min(CASES.length-1,n));index=0;
  for(const id of ['frame','imageFrame'])$(id).max=c().frames.length-1;
  $('caseSelect').value=String(ci);
  updateLanguage();
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
$('caseSelect').onchange=()=>select(Number($('caseSelect').value));
$('language').onchange=()=>{lang=$('language').value;document.documentElement.lang=lang==='zh'?'zh-CN':'en';updateLanguage()};
$('scorePlot').onclick=event=>{const box=$('scorePlot').getBoundingClientRect();stop();seek(Math.round((event.clientX-box.left-34)/Math.max(1,box.width-52)*(c().frames.length-1)))};
$('note').oninput=()=>{try{localStorage.setItem(`jev-version:${B.tag}:${f().frame}`,JSON.stringify({category:$('category').value,note:$('note').value}))}catch{}};
$('category').onchange=$('note').oninput;
$('export').onclick=()=>{
  const notes=[];for(const frame of c().frames){let note={};try{note=JSON.parse(localStorage.getItem(`jev-version:${B.tag}:${frame.frame}`)||'{}')}catch{}
    if(note.note||note.category)notes.push({frame:frame.frame,...note});}
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({tag:B.tag,notes},null,2)],{type:'application/json'}));a.download='jev_version_review_notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
};
window.addEventListener('resize',draw);
document.addEventListener('keydown',event=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();stop();seek(index+(event.key==='ArrowLeft'?-1:1))}});
for(const item of CASES){
  const option=document.createElement('option');option.value=String(CASES.indexOf(item));option.textContent=item.episode_id;$('caseSelect').append(option);
}
window.JEV_VERSION_COMPARE={bundle:B,cases:CASES,select,seek,draw,previousValue,newValue,previousColor,newColor,state:()=>({episode_id:c().episode_id,frame:index,previous:previousValue(f()),current:newValue(f())})};
updateLanguage();
seek(0);
