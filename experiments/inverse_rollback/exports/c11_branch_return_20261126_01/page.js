'use strict';
const $=id=>document.getElementById(id), bundle=JSON.parse($('payload').textContent);
const initialCases=bundle.replays||{[bundle.cases[0].case_id]:bundle};
const versions=bundle.versions?{branch120:initialCases,...bundle.versions}:null;
let version,replays;
const selectedRound=new Map(), ci=0;
let B,historyFrames,N,calls,result,grid,moves,last,alarmFrame,targetFrame,targetNode,endFrame,index;
let lang='zh',panelKey='',timer=null,focus=true;
const c=()=>B.cases[0];
function loadCase(){
 const parts=location.hash.slice(1).split('/');
 version=versions?(parts.length===2&&Object.hasOwn(versions,parts[0])?parts[0]:Object.hasOwn(initialCases,parts[0])?'return60':'branch120'):null;
 replays=versions?versions[version]:initialCases;
 const id=parts[parts.length-1];
 B=Object.hasOwn(replays,id)?replays[id]:Object.values(replays)[0];
 endFrame=c().end;
 calls=B.calls;result=B.result;grid=B.grid.geometry;
 const alarm=c().rounds.find(r=>r.answer.verdict==='deviated');
 alarmFrame=alarm.b; targetFrame=alarm.a; targetNode=alarm.answer.previous_id.split(':').slice(-2)[0];
 historyFrames=c().frames.slice(0,alarmFrame+1); N=historyFrames.length;
 moves=[calls[0],...calls.filter(r=>r.executed)]; last=N+calls.length-1;index=alarmFrame;
 selectedRound.clear();panelKey='';focus=true;
}
loadCase();
const localText=(zh,en)=>lang==='zh'?zh:en;
const staticText=[...document.querySelectorAll('[data-en]')].map(e=>[e,e.textContent]);
const current=()=>index<N?historyFrames[index]:calls[index-N];
const stepIndex=m=>N+calls.findIndex(r=>r.motion===m&&(m===0||r.executed));
const labels={
 observe:['主动观察','Observe'], forward:['前进','Forward'],turn_left:['左转','Turn left'],turn_right:['右转','Turn right'],finish_return:['声明回退到达','Declare arrival']
};
function actionText(r){
 if(B.recovery&&r.op==='finish_return')return localText('声明已进入支路','Declare branch entry');
 if(r.terminal_reason==='fall')return localText('前进 · 跌倒终止','Forward · fall ended movement');
 return localText(...labels[r.op]);
}
const geomDistance=p=>Math.hypot(p[0]-result.target_position[0],p[1]-result.target_position[1]);
const layerData=[
 ['original','原版轨迹','Original trajectory','#516d8c',true],
 ['showAlarm','偏航 F45–F57','Deviation F45–F57','#cf354f',true],
 ['returnPath','实走回退','Physical return','#007e89',true],
 ...(versions?[['earlierPath','回溯更早回退点','Retrace to earlier checkpoints','#9b541c',true],['entryPath','选路与尝试进入','Branch selection and attempted entry','#0864b2',true]]:[]),
 ['checkpoints','有效节点','Effective checkpoints','#7734a5',true],
 ['target','回退目标 S05','Return target S05','#16713e',true],
 ['milestones',...(B.summary?['最近位置与停点','Closest approach and final position']:['50 步与截断点','Move 50 and cutoff']),'#b35b00',true],
 ['reference','参考路线','Reference route','#a68843',false]
];
const is=(id)=>$(id).checked;
function button(text,action){const b=make('button',text);b.type='button';b.onclick=action;return b;}
function redrawStatic(){
 document.documentElement.lang=lang==='zh'?'zh-CN':'en';
 for(const [e,zh] of staticText)e.textContent=localText(zh,e.dataset.en);
 document.title=c().case_id+' · '+(B.recovery?localText('回退与进入支路','Return and branch entry'):localText('Codex 实走回退','Codex physical return'));
 document.querySelector('header h1').textContent=document.title;
 document.querySelector('header .sub').textContent=c().episode_id+' · GPT-6 Astra · medium · seed 2';
 $('graph').previousElementSibling.textContent=localText('回退过程距 '+targetNode+' 的水平距离','Horizontal distance to '+targetNode+' during the return');
 const compare=targetNode+' / F'+targetFrame;
 $('targetRgb').parentElement.querySelector('summary').textContent=localText('对照 '+compare+' 的目标图','Compare with the '+compare+' target view');
 $('targetRgb').alt=compare;
 if(B.startImage){
   let start=$('placementRgb');
   if(!start){const box=make('details');box.append(make('summary'));start=make('img');start.id='placementRgb';start.className='refThumb';start.loading='lazy';box.append(start);$('targetRgb').closest('details').after(box);}
   start.src=B.images[B.startImage];start.alt='F'+alarmFrame;
   start.parentElement.firstChild.textContent=localText('摆位后的第一人称 RGB','First-person RGB after placement')+' · F'+alarmFrame;
 }
 if(bundle.replays){
   let picker=$('returnCase');
   if(!picker){picker=make('select');picker.id='returnCase';for(const id of Object.keys(replays)){const opt=make('option',id);opt.value=id;picker.append(opt);} $('cases').prepend(picker);picker.onchange=()=>{location.hash=(versions?version+'/':'')+picker.value;};}
   picker.value=c().case_id;picker.setAttribute('aria-label',localText('选择回退案例','Select a return case'));
   if(versions){
     let v=$('returnVersion');
     if(!v){v=make('select');v.id='returnVersion';for(const id of Object.keys(versions)){const opt=make('option');opt.value=id;v.append(opt);}picker.before(v);v.onchange=()=>{location.hash=v.value+'/'+c().case_id;};}
     v.options[0].textContent=localText('120 步 · 回退与进入支路','120 moves · Return and enter a branch');
     v.options[1].textContent=localText('60 步 · 回到回退点','60 moves · Return to checkpoint');v.value=version;
     v.setAttribute('aria-label',localText('实验版本','Experiment version'));
   }
 }
 $('instruction').textContent=c()['instruction_'+lang];
 $('caseButton').textContent=c().case_id+' · '+c().episode_id+'\n'+(c().original_success?localText('原版导航成功 · 当前导航未评分','Original navigation succeeded · current navigation unscored'):localText('原版导航失败 · 当前导航未评分','Original navigation failed · current navigation unscored'))+'\n'+localText(...(B.summary?B.summary.verdict:['本次局部回退未达标','Local return unsuccessful']));
 $('caseButton').onclick=()=>jump(alarmFrame);
 const metric=(v,zh,en)=>{const box=make('div',undefined,'metric');box.append(make('strong',v),make('span',localText(zh,en)));return box;};
 if(B.summary){
  $('stats').replaceChildren(metric('F'+alarmFrame+' → F'+targetFrame,'报警位置 → 回退目标','Alarm frame → return target'),metric(result.movements+' / '+result.cap,'已用移动步数 / 上限','Moves used / budget'),metric(result.nearest_m.toFixed(3)+' m','最近时距 F'+targetFrame,'Closest distance to F'+targetFrame),metric(result.final_m.toFixed(3)+' m','停点距 F'+targetFrame,'Final distance to F'+targetFrame));
  document.querySelector('.notice').textContent=localText(...B.summary.notice);
  document.querySelector('.foot').textContent=localText(...B.summary.footer);
  $('graph').nextElementSibling.textContent=localText('距离仅作位置对照。点击曲线可跳到对应动作。','Distances are shown for reference. Click the curve to inspect a move.');
  if(B.recovery){
    $('stats').replaceChildren(metric('F'+alarmFrame+' → '+targetNode,'报警帧 → 初始回退点','Alarm frame → initial checkpoint'),metric(result.movements+' / '+result.cap,'已用移动步数 / 上限','Moves used / budget'),metric(B.recovery.checkpoints.join(' → '),'模型报告的回退点','Checkpoints reported by the model'),metric(B.recovery.elapsed,'单例总耗时（分:秒）','Total elapsed (min:sec)'));
    $('graph').nextElementSibling.textContent=localText('曲线以初始回退点为参照。轨迹分段以模型发言所在的工具调用为界。点击曲线可跳到对应动作。','Distance is measured to the initial checkpoint. Map segments change at tool calls associated with model statements. Click the curve to inspect a move.');
  }
 }else{
  $('stats').replaceChildren(metric('F'+alarmFrame+' → F'+targetFrame,'报警位置 → 回退目标','Alarm frame → return target'),metric(result.movements,'实际执行动作','Executed movements'),metric(result.at_limit.distance_m.toFixed(3)+' m','第 50 步距目标','Distance at move 50'),metric(result.final_horizontal_error_m.toFixed(3)+' m','截断时距目标','Distance at cutoff'));
 }
 $('jumpList').replaceChildren(...[
  [0,'F0 · 轨迹起点','F0 · Original start'],[targetFrame,'F'+targetFrame+' · '+targetNode+' 回退点','F'+targetFrame+' · '+targetNode+' checkpoint'],
  [alarmFrame,'F'+alarmFrame+' · 偏航报警','F'+alarmFrame+' · Deviation alarm'],[N,'R0 · 分支首次观察','R0 · First branch observation'],
  ...(B.summary?B.summary.events.map(([call,zh,en])=>[N+call-1,zh,en]):[[stepIndex(50),'R50 · 指定上限','R50 · Requested limit'],[stepIndex(54),'R54 · 最近位置','R54 · Closest approach'],[last,'R55 · 实际截断','R55 · Actual cutoff']])].map(([ix,zh,en])=>button(localText(zh,en),()=>jump(ix))));
 for(const [id,zh,en] of layerData) $(id).nextElementSibling.textContent=localText(zh,en);
 if(versions){$('entryPath').closest('label').hidden=!B.recovery;$('earlierPath').closest('label').hidden=!B.recovery?.earlierCall;}
 $('showAlarm').nextElementSibling.textContent=localText('偏航 ','Deviation ')+'F'+targetFrame+'–F'+alarmFrame;
 $('target').nextElementSibling.textContent=localText('回退目标 ','Return target ')+targetNode;
 $('returnPrompt').textContent=B.prompt[lang==='zh'?0:1];
 $('resumePrompt').closest('details').hidden=!B.resume;
 if(B.resume)$('resumePrompt').textContent=localText('接续指令：','Continuation instruction: ')+B.resume[lang==='zh'?0:1];
 $('errorNote').textContent=localText('首次左转完成了 50 个任务 tick，世界计数增加 91。旧接口因此返回错误。重试被拒绝，没有新增动作。修复后，同一分支从现场 F58 接续。','The first left turn completed 50 task ticks and advanced the world clock by 91 ticks. The old bridge reported an error. A retry was rejected without movement. After the fix, the same branch continued from live F58.');
 $('threadIds').textContent=localText('父会话 ','Parent ')+result.parent_thread+' · '+localText('动作分支 ','Action branch ')+result.branch_thread;
 $('messages').replaceChildren(...B.notes.map(n=>{const block=make('div',undefined,'actionnotes');const k=n.call;block.append(button(k?localText('调用 ','Call ')+k:localText('首次观察前','Before the first observation'),()=>jump(k?N+k-1:N)),make('p',n.text[lang==='zh'?0:1]));return block;}));
 $('callList').replaceChildren(...calls.map((r,i)=>{const label='#'+String(i+1).padStart(2,'0')+' · R'+r.motion+' · '+actionText(r)+(r.failed?' · '+localText(r.executed?'已动 / 回执报错':'未执行',r.executed?'moved / receipt error':'rejected'):'');return button(label,()=>jump(N+i));}));
 $('zoom').textContent=focus?localText('显示全图','Show full map'):localText('放大回退区域','Zoom to return');
 $('targetRgb').src=B.images[c().frames[targetFrame].image];
 panelKey='';seek(index);
}
function stop(){if(timer)clearInterval(timer);timer=null;$('play').textContent=localText('播放','Play');}
/* ORIGINAL REVIEW PANEL */
function seek(n){
 index=Math.max(0,Math.min(last,Math.round(n)));
 const r=current(),live=index>=N;
 const description=live?'R'+r.motion+' · '+localText('现场 F','Live F')+r.live+' · '+localText('调用 ','Call ')+(index-N+1)+'/'+calls.length:
   localText('原版 F','Original F')+r.frame+' / F'+alarmFrame;
 $('frame').value=index;$('imageFrame').value=index;$('step').textContent=description;$('imageStep').textContent=description;
 $('rgb').src=B.images[r.image];$('rgb').alt=description;
 const node=c().effective.find(v=>!live&&v.index===r.frame);
 $('frameStatus').textContent=live?actionText(r)+(r.failed&&!r.executed?' · '+localText('未执行','Rejected'):r.status==='physical_terminal'&&!r.terminal_reason?' · '+localText('仿真已终止','Simulation terminated'):!B.summary&&index===last?' · '+localText('截断','Cutoff'):''):
   (node?node.id+' · ':'')+(r.frame===endFrame?('END · '+localText('原版终止','Original terminal')+(alarmFrame===endFrame?localText(' / 报警',' / alarm'):'')):(r.frame===alarmFrame?localText('偏航报警','Deviation alarm')+' · F'+alarmFrame:description));
 $('imageSource').textContent=live?(r.feedback?localText('工具返回的原生前视图','Native front image returned by the tool'):
   r.executed?localText('仿真已保存左转后的前视图，此次报错未向分支回图。','The simulator saved this post-turn view. The error response did not include an image.'):
   localText('本次被拒绝，无新回图。显示最近一次实际观察。','Request rejected. Showing the last observed image.')):
   localText('冻结采集的原生前视图','Native front view from the frozen capture');
 const fields=[[geomDistance(r.position).toFixed(3)+' m','距 F'+targetFrame+' 水平距离','Horizontal distance to F'+targetFrame],
  [r.heading.toFixed(1)+'°','机身航向','Robot heading']];
 if(live)fields.push([r.taskTicks+' / '+r.worldTicks,'任务 / 世界 tick 增量','Task / world tick delta'],
  [r.utc?r.utc.slice(11,23):'—','回执时间 UTC','Receipt time UTC']);
 $('readout').replaceChildren(...fields.map(([v,zh,en])=>{const d=make('div');d.append(make('small',localText(zh,en)),make('b',v));return d;}));
 [...$('callList').children].forEach((el,i)=>el.setAttribute('aria-current',String(live&&i===index-N)));
 reviewPanel();draw();
}
function prepareCanvas(id){
 const el=$(id),rect=el.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
 const w=rect.width,h=rect.height;
 if(el.width!==Math.round(w*dpr)||el.height!==Math.round(h*dpr)){el.width=Math.round(w*dpr);el.height=Math.round(h*dpr);}
 const ctx=el.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);return {ctx,w,h};
}
const raster=new Image();
function drawMap(){
 const {ctx,w,h}=prepareCanvas('map');
 let x0=grid.low[0], y1=grid.high[1], width=grid.width*grid.resolution, height=grid.height*grid.resolution;
 if(focus){
  const ps=historyFrames.slice(targetFrame,alarmFrame+1).concat(moves,[current()]).map(r=>r.position),xs=ps.map(p=>p[0]),ys=ps.map(p=>p[1]);
  x0=Math.min(...xs)-.95;y1=Math.max(...ys)+.8;
  width=Math.max(...xs)+.95-x0;height=y1-Math.min(...ys)+.8;
 }
 const scale=Math.min(w/width,h/height),ox=(w-width*scale)/2,oy=(h-height*scale)/2;
 const xy=p=>[ox+(p[0]-x0)*scale,oy+(y1-p[1])*scale];
 const topLeft=xy([grid.low[0],grid.high[1]]);
 if(raster.complete&&raster.naturalWidth)ctx.drawImage(raster,...topLeft,grid.width*grid.resolution*scale,grid.height*grid.resolution*scale);
 function line(points,color,width,dash=[]){ctx.save();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin='round';ctx.lineCap='round';ctx.setLineDash(dash);ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(...xy(p)):ctx.moveTo(...xy(p)));ctx.stroke();ctx.restore();}
 function mark(p,label,color,dx,dy,radius=5){
  const [x,y]=xy(p);ctx.save();ctx.beginPath();ctx.arc(x,y,radius,0,Math.PI*2);ctx.strokeStyle='#fff';ctx.lineWidth=3;ctx.stroke();ctx.strokeStyle=color;ctx.lineWidth=2;ctx.stroke();
  ctx.font='bold 11px system-ui';ctx.lineWidth=3;ctx.strokeStyle='white';ctx.strokeText(label,x+dx,y+dy);ctx.fillStyle=color;ctx.fillText(label,x+dx,y+dy);ctx.restore();
 }
 if(is('reference'))line(c().reference_path,'#a68843',2,[5,4]);
 if(is('original'))line(c().frames.map(r=>r.position),'#516d8c',3.5);
 if(is('showAlarm'))line(historyFrames.slice(targetFrame,alarmFrame+1).map(r=>r.position),'#cf354f',5);
 if(B.recovery){
  const first=B.recovery.earlierCall?calls[B.recovery.earlierCall-1].motion:null, entry=calls[B.recovery.entryCall-1].motion;
  const segments=[['returnPath',0,first??entry,'#007e89'],['earlierPath',first??entry,entry,'#9b541c'],['entryPath',entry,result.movements,'#0864b2']];
  for(const [layer,a,b,color] of segments){
   if(a>=b||!is(layer))continue;
   line(moves.slice(a,b+1).map(v=>v.position),color,2,[4,3]);
   if(index>=N && current().motion>a)line(moves.slice(a,Math.min(current().motion,b)+1).map(v=>v.position),color,4);
  }
 }else if(is('returnPath')){
  line(moves.map(r=>r.position),'#54b0af',2,[4,3]);
  if(index>=N)line(moves.slice(0,current().motion+1).map(r=>r.position),'#007e89',4);
 }
 if(is('checkpoints')){
  for(const n of c().effective)mark(historyFrames[n.index].position,n.id,'#7734a5',6,14,4);
  mark(c().frames[endFrame].position,'END F'+endFrame,'#7734a5',6,14,4);
 }
 if(is('target')){
  const p=historyFrames[targetFrame].position;
  if(result.threshold_m){ctx.beginPath();ctx.arc(...xy(p),scale*result.threshold_m,0,Math.PI*2);ctx.fillStyle='rgba(20,120,70,.1)';ctx.fill();ctx.strokeStyle='#16713e';ctx.setLineDash([3,4]);ctx.stroke();ctx.setLineDash([]);}
  mark(p,'A · F'+targetFrame,'#16713e',7,-10,8);
  for(const id of (B.recovery?.checkpoints||[]).slice(1)){
   const n=c().effective.find(v=>v.id===id);
   if(n)mark(c().frames[n.index].position,id+' · F'+n.index,'#9b541c',6,-12,7);
  }
 }
 if(is('milestones')){
  const checkpoint=B.summary?result.nearest_move:50;
  mark(moves[checkpoint].position,'R'+checkpoint,'#aa5b0b',9,16);
  const fall=B.recovery?.stop==='fall';
  mark(moves[result.movements].position,'R'+result.movements+(fall?localText(' 跌倒',' Fall'):''),fall?'#b2323b':'#563277',-30,-12,7);
 }
 const r=current(),[x,y]=xy(r.position); ctx.save();ctx.translate(x,y);ctx.rotate(-r.heading*Math.PI/180);ctx.beginPath();ctx.moveTo(10,0);ctx.lineTo(-6,-5);ctx.lineTo(-3,0);ctx.lineTo(-6,5);ctx.closePath();ctx.fillStyle='#11394d';ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=1.4;ctx.stroke();ctx.restore();
}
function drawGraph(){
 const {ctx,w,h}=prepareCanvas('graph'),top=12,bottom=h-23, margin=42, span=w-margin-18;
 const xmax=moves.length-1, ymax=Math.ceil(Math.max(...moves.map(r=>r.distance))*2)/2;
 const x=i=>margin+i/xmax*span,y=v=>bottom-v/ymax*(bottom-top);
 ctx.font='11px system-ui';ctx.fillStyle='#53687c';
 for(let v=0;v<=ymax;v+=.5){ctx.beginPath();ctx.strokeStyle='#e0e6eb';ctx.moveTo(margin,y(v));ctx.lineTo(w-15,y(v));ctx.stroke();ctx.fillText(v+' m',0,y(v)+4);}
 for(let i=0;i<xmax-3;i+=10)ctx.fillText('R'+i,x(i)-7,h-4);
 ctx.fillText('R'+xmax,x(xmax)-7,h-4);
 if(result.threshold_m){ctx.beginPath();ctx.setLineDash([5,3]);ctx.strokeStyle='#16713e';ctx.moveTo(margin,y(result.threshold_m));ctx.lineTo(w-15,y(result.threshold_m));ctx.stroke();ctx.setLineDash([]);}
 ctx.beginPath();ctx.lineWidth=2.3;ctx.strokeStyle='#007e89';moves.forEach((r,i)=>i?ctx.lineTo(x(i),y(r.distance)):ctx.moveTo(x(i),y(r.distance)));ctx.stroke();ctx.lineWidth=1;
 if(index>=N){ctx.beginPath();ctx.fillStyle='#bc481c';ctx.arc(x(current().motion),y(current().distance),4,0,Math.PI*2);ctx.fill();}
}
function drawJev(){
 if(!$('jevDetails').open)return;
 const {ctx,w,h}=prepareCanvas('jevCurve'), margin=36, axis=h-22;
 const x=f=>margin+f/alarmFrame*(w-margin-20),y=v=>axis-v*(axis-16);
 ctx.font='11px system-ui';ctx.fillStyle='#617384';ctx.lineWidth=1;
 for(const v of [0,.5,1]){ctx.fillText(String(v),3,y(v)+4);ctx.strokeStyle='#d9e2eb';ctx.beginPath();ctx.moveTo(margin,y(v));ctx.lineTo(w-12,y(v));ctx.stroke();}
 ctx.beginPath();ctx.strokeStyle='#b34646';ctx.lineWidth=2;
 historyFrames.forEach((f,i)=>{if(f.jev){const yy=y(f.jev.probability_yes);if(i===0)ctx.moveTo(x(i),yy);else ctx.lineTo(x(i),yy);}});ctx.stroke();
 if(is('checkpoints')){
  for(const n of [...c().effective.filter(n=>n.index<=alarmFrame),...(endFrame===alarmFrame?[{id:'END',index:endFrame}]:[])]){ctx.strokeStyle='#7734a5';ctx.beginPath();ctx.moveTo(x(n.index),16);ctx.lineTo(x(n.index),axis);ctx.stroke();ctx.fillText(n.id+' F'+n.index,Math.max(4,Math.min(w-54,x(n.index)-18)),h-5);}
 }
 if(index<N){ctx.strokeStyle='#163650';ctx.beginPath();ctx.moveTo(x(index),9);ctx.lineTo(x(index),axis);ctx.stroke();}
}
function draw(){drawMap();drawGraph();drawJev();}
$('jevDetails').ontoggle=drawJev;
$('jevCurve').onclick=e=>{const rect=$('jevCurve').getBoundingClientRect();jump(Math.max(0,Math.min(alarmFrame,Math.round((e.clientX-rect.left-36)/(rect.width-56)*alarmFrame))));};
for(const [id,zh,en,color,on] of layerData){const label=make('label'),cb=make('input'),text=make('span');cb.type='checkbox';cb.id=id;cb.checked=on;cb.onchange=draw;label.append(cb,text);const swatch=make('i',undefined,'chip');swatch.style.background=color;label.prepend(swatch);$('layers').append(label);}
for(const id of ['frame','imageFrame']){$(id).max=last;$(id).oninput=e=>jump(+e.target.value);}
$('prev').onclick=()=>jump(index-1);$('next').onclick=()=>jump(index+1);
$('play').onclick=()=>{if(timer)return stop();if(index===last)seek(0);$('play').textContent=localText('暂停','Pause');timer=setInterval(()=>index>=last?stop():seek(index+1),450);};
$('zoom').onclick=()=>{focus=!focus;redrawStatic();};
$('graph').onclick=e=>{const rect=$('graph').getBoundingClientRect();const m=Math.round((e.clientX-rect.left-42)/(rect.width-60)*result.movements);jump(stepIndex(Math.max(0,Math.min(result.movements,m))));};
$('language').onchange=()=>{stop();lang=$('language').value;stop();redrawStatic();};
window.addEventListener('resize',draw);window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();jump(index+(e.key==='ArrowRight'?1:-1));}});
window.addEventListener('hashchange',()=>{stop();loadCase();for(const id of ['frame','imageFrame'])$(id).max=last;raster.src=B.images[B.grid.image];redrawStatic();});
raster.onload=draw;raster.src=B.images[B.grid.image];
stop();redrawStatic();
