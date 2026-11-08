'use strict';
const $=id=>document.getElementById(id), DATA=JSON.parse($('data').textContent);
const initialUI=$('app').outerHTML;
const clone=value=>JSON.parse(JSON.stringify(value));
const escapeHTML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const now=()=>new Date().toISOString();
const uid=()=>globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
let state=JSON.parse($('annotations').textContent), caseIndex=0,frameIndex=0,requestedFrame=0,epoch=0,ready=false;
let images=[],imageCache=new Map(),selectedId=null,undoStack=[],timer=null,playing=false,dirty=false,visible=[];
let zoom=1,pan=[0,0],mapHits=[],pointer=null;
const current=()=>DATA.cases[caseIndex], row=()=>current().frames[frameIndex];
const marks=()=>state.cases[current().episode_id].marks;
const sortedMarks=()=>[...marks()].sort((a,b)=>a.frame-b.frame);
const storageKey='crossing-annotation-v1:'+DATA.dataset_id+':'+state.document_id;
function validState(s){
 if(s?.schema!=='crossing-human-annotations-v1'||s.dataset_id!==DATA.dataset_id||s.document_id!==state.document_id)return false;
 const ids=new Set();
 for(const c of DATA.cases){
  const entry=s.cases?.[c.episode_id];if(!entry||!Array.isArray(entry.marks)||typeof entry.completed!=='boolean')return false;
  const seen=new Set();
  for(const m of entry.marks){const f=c.frames.find(f=>f.frame===m.frame);if(!f||f.rgb_reused||!['crossing','wrong_choice'].includes(m.type)||m.episode_id!==c.episode_id||m.seed!==2||ids.has(m.id)||seen.has(m.frame)||JSON.stringify(m.position)!==JSON.stringify(f.position)||m.image_sha256!==f.image_sha256)return false;ids.add(m.id);seen.add(m.frame)}
 }
 return true;
}
let recovered=false;
try{const draft=JSON.parse(localStorage.getItem(storageKey)||'null');if(draft&&validState(draft)&&draft.updated_at>state.updated_at){state=draft;dirty=true;recovered=true}}catch(e){}
const mapImages={};
for(const [scene,m] of Object.entries(DATA.maps)){const im=new Image();im.onload=()=>{if(current().scene===scene&&ready)drawMap()};im.src=m.image;mapImages[scene]=im}
function notify(text,error=false){$('notice').textContent=text;$('notice').className=error?'error':''}
function stop(){playing=false;clearTimeout(timer);timer=null;$('play').textContent='▶ 播放'}
function remember(){state.resume={episode_id:current().episode_id,frame:frameIndex}}
function stash(){remember();try{localStorage.setItem(storageKey,JSON.stringify(state));$('storage-status').textContent=dirty?'已自动暂存 · 有修改尚未下载，请保存 HTML。':'已自动暂存；最终请上传下载的 HTML 文件。'}catch(e){$('storage-status').textContent='本机自动暂存不可用，请及时保存 HTML。'}}
function changed(message){state.updated_at=now();dirty=true;stash();renderMarks();renderProgress();notify(message)}
function schedule(){clearTimeout(timer);if(playing&&ready)timer=setTimeout(()=>{if(frameIndex>=current().frames.length-1){stop();return}setFrame(frameIndex+1)},1000/Number($('speed').value))}
function enableMarking(){for(const id of ['mark-crossing','mark-error'])$(id).disabled=!ready||row().rgb_reused}
function getImage(n){if(imageCache.has(n))return imageCache.get(n);const im=new Image();im.src=images[n];imageCache.set(n,im);if(imageCache.size>8)imageCache.delete(imageCache.keys().next().value);return im}
function setFrame(n){
 if(!Number.isFinite(n))return;
 const target=Math.max(0,Math.min(current().frames.length-1,Math.round(n))),ticket=++epoch,eid=current().episode_id;
 requestedFrame=target;ready=false;selectedId=null;renderMarks();enableMarking();$('loading').hidden=false;
 const im=getImage(target);
 function commit(){
  if(ticket!==epoch||eid!==current().episode_id)return;
  frameIndex=target;ready=true;$('rgb').src=images[target];$('rgb').dataset.frame=String(row().frame);$('rgb').dataset.episodeId=eid;
  $('loading').hidden=true;for(const id of ['rgb-slider','map-slider','frame-input'])$(id).value=String(target);
  $('frame-status').textContent=`帧 ${row().frame} / ${current().frames.length-1}`;
  $('rgb-caption').textContent=`${(row().video_time_s).toFixed(2)} 秒`+(row().rgb_reused?' · 沿用上一观测，不能标注':row().terminal?' · 终止观测':' · 原始观测');
  const matching=marks().find(m=>m.frame===row().frame);selectedId=matching?.id||null;
  enableMarking();drawMap();renderMarks();remember();schedule();
 }
 if(im.complete&&im.naturalWidth)commit();else{im.onload=commit;im.onerror=()=>{if(ticket===epoch){stop();$('loading').textContent='画面载入失败';notify('当前画面未能载入，不能标注。',true)}}}
}
function mapTransform(){const g=DATA.maps[current().scene].geometry,s=Math.min(920/g.width,680/g.height),ox=(960-g.width*s)/2,oy=(720-g.height*s)/2;return p=>{const x=ox+(p[0]-g.low[0])/g.resolution*s,y=oy+(g.high[1]-p[1])/g.resolution*s;return[(x-480)*zoom+480+pan[0],(y-360)*zoom+360+pan[1]]}}
function drawMap(){
 if(!ready)return;const c=current(),cv=$('map'),ctx=cv.getContext('2d'),m=DATA.maps[c.scene],im=mapImages[c.scene];if(!im.complete||!im.naturalWidth)return;
 const g=m.geometry,s=Math.min(920/g.width,680/g.height),ox=(960-g.width*s)/2,oy=(720-g.height*s)/2,xy=mapTransform();
 ctx.clearRect(0,0,960,720);ctx.fillStyle='#f7f9fc';ctx.fillRect(0,0,960,720);ctx.save();ctx.translate(480+pan[0],360+pan[1]);ctx.scale(zoom,zoom);ctx.translate(-480,-360);ctx.drawImage(im,ox,oy,g.width*s,g.height*s);ctx.restore();
 function line(points,color,width,dash=[]){if(points.length<2)return;ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.lineJoin='round';ctx.lineCap='round';ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(...xy(p)):ctx.moveTo(...xy(p)));ctx.stroke();ctx.setLineDash([])}
 line(c.frames.map(f=>f.position),'#3b6da45c',3);line(c.reference_path,'#178064',4,[9,5]);line(c.frames.slice(0,frameIndex+1).map(f=>f.position),'#3b6da4',4);
 function dot(p,color,r){ctx.beginPath();ctx.arc(...xy(p),r,0,2*Math.PI);ctx.fillStyle=color;ctx.fill();ctx.strokeStyle='white';ctx.lineWidth=2;ctx.stroke()}
 function label(p,text,color){const q=xy(p);ctx.font='bold 15px ReviewChinese, sans-serif';ctx.strokeStyle='white';ctx.lineWidth=4;ctx.strokeText(text,q[0]+12,q[1]-10);ctx.fillStyle=color;ctx.fillText(text,q[0]+12,q[1]-10)}
 dot(c.frames[0].position,'#64748b',5);label(c.frames[0].position,'起点','#526477');dot(c.reference_path[c.reference_path.length-1],'#178064',5);label(c.reference_path[c.reference_path.length-1],'目标','#178064');
 mapHits=[];sortedMarks().forEach((m,i)=>{const color=m.type==='wrong_choice'?'#d75a13':'#2166db';if(m.id===selectedId){ctx.beginPath();ctx.arc(...xy(m.position),15,0,2*Math.PI);ctx.strokeStyle=color;ctx.lineWidth=3;ctx.stroke()}dot(m.position,color,9);label(m.position,String(i+1),color);mapHits.push({id:m.id,point:xy(m.position),frame:m.frame})});
 dot(row().position,'#7441c6',5);cv.dataset.frame=String(row().frame);cv.dataset.episodeId=c.episode_id;cv.dataset.position=JSON.stringify(row().position);cv.dataset.markerCount=String(marks().length);cv.dataset.currentPixel=JSON.stringify(xy(row().position));
 $('map-caption').textContent=`帧 ${row().frame} · (${row().position[0].toFixed(2)}, ${row().position[1].toFixed(2)}) m`;
}
function updateOptions(){
 const f=$('filter').value;visible=DATA.cases.map((c,i)=>({c,i})).filter(({c})=>f==='all'||f===c.group||f==='pending'&&!state.cases[c.episode_id].completed||f==='complete'&&state.cases[c.episode_id].completed).map(x=>x.i);
 // Keep the current task accessible when its completion status changes under a filter.
 const options=visible.includes(caseIndex)?visible:[caseIndex,...visible];
 $('case-select').innerHTML=options.map(i=>{const c=DATA.cases[i],s=state.cases[c.episode_id];return`<option value="${i}">${String(i+1).padStart(2,'0')} · ${c.episode_id} · ${c.group==='failure'?'失败':'成功'}${s.completed?' · ✓ 已完成':''} · ${s.marks.length} 点</option>`}).join('');$('case-select').value=String(caseIndex);
 $('prev-case').disabled=!visible.some(i=>i<caseIndex);$('next-case').disabled=!visible.some(i=>i>caseIndex);
}
function renderProgress(){const all=Object.values(state.cases);$('progress').textContent=`已完成 ${all.filter(c=>c.completed).length} / ${DATA.cases.length}`;$('total-marks').textContent=`${all.reduce((n,c)=>n+c.marks.length,0)} 个标注点`;updateOptions()}
function renderMarks(){
 const list=sortedMarks();$('empty').hidden=!!list.length;$('mark-table').hidden=!list.length;
 $('marks').innerHTML=list.map((m,i)=>`<tr data-id="${m.id}" class="${selectedId===m.id?'active':''}"><td>${i+1}</td><td><button data-jump="${m.id}">帧 ${m.frame} · ${m.video_time_s.toFixed(2)} 秒</button></td><td class="${m.type==='wrong_choice'?'type-error':'type-crossing'}">${m.type==='wrong_choice'?'错误选择 Crossing':'Crossing'}</td><td>${m.position[0].toFixed(3)}, ${m.position[1].toFixed(3)}</td><td><button class="danger" data-delete="${m.id}">删除</button></td></tr>`).join('');
 const selected=list.find(m=>m.id===selectedId);$('selected-label').textContent=selected?`已选中 #${list.indexOf(selected)+1} · 帧 ${selected.frame} · ${selected.type==='wrong_choice'?'错误选择 Crossing':'Crossing'}`:'点击地图标注点或下方条目，可以选中并跳回该帧。';
 $('delete-selected').disabled=!selected;$('change-type').disabled=!selected;$('change-type').textContent=selected?.type==='wrong_choice'?'改为普通 Crossing':'改为错误选择';$('undo-delete').disabled=!undoStack.length;
 $('annotation-summary').textContent=`${list.length} 个 Crossing，其中 ${list.filter(m=>m.type==='wrong_choice').length} 个错误选择`;
 $('completed').checked=state.cases[current().episode_id].completed;
}
function selectCase(n,target=0){
 stop();epoch++;caseIndex=Math.max(0,Math.min(DATA.cases.length-1,n));selectedId=null;zoom=1;pan=[0,0];imageCache.clear();
 images=JSON.parse($('media-'+current().episode_id).textContent);const c=current();
 $('instruction').textContent=c.instruction_zh||c.instruction;$('case-meta').textContent=`任务 ${caseIndex+1} / ${DATA.cases.length} · ${c.episode_id} · seed2 ${c.group==='failure'?'失败（'+c.failed_seeds.length+' 个 seed 失败）':'成功'} · ${c.frames.length} 帧`;
 for(const id of ['rgb-slider','map-slider','frame-input'])$(id).max=String(c.frames.length-1);document.querySelectorAll('.last-frame').forEach(el=>el.textContent=`末帧 ${c.frames.length-1}`);
 updateOptions();renderMarks();setFrame(target);
}
function mark(type){
 stop();if(!ready||row().rgb_reused){notify('请等待有效观测帧载入后再标注。',true);return}
 let m=marks().find(m=>m.frame===row().frame);
 if(m){if(m.type===type){selectedId=m.id;renderMarks();drawMap();notify('这一帧已经标注，无需重复添加。');return}m.type=type;m.updated_at=now()}
 else{const f=row();m={id:uid(),episode_id:current().episode_id,scene:current().scene,seed:2,frame:f.frame,action_index:f.action_index,video_time_s:f.video_time_s,position:clone(f.position),heading:null,heading_source:'not_recorded',image_sha256:f.image_sha256,type,created_at:now(),updated_at:now()};marks().push(m)}
 selectedId=m.id;changed(`已标注帧 ${m.frame}：${type==='wrong_choice'?'错误选择 Crossing':'Crossing'}。`);drawMap();
}
function jumpToMark(id){const m=marks().find(m=>m.id===id);if(!m)return;stop();setFrame(m.frame)}
function deleteMark(id){const index=marks().findIndex(m=>m.id===id);if(index<0)return;stop();const [m]=marks().splice(index,1);undoStack.push({episode_id:current().episode_id,mark:clone(m)});selectedId=null;changed(`已删除帧 ${m.frame} 的标注。可点击“撤销删除”恢复。`);drawMap()}
function undoDelete(){
 const item=undoStack[undoStack.length-1];if(!item)return;
 if(state.cases[item.episode_id].marks.some(m=>m.frame===item.mark.frame)){notify('该帧已有新标注，请先删除新标注再恢复旧点。',true);return}
 undoStack.pop();state.cases[item.episode_id].marks.push(item.mark);const i=DATA.cases.findIndex(c=>c.episode_id===item.episode_id);if(!visible.includes(i))$('filter').value='all';selectCase(i,item.mark.frame);changed(`已恢复帧 ${item.mark.frame} 的标注。`);
}
function saveHTML(){
 stop();if(!validState(state)){notify('标注数据校验失败，未导出。请保留当前页面。',true);return}
 remember();const saved=clone(state);saved.document_id=uid();saved.exported_at=now();saved.updated_at=saved.exported_at;
 const json=JSON.stringify(saved).replace(/</g,'\\u003c');
 // Build from the pristine UI and immutable embedded assets, never serialize live image URLs or localStorage.
 const chunks=['<!doctype html>\n<html lang="zh-CN">\n',document.head.outerHTML,'\n<body>\n',initialUI,'\n', $('data').outerHTML,'\n<script id="annotations" type="application/json">',json,'</scr'+'ipt>\n<div id="media" hidden>'];
 for(const child of $('media').children)chunks.push(child.outerHTML,'\n');
 chunks.push('</div>\n',$('controller').outerHTML,'\n</body></html>');
 const blob=new Blob(chunks,{type:'text/html;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='crossing_annotation_69_'+(DATA.instruction_language==='zh-CN'?'zh_':'')+saved.exported_at.replace(/[:.]/g,'-')+'.html';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
 dirty=false;stash();$('storage-status').textContent='已生成含最新标注的 HTML，请确认下载完成并保留文件。';notify('保存文件已开始下载。重新打开该文件可继续标注，也可将它上传服务器。');
}
$('marks').onclick=e=>{const del=e.target.closest('[data-delete]'),jump=e.target.closest('[data-jump]');if(del)deleteMark(del.dataset.delete);else if(jump)jumpToMark(jump.dataset.jump)};
$('mark-crossing').onclick=()=>mark('crossing');$('mark-error').onclick=()=>mark('wrong_choice');$('delete-selected').onclick=()=>deleteMark(selectedId);$('undo-delete').onclick=undoDelete;
$('change-type').onclick=()=>{const m=marks().find(m=>m.id===selectedId);if(!m)return;m.type=m.type==='wrong_choice'?'crossing':'wrong_choice';m.updated_at=now();changed('已修改选中点的类型。');drawMap()};
$('completed').onchange=()=>{state.cases[current().episode_id].completed=$('completed').checked;changed($('completed').checked?'本条已标注完成。':'本条已恢复为未完成。')};
$('case-select').onchange=e=>{stash();selectCase(Number(e.target.value))};
function moveCase(direction){const options=visible.filter(i=>direction>0?i>caseIndex:i<caseIndex),n=direction>0?options[0]:options[options.length-1];if(n!==undefined){stash();selectCase(n)}}
$('prev-case').onclick=()=>moveCase(-1);$('next-case').onclick=()=>moveCase(1);
$('filter').onchange=()=>{updateOptions();if(visible.length){selectCase(visible.includes(caseIndex)?caseIndex:visible[0])}else notify('此筛选下没有任务，仍保留当前任务供查看。')};
for(const id of ['rgb-slider','map-slider'])$(id).oninput=e=>{stop();setFrame(Number(e.target.value))};
$('prev-frame').onclick=()=>{stop();setFrame(requestedFrame-1)};$('next-frame').onclick=()=>{stop();setFrame(requestedFrame+1)};
$('jump-frame').onclick=()=>{stop();setFrame(Number($('frame-input').value))};$('frame-input').onkeydown=e=>{if(e.key==='Enter')$('jump-frame').click()};
$('play').onclick=()=>{if(playing){stop();return}playing=true;$('play').textContent='Ⅱ 暂停';if(frameIndex===current().frames.length-1)setFrame(0);else schedule()};$('speed').onchange=()=>{if(playing){clearTimeout(timer);schedule()}};
$('save-html').onclick=saveHTML;
function setZoom(z){zoom=Math.max(1,Math.min(5,z));if(zoom===1)pan=[0,0];drawMap()}
$('zoom-in').onclick=()=>setZoom(zoom*1.4);$('zoom-out').onclick=()=>setZoom(zoom/1.4);$('zoom-reset').onclick=()=>{zoom=1;pan=[0,0];drawMap()};
function canvasPoint(e){const r=$('map').getBoundingClientRect();return[(e.clientX-r.left)*960/r.width,(e.clientY-r.top)*720/r.height]}
$('map').onpointerdown=e=>{const p=canvasPoint(e);pointer={start:p,pan:[...pan],moved:false};$('map').setPointerCapture(e.pointerId)};
$('map').onpointermove=e=>{if(!pointer)return;const p=canvasPoint(e),dx=p[0]-pointer.start[0],dy=p[1]-pointer.start[1];if(Math.hypot(dx,dy)>4)pointer.moved=true;if(pointer.moved){pan=[pointer.pan[0]+dx,pointer.pan[1]+dy];drawMap()}};
$('map').onpointerup=e=>{if(!pointer)return;if(!pointer.moved){const p=canvasPoint(e),hits=mapHits.map(h=>({...h,d:Math.hypot(h.point[0]-p[0],h.point[1]-p[1])})).filter(h=>h.d<20).sort((a,b)=>a.d-b.d);if(hits.length)jumpToMark(hits[0].id)}pointer=null};$('map').onpointercancel=()=>pointer=null;
document.addEventListener('keydown',e=>{const mod=e.ctrlKey||e.metaKey;if(mod&&e.key.toLowerCase()==='s'){e.preventDefault();saveHTML();return}if(/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName))return;if(mod&&e.key.toLowerCase()==='z'){e.preventDefault();undoDelete();return}if(e.altKey||mod)return;const key=e.key.toLowerCase();const action={'arrowleft':'prev-frame','arrowright':'next-frame',' ':'play','c':'mark-crossing','e':'mark-error','delete':'delete-selected'}[key];if(action){e.preventDefault();$(action).click()}});
window.addEventListener('beforeunload',e=>{stash();if(dirty){e.preventDefault();e.returnValue=''}});document.addEventListener('visibilitychange',()=>{if(document.hidden){stop();stash()}});
$('footer').textContent=`69 条任务 · ${DATA.summary.frames} 帧 · 全部画面和地图内嵌，可断网使用 · ${DATA.created_at.slice(0,10)}`;
const resumeIndex=DATA.cases.findIndex(c=>c.episode_id===state.resume?.episode_id);selectCase(resumeIndex<0?0:resumeIndex,state.resume?.frame||0);renderProgress();
if(recovered)notify('已恢复本浏览器自动暂存的标注。请记得下载最新 HTML。');
