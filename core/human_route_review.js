'use strict';
const DATA=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DIR={front:'正前方',front_left:'左前方',front_right:'右前方',left:'左侧',right:'右侧',back:'后方',back_left:'左后方',back_right:'右后方',unclear:'方向不明确',unknown:'不确定'};
const ACTION={FORWARD:'前进',LEFT:'左转',RIGHT:'右转',STOP:'停止',WAIT:'等待',TERMINAL:'终止记录'},CONF={high:'高',medium:'中',low:'低'};
let caseIndex=0,frameIndex=0,requestedFrame=0,english=false,timer=null,epoch=0,imageCache=new Map(),review={};
const mapImages={},current=()=>DATA.cases[caseIndex],answer=n=>current().calls[n].display,original=n=>current().calls[n].display;
const imageURL=key=>DATA.images[key],reviewKey='route-v001-timeline-'+DATA.run_hash;
try{review=JSON.parse(localStorage.getItem(reviewKey)||'{}')}catch(e){}
for(const [scene,map] of Object.entries(DATA.maps)){const im=new Image();im.onload=()=>{if(current().review.scene===scene)drawMap()};im.src=map.image;mapImages[scene]=im}
function stop(){if(timer)clearInterval(timer);timer=null;$('play').textContent='▶ 播放'}
function branchName(id){const b=answer(1).branches.find(b=>b.id===id);return b?`${id} · ${DIR[b.direction]} · ${b.landmark}`:id||'未确定'}
function badges(b){const a=original(2);return (a.selected_branch_id===b.id?'<span class="pill good">最终选择</span>':'')+(a.excluded_branch_ids.includes(b.id)?'<span class="pill bad">模型排除</span>':'')+(b.incoming==='yes'?'<span class="pill incoming">第一次标为来路</span>':b.incoming==='unknown'?'<span class="pill incoming">来路属性不确定</span>':'')}
function evidence(ids){return (ids||[]).map(id=>`<button class="evidence-jump" data-frame="${Number(id.slice(1))}">看 ${esc(id)}</button>`).join(' ')}
function bindEvidence(){document.querySelectorAll('.evidence-jump').forEach(b=>b.onclick=()=>{stop();setFrame(Number(b.dataset.frame));$('replay').scrollIntoView({block:'start',behavior:'smooth'})})}
function drawMap(){
 const c=current(),cv=$('map'),ctx=cv.getContext('2d'),m=DATA.maps[c.review.scene],im=mapImages[c.review.scene];if(!im?.complete||!im.naturalWidth)return;
 const g=m.geometry,s=Math.min(616/g.width,452/g.height),ox=(640-g.width*s)/2,oy=(480-g.height*s)/2;
 const xy=p=>[ox+(p[0]-g.low[0])/g.resolution*s,oy+(g.high[1]-p[1])/g.resolution*s];
 ctx.clearRect(0,0,640,480);ctx.fillStyle='#f7f9fb';ctx.fillRect(0,0,640,480);ctx.drawImage(im,ox,oy,g.width*s,g.height*s);
 function line(rows,color,dash=[]){if(rows.length<2)return;ctx.strokeStyle=color;ctx.lineWidth=3;ctx.setLineDash(dash);ctx.beginPath();rows.forEach((r,i)=>{const q=xy(r.position||r);i?ctx.lineTo(...q):ctx.moveTo(...q)});ctx.stroke();ctx.setLineDash([])}
 function dot(p,color,label,r=5){const q=xy(p);ctx.beginPath();ctx.arc(...q,r,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();ctx.strokeStyle='white';ctx.lineWidth=2;ctx.stroke();ctx.font='bold 13px ReviewChinese, sans-serif';ctx.lineWidth=4;ctx.strokeText(label,q[0]+9,q[1]-9);ctx.fillText(label,q[0]+9,q[1]-9)}
 if($('show-reference').checked)line(c.review.reference_path,'#9d78b8',[5,4]);
 const prefix=c.frames.slice(0,frameIndex+1);
 line(prefix.filter(r=>r.frame<=c.checkpoint_frame),'#15966a');
 line(prefix.filter(r=>r.frame>=c.checkpoint_frame&&r.frame<=c.wrong_end_frame),'#d23d4c');
 line(prefix.filter(r=>r.frame>=c.wrong_end_frame),'#788399');
 dot(c.review.crossing.position,'#1165bc','C',6);dot(c.review.checkpoint_position,'#c27407','P',5);
 const row=c.frames[frameIndex];dot(row.position,'#7441c6',`F${String(frameIndex).padStart(4,'0')}`,6);
 cv.dataset.frame=String(frameIndex);cv.dataset.sampleId=c.sample_id;cv.dataset.prefixFrames=String(prefix.length);cv.dataset.position=JSON.stringify(row.position);
 $('map-caption').textContent=`地图同步到 F${String(frameIndex).padStart(4,'0')} · 当前位置 (${row.position[0].toFixed(2)}, ${row.position[1].toFixed(2)}) m`;
}
function getImage(key){if(imageCache.has(key))return imageCache.get(key);const im=new Image();im.src=imageURL(key);imageCache.set(key,im);if(imageCache.size>18)imageCache.delete(imageCache.keys().next().value);return im}
function setFrame(n){
 const c=current(),target=Math.max(0,Math.min(c.frames.length-1,Math.round(n))),ticket=++epoch,sid=c.sample_id;requestedFrame=target;
 const row=c.frames[target],image=getImage(row.image_key);
 function commit(){if(ticket!==epoch||sid!==current().sample_id)return;frameIndex=target;const rgb=$('rgb');rgb.src=imageURL(row.image_key);rgb.dataset.frame=String(target);rgb.dataset.sampleId=sid;rgb.dataset.imageKey=row.image_key;
  for(const id of ['rgb-slider','map-slider'])$(id).value=String(target);
  const at=target===c.checkpoint_frame,phase=at?'Crossing判断帧':target<c.checkpoint_frame?'判断前历史':target<=c.wrong_end_frame?'错误尝试片段':'原录像后续';
  $('frame-status').className='frame-tag '+(at?'at-crossing':target>c.checkpoint_frame&&target<=c.wrong_end_frame?'attempt':'');
  $('frame-status').textContent=`F${String(target).padStart(4,'0')} / F${String(c.frames.length-1).padStart(4,'0')} · ${phase}`;
  const input=c.images.find(im=>im.frame===target);
  $('rgb-caption').innerHTML=`<b>${at?'当前就是模型作判断的Crossing画面。':`当前正在查看${phase}。`}</b> <span class="muted">${input?(input.phase==='wrong_attempt'&&!c.calls[2].answer?'此错误帧未发送给模型，仅供复核。':'此帧是模型输入之一，保留原PNG。'):'此帧仅供完整回放，没有发送给外部模型。'}${row.rgb_reused?' 原记录注明RGB沿用上一观测。':''}</span>`;
  const prior=target?c.frames[target-1]:null;
  $('action-note').textContent=(prior?`上一帧记录的动作：${ACTION[prior.action]||prior.action}；`:'初始观测；')+`当前帧记录的动作：${ACTION[row.action]||row.action}。`;
  document.querySelectorAll('.input-view').forEach(b=>b.classList.toggle('active',Number(b.dataset.frame)===target));drawMap();
  for(const next of [target-1,target+1])if(c.frames[next])getImage(c.frames[next].image_key);
 }
 if(image.complete&&image.naturalWidth)commit();else image.addEventListener('load',commit,{once:true});
}
function decisionText(c){const a=c.calls[2].answer;return !a?'未调用第二轮':a.status==='insufficient_evidence'?'证据不足 · 未选择分支':a.selected_branch_id||'未选择分支'}
function renderDetails(){
 const c=current(),inv=answer(1),a=answer(2),raw=original(2),valid=c.calls[1].validated&&c.calls[2].validated;
 $('case-title').textContent=`样本 ${caseIndex+1}/${DATA.cases.length} · ${c.review.scene}`;
 $('task').textContent=english?c.instruction:c.instruction_zh;
 $('case-meta').textContent=`任务 ${c.review.episode_id} · 原录像 ${c.frames.length} 帧 · 人工标定与判断帧 F${String(c.checkpoint_frame).padStart(4,'0')}（C/P重合）`;
 $('decision').className='card decision '+(valid?'':'invalid');
 $('decision').innerHTML=`<div class="decision-title">模型最终结果：${esc(decisionText(c))}</div><div class="outcomes"><span>识别支路：${esc(inv.branches.map(b=>b.id).join('、')||'无')}</span><span class="bad">判断走错：${esc(raw.wrong_branch_id||'未确定')}</span><span>排除：${esc(raw.excluded_branch_ids.join('、')||'无')}</span><span class="good">选择：${esc(raw.selected_branch_id||'无')}</span></div><p>${esc(a.route_description||'原答未提供路线描述')}</p><p>${valid?'原协议校验通过；不代表选择正确。':'原协议校验未通过：'+esc(c.status.error||c.status.phase)}</p>`;
 $('branch-title').textContent=`③ 第一次调用：模型识别 ${inv.branches.length} 条支路`;
 $('inventory-summary').textContent=inv.view_summary||'未提供视图描述';
 $('branches').innerHTML=inv.branches.map(b=>{const chosen=raw.selected_branch_id===b.id,excluded=raw.excluded_branch_ids.includes(b.id);return `<article class="branch ${chosen?'chosen':''} ${excluded?'wrong':''} ${chosen&&excluded?'conflict':''}" data-branch="${esc(b.id)}" data-selected="${chosen}" data-excluded="${excluded}"><h3>${esc(b.id)} · ${esc(DIR[b.direction]||b.direction)}</h3>${badges(b)}<p><b>入口标志：</b>${esc(b.landmark)}</p><p><b>模型认为通向：</b>${esc(b.destination_hypothesis)}</p>${evidence(b.evidence_ids)}</article>`}).join('');
 $('incoming-note').textContent='来路按第一次原答展示；本协议只要求排除已识别的错误支路。模型描述保留英文原文，界面与任务提供中文。';
 $('wrong-detail').innerHTML=`<p class="bad"><b>${esc(branchName(raw.wrong_branch_id))}</b></p><p>${esc(a.error_reason||'未提供错误原因')}</p>${evidence(raw.wrong_branch_evidence_ids)}`;
 $('task-evidence').innerHTML='<ul>'+a.instruction_evidence.map(t=>'<li>'+esc(t)+'</li>').join('')+'</ul>';
 $('selection-detail').innerHTML=`<p><b>${esc(decisionText(c))}</b></p><p>${esc(a.route_description||'原答未提供路线描述')}</p>${evidence(raw.selection_evidence_ids)}<p>模型自报置信度：${esc(CONF[raw.confidence]||'未提供')}</p>`;
 $('uncertainties').innerHTML='<h3>模型指出的不确定性（原文）</h3><ul>'+[...inv.uncertainties.map(t=>'第一次：'+t),...a.uncertainties.map(t=>'第二次：'+t)].map(t=>'<li>'+esc(t)+'</li>').join('')+'</ul>';
 $('protocol').textContent=`第一轮：${c.calls[1].validated?'校验通过':'校验失败'}；第二轮：${!c.calls[2].answer?'未调用':c.calls[2].validated?'校验通过':'校验失败'}。完整清单传递：${c.inventory_transfer_verified?'哈希与内容核验一致':'未调用第二轮，不适用'}。本次导出没有模型调用。`;
 $('raw').textContent=JSON.stringify({first:c.calls[1].answer,second:c.calls[2].answer,first_raw:c.calls[1].raw_content,second_raw:c.calls[2].raw_content,original_status:c.status},null,2);
 $('reference-text').textContent='人工标注事件：'+c.review.crossing_id+'；标记为错误选路。正确分支尚待人工复核。地图上 C/P 同为人工标注帧，没有额外预测存档点。';
 bindEvidence();
}
function selectCase(n){
 stop();epoch++;caseIndex=Math.max(0,Math.min(DATA.cases.length-1,n));imageCache=new Map();const c=current();$('case-select').value=String(caseIndex);
 $('inputs').innerHTML=c.images.map(im=>`<button class="input-view ${im.frame===c.checkpoint_frame?'checkpoint':''}" data-frame="${im.frame}"><img src="${imageURL(im.sha256)}" alt="输入帧${im.id}"><b>${im.id}${im.frame===c.checkpoint_frame?' · Crossing':''}</b><br>${im.phase==='checkpoint_context'?'第一次输入':c.calls[2].answer?'第二次新增':'未发送 · 复核用'}</button>`).join('');
 document.querySelectorAll('.input-view').forEach(b=>b.onclick=()=>{stop();setFrame(Number(b.dataset.frame))});
 for(const id of ['rgb-slider','map-slider'])$(id).max=String(c.frames.length-1);
 document.querySelectorAll('.timeline-track').forEach(t=>t.style.setProperty('--cp-percent',`${100*c.checkpoint_frame/(c.frames.length-1)}%`));
 document.querySelectorAll('.crossing-mark').forEach(t=>t.textContent=`蓝线：Crossing F${String(c.checkpoint_frame).padStart(4,'0')}`);
 document.querySelectorAll('.last-frame').forEach(t=>t.textContent=`末帧 ${c.frames.length-1}`);
 const cp=c.images.find(im=>im.frame===c.checkpoint_frame);$('checkpoint-image').src=imageURL(cp.sha256);$('checkpoint-image').dataset.frame=String(cp.frame);$('checkpoint-note').textContent=`${cp.id} · 这就是两次独立调用共同指定的当前观测帧。`;
 $('jump-crossing').textContent=`◎ 回到Crossing · F${String(c.checkpoint_frame).padStart(4,'0')}`;
 $('review-verdict').value=review[c.sample_id]?.verdict||'pending';$('review-note').value=review[c.sample_id]?.note||'';
 renderDetails();setFrame(c.checkpoint_frame);
}
function jumpCrossing(){stop();setFrame(current().checkpoint_frame)}
function saveReview(){review[current().sample_id]={verdict:$('review-verdict').value,note:$('review-note').value,viewed_frame:frameIndex,updated_at:new Date().toISOString()};try{localStorage.setItem(reviewKey,JSON.stringify(review));$('save-status').textContent='已在本机浏览器保存。'}catch(e){$('save-status').textContent='本机存储不可用，请导出JSON。'}}
$('stats').innerHTML=[`${DATA.cases.length}条手工样本`,`${DATA.summary.response_count}次原响应 · 无新推理`,`明确选择 ${DATA.summary.selected}条`,`证据不足 ${DATA.summary.insufficient}条`,`第二轮未调用 ${DATA.summary.no_second}条`,`协议有效 ${DATA.summary.valid_samples}/${DATA.cases.length}`,'语义正确率：待复核'].map(t=>'<span class="stat">'+esc(t)+'</span>').join('');
$('case-select').innerHTML=DATA.cases.map((c,i)=>`<option value="${i}">${String(i+1).padStart(2,'0')} · ${c.review.episode_id} · ${esc(decisionText(c))}${c.calls[2].validated?'':'（校验未通过）'}</option>`).join('');
$('case-select').onchange=e=>selectCase(Number(e.target.value));$('prev-case').onclick=()=>selectCase(caseIndex-1);$('next-case').onclick=()=>selectCase(caseIndex+1);
$('language').onclick=()=>{english=!english;$('language').textContent=english?'切换任务中文':'切换任务英文';renderDetails()};
for(const id of ['rgb-slider','map-slider'])$(id).oninput=e=>{stop();setFrame(Number(e.target.value))};
$('jump-crossing').onclick=jumpCrossing;$('jump-crossing-detail').onclick=()=>{jumpCrossing();$('replay').scrollIntoView({block:'start'})};$('jump-wrong-end').onclick=()=>{stop();setFrame(current().wrong_end_frame)};
$('prev-frame').onclick=()=>{stop();setFrame(requestedFrame-1)};$('next-frame').onclick=()=>{stop();setFrame(requestedFrame+1)};
$('play').onclick=()=>{if(timer){stop();return}if(frameIndex===current().frames.length-1)setFrame(0);$('play').textContent='Ⅱ 暂停';timer=setInterval(()=>{if(requestedFrame>=current().frames.length-1){stop();return}setFrame(requestedFrame+1)},1000/Number($('speed').value))};$('speed').onchange=()=>{if(timer){stop();$('play').click()}};
$('show-reference').onchange=drawMap;$('review-note').oninput=saveReview;$('review-verdict').onchange=saveReview;
function zoom(src,title){$('zoom-image').src=src;$('zoom-title').textContent=title;$('zoom').showModal()}
$('rgb').onclick=()=>zoom($('rgb').src,`${current().sample_id} · 当前回放 F${String(frameIndex).padStart(4,'0')}`);$('checkpoint-image').onclick=()=>zoom($('checkpoint-image').src,`${current().sample_id} · 固定Crossing帧`);$('close-zoom').onclick=()=>$('zoom').close();$('zoom').onclick=e=>{if(e.target===$('zoom'))$('zoom').close()};
$('export-review').onclick=()=>{saveReview();const blob=new Blob([JSON.stringify({run_hash:DATA.run_hash,exported_at:new Date().toISOString(),cases:DATA.cases.map(c=>({sample_id:c.sample_id,...(review[c.sample_id]||{verdict:'pending',note:''})}))},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='crossing_v001_timeline_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$('footer').textContent=`生成于 ${DATA.exported_at} · 图片、地图和字体全部内嵌，断网可用。回放保留数据集WebP；关键帧PNG保持原样。`;
selectCase(0);
