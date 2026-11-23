'use strict';
const el = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const paired=Boolean(aggregate.original);
let language = params.get('lang') === 'en' ? 'en' : 'zh';
let mode = params.get('mode') === 'out' ? 'out' : paired && params.get('mode')==='original' ? 'original' : 'return';
let desired = catalog.find(x => x.id === params.get('case'))?.id || catalog[0].id;
let atEnd = params.get('at') === 'end', c = null, step = 0, timer = null, view = null;
const cached = new Map(), layers = [
  {id:'actual', zh:'当前路线 · 实际回退', en:'Current route · actual return', color:'#ad4a21', show:true, width:3.5, lines:['actualLine','walkedLine']},
  {id:'history', zh:'回退参考 · 历史去程 A→B', en:'Return reference · recorded A→B', color:'#355e99', show:true, width:3, lines:['historyLine']},
  {id:'task', zh:'原任务标注参考路线', en:'Annotated task reference route', color:'#8055a1', show:false, width:3, lines:['taskLine']}
];
if(paired){
  layers[0].zh='新版实际回退';layers[0].en='Current return';
  layers.push({id:'original',zh:'旧版实际回退',en:'Original return',color:'#007873',show:true,width:3,lines:['originalLine','originalWalked']},
    {id:'after',zh:'历史偏航段 · B 至下一有效节点',en:'Historical deviation · B to next retained node',color:'#884054',show:false,width:3,lines:['afterLine']});
}
const textNodes = new Map([...document.querySelectorAll('[data-en]')].map(x => [x,x.textContent]));
const t = (zh,en) => language==='zh'?zh:en;
const actions = {
  FORWARD:['前进','Forward'], LEFT:['左转','Left'], RIGHT:['右转','Right'], turnaround:['初始掉头完成','Initial turnaround complete'],
  start:['起始观测','Initial observation'], move_forward:['前进','Forward'], turn_left:['左转','Left'], turn_right:['右转','Right'], stop:['停止','Stop']
};
const action = a => t(...actions[a]);
const activeReturn = () => mode==='original'?c.original:c;
const frames = () => mode==='out'?c.history:activeReturn().frames;
const versionLabel=()=>mode==='original'?t('旧版回退','Original return'):t('新版回退','Current return');
const svgNS = 'http://www.w3.org/2000/svg';
function stop(){clearInterval(timer);timer=null;el('play').textContent=t('播放','Play');}
function layerInputs(){
  el('layers').replaceChildren(...layers.map(l=>{
    const row=document.createElement('div');row.className='layerRow';
    const label=document.createElement('label'), check=document.createElement('input'), swatch=document.createElement('i');
    check.type='checkbox';check.checked=l.show;check.id=l.id+'Toggle';swatch.style.setProperty('--c',l.color);
    if(l.id!=='actual')swatch.className='dash';
    label.append(check,swatch,document.createTextNode(t(l.zh,l.en)));
    const range=document.createElement('input'),value=document.createElement('output');
    range.type='range';range.min=.5;range.max=12;range.step=.5;range.value=l.width;range.id=l.id+'Width';
    range.setAttribute('aria-label',t(l.zh+'线宽',l.en+' line width'));value.value=l.width+' px';value.htmlFor=range.id;
    check.onchange=()=>{l.show=check.checked;updateStyle();};
    range.oninput=()=>{l.width=Number(range.value);value.value=l.width+' px';updateStyle();};
    row.append(label,range,value);return row;
  }));
}
function updateStyle(){
  for(const l of layers)for(const id of l.lines){
    el(id).style.display=l.show?'':'none';el(id).setAttribute('stroke-width',l.width);
  }
  el('endPoints').style.display=paired&&el('pointToggle').checked?'':'none';
  el('markB').style.display=!paired||el('pointToggle').checked?'':'none';
}
function localize(){
  document.documentElement.lang=language==='zh'?'zh-CN':'en';
  document.title=paired?t('DeepSeek · H1 回退新旧版对照','DeepSeek · H1 paired rollback replay'):t('DeepSeek · H1 实走回退','DeepSeek · H1 rollback replay');
  el('map').setAttribute('aria-label',t('俯视地图','Floor plan'));
  textNodes.forEach((zh,x)=>x.textContent=t(zh,x.dataset.en));
  el('lang').value=language;
  const verdict=passed=>passed?t('达标','pass'):t('未达标','fail');
  el('cases').replaceChildren(...catalog.map(x=>new Option(x.id+' · '+(paired?t('新版','Current ')+verdict(x.passed)+' / '+t('旧版','original ')+verdict(x.originalPassed):verdict(x.passed)),x.id)));
  el('cases').value=desired;
  el('aggregate').textContent=t('落点达标 ','Within tolerance ')+aggregate.passed+'/'+catalog.length+
    '　·　'+t('平均终点误差 ','Mean endpoint error ')+aggregate.mean.toFixed(3)+' m';
  el('originalMode').hidden=el('pairStats').hidden=el('pointTools').hidden=!paired;
  if(paired){
    document.querySelector('h1').textContent=document.title;
    el('returnMode').textContent=t('新版回退','Current return');
    const stats=x=>x.passed+'/'+catalog.length+' · '+x.mean.toFixed(3)+' m';
    el('aggregate').textContent=t('达标数 / 案例数 · 平均终点误差　 新版 ','Passed / cases · mean endpoint error　 Current ')+stats(aggregate)+t('　｜　旧版 ','　|　Original ')+stats(aggregate.original);
  }
  layerInputs();updateStyle();if(c)renderCase();
}
function loadCase(id){
  desired=id;stop();c=null;el('error').textContent='';
  if(cached.has(id)){show(cached.get(id));return;}
  const s=document.createElement('script');s.src='cases/'+encodeURIComponent(id)+'.js';
  s.onload=()=>s.remove();s.onerror=()=>{if(desired===id)el('error').textContent=t('无法加载案例','Case failed to load');};
  document.body.append(s);
}
window.loadRollback = data=>{cached.set(data.id,data);if(data.id===desired)show(data);};
function show(data){
  c=data;step=atEnd?frames().length-1:0;atEnd=false;
  el('mapImage').setAttribute('href',c.map.src);fit(false);renderCase();updateURL();
}
function updateURL(){
  const url=new URL(location.href);url.searchParams.set('case',desired);url.searchParams.set('mode',mode);
  url.searchParams.set('lang',language);url.searchParams.delete('at');
  try{history.replaceState(null,'',url);}catch(error){/* Some offline viewers disable history changes. */}
}
function renderCase(){
  const active=activeReturn();
  el('cases').value=c.id;
  el('instruction').textContent=c.instruction[language==='zh'?0:1];
  el('caseId').textContent=c.eid;
  el('interval').textContent='A F'+c.a+' → B F'+c.b+'　·　'+c.ab.toFixed(2)+' m';
  el('returnMode').setAttribute('aria-pressed',mode==='return');el('originalMode').setAttribute('aria-pressed',mode==='original');el('outMode').setAttribute('aria-pressed',mode==='out');
  el('source').textContent=t('原生前视 RGB · 640 × 480','Native front RGB · 640 × 480');
  el('outcome').textContent=(paired?versionLabel()+' · ':'')+(active.passed?t('达标','Pass'):t('未达标','Fail'));el('outcome').className=active.passed?'pass':'fail';
  el('finalDist').textContent=active.error.toFixed(3)+' m';el('yaw').textContent=active.yaw.toFixed(2)+'°';el('count').textContent=active.frames.length-1;
  const reason=active.arrived?t('模型判断已到','Model declared arrival'):active.reason==='fall'?t('仿真判定跌倒','Simulator detected a fall'):active.reason==='stuck'?t('仿真判定卡住','Simulator detected stuck robot'):t('物理步数达到上限','Physical step budget exhausted');
  el('why').textContent=reason+'　·　'+t('达标要求模型自主退出且终点距 A ≤ 0.35 米。','A pass requires declared arrival within 0.35 m of A.');
  if(paired)el('pairStats').textContent=t('同例终点距 A　新版 ','Endpoint distance to A　Current ')+c.error.toFixed(3)+' m'+t('　旧版 ','　Original ')+c.original.error.toFixed(3)+' m';
  el('decisionHead').textContent=mode!=='out'?t('本轮 DeepSeek 决策','DeepSeek decision'):t('去程记录','Outbound recording');
  el('note').textContent=mode!=='out'?t('R0 为初始 12 次左转后的首张实拍图。实线高亮当前版本截至本帧已走的路线。','R0 is the first recorded view after 12 initial left turns. The solid highlight shows the selected return up to this frame.'):
    t('F 为去程原始动作边界帧号，A 是目标存档节点，B 是历史报警点。','F labels the original outbound action boundary. A is the target checkpoint and B is the historical alarm point.');
  drawStatic();display();
}
const W=640,H=365;
function fit(full){
  if(!c)return;
  let bounds=[0,0,c.map.w,c.map.h];
  if(!full){
    const pts=[...c.frames.map(f=>f.p),...c.turn,...c.history.map(f=>f.p)];
    if(layers[2].show)pts.push(...c.reference);
    if(paired&&layers.find(l=>l.id==='original').show)pts.push(...c.original.turn,...c.original.frames.map(f=>f.p));
    if(paired&&layers.find(l=>l.id==='after').show)pts.push(...c.after);
    const x=pts.map(p=>p[0]),y=pts.map(p=>p[1]),pad=.5/c.map.res;
    bounds=[Math.min(...x)-pad,Math.min(...y)-pad,Math.max(...x)+pad,Math.max(...y)+pad];
  }
  const [x0,y0,x1,y1]=bounds;
  view={x:(x0+x1)/2,y:(y0+y1)/2,s:Math.min((W-38)/(x1-x0),(H-34)/(y1-y0))};
}
const screen=p=>[(p[0]-view.x)*view.s+W/2,(p[1]-view.y)*view.s+H/2];
const points=seq=>seq.map(p=>screen(p).map(x=>x.toFixed(2)).join(',')).join(' ');
const place=(e,p)=>e.setAttribute('transform','translate('+screen(p).join(' ')+')');
function drawStatic(){
  if(!c)return;
  const image=el('mapImage'),[x,y]=screen([0,0]);
  for(const [key,value] of Object.entries({x,y,width:c.map.w*view.s,height:c.map.h*view.s}))image.setAttribute(key,value);
  el('taskLine').setAttribute('points',points(c.reference));
  el('historyLine').setAttribute('points',points(c.history.map(f=>f.p)));
  el('actualLine').setAttribute('points',points([...c.turn,...c.frames.slice(1).map(f=>f.p)]));
  if(paired){
    el('originalLine').setAttribute('points',points([...c.original.turn,...c.original.frames.slice(1).map(f=>f.p)]));
    el('afterLine').setAttribute('points',points(c.after));
    const afterToggle=el('afterToggle');
    afterToggle.disabled=c.after.length<2;el('afterWidth').disabled=afterToggle.disabled;
    afterToggle.parentElement.lastChild.textContent=t(layers.at(-1).zh,layers.at(-1).en)+(afterToggle.disabled?t('（无下一节点）',' (no next node)'):'');
    place(el('currentEnd'),c.frames.at(-1).p);place(el('originalEnd'),c.original.frames.at(-1).p);
  }
  place(el('markA'),c.history[0].p);place(el('markB'),c.history.at(-1).p);
  el('nodes').replaceChildren(...c.nodes.map(n=>{
    const circle=document.createElementNS(svgNS,'circle'),title=document.createElementNS(svgNS,'title');
    place(circle,n.p);circle.setAttribute('r',4.5);circle.setAttribute('fill','white');circle.setAttribute('stroke','#405c50');
    title.textContent=n.label+' · F'+n.step;circle.append(title);return circle;
  }));el('nodes').style.display=el('nodeToggle').checked?'':'none';
  const max=85*c.map.res/view.s,pow=10**Math.floor(Math.log10(max)),unit=([5,2,1].find(n=>n*pow<=max)||1)*pow;
  el('scaleBar').setAttribute('d','M0 -4v4h'+unit/c.map.res*view.s+'v-4');el('scaleText').textContent=Number(unit.toPrecision(3))+' m';
  updateStyle();
}
function display(){
  if(!c)return;
  const seq=frames();step=Math.max(0,Math.min(step,seq.length-1));
  const f=seq[step], label=mode!=='out'?'R'+step:'F'+f.origin;
  place(el('cursorShape'),f.p);el('cursorShape').setAttribute('fill',mode==='return'?'#ad4a21':mode==='original'?'#007873':'#355e99');el('heading').setAttribute('transform','rotate('+f.p[2]+')');
  el('walkedLine').setAttribute('points',mode==='return'?points([...c.turn,...c.frames.slice(1,step+1).map(x=>x.p)]):'');
  el('originalWalked').setAttribute('points',mode==='original'?points([...c.original.turn,...c.original.frames.slice(1,step+1).map(x=>x.p)]):'');
  for(const id of ['mapStep','rgbStep']){
    const r=el(id);r.max=seq.length-1;r.value=step;r.nextElementSibling.textContent=label+' · '+(step+1)+'/'+seq.length;
  }
  const img=el('rgb');if(img.getAttribute('src')!==f.img)img.src=f.img;img.alt=c.id+' · '+label+' RGB';
  el('frameCaption').textContent=(paired&&mode!=='out'?versionLabel()+' · ':'')+label+' · '+action(f.act)+(mode!=='out'?'　·　'+t('距 A ','Distance to A ')+f.error.toFixed(3)+' m':'');
  if(mode==='out'){
    el('decision').textContent='F'+c.a+' → F'+c.b+'　·　'+(c.history.length-1)+t(' 个历史动作',' recorded actions');
  }else if(step===seq.length-1&&!activeReturn().arrived){
    el('decision').textContent=activeReturn().reason==='fall'?t('机器人在这一步跌倒，仿真终止。','The robot fell on this step and the simulator terminated.'):t('仿真在这一步终止。','The simulator terminated on this step.');
  }else{
    const decisionStep=step-step%4, d=activeReturn().decisions[decisionStep];
    el('decision').textContent='R'+decisionStep+' · '+(d.arrived?t('判断已回到 A，退出回退。','Declared arrival at A and exited.'):d.actions.map(action).join(' → '));
  }
  el('prev').disabled=el('start').disabled=step===0;el('next').disabled=el('end').disabled=step===seq.length-1;
  el('play').textContent=timer?t('暂停','Pause'):t('播放','Play');
}
function jump(i){if(c){stop();step=i;display();}}
function changeMode(m){if(!c||m===mode)return;stop();mode=m;step=0;renderCase();updateURL();}
el('cases').onchange=e=>loadCase(e.target.value);
el('lang').onchange=e=>{language=e.target.value;localize();updateURL();};
el('returnMode').onclick=()=>changeMode('return');el('outMode').onclick=()=>changeMode('out');
el('originalMode').onclick=()=>changeMode('original');
for(const id of ['rgbStep','mapStep'])el(id).oninput=e=>jump(Number(e.target.value));
el('start').onclick=()=>jump(0);el('prev').onclick=()=>jump(step-1);el('next').onclick=()=>jump(step+1);el('end').onclick=()=>{if(c)jump(frames().length-1);};
el('play').onclick=()=>{if(!c)return;if(timer){stop();return;}if(step===frames().length-1)step=0;
  timer=setInterval(()=>{if(step===frames().length-1){stop();return;}step++;display();},320);display();};
