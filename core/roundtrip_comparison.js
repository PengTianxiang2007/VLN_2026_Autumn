'use strict';
const el = id => document.getElementById(id);
const param = new URLSearchParams(location.search);
const initial = catalog.find(c => c.id === param.get('case')) || catalog.find(c => c.group === param.get('group')) || catalog[0];
let group = initial.group, wanted = initial.id, lang = param.get('lang') === 'en' ? 'en' : 'zh';
let c = null, mode = 'compare', step = 0, timer = null, view = null, initialEnd = param.get('at') === 'end';
const cache = new Map();
const tr = (zh,en) => lang === 'zh' ? zh : en;
const staticText = new Map([...document.querySelectorAll('[data-en]')].map(e => [e,e.textContent]));
const names = {out:['去程','Outbound'],turn:['掉头回退','Turnaround'],back:['倒走回退','Backward'],
  reset_turn:['直接 reset · 掉头批次','Direct reset · turnaround run'],reset_back:['直接 reset · 倒走批次','Direct reset · backward run'],
  after:['报警后至下一节点','Alarm to next node'],nodes:['有效节点','Retained nodes'],heading:['当前朝向','Current heading']};
const actions = {start:['起始观测','Initial observation'],endpoint:['实测末态','Measured endpoint'],reset:['位姿重置','Pose reset'],
  move_forward:['前进','Forward'],move_backward:['后退','Backward'],turn_left:['左转','Turn left'],turn_right:['右转','Turn right'],stop:['停止','Stop']};
