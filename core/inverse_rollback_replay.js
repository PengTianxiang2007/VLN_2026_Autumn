const replay = JSON.parse(document.getElementById('data').textContent);
const el = id => document.getElementById(id);
const tr = (zh,en) => language === 'zh' ? zh : en;
const phases = {history:['历史去程 A → B','Historical A → B'],inverse:['逆动作 B → A','Inverse B → A'],reset:['直接 reset','Direct reset']};
const colors = {history:'#21648d',inverse:'#b24f22',reset:'#17745c',after:'#946399',nodes:'#515463',heading:'#162f35'};
const labels = {history:['历史去程','Outbound track'],inverse:['逆动作轨迹','Inverse track'],reset:['reset 跳转','Reset jump'],after:['报警后至下一节点','Alarm to next node'],nodes:['有效节点','Retained nodes'],heading:['当前朝向','Current heading']};
const visible = {history:true,inverse:true,reset:true,after:false,nodes:true,heading:true};
const map = el('map');
const zhText = new Map([...document.querySelectorAll('[data-en]')].map(e=>[e,e.textContent]));
const requestedCase = new URLSearchParams(location.search).get('case');
let selected = replay.cases.find(c=>c.id===requestedCase || c.eid===requestedCase) || replay.cases[0];
let language='zh', mode='inverse', step=0, frames=[], timer=null, view=null;
const W=720,H=412;
function name(arm){return tr(...phases[arm]);}
function outcome(ok){return ok ? tr('达标','Pass') : tr('未达标','Fail');}
function makeButton(text,func){const b=document.createElement('button');b.textContent=text;b.onclick=func;return b;}
function stop(){clearInterval(timer);timer=null;el('play').textContent=tr('播放','Play');}
function setFrames(){
  const b=selected.history.at(-1);
  if(mode==='history') frames=selected.history;
  else frames=[selected.starts[mode] || {...b,index:0,action:null},...(mode==='inverse'?selected.inverse:[selected.reset])];
}
function switchMode(next,index=0){
  stop();mode=next;setFrames();step=Math.max(0,Math.min(index,frames.length-1));renderPanel();
}
function selectCase(id){
  stop();selected=replay.cases.find(c=>c.id===id);step=0;setFrames();fit('routes');renderPanel();
}
function writeControlText(){
  document.documentElement.lang=language==='zh'?'zh-CN':'en';
  zhText.forEach((zh,e)=>e.textContent=tr(zh,e.dataset.en));
  document.title=tr('逆动作回退回放','Inverse-action rollback replay');
  el('rgb').alt=tr('当前回放帧的第一人称视图','First-person view at the current frame');
  map.setAttribute('aria-label',tr('俯视地图','Floor plan'));
  for(const [id,zh,en] of [['plus','放大','Zoom in'],['minus','缩小','Zoom out']]){
    el(id).setAttribute('aria-label',tr(zh,en));el(id).title=tr(zh,en);
  }
  el('cases').replaceChildren(...replay.cases.map(c=>{
    const text=c.id+' · '+c.eid+'　'+tr('逆动作 ','Inverse ')+outcome(c.metrics.inverse.passed)+' / reset '+outcome(c.metrics.reset.passed);
    return new Option(text,c.id,false,c.id===selected.id);
  }));
  el('summary').innerHTML='<span>'+tr('配对完成','Pairs completed')+' <b>'+replay.cases.length+'</b></span>'+
    ['inverse','reset'].map(k=>'<span>'+tr(...(k==='inverse'?['逆动作达标','Inverse passes']:['reset 达标','Reset passes']))+' <b>'+replay.summary[k].passed+'/'+replay.cases.length+'</b></span>').join('');
  el('modes').replaceChildren(...Object.keys(phases).map(k=>{
    const b=makeButton(name(k),()=>switchMode(k));b.setAttribute('aria-pressed',String(k===mode));return b;
  }));
  el('layers').replaceChildren(...Object.keys(labels).map(k=>{
    const l=document.createElement('label'), input=document.createElement('input'), swatch=document.createElement('i');
    input.type='checkbox';input.checked=visible[k];input.id='layer-'+k;
    input.onchange=()=>{visible[k]=input.checked;drawMap();};
    swatch.className='sample';swatch.style.borderColor=colors[k];
    if(k==='reset'||k==='after')swatch.style.borderTopStyle='dashed';
    l.append(input,swatch,document.createTextNode(tr(...labels[k])));return l;
  }));
}
function renderPanel(){
  writeControlText();
  el('instruction').textContent=selected.instruction[language==='zh'?0:1];
  el('ident').textContent=selected.scene+'　·　'+tr('已执行逆动作 ','Inverse actions executed ')+selected.executed+' / '+selected.planned;
  el('locations').textContent='A '+selected.node+' · F'+selected.a+'　 B · F'+selected.b+'　 A–B '+selected.ab_xy_m.toFixed(2)+' m';
  el('results').innerHTML=['inverse','reset'].map(k=>{
    const m=selected.metrics[k];
    const reasons={fall:['跌倒','fall'],stuck:['卡住','stuck'],exceed_total_max_step:['耗尽步数','step limit']};
    return '<tr><th>'+name(k)+'</th><td>'+m.xy_m.toFixed(3)+' m</td><td>'+m.yaw_deg.toFixed(2)+'°</td><td class="'+(m.passed?'pass':'fail')+'">'+outcome(m.passed)+(m.ended?' · '+tr(...(reasons[m.reason]||['提前终止','terminated'])):'')+'</td></tr>';
  }).join('');
  el('links').replaceChildren(makeButton(tr('目标 A 原图','Target A image'),()=>switchMode('history',0)),
    makeButton(tr('报警 B 原图','Alarm B image'),()=>switchMode('history',selected.history.length-1)),
    makeButton(tr('逆动作落点','Inverse endpoint'),()=>switchMode('inverse',selected.inverse.length)),
    makeButton(tr('reset 落点','Reset endpoint'),()=>switchMode('reset',1)));
  display();
}
function display(){
  const f=frames[step], pos=f.p, dest=selected.history[0].p;
  for(const id of ['mapStep','rgbStep']){
    const s=el(id);s.max=frames.length-1;s.value=step;s.nextElementSibling.textContent=(step+1)+' / '+frames.length;
  }
  el('rgb').style.display=f.image?'block':'none';el('missing').hidden=Boolean(f.image);
  if(f.image && el('rgb').dataset.frame!==f.image){
    el('rgb').dataset.frame=f.image;el('rgb').src=replay.media[f.image];
  }else if(!f.image){
    el('rgb').removeAttribute('src');delete el('rgb').dataset.frame;
  }
  if(f.tick!=null){
    const gap=f.cameraGap;
    el('source').textContent=tr('回退实采 · H1 前视','Measured rollback · H1 front camera');
    el('sourceNote').textContent=tr('仿真步 ','Simulation step ')+f.tick;
    if(gap>1){
      el('source').textContent=tr('起始帧 · 相机位置有偏差','Start frame · camera position mismatch');
      el('sourceNote').textContent+=tr('。此帧相机与 B 点机器人水平相距 ',' · Camera offset from the robot at B: ')+gap.toFixed(2)+
        tr(' 米。点击“报警 B 原图”可对照历史视角。',' m. Select “Alarm B image” for the historical view.');
    }
  }else if(f.image){
    el('source').textContent=tr('历史采集 · 原始前视','Recorded outbound RGB');
    el('sourceNote').textContent=tr('原采集帧 F','Original capture F')+(mode==='history'?f.index:selected.b)+' · '+tr('H1 原生相机','H1 native camera');
  }else{
    el('source').textContent=tr('未保存前视','RGB unavailable');
    el('sourceNote').textContent=tr('此步的实测位置和朝向见左侧地图。','The floor plan shows the measured position and heading for this step.');
  }
  el('observations').textContent=replay.captureRGB
    ?tr('历史去程使用原采集的前视图。逆动作与直接 reset 使用本轮 H1 相机实采图像，地图箭头表示机器人朝向。','Outbound frames use the original camera recordings. Inverse and reset frames use the H1 camera recordings from this run. The map arrow shows the robot heading.')
    :tr('历史去程展示原生相机的实测画面。两组回退记录了机器人位姿。','Outbound frames come from the recorded native camera. Both return arms recorded robot poses.');
  const actionNames=[['停止','Stop'],['前进','Forward'],['左转','Turn left'],['右转','Turn right'],['后退','Step backward']];
  let caption=mode==='history'?'F'+f.index:tr('回退起点 B','Return start B');
  if(mode!=='history'&&step>0) caption=step===frames.length-1?tr('实测末态','Measured endpoint'):tr('逆动作 ','Inverse action ')+f.index;
  if(f.action!=null)caption+=' · '+tr(...actionNames[f.action]);
  el('action').textContent=caption;
  el('pose').innerHTML='<span>XYZ <strong>'+pos.slice(0,3).map(x=>x.toFixed(3)).join(', ')+' m</strong></span><span>'+tr('朝向','Heading')+' <strong>'+pos[3].toFixed(1)+'°</strong></span>';
  const distance=Math.hypot(pos[0]-dest[0],pos[1]-dest[1]);
  const angle=Math.abs(((pos[3]-dest[3]+540)%360)-180);
  el('relative').textContent=tr('当前距 A ','Distance to A ')+distance.toFixed(3)+' m　·　'+tr('与 A 的朝向差 ','Heading difference from A ')+angle.toFixed(1)+'°';
  el('prev').disabled=step===0;el('next').disabled=step===frames.length-1;
  el('play').textContent=timer?tr('暂停','Pause'):tr('播放','Play');
  drawMap();
}
function jump(n){step=Math.max(0,Math.min(frames.length-1,n));display();}
function fit(preset){
  const g=replay.maps[selected.scene];
  let xmin,xmax,ymin,ymax;
  if(preset==='full'){
    xmin=g.low[0];xmax=xmin+g.width*g.resolution;ymax=g.high[1];ymin=ymax-g.height*g.resolution;
  }else{
    const points=[...selected.history,...selected.inverse,selected.reset].map(f=>f.p);
    if(visible.after)points.push(...selected.after);
    xmin=Math.min(...points.map(p=>p[0]))-.55;xmax=Math.max(...points.map(p=>p[0]))+.55;
    ymin=Math.min(...points.map(p=>p[1]))-.55;ymax=Math.max(...points.map(p=>p[1]))+.55;
  }
  view={x:(xmin+xmax)/2,y:(ymin+ymax)/2,scale:Math.min((W-60)/(xmax-xmin),(H-48)/(ymax-ymin))};
}
function screen(p){return [W/2+(p[0]-view.x)*view.scale,H/2-(p[1]-view.y)*view.scale];}
function project(p){return screen(p).map(n=>n.toFixed(2)).join(',');}
function drawMap(){
  const g=replay.maps[selected.scene], v=view, width=Number(el('width').value);
  const origin=screen([g.low[0],g.high[1]]);
  let svg='<image href="'+g.image+'" x="'+origin[0]+'" y="'+origin[1]+'" width="'+g.width*g.resolution*v.scale+'" height="'+g.height*g.resolution*v.scale+'" preserveAspectRatio="none"/>';
  function line(arr,k,dash,opacity=1){
    if(!visible[k]||arr.length<2)return;
    svg+='<polyline data-track="'+k+'" points="'+arr.map(project).join(' ')+'" fill="none" stroke="'+colors[k]+'" stroke-opacity="'+opacity+'" stroke-linejoin="round" stroke-linecap="round" stroke-width="'+width+'" '+(dash?'stroke-dasharray="'+dash+'"':'')+'/>';
  }
  const a=selected.history[0].p,b=selected.history.at(-1).p,iEnd=selected.inverse.at(-1).p,rEnd=selected.reset.p;
  line(selected.history.map(f=>f.p),'history',null,mode==='history'?.38:1);
  line(selected.after,'after','4 6');
  line([selected.starts.inverse?.p||b,...selected.inverse.map(f=>f.p)],'inverse',null,mode==='inverse'?.43:1);
  line([selected.starts.reset?.p||b,rEnd],'reset','8 7');
  if(mode!=='reset')line(frames.slice(0,step+1).map(f=>f.p),mode);
  if(visible.nodes){
    for(const n of selected.nodes){
      if(n.f>selected.b&&!visible.after)continue;
      const [x,y]=screen(n.p);svg+='<circle cx="'+x+'" cy="'+y+'" r="5" fill="white" stroke="#515463" stroke-width="2"><title>'+n.id+' · F'+n.f+'</title></circle>';
    }
  }
  function marker(p,s,text,color,dx,dy){
    const [x,y]=screen(p);
    svg+='<g transform="translate('+x+' '+y+')" fill="'+color+'">'+s+'<text x="'+dx+'" y="'+dy+'" font-size="13" font-weight="bold" paint-order="stroke" stroke="white" stroke-width="3">'+text+'</text></g>';
  }
  marker(a,'<circle r="7" fill="white" stroke="#173d49" stroke-width="2"/>','A','#173d49',-16,-12);
  marker(b,'<rect x="-5" y="-5" width="10" height="10" stroke="white" stroke-width="1.5"/>','B','#35464c',8,-8);
  if(visible.inverse)marker(iEnd,'<path d="M0 -6L6 0 0 6 -6 0Z" stroke="white"/>','',colors.inverse,0,0);
  if(visible.reset)marker(rEnd,'<path d="M-5 0H5M0 -5V5" fill="none" stroke="'+colors.reset+'" stroke-width="3"/>','',colors.reset,0,0);
  const p=frames[step].p, [x,y]=screen(p);
  svg+='<g data-current transform="translate('+x+' '+y+')"><circle r="4.5" fill="#142d36" stroke="white" stroke-width="1.6"/>';
  if(visible.heading)svg+='<g data-direction transform="rotate('+(-p[3])+')"><path d="M6 0H26 M20 -5L27 0 20 5" fill="none" stroke="white" stroke-width="5"/><path d="M6 0H26 M20 -5L27 0 20 5" fill="none" stroke="#172f36" stroke-width="2.6"/></g>';
  svg+='</g>';
  const max=90/v.scale,unit=Math.pow(10,Math.floor(Math.log10(max))),len=([5,2,1].find(f=>f*unit<=max)||1)*unit;
  svg+='<g transform="translate(16 389)"><path d="M0 -4V0H'+len*v.scale+'V-4" stroke="#253d3d" fill="none" stroke-width="2"/><text y="-8" font-size="12" fill="#19342c" paint-order="stroke" stroke="white" stroke-width="3">'+Number(len.toPrecision(3))+' m</text></g>';
  map.innerHTML=svg;
}
function zoom(from,to,mult){
  const g=replay.maps[selected.scene], prior=view.scale;
  const floor=Math.min(W/(g.width*g.resolution),H/(g.height*g.resolution));
  const scale=Math.max(floor/3,Math.min(Math.max(floor*100,800),prior*mult));
  view.x+=(from[0]-W/2)/prior-(to[0]-W/2)/scale;
  view.y-=(from[1]-H/2)/prior-(to[1]-H/2)/scale;
  view.scale=scale;drawMap();
}
function cursor(e){
  const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(map.getScreenCTM().inverse());return [p.x,p.y];
}
const pointers=new Map();
function gesture(){
  const [a,b]=[...pointers.values()];
  return b?{p:[(a[0]+b[0])/2,(a[1]+b[1])/2],d:Math.hypot(a[0]-b[0],a[1]-b[1])}:{p:a,d:0};
}
map.addEventListener('wheel',e=>{e.preventDefault();const p=cursor(e);zoom(p,p,Math.exp(-Math.max(-300,Math.min(300,e.deltaY))*.002));},{passive:false});
map.onpointerdown=e=>{map.setPointerCapture(e.pointerId);pointers.set(e.pointerId,cursor(e));};
map.onpointermove=e=>{
  if(!pointers.has(e.pointerId))return;
  const old=gesture();pointers.set(e.pointerId,cursor(e));const next=gesture();
  zoom(old.p,next.p,old.d>0&&next.d>0?next.d/old.d:1);
};
map.onpointerup=map.onpointercancel=map.onlostpointercapture=e=>pointers.delete(e.pointerId);
el('plus').onclick=()=>zoom([W/2,H/2],[W/2,H/2],1.5);
el('minus').onclick=()=>zoom([W/2,H/2],[W/2,H/2],1/1.5);
el('fit').onclick=()=>{fit('routes');drawMap();};el('full').onclick=()=>{fit('full');drawMap();};
el('width').oninput=e=>{el('widthVal').textContent=e.target.value+' px';drawMap();};
for(const id of ['rgbStep','mapStep'])el(id).oninput=e=>{stop();jump(Number(e.target.value));};
el('prev').onclick=()=>{stop();jump(step-1);};el('next').onclick=()=>{stop();jump(step+1);};
el('play').onclick=()=>{
  if(timer){stop();return;}
  if(step===frames.length-1)jump(0);
  timer=setInterval(()=>{if(step>=frames.length-1){stop();return;}jump(step+1);},300);
  el('play').textContent=tr('暂停','Pause');
};
el('cases').onchange=e=>selectCase(e.target.value);
el('lang').onchange=e=>{language=e.target.value;renderPanel();};
setFrames();fit('routes');renderPanel();
