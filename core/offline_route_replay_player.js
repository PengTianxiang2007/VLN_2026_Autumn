'use strict';
const $ = id => document.getElementById(id);
const {tasks, maps} = REPLAY;
let task = tasks[0], step = 0, lang = 0, slot = 1, timer = null, atlasURL = '', loadState = 'loading';
const text = (zh, en) => lang ? en : zh;
const labels = {
  branch_core:['明确分支','Branch choices'],direction_extension:['方向扩展','Direction errors'],
  older48:['第一批','First batch'],newer56:['第二批','Second batch'],
  missed_turn:['漏掉转弯','Missed turn'],wrong_branch:['选错支路','Wrong branch'],
  wrong_doorway:['选错房门','Wrong doorway'],wrong_open_area_direction:['开放区域方向错误','Wrong open-area direction'],
  wrong_initial_direction:['初始方向错误','Wrong initial direction'],high:['高','High'],medium:['中','Medium']
};
const offsets = [null,0,45,90,135,-180,-135,-90,-45];
const fixedLabels = Array.from(document.querySelectorAll('[data-en]'), el => [el,el.textContent,el.dataset.en]);
const lastStep = () => task.robot.length - 1;
function putAttrs(el, attrs) {
  for (const [name,val] of Object.entries(attrs)) el.setAttribute(name,val);
}
function xy(position) {
  const g = maps[task.scene];
  return [(position[0]-g.low[0])/g.resolution,(g.high[1]-position[1])/g.resolution];
}
let symbolScale = 1;
function drawRoutes() {
  const g = maps[task.scene];
  const actual = task.robot.map(xy), reference = task.reference.map(xy);
  const all = actual.concat(reference), xs = all.map(p=>p[0]), ys = all.map(p=>p[1]);
  const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  const side = Math.max(xmax-xmin,ymax-ymin,4/g.resolution)+2.3/g.resolution;
  const left = (xmin+xmax-side)/2, top = (ymin+ymax-side)/2;
  symbolScale = side/450;
  $('map').setAttribute('viewBox',[left,top,side,side].join(' '));
  putAttrs($('floor'),{href:'maps/'+task.scene+'.png',width:g.width,height:g.height});
  $('actualLine').setAttribute('points',actual.map(p=>p.join(',')).join(' '));
  $('refLine').setAttribute('points',reference.map(p=>p.join(',')).join(' '));
  const r = 4*symbolScale, end = actual[actual.length-1], goal = reference[reference.length-1];
  putAttrs($('end'),{cx:end[0],cy:end[1],r,'stroke-width':symbolScale});
  putAttrs($('goal'),{x:goal[0]-r,y:goal[1]-r,width:2*r,height:2*r,'stroke-width':symbolScale});
  const x = left+side*.04, y = top+side*.95, length = 1/g.resolution;
  $('bar').setAttribute('d','M '+x+' '+(y-2*symbolScale)+' v '+(4*symbolScale)+' m 0 '+(-2*symbolScale)+' h '+length+' m 0 '+(-2*symbolScale)+' v '+(4*symbolScale));
  putAttrs($('scaleText'),{x,y:y-5*symbolScale,'font-size':12*symbolScale});
}
function setLayers() {
  $('actualLayer').style.display = $('actual').checked ? '' : 'none';
  $('refLayer').style.display = $('ref').checked ? '' : 'none';
}
function slots() {
  return {front:[0],'180':[2,1,8],'360':[1,2,3,4,5,6,7,8]}[$('mode').value];
}
function viewName(i) {
  if (i===0) return text('原生前视','Native front');
  const a = offsets[i];
  if (!a) return text('正前','Forward')+' · 0°';
  if (a===-180) return text('正后','Rear')+' · 180°';
  return (a>0 ? text('向左','Left') : text('向右','Right'))+' '+Math.abs(a)+'°';
}
function tile(el,i) {
  el.style.backgroundPosition = ((i%3)*50)+'% '+(Math.floor(i/3)*50)+'%';
  el.style.backgroundImage = loadState==='ready' ? 'url("'+atlasURL+'")' : 'none';
}
function showViews() {
  const list = slots();
  if (!list.includes(slot)) slot = list.includes(1) ? 1 : list[0];
  tile($('focus'),slot);
  $('focus').setAttribute('aria-label',viewName(slot));
  $('viewCaption').textContent = viewName(slot);
  const thumb = $('thumbs'); thumb.replaceChildren();
  thumb.style.setProperty('--n',list.length===8 ? 4 : list.length);
  if(list.length>1) for (const i of list) {
    const button = document.createElement('button');
    button.className = 'tile'; button.title = viewName(i);
    button.setAttribute('aria-label',button.title); button.setAttribute('aria-pressed',String(slot===i));
    tile(button,i);
    const label = document.createElement('span');
    label.textContent = (offsets[i]>0?'+':'')+offsets[i]+'°';
    button.append(label); button.onclick = () => {slot=i; showViews();};
    thumb.append(button);
  }
  $('load').textContent = loadState==='loading' ? text('载入观测…','Loading observation…') :
    loadState==='error' ? text('观测图加载失败','Observation failed to load') : '';
}
function syncAtlas() {
  const url = 'frames/'+task.id+'/'+String(step).padStart(4,'0')+'.webp';
  if(url!==atlasURL) {
    atlasURL=url; loadState='loading';
    const image=new Image();
    image.onload=()=>{if(atlasURL===url){loadState='ready';showViews();}};
    image.onerror=()=>{if(atlasURL===url){loadState='error';stop();showViews();}};
    image.src=url;
  }
  showViews();
}
function setStep(value) {
  step=Math.max(0,Math.min(lastStep(),Number(value)));
  for(const id of ['mapStep','imageStep']) {$(id).max=lastStep(); $(id).value=step;}
  const robot=task.robot[step], camera=task.camera[step], [x,y]=xy(robot);
  $('robot').setAttribute('transform','translate('+x+' '+y+') rotate('+(-robot[3])+') scale('+symbolScale+')');
  $('map').dataset.step=step;
  $('counter').textContent=text('步数 ','Step ')+step+' / '+lastStep();
  $('elapsed').textContent=task.seconds[step].toFixed(1)+' s';
  for(const [prefix,pose] of [['robot',robot],['cam',camera]]) {
    $(prefix+'XYZ').textContent=pose.slice(0,3).map(n=>n.toFixed(2)).join(', ');
    $(prefix+'Heading').textContent=pose[3].toFixed(1)+'°';
  }
  $('quats').textContent=[text('机器人','Robot')+'　'+robot.slice(4).map(n=>n.toFixed(4)).join(', '),
    text('原生相机','Native camera')+'　'+camera.slice(4).map(n=>n.toFixed(4)).join(', ')].join('\n');
  $('prev').disabled=step===0; $('next').disabled=step===lastStep(); syncAtlas();
}
function playLabel() {
  $('play').textContent=timer===null ? text('▶ 播放','▶ Play') : text('Ⅱ 暂停','Ⅱ Pause');
}
function stop() {clearInterval(timer); timer=null; playLabel();}
function jump(value) {stop();setStep(value);}
function showEvents() {
  const el=$('events');el.replaceChildren();
  task.events.forEach((event,i)=>{
    const row=document.createElement('div');row.className='event';
    const name=document.createElement('strong');
    name.textContent=text('事件 ','Event ')+(i+1)+' · '+text('区间 ','interval ')+event.interval.join('–');
    row.append(name);
    for(const [title,target] of [[text('决策步','Decision'),event.anchor],[text('确认步','Confirmed'),event.confirm]]) {
      const button=document.createElement('button');button.textContent=title+' '+target;
      button.onclick=()=>jump(target);row.append(button);
    }
    el.append(row);
  });
}
function localize() {
  document.documentElement.lang=lang?'en':'zh-CN';
  for(const [el,zh,en] of fixedLabels) el.textContent=text(zh,en);
  document.title=text('选路错误轨迹回放','Route-choice replay');
  for(const [id,zh,en] of [['mapStep','地图步数','Map step'],['imageStep','观测步数','Observation step'],['map','俯视地图','Floor plan'],['mode','观测模式','Observation mode']])
    $(id).setAttribute('aria-label',text(zh,en));
  document.querySelector('nav').setAttribute('aria-label',text('回放','Playback'));
  $('instruction').textContent=task.instruction[lang]; $('reason').textContent=task.reason[lang];
  for(const id of ['group','batch','subtype']) $(id).textContent=labels[task[id]][lang];
  $('confidence').textContent=text('置信度 · ','Confidence · ')+labels[task.confidence][lang];
  playLabel();showEvents();setStep(step);
}
tasks.forEach((t,i)=>$('task').add(new Option(String(i+1).padStart(2,'0')+' / '+tasks.length+'　'+t.id,t.id)));
$('task').onchange=()=>{stop();task=tasks.find(t=>t.id===$('task').value);step=0;drawRoutes();localize();};
$('language').onchange=()=>{lang=Number($('language').value);localize();};
$('actual').onchange=$('ref').onchange=setLayers;
$('mapStep').oninput=$('imageStep').oninput=e=>jump(e.target.value);
$('prev').onclick=()=>jump(step-1);$('next').onclick=()=>jump(step+1);
$('mode').onchange=showViews;
$('play').onclick=()=>{
  if(timer!==null) {stop();return;}
  if(step===lastStep()) setStep(0);
  timer=setInterval(()=>{if(loadState==='ready'){if(step===lastStep()) stop(); else setStep(step+1);}},400);
  playLabel();
};
drawRoutes();setLayers();localize();