const colors = {out:'#355e99',turn:'#ad4a21',back:'#126a61',reset_turn:'#88569a',reset_back:'#4c5c91',after:'#996c48',nodes:'#5c6269',heading:'#203a33'};
const visible = {out:true,turn:true,back:true,reset_turn:false,reset_back:false,after:false,nodes:true,heading:true};
const W=640,H=365;
const name = k => tr(...names[k]);
const pass = value => value ? tr('达标','Pass') : tr('未达标','Fail');
const keys = () => mode === 'out' ? ['out'] : mode === 'reset' ? ['reset_turn','reset_back'] : ['turn','back'];
const lastStep = () => Math.max(...keys().map(k => c.legs[k].length))-1;
const frame = k => c.legs[k][Math.min(step,c.legs[k].length-1)];
const isH1 = () => group === 'h1';
function button(text,callback) { const b=document.createElement('button'); b.textContent=text;b.onclick=callback;return b; }
function stop() { clearInterval(timer);timer=null;el('play').textContent=tr('播放','Play'); }
function loadCase(id) {
  stop();wanted=id;c=null;step=0;el('error').textContent='';el('cases').value=id;
  if(cache.has(id)){showCase(cache.get(id));return;}
  const script=document.createElement('script');script.src='cases/'+id+'.js';
  script.onerror=()=>{if(wanted===id)el('error').textContent=tr('案例数据加载失败，请刷新重试。','Could not load this case. Refresh to retry.');};
  script.onload=()=>script.remove();document.body.append(script);
}
window.loadRoundtrip = function(data) {
  cache.set(data.id,data);
  if(data.id===wanted)showCase(data);
};
function showCase(data) {
  c=data;step=initialEnd?lastStep():0;initialEnd=false;
  el('mapImage').setAttribute('href',c.map.src);
  fit(false);render();
  const url=new URL(location.href);url.searchParams.set('case',c.id);url.searchParams.delete('at');
  try{history.replaceState(null,'',url);}catch(e){/* Some local-file viewers forbid URL changes. */}
}
function options() {
  el('dataset').value=group;el('lang').value=lang;
  const cases=catalog.filter(x=>x.group===group);
  el('cases').replaceChildren(...cases.map(x=>new Option(x.id+' · '+tr('掉头','Turnaround')+' '+pass(x.passed.turn)+' / '+tr('倒走','Backward')+' '+pass(x.passed.back),x.id)));
  el('cases').value=wanted;
  el('summary').textContent=[cases.length+tr(' 组',' cases'),...['turn','back'].map(k=>name(k)+' '+cases.filter(x=>x.passed[k]).length+'/'+cases.length+' '+tr('达标','passed'))].join('　·　');
}
function changeMode(next) {
  stop();mode=next;step=0;
  if(next==='reset'){visible.reset_turn=true;visible.reset_back=true;}
  render();
}
function render() {
  document.documentElement.lang=lang==='zh'?'zh-CN':'en';
  staticText.forEach((zh,e)=>e.textContent=tr(zh,e.dataset.en));document.title=tr('回退轨迹对照','Rollback trajectory comparison')+' · RxR-CE / H1';
  el('map').setAttribute('aria-label',tr('俯视地图','Floor plan'));options();
  if(!c)return;
  const h1=isH1();
  el('instruction').hidden=!c.instruction;el('instruction').textContent=c.instruction?.[lang==='zh'?0:1] || '';
  const modes=[['compare',tr('对照回退','Compare returns')],['out',tr('查看去程','View outbound')]];
  if(h1)modes.push(['reset',tr('直接 reset 对照','Direct reset controls')]);
  el('modes').replaceChildren(...modes.map(([key,label])=>{const b=button(label,()=>changeMode(key));b.setAttribute('aria-pressed',String(key===mode));return b;}));
  el('identity').textContent=c.id+' · '+c.scene+(c.eid?' · '+c.eid:'');
  el('distance').textContent='A–B '+c.ab.toFixed(2)+' m'+(h1?' · F'+c.a+' → F'+c.b:'');
  el('source').textContent=mode==='out'&&h1?tr('历史去程实采','Original outbound recording'):tr('仿真实采','Recorded in simulation');
  el('explanation').textContent=tr('两条返程按各自从 B 出发后的动作序号并排显示。先结束的一侧停在末帧。地图上 A 为回退目标，B 为返程起点。','Returns are aligned by action count from B. A shorter run holds its final frame. A is the return target and B the return start.');
  el('criterion').textContent=tr('达标要求水平误差 ≤0.35 米、朝向误差 ≤15°','A pass requires horizontal error ≤0.35 m and heading error ≤15°')+(h1?tr('，且 H1 仍可行动。虚线 reset 表示直接恢复位姿。',', with H1 still operational. Dashed reset tracks show direct pose changes.'):tr('。B 使用去程实测落点。','. B is the measured outbound endpoint.'));
  el('metrics').replaceChildren(...Object.entries(c.metrics).sort(([a],[b])=>Object.keys(names).indexOf(a)-Object.keys(names).indexOf(b)).map(([k,v])=>{
    const row=document.createElement('tr');
    for(const value of [name(k),v.m.toFixed(3)+' m',v.deg.toFixed(2)+'°',pass(v.pass)+(v.fall?tr(' · 跌倒',' · fall'):'')])row.insertCell().textContent=value;
    row.lastChild.className=v.pass?'pass':'fail';return row;
  }));
  const layers=['out','turn','back',...(h1?['reset_turn','reset_back','after','nodes']:[]),'heading'];
  el('layers').replaceChildren(...layers.map(k=>{
    const box=document.createElement('input');box.type='checkbox';box.checked=visible[k];box.dataset.layer=k;
    box.onchange=()=>{visible[k]=box.checked;drawMap();};
    const label=document.createElement('label'),swatch=document.createElement('i');swatch.className='swatch';swatch.style.setProperty('--c',colors[k]);
    if(k.startsWith('reset')||k==='back')swatch.style.borderTopStyle='dashed';
    label.append(box,swatch,document.createTextNode(name(k)));return label;
  }));
  el('pictures').className='pictures'+(mode==='out'?' single':'');
  el('pictures').replaceChildren(...keys().map(k=>{
    const figure=document.createElement('figure'),title=document.createElement('h3'),img=new Image(),caption=document.createElement('figcaption');
    figure.style.setProperty('--c',colors[k]);title.textContent=name(k);img.id='img_'+k;img.alt=name(k)+' RGB';caption.id='caption_'+k;caption.className='caption';
    figure.append(title,img,caption);return figure;
  }));
  display();
}
function display() {
  if(!c)return;
  const end=lastStep();step=Math.max(0,Math.min(step,end));
  for(const id of ['rgbStep','mapStep']){
    const input=el(id);input.max=end;input.value=step;input.nextElementSibling.textContent=(step+1)+' / '+(end+1);
  }
  for(const k of keys()){
    const f=frame(k), img=el('img_'+k),cap=el('caption_'+k), endHere=c.legs[k].length-1;
    if(img.getAttribute('src')!==f.img)img.src=f.img;
    const parts=[tr('帧 ','Frame ')+(Math.min(step,endHere)+1)+'/'+(endHere+1),tr(...actions[f.act])];
    if(f.origin!=null)parts.push('F'+f.origin);
    if(f.tick!=null)parts.push(tr('仿真步 ','Sim tick ')+f.tick);
    if(f.collision)parts.push(tr('发生碰撞','Collision'));
    if(step>endHere)parts.push(tr('已停在末帧','Holding endpoint'));
    if(f.gap>1)parts.push(tr('起始相机距机器人 ','Initial camera offset ')+f.gap.toFixed(2)+' m');
    cap.textContent=parts.join(' · ');cap.className='caption'+(f.gap>1?' alert':'');
  }
  el('prev').disabled=el('start').disabled=step===0;el('next').disabled=el('end').disabled=step===end;
  el('play').textContent=timer?tr('暂停','Pause'):tr('播放','Play');drawMap();
}
function fit(full) {
  if(!c)return;
  let xmin=0,ymin=0,xmax=c.map.w,ymax=c.map.h;
  if(!full){
    const pts=Object.values(c.legs).flat().map(f=>f.p);
    if(c.after&&visible.after)pts.push(...c.after);
    const pad=.45/c.map.res;
    xmin=Math.min(...pts.map(p=>p[0]))-pad;xmax=Math.max(...pts.map(p=>p[0]))+pad;
    ymin=Math.min(...pts.map(p=>p[1]))-pad;ymax=Math.max(...pts.map(p=>p[1]))+pad;
  }
  view={x:(xmin+xmax)/2,y:(ymin+ymax)/2,s:Math.min((W-45)/(xmax-xmin),(H-40)/(ymax-ymin))};
}
function screen(p) { return [(p[0]-view.x)*view.s+W/2,(p[1]-view.y)*view.s+H/2]; }
function pos(p) {return screen(p).map(n=>n.toFixed(2)).join(' ');}
function drawMap(){
  if(!c||!view)return;
  const img=el('mapImage'),[x,y]=screen([0,0]);img.setAttribute('x',x);img.setAttribute('y',y);
  img.setAttribute('width',c.map.w*view.s);img.setAttribute('height',c.map.h*view.s);
  let svg='';const width=Number(el('width').value);
  function line(k,pts,opacity,dash){
    if(!visible[k]||pts.length<2)return;
    svg+='<polyline data-line="'+k+'" points="'+pts.map(p=>screen(p).map(n=>n.toFixed(1)).join(',')).join(' ')+'" fill="none" stroke="'+colors[k]+'" stroke-width="'+width+'" stroke-opacity="'+opacity+'" stroke-linecap="round" stroke-linejoin="round" '+(dash?'stroke-dasharray="'+dash+'"':'')+'/>';
  }
  function marker(p,shape){
    svg+='<g transform="translate('+pos(p)+')">'+shape+'</g>';
  }
  for(const k of Object.keys(c.legs)){
    const pts=c.legs[k].map(f=>f.p), dash=k.startsWith('reset')?'8 6':k==='back'?'5 4':null;
    line(k,pts,keys().includes(k)?.42:.82,dash);
    if(keys().includes(k))line(k,pts.slice(0,step+1),1,dash);
  }
  if(c.after)line('after',c.after,.85,'4 5');
  if(visible.nodes)for(const n of c.nodes||[]){
    if(n.step>c.b&&!visible.after)continue;
    marker(n.p,'<circle r="5" fill="white" stroke="'+colors.nodes+'" stroke-width="2"><title>'+n.label+' · F'+n.step+'</title></circle>');
  }
  for(const [k,leg] of Object.entries(c.legs)){
    if(k==='out'||!visible[k])continue;
    const icon=k==='turn'?'<path d="M0 -7l7 7-7 7-7-7Z"/>':k==='back'?'<circle r="4.5"/>':'<path d="M-5 0h10m-5 -5v10"/>';
    marker(leg.at(-1).p,'<g fill="none" stroke="'+colors[k]+'" stroke-width="2">'+icon+'</g>');
  }
  const a=c.legs.out[0].p,b=c.legs.out.at(-1).p;
  for(const [p,label,dx] of [[a,'A',-16],[b,'B',8]]){
    marker(p,'<circle r="3.5" fill="#182c24" stroke="#fff"/><text x="'+dx+'" y="-8" font-size="14" font-weight="bold" paint-order="stroke" stroke="white" stroke-width="3">'+label+'</text>');
  }
  for(const [i,k] of keys().entries()){
    if(!visible[k])continue;
    const p=frame(k).p,color=colors[k];
    let mark='<circle r="'+(i?3:5)+'" stroke="white" fill="'+color+'"/>';
    if(visible.heading){
      const length=i?19:27;
      mark+='<g data-arrow="'+k+'" transform="rotate('+p[2]+')"><path d="M5 0H'+length+'m-6 -4 6 4-6 4" fill="none" stroke="white" stroke-width="5"/><path d="M5 0H'+length+'m-6 -4 6 4-6 4" fill="none" stroke="'+color+'" stroke-width="2.5"/></g>';
    }
    marker(p,mark);
  }
  const max=80*c.map.res/view.s,pow=10**Math.floor(Math.log10(max)),unit=([5,2,1].find(n=>n*pow<=max)||1)*pow;
  svg+='<g transform="translate(15 351)"><path d="M0 -4v4h'+unit/c.map.res*view.s+'v-4" stroke="#243b32" stroke-width="2" fill="none"/><text y="-7" font-size="12" paint-order="stroke" stroke="white" stroke-width="3">'+Number(unit.toPrecision(3))+' m</text></g>';
  el('drawing').innerHTML=svg;
}
function zoom(from,to,mult){
  if(!c)return;const s=view.s,base=Math.min(W/c.map.w,H/c.map.h);
  view.s=Math.max(base/3,Math.min(Math.max(base*100,32),s*mult));
  view.x+=(from[0]-W/2)/s-(to[0]-W/2)/view.s;view.y+=(from[1]-H/2)/s-(to[1]-H/2)/view.s;drawMap();
}
const map=el('map'),pointers=new Map();
function cursor(e){const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(map.getScreenCTM().inverse());return [p.x,p.y];}
function gesture(){const [a,b]=[...pointers.values()];return b?{p:[(a[0]+b[0])/2,(a[1]+b[1])/2],d:Math.hypot(a[0]-b[0],a[1]-b[1])}:{p:a,d:0};}
map.onwheel=e=>{e.preventDefault();const p=cursor(e);zoom(p,p,Math.exp(-Math.max(-300,Math.min(300,e.deltaY))*.002));};
map.onpointerdown=e=>{map.setPointerCapture(e.pointerId);pointers.set(e.pointerId,cursor(e));};
map.onpointermove=e=>{if(!pointers.has(e.pointerId))return;const old=gesture();pointers.set(e.pointerId,cursor(e));const next=gesture();zoom(old.p,next.p,old.d&&next.d?next.d/old.d:1);};
map.onpointerup=map.onpointercancel=map.onlostpointercapture=e=>pointers.delete(e.pointerId);
el('plus').onclick=()=>zoom([W/2,H/2],[W/2,H/2],1.45);el('minus').onclick=()=>zoom([W/2,H/2],[W/2,H/2],1/1.45);
el('fit').onclick=()=>{fit(false);drawMap();};el('full').onclick=()=>{fit(true);drawMap();};
el('width').oninput=e=>{el('widthVal').value=e.target.value+' px';drawMap();};
function jump(n){if(!c)return;stop();step=n;display();}
for(const id of ['mapStep','rgbStep'])el(id).oninput=e=>jump(Number(e.target.value));
el('start').onclick=()=>jump(0);el('prev').onclick=()=>jump(step-1);el('next').onclick=()=>jump(step+1);el('end').onclick=()=>{if(c)jump(lastStep());};
el('play').onclick=()=>{if(!c)return;if(timer){stop();return;}if(step>=lastStep())step=0;timer=setInterval(()=>{if(step>=lastStep()){stop();return;}step++;display();},350);display();};
el('dataset').onchange=e=>{group=e.target.value;mode='compare';wanted=catalog.find(x=>x.group===group).id;options();loadCase(wanted);};
el('cases').onchange=e=>loadCase(e.target.value);el('lang').onchange=e=>{lang=e.target.value;render();};
options();loadCase(wanted);
