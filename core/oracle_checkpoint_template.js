/* Full evidence timelines. A restore is a discontinuity, never a navigation edge. */
const $ = id => document.getElementById(id);
const armNames = {streamvln:'走错 → 复位 → StreamVLN 再走', oracle_actions:'走错 → 复位 → Oracle 动作接管', trunk:'仅查看原始走错过程'};
let ci = 0, arm = 'streamvln', idx = 0, timer = null, playing = false, bg = new Image();
const current = () => B.cases[ci];
const timeline = () => current().timelines[arm];
const rows = () => timeline().frames;
const frame = () => rows()[idx];
const event = kind => timeline().events.find(e => e.kind === kind);
const branch = () => current().arms[arm];
const isAfterRestore = () => timeline().restore_index !== null && idx >= timeline().restore_index;
const coordinate = p => p.slice(0, 2).map(n => n.toFixed(3)).join(', ');

for (const id of ['radii', 'diagnostics']) $(id).closest('details').hidden = true;
for (const id of ['showPrior','showCurrent','visitedOnly','full','labels','ranges']) $(id).parentElement.hidden = true;
$('eventFilter').hidden = $('eventCount').hidden = true;
$('filters').innerHTML = '<option>全部十条任务</option>';
const counts = B.counts;
$('runInfo').textContent = `${counts.valid_pairs} 条有效配对 · ${counts.untriggered} 条未触发 · ${counts.technical_failures} 条恢复技术失败`;
$('auditInfo').textContent = '完整记录首次错误与复位；位置、朝向、策略记忆和预算均回滚到存档。Oracle 恢复后用真实动作选路。';
$('stats').innerHTML = [[counts.requested_cases,'固定任务'],[counts.valid_pairs,'有效配对'],
 [`${counts.paired_local_correct.streamvln}/${counts.valid_pairs} → ${counts.paired_local_correct.oracle_actions}/${counts.valid_pairs}`,'局部分支选对'],
 [`${counts.paired_final_success.streamvln}/${counts.valid_pairs} → ${counts.paired_final_success.oracle_actions}/${counts.valid_pairs}`,'最终成功'],
 [counts.untriggered,'未触发'],[counts.technical_failures,'恢复技术失败']].map(([n,label])=>`<div class="metric"><b>${n}</b><span>${label}</span></div>`).join('');
$('mapMode').textContent = '灰线：参考路线；红线：从存档到首次错误确认的实际片段；橙色虚线：复位关系；绿色：StreamVLN 实际行走；紫色：Oracle 实际动作。';
document.querySelector('.legend').textContent = '蓝 C：地图先验　红 P：真实存档　红 E：首次错误　橙虚线：复位（非行走）';
document.querySelector('.comparisonHint').textContent = '每个恢复组的回放都包含完整首次走错片段。复位前的红色错误轨迹会保留，复位后的实际路线从 P 附近重新开始。';
$('footer').textContent = '固定十条、seed 2；只重建已保存日志，未重跑导航。两组独立恢复；共用错误触发片段不代表全实验的墙钟执行顺序。共同站姿稳定不是 PhysX 位级恢复。';
$('caseStats').closest('details').querySelector('summary').textContent = '按实际回放顺序排列的审阅事件';
document.querySelector('#cases+p').textContent = '七条可切换两种恢复方式；未触发和恢复技术失败仅展示实际已有记录。';
const scope = [...document.querySelectorAll('details')].find(d=>d.querySelector('summary')?.textContent==='评分口径与输入边界');
scope.innerHTML = '<summary>实验口径与输入边界</summary><p>先保存真实存档，继续走到实际错误，再分别从同一存档恢复。位置、朝向、策略记忆、随机状态和预算一起回滚；首次错误后的记忆不带入恢复组。每组只恢复一次。</p><p>Oracle 可看参考路线，恢复后仅给前进、左转、右转。跨过正确分支后交回 StreamVLN，不再干预。局部选对与最终任务成功分别计算。两个未触发任务不具有独立恢复结果；技术失败任务没有合格复位观测。</p>';

