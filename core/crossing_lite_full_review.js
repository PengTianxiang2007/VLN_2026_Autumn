'use strict';
const B=JSON.parse(document.getElementById('payload').textContent),$=id=>document.getElementById(id);
let language='zh';
const tr=(s)=>language==='zh'?s:(B.translations.zh_en[s]||s);
let ci=0,index=0,timer=null,mapImage=null;const c=()=>B.cases[ci],row=()=>c().frames[index];
const scoreNames=['','无明显迹象','弱怀疑','中等怀疑','强怀疑','明确多分支'];
const routePalette={1:'#bde5cf',2:'#8bd3ac',3:'#4fb982',4:'#20965e',5:'#006d3a',unknown:'#929aa4'};
function routeScore(r){const p=r?.prediction;return p?.valid&&Number.isInteger(p.score)&&p.score>=1&&p.score<=5?p.score:null}
function routeColor(r){return routePalette[routeScore(r)]||routePalette.unknown}
function routeSegments(frames){return frames.slice(0,-1).map((r,i)=>({from:r.position,to:frames[i+1].position,frame:r.frame,score:routeScore(r),color:routeColor(r)}))}
function renderRouteLegend(){
 const old=document.querySelector('.legend .green');if(old)old.remove();
 const legend=document.createElement('div');legend.id='routeScoreLegend';legend.className='legend';legend.setAttribute('aria-label','轨迹分数：1到5由浅绿到深绿');
 for(const score of [1,2,3,4,5,null]){const item=document.createElement('span'),swatch=document.createElement('i');item.dataset.score=score??'unknown';swatch.style.cssText=`display:inline-block;width:24px;height:5px;margin-right:5px;vertical-align:middle;background:${routePalette[score]||routePalette.unknown}`;item.append(swatch,document.createTextNode(score===null?'灰色：无有效评分':`${score}分`));legend.append(item)}
 document.querySelector('.legend').after(legend);const hint=document.createElement('p');hint.className='muted';hint.textContent='路线由浅绿（1分）到深绿（5分）。每段使用起点观测的原始分数；灰色虚线表示无有效评分，不代表低分。红色圆点表示当前机器人位置；重叠路线可逐帧回放查看。';legend.after(hint);
}

