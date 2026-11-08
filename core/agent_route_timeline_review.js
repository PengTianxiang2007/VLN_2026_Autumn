'use strict';
const DATA=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DIR={front:'正前方',front_left:'左前方',front_right:'右前方',left:'左侧',right:'右侧',back:'后方',back_left:'左后方',back_right:'右后方',unclear:'方向不明确',unknown:'不确定'};
const ACTION={FORWARD:'前进',LEFT:'左转',RIGHT:'右转',STOP:'停止',WAIT:'等待',TERMINAL:'终止记录'},CONF={high:'高',medium:'中',low:'低'};
let caseIndex=0,frameIndex=0,requestedFrame=0,english=false,timer=null,epoch=0,imageCache=new Map(),review={};
const mapImages={},current=()=>DATA.cases[caseIndex],answer=n=>current().calls[n][english?'answer':'answer_zh'],original=n=>current().calls[n].answer;
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
  $('rgb-caption').innerHTML=`<b>${at?'当前就是模型作判断的Crossing画面。':`当前正在查看${phase}。`}</b> <span class="muted">${input?'此帧是模型输入之一，保留原PNG。':'此帧仅供完整回放，没有发送给外部模型。'}${row.rgb_reused?' 原记录注明RGB沿用上一观测。':''}</span>`;
  const prior=target?c.frames[target-1]:null;
  $('action-note').textContent=(prior?`上一帧记录的动作：${ACTION[prior.action]||prior.action}；`:'初始观测；')+`当前帧记录的动作：${ACTION[row.action]||row.action}。`;
  document.querySelectorAll('.input-view').forEach(b=>b.classList.toggle('active',Number(b.dataset.frame)===target));drawMap();
  for(const next of [target-1,target+1])if(c.frames[next])getImage(c.frames[next].image_key);
 }
 if(image.complete&&image.naturalWidth)commit();else image.addEventListener('load',commit,{once:true});
}
function renderDetails(){
 const c=current(),inv=answer(1),a=answer(2),raw=original(2),conflict=raw.excluded_branch_ids.includes(raw.selected_branch_id),valid=c.calls[2].validated;
 $('case-title').textContent=`样本 ${caseIndex+1}/10 · ${c.review.scene} / ${c.review.crossing_id}`;
 $('task').textContent=english?c.instruction:c.instruction_zh;
 $('case-meta').textContent=`任务 ${c.review.episode_id} · 原始录像 ${c.frames.length} 帧 · Crossing判断帧 F${String(c.checkpoint_frame).padStart(4,'0')} · C与P相距 ${c.crossing_distance_m.toFixed(2)} m`;
 $('decision').className='card decision '+(valid?'':'invalid');
 $('decision').innerHTML=`<div class="decision-title">模型最终选择：${esc(branchName(raw.selected_branch_id))}</div><div class="outcomes"><span><b>识别支路：</b>${inv.branches.map(b=>b.id).join('、')}</span><span class="bad"><b>判断走错：</b>${esc(raw.wrong_branch_id)}</span><span><b>排除：</b>${esc(raw.excluded_branch_ids.join('、'))}</span><span class="good"><b>选择：</b>${esc(raw.selected_branch_id)}</span></div><p>${esc(a.route_description)}</p>${conflict?'<p class="bad"><b>原始回答矛盾：模型已经排除 '+esc(raw.selected_branch_id)+'，却又选择了它。此条无效，展示保留原答。</b></p>':''}`;
 $('branch-title').textContent=`③ 第一次调用：模型识别 ${inv.branches.length} 条支路`;$('inventory-summary').textContent=inv.view_summary;
 $('branches').innerHTML=inv.branches.map(b=>{const chosen=raw.selected_branch_id===b.id,excluded=raw.excluded_branch_ids.includes(b.id);return `<article class="branch ${chosen?'chosen':''} ${excluded?'wrong':''} ${chosen&&excluded?'conflict':''}" data-branch="${b.id}" data-selected="${chosen}" data-excluded="${excluded}"><h3>${b.id} · ${DIR[b.direction]}</h3>${badges(b)}<p><b>入口标志：</b>${esc(b.landmark)}</p><p><b>模型认为通向：</b>${esc(b.destination_hypothesis)}</p><div>${evidence(b.evidence_ids)}</div></article>`}).join('');
 const incoming=inv.branches.filter(b=>b.incoming==='yes').map(b=>b.id);$('incoming-note').textContent=`第一次标为来路：${incoming.join('、')||'未明确标出'}。该旧版不要求自动排除来路；图中仅标记原回答的实际排除项。`;
 $('wrong-detail').innerHTML=`<p class="bad"><b>${esc(branchName(raw.wrong_branch_id))}</b></p><p>${esc(a.error_reason)}</p><div>${evidence(raw.wrong_branch_evidence_ids)}</div>`;
 $('task-evidence').innerHTML='<ul>'+a.instruction_evidence.map(t=>'<li>'+esc(t)+'</li>').join('')+'</ul>';
 $('selection-detail').innerHTML=`<p class="${conflict?'bad':'good'}"><b>${esc(branchName(raw.selected_branch_id))}</b></p><p>${esc(a.route_description)}</p><div>${evidence(raw.selection_evidence_ids)}</div><p>模型自报置信度：${CONF[raw.confidence]}</p>`;
 $('uncertainties').innerHTML='<h3>模型指出的不确定性</h3><ul>'+[...inv.uncertainties.map(t=>'第一次：'+t),...a.uncertainties.map(t=>'第二次：'+t)].map(t=>'<li>'+esc(t)+'</li>').join('')+'</ul>';
 $('protocol').textContent=(valid?'两次回答通过原协议校验，语义正确性尚未确认。':'第二次回答无效：选择了已排除的支路。')+' 第二次完整携带第一次实际支路清单：'+(c.inventory_transfer_verified?'已核验一致。':'未通过。')+' 本次只重做展示，没有新模型调用。';
 $('raw').textContent=JSON.stringify({first:c.calls[1].answer,second:c.calls[2].answer,original_status:c.status},null,2);
 $('reference-text').innerHTML=`<p>历史期望路线：${esc(c.review.expected_route)}</p><p>历史错误路线：${esc(c.review.wrong_route)}</p><p>既有归因：${esc(c.review.historical_rationale)}</p>`;
 bindEvidence();
}
function selectCase(n){
 stop();epoch++;caseIndex=Math.max(0,Math.min(DATA.cases.length-1,n));imageCache=new Map();const c=current();$('case-select').value=String(caseIndex);
 $('inputs').innerHTML=c.images.map(im=>`<button class="input-view ${im.frame===c.checkpoint_frame?'checkpoint':''}" data-frame="${im.frame}"><img src="${imageURL(im.sha256)}" alt="输入帧${im.id}"><b>${im.id}${im.frame===c.checkpoint_frame?' · Crossing':''}</b><br>${im.phase==='checkpoint_context'?'第一次输入':'第二次新增'}</button>`).join('');
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
$('stats').innerHTML=[`10条样本`,`原20次响应 · 无新推理`,`识别 ${DATA.summary.branch_count} 条支路`,`原协议有效 ${DATA.summary.valid_samples}/10`,`完整回放 ${DATA.summary.replay_frames} 帧`,`语义正确率：待复核`].map(t=>'<span class="stat">'+esc(t)+'</span>').join('');
$('case-select').innerHTML=DATA.cases.map((c,i)=>`<option value="${i}">${String(i+1).padStart(2,'0')} · ${c.review.episode_id} · 选 ${c.calls[2].answer.selected_branch_id}${c.calls[2].validated?'':'（原答矛盾）'}</option>`).join('');
$('case-select').onchange=e=>selectCase(Number(e.target.value));$('prev-case').onclick=()=>selectCase(caseIndex-1);$('next-case').onclick=()=>selectCase(caseIndex+1);
$('language').onclick=()=>{english=!english;$('language').textContent=english?'切换中文译文':'切换英文原文';renderDetails()};
for(const id of ['rgb-slider','map-slider'])$(id).oninput=e=>{stop();setFrame(Number(e.target.value))};
$('jump-crossing').onclick=jumpCrossing;$('jump-crossing-detail').onclick=()=>{jumpCrossing();$('replay').scrollIntoView({block:'start'})};$('jump-wrong-end').onclick=()=>{stop();setFrame(current().wrong_end_frame)};
$('prev-frame').onclick=()=>{stop();setFrame(requestedFrame-1)};$('next-frame').onclick=()=>{stop();setFrame(requestedFrame+1)};
$('play').onclick=()=>{if(timer){stop();return}if(frameIndex===current().frames.length-1)setFrame(0);$('play').textContent='Ⅱ 暂停';timer=setInterval(()=>{if(requestedFrame>=current().frames.length-1){stop();return}setFrame(requestedFrame+1)},1000/Number($('speed').value))};$('speed').onchange=()=>{if(timer){stop();$('play').click()}};
$('show-reference').onchange=drawMap;$('review-note').oninput=saveReview;$('review-verdict').onchange=saveReview;
function zoom(src,title){$('zoom-image').src=src;$('zoom-title').textContent=title;$('zoom').showModal()}
$('rgb').onclick=()=>zoom($('rgb').src,`${current().sample_id} · 当前回放 F${String(frameIndex).padStart(4,'0')}`);$('checkpoint-image').onclick=()=>zoom($('checkpoint-image').src,`${current().sample_id} · 固定Crossing帧`);$('close-zoom').onclick=()=>$('zoom').close();$('zoom').onclick=e=>{if(e.target===$('zoom'))$('zoom').close()};
$('export-review').onclick=()=>{saveReview();const blob=new Blob([JSON.stringify({run_hash:DATA.run_hash,exported_at:new Date().toISOString(),cases:DATA.cases.map(c=>({sample_id:c.sample_id,...(review[c.sample_id]||{verdict:'pending',note:''})}))},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='crossing_v001_timeline_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$('footer').textContent=`生成于 ${DATA.exported_at} · 图片、地图、译文和字体全部内嵌，断网可用。回放附加帧采用JPEG；原模型输入PNG保持原样。`;
selectCase(0);