const map=el('map'),pointers=new Map();
function redraw(){drawStatic();display();}
function zoom(from,to,mult){
  if(!c)return;const s=view.s,base=Math.min(W/c.map.w,H/c.map.h);
  view.s=Math.max(base/3,Math.min(Math.max(base*100,32),s*mult));
  view.x+=(from[0]-W/2)/s-(to[0]-W/2)/view.s;view.y+=(from[1]-H/2)/s-(to[1]-H/2)/view.s;redraw();
}
function cursor(e){const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(map.getScreenCTM().inverse());return [p.x,p.y];}
function gesture(){const [a,b]=pointers.values();return b?{p:[(a[0]+b[0])/2,(a[1]+b[1])/2],d:Math.hypot(a[0]-b[0],a[1]-b[1])}:{p:a,d:0};}
map.onwheel=e=>{e.preventDefault();const p=cursor(e);zoom(p,p,Math.exp(-Math.max(-300,Math.min(300,e.deltaY))*.002));};
map.onpointerdown=e=>{map.setPointerCapture(e.pointerId);pointers.set(e.pointerId,cursor(e));};
map.onpointermove=e=>{if(!pointers.has(e.pointerId))return;const old=gesture();pointers.set(e.pointerId,cursor(e));const next=gesture();zoom(old.p,next.p,old.d&&next.d?next.d/old.d:1);};
map.onpointerup=map.onpointercancel=map.onlostpointercapture=e=>pointers.delete(e.pointerId);
el('minus').onclick=()=>zoom([W/2,H/2],[W/2,H/2],1/1.45);el('plus').onclick=()=>zoom([W/2,H/2],[W/2,H/2],1.45);
el('fit').onclick=()=>{fit(false);redraw();};el('full').onclick=()=>{fit(true);redraw();};
el('nodeToggle').onchange=e=>{el('nodes').style.display=e.target.checked?'':'none';};
el('pointToggle').onchange=updateStyle;
localize();loadCase(desired);