function stop() { clearTimeout(timer); timer = null; playing = false; $('play').textContent = '顺序回放'; }
function seek(i) { idx = Math.max(0, Math.min(rows().length - 1, i)); render(); }
function jumpEvent(kind) { stop(); const e = event(kind); if (e) seek(e.index); }
function jump(action, source = frame()?.source_arm) {
  const i = rows().findIndex(f=>f.source_arm === source && f.action_index >= action);
  stop(); if (i >= 0) seek(i);
}
function schedule() {
  const key = timeline().events.some(e=>e.index === idx && ['error','restore','choice'].includes(e.kind));
  timer = setTimeout(()=>{ if (idx >= rows().length - 1) {stop();return;} seek(idx+1); schedule(); }, key ? 2200 : +$('speed').value);
}
function play() {
  if (playing) { stop(); return; }
  if (idx === rows().length - 1) seek(0);
  playing = true; $('play').textContent = '暂停'; schedule();
}
function reviewAt(f) {
  return [...current().arms[f.source_arm].reviews].reverse().find(r=>r.action <= f.action_index);
}
function labelAt(f) {
  const local = branch().result?.local_choice;
  if (f.phase === 'restore') return `复位发生：动作 ${current().actual_error.action_index} → ${f.action_index}，回到实际存档`;
  if (f.phase === 'error') return arm === 'trunk' ? (current().technical_failure ? '首次确认走错 · 随后复位技术失败，无有效恢复观测' : '首次确认走错 · 原始主干记录至此') : '首次确认走错 · 下一帧显示本组复位';
  if (f.phase === 'trunk' && !current().actual_error) return '未触发恢复 · 原始 StreamVLN 行走';
  if (f.phase === 'trunk') return current().checkpoint && f.action_index >= current().checkpoint.action_index ? '已保存存档 · StreamVLN 继续走向首次错误' : '原始 StreamVLN 行走 · 尚未保存存档';
  if (f.phase === 'retry') return local && f.action_index >= local.action_index ? (local.choice === 'wrong' ? '恢复后再次选错 · StreamVLN 继续到自然结束' : '恢复后自主选对 · StreamVLN 继续到自然结束') : '恢复后 · StreamVLN 重新选路';
  if (f.phase === 'oracle') return f.action_index === local.action_index ? 'Oracle 已通过正确分支 · 此帧交回 StreamVLN' : '恢复后 · Oracle 正在执行真实前进／转向动作';
  return 'Oracle 已交回 · StreamVLN 自主继续';
}
function addEventButton(parent, label, index, kind) {
  const b = document.createElement('button'); b.textContent = label; b.dataset.index = index; b.dataset.kind = kind;
  b.onclick = ()=>{ stop(); seek(index); }; parent.append(b); return b;
}
function renderEvidence() {
  const box = $('restoreEvidence'); box.replaceChildren(); box.hidden = timeline().restore_index === null;
  if (box.hidden) return;
  const before = rows()[event('error').index], after = rows()[timeline().restore_index];
  const title = document.createElement('strong'); title.textContent = '复位证据 · 点击两张真实画面可跳转'; box.append(title);
  const pair = document.createElement('div'); pair.className = 'restorePair';
  for (const [f,label,i] of [[before,'共同触发：首次走错',event('error').index],[after,'本组独立复位后',timeline().restore_index]]) {
    if (pair.children.length) { const arrow = document.createElement('div'); arrow.className = 'restoreArrow'; arrow.textContent = '↪'; pair.append(arrow); }
    const b = addEventButton(pair, '', i, f.phase), im = document.createElement('img'); im.src = B.images[f.image_id]; im.alt = label;
    b.append(im, document.createTextNode(`${label} · 动作 ${f.action_index}\n坐标 (${coordinate(f.position)})`));
  }
  box.append(pair);
  const p = document.createElement('p');
  p.textContent = `动作号 ${before.action_index} → ${after.action_index}。复位设置为原存档姿态，图右为稳定后的真实观测；没有回走动作或中间视频帧。两组各自独立恢复，共享左侧首次错误记录。`;
  box.append(p);
}
function choose(i, requestedArm = 'streamvln', target = null) {
  stop(); ci = i; arm = current().paired ? requestedArm : 'trunk'; idx = 0;
  $('title').textContent = current().episode_id;
  $('instruction').textContent = current().instruction;
  $('cases').replaceChildren();
  B.cases.forEach((c,j)=>{ const b = document.createElement('button'); b.textContent = c.episode_id+'\n'+(c.paired?'有效配对':c.technical_failure?'恢复技术失败':'未触发'); b.className = j===ci?'active':''; b.onclick=()=>choose(j,arm==='trunk'?'streamvln':arm); $('cases').append(b); });
  $('armChoices').replaceChildren();
  for (const ar of ['streamvln','oracle_actions','trunk']) {
    const b = document.createElement('button'), r = current().arms[ar].result;
    b.className = 'runChoice'+(ar===arm?' active':''); b.dataset.arm = ar;
    b.textContent = armNames[ar] + '\n' + (ar==='trunk'?'共同触发记录，不是第三个实验组':current().paired?`局部${r.local_choice.choice==='correct'?'选对':'选错'} · 最终${r.metrics.success?'成功':'失败'}`:'没有有效恢复轨迹');
    b.disabled = ar !== 'trunk' && !current().paired;
    b.onclick = ()=>{ const f=frame(); choose(ci,ar,{source:f.source_arm==='trunk'?'trunk':'restored', action:f.action_index, restore:f.phase==='restore', terminal:f.terminal}); };
    $('armChoices').append(b);
  }
  $('runDescription').textContent = current().paired ? '完整回放包含：原始行走、首次错误、复位观测、恢复后续走。切换组时按阶段与日志动作编号对齐。' : current().technical_failure?'本条首次复位稳定后的朝向误差超限，未产生有效恢复组；不展示虚构复位画面。':'本条没有确认错误并触发恢复；只展示一次真实主干行走。';
  $('timelineEvents').replaceChildren();
  timeline().events.forEach(e=>addEventButton($('timelineEvents'), `${e.label} · ${rows()[e.index].action_index}`, e.index, e.kind));
  $('eventList').replaceChildren();
  for (const e of timeline().events) addEventButton($('eventList'), `${e.label} · 回放 ${e.index+1} / 日志动作 ${rows()[e.index].action_index}`,e.index,e.kind).className='event';
  for (const source of arm === 'trunk' ? ['trunk'] : ['trunk',arm]) {
    for (const r of current().arms[source].reviews) {
      const i=rows().findIndex(f=>f.source_arm===source&&f.action_index===r.action);
      if(i<0) continue;
      addEventButton($('eventList'), `${source==='trunk'?'首次行走':'恢复后'} · 动作 ${r.action} · ${r.response?.decision||'未响应'}\n${r.response?.reason||''}`, i, 'review').className='event';
    }
  }
  // All events are ordered by replay index, including duplicate action numbers.
  [...$('eventList').children].sort((a,b)=>+a.dataset.index - +b.dataset.index).forEach(b=>$('eventList').append(b));
  $('priorList').textContent = 'C · 固定地图分歧先验（非本次自动预测）';
  $('currentList').replaceChildren();
  if(event('checkpoint')) addEventButton($('currentList'), 'P · 保存真实位置与朝向 · 动作 '+current().checkpoint.action_index,event('checkpoint').index,'checkpoint');
  else $('currentList').textContent = '没有有效分歧存档';
  $('caseReview').textContent = current().technical_failure?.reason || '每组只复位一次；再次走错只记录判定，之后由原模型自然结束。';
  $('caseStats').textContent = '审阅中的相同动作号按首次行走／复位后区分。';
  $('playError').disabled = timeline().restore_index === null;
  renderEvidence();
  bg = new Image(); bg.onload = draw; bg.src = B.scenes[current().scene].image;
  let selected = event('error')?.index ?? 0;
  if (target && typeof target === 'object') {
    const source = target.source === 'trunk' ? 'trunk' : arm;
    let at = target.restore ? timeline().restore_index : rows().findIndex(f=>f.source_arm===source && f.action_index>=target.action && (!target.terminal || f.terminal));
    if (at !== null && at >= 0) selected = at;
  }
  seek(selected);
}
function render() {
  const f = frame(), r = branch().result, rev = reviewAt(f), restored = isAfterRestore();
  for(const id of ['frame','imageFrame']) { $(id).max = rows().length-1; $(id).value = idx; }
  const text = `回放帧 ${idx+1}/${rows().length} · ${f.source_arm==='trunk'?'首次行走':'复位后'}日志动作 ${f.action_index} · tick ${f.physics_ticks}`;
  $('step').textContent = $('imageStep').textContent = text;
  $('rgb').src = B.images[f.image_id]; $('rgb').alt = labelAt(f);
  $('phaseBanner').textContent = labelAt(f); $('phaseBanner').className = f.phase;
  if (!current().paired && f.phase==='trunk') $('phaseBanner').textContent = current().technical_failure?'仅有恢复失败前的主干记录':'未触发恢复 · 原始 StreamVLN 行走';
  $('state').textContent = labelAt(f);
  if (f.terminal) $('state').textContent += ` · 最终${(r || current().arms.streamvln.result)?.metrics.success?'成功':'失败'}`;
  $('mapCounts').textContent = `${restored?'已复位：红色原错误轨迹保留，当前机器人从存档重新出发':'首次行走：尚未复位'}${current().technical_failure?'；后续复位技术失败':''}`;
  $('answer').textContent = f.phase==='restore' ? JSON.stringify({事件:'复位到真实存档；此条为恢复证据，不是 Oracle 新决策',原始错误动作:current().actual_error.action_index,恢复动作:f.action_index,保存姿态:branch().restore_proof.saved_world_pose,稳定后位置:f.position,策略记忆:'回滚到存档时刻',策略哈希:branch().restore_proof.policy.content_sha256},null,2) : rev?JSON.stringify(rev.response,null,2):'当前没有 Oracle 审阅响应';
  $('inputInfo').textContent = f.image_missing ? `终止记录未保存独立 RGB；此处沿用同组动作 ${f.image_source_action} 的最近真实画面。` : f.phase==='restore'?'本帧取自恢复组实际观测，已核对 restore_proof 的位置与 tick。':'显示实际 Oracle 审阅响应；不是 StreamVLN 隐藏思维。';
  $('selectedEvent').textContent = f.phase==='restore'?'机器人已从错误分支跳回原存档。橙色虚线仅说明复位关系，不能计为实际行走轨迹。':rev?.response?.reason||'尚无审阅。';
  const cp=current().checkpoint;
  $('memory').textContent = !cp || (!restored && f.action_index<cp.action_index) ? '此刻尚未保存有效分歧存档。' : restored?`已恢复动作 ${cp.action_index} 的位置、朝向与策略记忆。首次走错后的记忆已回滚。${arm==='oracle_actions'?'Oracle 动作期间冻结该记忆；交回后恢复模型推理。':''}`:`已于动作 ${cp.action_index} 保存真实存档；此刻尚未复位。`;
  $('history').replaceChildren();
  if (f.phase !== 'restore') for(const h of rev?.request.history||[]) {
    const available = rows().slice(0,idx+1);
    // Match tick as well as action: checkpoint and restored frame share an action ID.
    const hi=available.findIndex(v=>v.action_index===h.action_index&&v.physics_ticks===h.physics_ticks&&v.position.every((n,j)=>n===h.position[j]));
    if(hi<0) continue;
    const b=document.createElement('button'), im=document.createElement('img'); im.src=B.images[rows()[hi].image_id];
    b.append(im,document.createTextNode(`${rows()[hi].source_arm==='trunk'?'首次':'恢复后'} ${h.action_index}`)); b.onclick=()=>{stop();seek(hi);}; $('history').append(b);
  }
  $('actions').textContent = f.phase==='restore'?'复位不对应前进或转向动作。':rev?.response?.decision==='action'?`该审阅随后执行：${({1:'前进',2:'左转',3:'右转'})[rev.response.action]||rev.response.action}`:'详见原始审阅响应。';
  for(const b of $('timelineEvents').children) b.classList.toggle('active',+b.dataset.index===idx);
  try { const n=JSON.parse(localStorage.getItem(noteKey())||'{}'); $('note').value=n.note||''; $('category').value=n.category||''; } catch {}
  draw();
}
function draw() {
  const cv=$('map'), g=B.scenes[current().scene].geometry;
  cv.width=g.width; cv.height=g.height;
  const ctx=cv.getContext('2d'); if(bg.complete&&bg.naturalWidth)ctx.drawImage(bg,0,0,cv.width,cv.height);
  const xy=p=>[(p[0]-g.low[0])/g.resolution,g.height-(p[1]-g.low[1])/g.resolution];
  const unit=Math.max(1,g.width/650);
  function line(ps,color,width=2.6,dashed=false) {
    if(!ps.length)return;
    ctx.save();ctx.strokeStyle=color;ctx.lineWidth=width*unit;ctx.setLineDash(dashed?[7*unit,5*unit]:[]);ctx.beginPath();
    ps.forEach((p,i)=>{const q=xy(p);i?ctx.lineTo(...q):ctx.moveTo(...q);});ctx.stroke();ctx.restore();
  }
  line(current().reference,'#9ca8b5',1.8);
  const visited=rows().slice(0,idx+1), trunk=visited.filter(f=>f.source_arm==='trunk');
  const cp=current().checkpoint, cpAction=cp?.action_index;
  line(trunk.filter(f=>cpAction==null||f.action_index<=cpAction).map(f=>f.position),'#43877b');
  line(trunk.filter(f=>cpAction!=null&&f.action_index>=cpAction).map(f=>f.position),'#dc3b46',3.3);
  const continued=visited.filter(f=>f.source_arm!=='trunk');
  if(arm==='oracle_actions') {
    const hand=branch().result?.local_choice.action_index;
    line(continued.filter(f=>f.action_index<=hand).map(f=>f.position),'#8e42bc',3.4);
    line(continued.filter(f=>f.action_index>=hand).map(f=>f.position),'#159377',3.4);
  } else line(continued.map(f=>f.position),'#159377',3.4);
  if(isAfterRestore()) {
    const from=rows()[event('error').index].position,to=rows()[timeline().restore_index].position;
    line([from,to],'#d58205',3,true);
    const q=xy(to),p=xy(from),angle=Math.atan2(q[1]-p[1],q[0]-p[0]);
    ctx.save();ctx.fillStyle='#d58205';ctx.beginPath();ctx.moveTo(...q);
    for(const theta of [angle-.5,angle+.5])ctx.lineTo(q[0]-14*unit*Math.cos(theta),q[1]-14*unit*Math.sin(theta));
    ctx.closePath();ctx.fill();ctx.font=`bold ${13*unit}px ReviewSans`;ctx.fillText('复位（非行走）',(p[0]+q[0])/2+8*unit,(p[1]+q[1])/2);ctx.restore();
  }
  const cpFrame=event('checkpoint')&&idx>=event('checkpoint').index?rows()[event('checkpoint').index]:null;
  const erFrame=event('error')&&idx>=event('error').index?rows()[event('error').index]:null;
  const prior=current().crossing?.position || current().arms.trunk.reviews[0]?.request.crossing?.position;
  for(const [p,color,label] of [[prior,'#2563eb','C'],[cpFrame?.position,'#dc3545','P'],[erFrame?.position,'#b11e30','E 首错'],[frame().position,'#d28b08','当前']]) {
    if(!p)continue;const q=xy(p);ctx.fillStyle=color;ctx.beginPath();ctx.arc(...q,5*unit,0,2*Math.PI);ctx.fill();ctx.font=`bold ${13*unit}px ReviewSans`;ctx.fillText(label,q[0]+7*unit,q[1]-7*unit);
  }
}
for(const id of ['frame','imageFrame'])$(id).oninput=e=>{stop();seek(+e.target.value);};
$('prev').onclick=()=>{stop();seek(idx-1);}; $('next').onclick=()=>{stop();seek(idx+1);}; $('play').onclick=play;
$('playError').onclick=()=>{stop();seek(Math.max(0,event('error').index-4));play();};
$('speed').onchange=()=>{if(playing){stop();play();}};
document.addEventListener('keydown',e=>{if(['TEXTAREA','INPUT','SELECT'].includes(document.activeElement.tagName))return;if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();stop();seek(idx+(e.key==='ArrowRight'?1:-1));}});
function noteKey(){const f=frame();return `oracle-timeline-v2:${current().episode_id}:${arm}:${f.source_arm}:${f.source_index}`;}
function save(){try{localStorage.setItem(noteKey(),JSON.stringify({note:$('note').value,category:$('category').value}));$('notesStatus').textContent='已本地保存';}catch{$('notesStatus').textContent='浏览器禁止本地保存';}}
$('note').oninput=$('category').onchange=save;
$('export').onclick=()=>{const notes={};for(const k of Object.keys(localStorage))if(k.startsWith('oracle-timeline-v2:'))notes[k]=JSON.parse(localStorage[k]);const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([JSON.stringify(notes,null,2)],{type:'application/json'}));link.download='oracle_timeline_review_notes.json';link.click();URL.revokeObjectURL(link.href);};
window.ORACLE_REVIEW={choose,seek,jump,jumpEvent,stop,state:()=>({ci,arm,idx,frame:frame(),restore_index:timeline().restore_index,events:timeline().events,playing})};
choose(0,'streamvln'); document.fonts.ready.then(draw);