function points(){const threshold=Number($('threshold').value),out=[];let previous=false;for(const f of c().frames){const high=f.prediction?.score>=threshold;if(high&&!previous)out.push({frame:f.frame,position:f.position,id:'P'+String(out.length+1).padStart(3,'0'),score:f.prediction.score});previous=high}return out}
function stop(){if(timer!==null)clearInterval(timer);timer=null;$('play').textContent='顺序回放'}
function key(frame=index){return `crossing-lite:${B.manifest_sha256}:${B.tag}:${c().episode_id}:${frame}`}
function note(){try{return JSON.parse(localStorage.getItem(key())||'{}')}catch{return {}}}
function save(){try{localStorage.setItem(key(),JSON.stringify({note:$('note').value,category:$('category').value}));$('notesStatus').textContent='已保存在本浏览器，请导出保存'}catch{$('notesStatus').textContent='浏览器未允许本地保存'}}
function canvas(id){const el=$(id),box=el.getBoundingClientRect(),dpr=window.devicePixelRatio||1;el.width=Math.max(1,Math.round(box.width*dpr));el.height=Math.max(1,Math.round(box.height*dpr));const ctx=el.getContext('2d');ctx.scale(dpr,dpr);return {ctx,w:box.width,h:box.height}}
function draw(){if(!mapImage?.complete||!mapImage.naturalWidth)return;const {ctx,w,h}=canvas('map'),g=B.maps[c().scene].geometry,scale=Math.min(w/g.width,h/g.height),ox=(w-g.width*scale)/2,oy=(h-g.height*scale)/2;
 const xy=p=>[ox+(p[0]-g.low[0])/g.resolution*scale,oy+(g.high[1]-p[1])/g.resolution*scale];
 ctx.drawImage(mapImage,ox,oy,g.width*scale,g.height*scale);const frames=$('full').checked?c().frames:c().frames.slice(0,index+1);
 ctx.save();if(c().group==='failure'&&$('showReference').checked){ctx.strokeStyle='#e79620';ctx.lineWidth=3;ctx.setLineDash([7,5]);ctx.beginPath();c().reference_path.forEach((p,i)=>{i?ctx.lineTo(...xy(p)):ctx.moveTo(...xy(p))});ctx.stroke();ctx.setLineDash([])}ctx.lineWidth=4;ctx.lineCap='round';ctx.lineJoin='round';
 for(const segment of routeSegments(frames)){ctx.strokeStyle=segment.color;ctx.setLineDash(segment.score===null?[4,3]:[]);ctx.beginPath();ctx.moveTo(...xy(segment.from));ctx.lineTo(...xy(segment.to));ctx.stroke()}
 ctx.setLineDash([]);

 ctx.restore();
 // Draw the robot last so it remains visible over both routes.
 const [robotX,robotY]=xy(row().position);
 ctx.save();ctx.setLineDash([]);ctx.beginPath();ctx.arc(robotX,robotY,6,0,2*Math.PI);
 ctx.fillStyle='#e11d48';ctx.fill();ctx.lineWidth=2;ctx.strokeStyle='#ffffff';ctx.stroke();ctx.restore();
}
function plot(){const {ctx,w,h}=canvas('scorePlot'),margin=22,x=f=>margin+f/Math.max(1,c().frames.length-1)*(w-margin*2),y=s=>h-18-(s-1)*(h-36)/4;
 ctx.font='11px CrossingSans';for(let s=1;s<=5;s++){ctx.strokeStyle='#dce4ec';ctx.beginPath();ctx.moveTo(margin,y(s));ctx.lineTo(w-margin,y(s));ctx.stroke();ctx.fillStyle='#52677a';ctx.fillText(String(s),4,y(s)+4)}
 ctx.strokeStyle='#d4403e';ctx.lineWidth=2;let pen=false;ctx.beginPath();for(const f of c().frames){const s=f.prediction?.score;if(s==null){pen=false;continue}pen?ctx.lineTo(x(f.frame),y(s)):ctx.moveTo(x(f.frame),y(s));pen=true}ctx.stroke();
 ctx.strokeStyle='#2563eb';ctx.lineWidth=1;for(const e of c().marks){ctx.beginPath();ctx.moveTo(x(e.frame),12);ctx.lineTo(x(e.frame),h-15);ctx.stroke()}
 ctx.strokeStyle='#111';ctx.beginPath();ctx.moveTo(x(index),0);ctx.lineTo(x(index),h);ctx.stroke();
}
function seek(n){index=Math.max(0,Math.min(c().frames.length-1,n));const r=row(),p=r.prediction;for(const id of ['frame','imageFrame']){$(id).max=c().frames.length-1;$(id).value=index}for(const id of ['step','imageStep'])$(id).textContent=`观测 ${index} / ${c().frames.length-1}`;
 $('rgb').src=B.images[r.image];$('imageScore').textContent=p?.valid?`${p.score} / 5`:(language==='zh'?'未评分':'Unscored');$('state').textContent=p?.valid?`${p.score} / 5 · ${scoreNames[p.score]}`:r.eligible?'未取得有效评分':'终止/复用帧，不调用模型';$('answer').textContent=p?.answer?JSON.stringify({...p.answer,reason:tr(p.answer.reason)},null,2):(p?.error||'无模型回答');$('raw').textContent=p?JSON.stringify(p,null,2):'本帧未调用';
 $('inputInfo').textContent=p?`实际输入：${p.image_frames.join('、')}；请求耗时 ${p.latency_seconds.toFixed(2)} 秒`:'无本帧请求';$('history').replaceChildren();for(const f of p?.image_frames||[]){const button=document.createElement('button'),img=document.createElement('img'),label=document.createElement('span');img.src=B.images[c().frames[f].image];label.textContent=`${language==='zh'?'观测':'Frame'} ${f} · ${c().frames[f].prediction?.valid?c().frames[f].prediction.score+' / 5':(language==='zh'?'未评分':'Unscored')}${f===index?(language==='zh'?'（当前）':' (current)'):''}`;button.append(img,label);button.onclick=()=>{stop();seek(f)};$('history').append(button)}
 const saved=note();$('note').value=saved.note||'';$('category').value=saved.category||'';$('notesStatus').textContent=saved.note||saved.category?'本帧已有复核意见':'';draw();plot();
}
function lists(){const ps=points();$('priorList').replaceChildren();$('currentList').replaceChildren();for(const e of c().marks){const b=document.createElement('button');b.className='annotationItem priorItem';b.textContent=`${e.display_id} · 观测 ${e.frame} · ${e.type==='wrong_choice'?'错误选择点':'普通Crossing'}`;b.onclick=()=>{stop();seek(e.frame)};$('priorList').append(b)}for(const p of ps){const b=document.createElement('button');b.className='annotationItem currentItem';b.textContent=`${p.id} · 观测 ${p.frame} · ${p.score}分`;b.onclick=()=>{stop();seek(p.frame)};$('currentList').append(b)}$('mapCounts').textContent=`人工 C：${c().marks.length} 个；达到展示阈值的片段：${ps.length} 个（非确认存档）`}
function renderCases(){const filter=$('filters').value;$('cases').replaceChildren();for(const [i,r] of B.cases.entries()){if(filter!=='all'&&r.group!==filter)continue;const b=document.createElement('button');b.textContent=`${r.episode_id}\n原导航${r.group==='success'?'成功':'失败'} · ${r.expected} 次计划调用`;b.className=i===ci?'active':'';b.dataset.id=r.episode_id;b.onclick=()=>select(i);$('cases').append(b)}}
function select(n){stop();ci=n;index=0;$('showReference').checked=false;$('referenceControl').hidden=c().group!=='failure';$('title').textContent=c().episode_id;$('instruction').textContent=(language==='zh'?'原任务（仅供复核，未输入模型）：'+c().instruction:'Original task (review only, not model input): '+c().instruction_en);const valid=c().frames.filter(f=>f.prediction?.valid).length;$('caseStats').textContent=`有效评分 ${valid}/${c().expected}；终止/复用帧 ${c().frames.filter(f=>!f.eligible).length}；未建立逐帧正确率。`;renderCases();lists();mapImage=new Image();mapImage.onload=draw;mapImage.src=B.images[B.maps[c().scene].image];seek(0)}
$('filters').onchange=()=>{renderCases();if($('filters').value!=='all'&&c().group!==$('filters').value)select(B.cases.findIndex(c=>c.group===$('filters').value))};
$('threshold').onchange=()=>{lists();draw()};for(const id of ['showReference','full'])$(id).onchange=draw;
for(const id of ['frame','imageFrame'])$(id).oninput=e=>{stop();seek(Number(e.target.value))};$('prev').onclick=()=>{stop();seek(index-1)};$('next').onclick=()=>{stop();seek(index+1)};
$('play').onclick=()=>{if(timer!==null){stop();return}if(index===c().frames.length-1)seek(0);$('play').textContent='暂停';timer=setInterval(()=>{if(index===c().frames.length-1){stop();return}seek(index+1)},Number($('speed').value))};$('speed').onchange=stop;
$('scorePlot').onclick=e=>{const b=$('scorePlot').getBoundingClientRect();stop();seek(Math.round((e.clientX-b.left-22)/Math.max(1,b.width-44)*(c().frames.length-1)))};
$('note').oninput=save;$('category').onchange=save;
$('export').onclick=()=>{const notes=[];for(const c of B.cases)for(const f of c.frames){let n={};try{n=JSON.parse(localStorage.getItem(`crossing-lite:${B.manifest_sha256}:${B.tag}:${c.episode_id}:${f.frame}`)||'{}')}catch{}if(n.note||n.category)notes.push({episode_id:c.episode_id,frame:f.frame,...n})}const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({tag:B.tag,manifest_sha256:B.manifest_sha256,notes},null,2)],{type:'application/json'}));a.download='crossing_lite_notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
$('rgb').onclick=()=>{$('largeImage').src=$('rgb').src;$('imageDialog').showModal()};$('closeImage').onclick=()=>$('imageDialog').close();
document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();stop();seek(index+(e.key==='ArrowLeft'?-1:1))}});window.addEventListener('resize',()=>{draw();plot()});
$('version').add(new Option(B.tag,B.tag));$('version').onchange=()=>seek(index);
$('runInfo').textContent=`${B.version} · ${B.cases.length} 条轨迹 · ${B.summary.valid_calls}/${B.summary.expected_calls} 次有效评分`;$('prompt').textContent=B.translations.prompt_zh;
for(const [label,value] of [['轨迹',B.summary.episodes],['原导航失败',B.summary.groups.failure],['原导航成功',B.summary.groups.success],['有效评分',B.summary.valid_calls],['人工点',B.summary.annotation_points],['回放帧',B.summary.replay_frames]]){const el=document.createElement('div');el.className='metric';const b=document.createElement('b'),s=document.createElement('span');b.textContent=value;s.textContent=label;el.append(b,s);$('stats').append(el)}
$('footer').textContent='本文件完全离线；原始RGB未重编码；每步请求可按哈希重建。字体许可见随导出保存的 FONT_LICENSE.txt。';
renderRouteLegend();
window.CROSSING_LITE={bundle:B,select,seek,points,routePalette,routeScore,routeColor,routeSegments,draw,state:()=>({episode_id:c().episode_id,frame:index,score:row().prediction?.score??null})};select(0);

$('language').onchange=()=>{const old=index;language=$('language').value;$('prompt').textContent=language==='zh'?B.translations.prompt_zh:B.prompt;$('instruction').textContent=language==='zh'?'原任务（仅供复核，未输入模型）：'+c().instruction:'Original task (review only, not model input): '+c().instruction_en;seek(old)};
