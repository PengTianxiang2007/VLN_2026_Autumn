'use strict';
const DATA=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DIR={front:'正前方',front_left:'左前方',left:'左侧',back_left:'左后方',back:'后方',back_right:'右后方',right:'右侧',front_right:'右前方',unclear:'方向不明确'};
const ANG={front:0,front_left:45,left:90,back_left:135,back:180,back_right:225,right:270,front_right:315};
const COVER={complete:'覆盖完整',partial:'部分覆盖',insufficient:'观测不足'},CONF={high:'高',medium:'中',low:'低'};
let index=0,english=false,view='V0',activeBranch=null,hist=3,timer=null,review={};
const reviewKey='crossing-panorama-review-'+DATA.run_hash;
try{review=JSON.parse(localStorage.getItem(reviewKey)||'{}')}catch(e){}
const current=()=>DATA.cases[index],original=stage=>current().calls[String(stage)]?.answer,
      answer=stage=>english?original(stage):(current().translation.calls[String(stage)]?.answer_zh||original(stage));
const src=im=>DATA.images[im.image_key],pano=()=>current().images.filter(im=>im.phase==='crossing_panorama'),history=()=>current().images.filter(im=>im.phase!=='crossing_panorama');
const evidence=ids=>'<span class="evidence">图像依据：'+esc((ids||[]).join('、')||'未给出')+'</span>';
const incomingId=()=>original(2)?original(2).incoming_branch_id:original(1)?.incoming_branch_id;
function badges(id){const a=original(2),b=original(1),suffix=a?.excluded_branch_ids?.includes(id)?' · 排除':'';return (a?.selected_branch_id===id?'<span class="pill good">最终选择</span>':'')+(a?.wrong_branch_id===id?'<span class="pill bad">原错误路'+suffix+'</span>':'')+(a?.incoming_branch_id===id?'<span class="pill incoming">原来路'+suffix+'</span>':b?.incoming_branch_id===id?'<span class="pill incoming">第一次认为是来路'+(a?' · 第二次未确认':'')+'</span>':'')}
function branchName(id){if(!id)return '无法确定';const b=answer(1)?.branches?.find(b=>b.id===id);return b?`${id} · ${DIR[b.direction]} · ${b.landmark}`:id}
function drawMap(id,withHistory=false){
 const c=current(),cv=$(id),ctx=cv.getContext('2d'),m=DATA.maps[c.review.scene],im=new Image(),epoch=index;
 im.onload=()=>{if(epoch!==index)return;ctx.clearRect(0,0,cv.width,cv.height);ctx.fillStyle='#f7f9fb';ctx.fillRect(0,0,cv.width,cv.height);
 const g=m.geometry,s=Math.min((cv.width-32)/g.width,(cv.height-32)/g.height),ox=(cv.width-g.width*s)/2,oy=(cv.height-g.height*s)/2;
 ctx.drawImage(im,ox,oy,g.width*s,g.height*s);const xy=p=>[ox+(p[0]-g.low[0])/g.resolution*s,oy+(g.high[1]-p[1])/g.resolution*s];
 function line(points,color,width=3,dash=[]){if(points.length<2)return;ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);points.forEach((p,i)=>{const q=xy(p);i?ctx.lineTo(...q):ctx.moveTo(...q)});ctx.stroke();ctx.setLineDash([])}
 function dot(p,color,label,r=5){const q=xy(p);ctx.beginPath();ctx.arc(...q,r,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();ctx.strokeStyle='white';ctx.lineWidth=2;ctx.stroke();if(label){ctx.font='bold 14px ReviewChinese, sans-serif';ctx.lineWidth=4;ctx.strokeText(label,q[0]+8,q[1]-8);ctx.fillText(label,q[0]+8,q[1]-8)}}
 if($('show-reference').checked)line(c.review.reference_path,'#8755b7',2,[5,4]);
 const t=c.review.trajectory,cut=withHistory?history()[hist].frame:Infinity;
 line(t.filter(p=>p.frame<=c.checkpoint_frame&&p.frame<=cut).map(p=>p.position),'#15966a',3);
 line(t.filter(p=>p.frame>=c.checkpoint_frame&&p.frame<=cut).map(p=>p.position),'#d23d4c',3);
 const C=c.review.panorama_position;dot(c.review.checkpoint_position,'#c27407','P',5);dot(C,'#1165bc','C',7);
 if(withHistory){const target=t.find(p=>p.frame===history()[hist].frame);if(target)dot(target.position,'#6f42c1','当前帧',6)}
 else{const a=original(2),branches=original(1)?.branches||[];const visible=new Set([activeBranch,a?.selected_branch_id]);for(const b of branches){if(!visible.has(b.id)||ANG[b.direction]===undefined)continue;const ang=ANG[b.direction]*Math.PI/180,origin=xy(C),len=b.id===activeBranch?75:58,end=[origin[0]+Math.cos(ang)*len,origin[1]-Math.sin(ang)*len],color=b.id===a?.selected_branch_id?'#139564':b.id===a?.wrong_branch_id?'#d23d4c':b.id===incomingId()?'#68758a':'#007da8';ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=3;ctx.setLineDash([6,4]);ctx.beginPath();ctx.moveTo(...origin);ctx.lineTo(...end);ctx.stroke();ctx.setLineDash([]);const aa=Math.atan2(end[1]-origin[1],end[0]-origin[0]);ctx.beginPath();ctx.moveTo(...end);ctx.lineTo(end[0]-12*Math.cos(aa-.4),end[1]-12*Math.sin(aa-.4));ctx.lineTo(end[0]-12*Math.cos(aa+.4),end[1]-12*Math.sin(aa+.4));ctx.fill();ctx.font='bold 15px ReviewChinese, sans-serif';ctx.strokeStyle='white';ctx.lineWidth=4;ctx.strokeText(b.id,end[0]+5,end[1]-7);ctx.fillText(b.id,end[0]+5,end[1]-7)}}
 ctx.fillStyle='#52657b';ctx.font='12px ReviewChinese, sans-serif';ctx.fillText('V0 = 世界 +X →；向左转 = 地图逆时针',12,cv.height-8);
 };im.src=m.image;
}
function setView(id){view=id;const im=pano().find(x=>x.id===id);$('main-image').src=src(im);$('view-caption').innerHTML=`<b>${esc(id)} · ${im.yaw_deg}° · ${DIR[Object.keys(ANG).find(k=>ANG[k]===im.yaw_deg)]}</b>　<span class="muted">固定在C处拍摄，点击放大</span>`;document.querySelectorAll('.view').forEach(el=>el.classList.toggle('active',el.dataset.view===id))}
function focusBranch(id){activeBranch=id;const b=answer(1)?.branches.find(x=>x.id===id);if(!b)return;const cited=new Set(b.panorama_view_ids);document.querySelectorAll('.branch').forEach(el=>el.classList.toggle('active',el.dataset.branch===id));document.querySelectorAll('.view').forEach(el=>el.classList.toggle('cited',cited.has(el.dataset.view)));$('active-branch').innerHTML='<b>正在查看：'+esc(branchName(id))+'</b> '+badges(id)+(original(2)?.selected_branch_id?'':'<span class="muted">（仅查看，不代表模型已选择）</span>');setView(b.panorama_view_ids[0]||'V0');drawMap('map')}
function setHistory(n){hist=Number(n);$('map-slider').value=hist;$('rgb-slider').value=hist;const im=history()[hist];$('history-image').src=src(im);$('history-label').textContent=`${hist+1}/8 · ${im.id} · ${im.phase==='approach_history'?'原来路历史':'错误尝试之后'}`;drawMap('history-map',true);const acts=im.phase==='approach_history'?current().approach_actions:current().attempt_actions;const N={FORWARD:'前进',LEFT:'左转',RIGHT:'右转',STOP:'停止',WAIT:'等待'};$('history-actions').textContent='该帧之前已执行的指令（不保证实际位移）：'+acts.filter(a=>a.frame<im.frame).map(a=>`F${String(a.frame).padStart(4,'0')} ${N[a.action]}`).join(' → ')}
function render(){
 const c=current(),i=answer(1),a=answer(2),o=original(2),valid=c.review_audit.decision_valid_after_empty_route_fix;
 $('case-select').value=index;$('case-title').textContent=`样本 ${index+1}/10 · ${c.review.scene} / ${c.review.crossing_id}`;$('task').textContent=english?c.instruction:c.translation.instruction_zh;
 $('pose-note').textContent=`任务 ${c.review.episode_id} · 全景C与原存档P相距 ${c.review.checkpoint_to_crossing_distance_m.toFixed(2)} m · 原存档帧 F${String(c.checkpoint_frame).padStart(4,'0')} · 两次调用分别输入12 / 16张图片`;
 $('decision').className='card decision '+(o?.status==='selected'?(valid?'':'invalid'):'abstain');
 $('decision').innerHTML=`<div class="decision-title">${o?.status==='selected'?'模型最终选择：'+esc(branchName(o.selected_branch_id)):'模型最终选择：未选择（证据不足）'}</div><div class="outcomes"><span><b>识别支路：</b>${i?.branches?.map(b=>b.id).join('、')||'无有效清单'}</span><span class="bad"><b>错误路：</b>${esc(o?.wrong_branch_id||'不确定')}</span><span class="incoming"><b>原来路：</b>${esc(incomingId()||'不确定')}</span><span><b>排除：</b>${esc(o?.excluded_branch_ids?.join('、')||'未确定')}</span><span><b>选择：</b>${esc(o?.selected_branch_id||'未选择')}</span></div><div style="margin-top:7px">${esc(a?.route_description||(o?.status==='insufficient_evidence'?'模型已给出排除项，但认为剩余支路没有足够证据与任务匹配。':'没有第二次回答'))}</div>${valid?'':'<p class="bad">另有证据引用问题：第二次判定来路时只引用了历史帧，没有引用全景图。该判断需额外复核。</p>'}`;
 $('panos').innerHTML=pano().map(im=>`<button class="view" data-view="${im.id}"><img src="${src(im)}" alt="${im.id} ${im.yaw_deg}度"><span class="small"><b>${im.id} · ${im.yaw_deg}°</b><br>${esc((i?.branches||[]).filter(b=>b.panorama_view_ids.includes(im.id)).map(b=>b.id).join(' / ')||'未被任何支路引用')}</span></button>`).join('');
 document.querySelectorAll('.view').forEach(el=>el.onclick=()=>{setView(el.dataset.view)});
 $('branch-title').textContent=`③ 第一次调用：模型共识别 ${i?.branches?.length||0} 条支路（含原来路）`;$('inventory-summary').textContent=i?.view_summary||'无回答';
 $('branches').innerHTML=(i?.branches||[]).map(b=>`<article tabindex="0" class="branch ${o?.selected_branch_id===b.id?'chosen':''} ${o?.wrong_branch_id===b.id?'wrong':''} ${incomingId()===b.id?'arrival':''}" data-branch="${b.id}"><h3>${b.id} · ${DIR[b.direction]}</h3>${badges(b.id)}<p><b>入口标志：</b>${esc(b.landmark)}</p><p><b>通向哪里：</b>${esc(b.destination_hypothesis)}</p><div>${b.panorama_view_ids.map(id=>`<button data-evidence="${id}">看 ${id}</button>`).join('')}</div>${evidence(b.evidence_ids)}</article>`).join('');
 document.querySelectorAll('.branch').forEach(el=>{el.onclick=e=>{focusBranch(el.dataset.branch);if(e.target.dataset.evidence)setView(e.target.dataset.evidence)};el.onkeydown=e=>{if(e.key==='Enter')focusBranch(el.dataset.branch)}});
 $('inventory-incoming').textContent=`第一次判定的来路：${i?.incoming_branch_id||'不确定'}。${i?.incoming_reason||''}　模型自报覆盖：${COVER[i?.coverage]||'未知'}。`;
 $('wrong-detail').innerHTML=`<p><b>${esc(branchName(o?.wrong_branch_id))}</b></p><p>${esc(a?.error_reason||'无回答')}</p>${evidence(a?.wrong_branch_evidence_ids)}`;
 $('incoming-detail').innerHTML=`<p><b>${esc(branchName(o?.incoming_branch_id))}</b></p><p>${esc(a?.incoming_reason||'无回答')}</p>${evidence(a?.incoming_evidence_ids)}`;
 $('selection-detail').innerHTML=`<p><b class="good">${o?.selected_branch_id?esc(branchName(o.selected_branch_id)):'未选择'}</b></p><p>${esc(a?.route_description||(o?.status==='insufficient_evidence'?'模型未选择路线，因此没有路线描述。':'无回答'))}</p>${evidence(a?.selection_evidence_ids)}<p><b>对应任务语句：</b>${esc(a?.instruction_evidence?.join('；')||'未给出')}</p><p>模型自报置信度：${CONF[a?.confidence]||'无'}</p>`;
 $('uncertainties').innerHTML='<h3>模型指出的不确定性</h3><ul>'+[...(i?.uncertainties||[]).map(t=>'第一次：'+t),...(a?.uncertainties||[]).map(t=>'第二次：'+t)].map(t=>'<li>'+esc(t)+'</li>').join('')+'</ul>';
 $('protocol').textContent='原始运行记录保留：未选择时route_description为空，被原校验器拦截。展示复核已允许未选择时的空描述，未改变任何回答或重跑模型。'+(valid?'复核后本条通过其余协议校验。':'本条还存在来路证据问题：第二次仅引用历史帧，缺少全景引用。')+' 第二次显式携带第一次完整JSON：'+(c.inventory_transfer_verified?'已核对一致':'未执行或未通过')+'。协议通过不等于语义正确。';
 $('raw').textContent=JSON.stringify(c.calls,null,2);
 $('reference-text').innerHTML=`<p>历史参考期望：${esc(c.review.expected_route)}</p><p>历史错误描述：${esc(c.review.wrong_route)}</p><p>既有归因：${esc(c.review.historical_rationale)}</p><p>标注来源状态：${esc(c.review.label_status)}；保留既有来源，未新增独立人工金标准。</p>`;
 $('review-verdict').value=review[c.sample_id]?.verdict||'pending';$('review-note').value=review[c.sample_id]?.note||'';
 activeBranch=o?.selected_branch_id||i?.branches?.[0]?.id||null;setView('V0');if(activeBranch)focusBranch(activeBranch);else drawMap('map');setHistory(3);
}
function select(n){if(timer){clearInterval(timer);timer=null;$('play').textContent='播放'}index=Math.max(0,Math.min(DATA.cases.length-1,n));render()}
function save(){review[current().sample_id]={verdict:$('review-verdict').value,note:$('review-note').value,updated_at:new Date().toISOString()};try{localStorage.setItem(reviewKey,JSON.stringify(review));$('save-status').textContent='已在本机浏览器保存。'}catch(e){$('save-status').textContent='本机存储不可用，请及时导出JSON。'}}
$('stats').innerHTML=[`10条样本 / 9处Crossing`,`收到 ${DATA.summary.received_responses} / 20次回答`,`识别支路共 ${DATA.review_audit.branch_total} 条（含来路）`,`明确选择 ${DATA.review_audit.model_selected} 条`,`证据不足 ${DATA.review_audit.model_insufficient} 条`,`尚不能认定选路正确`].map(t=>'<span class="stat">'+esc(t)+'</span>').join('');
$('case-select').innerHTML=DATA.cases.map((c,i)=>`<option value="${i}">${String(i+1).padStart(2,'0')} · ${c.review.episode_id} · ${c.calls['2']?.answer?.selected_branch_id?'选择 '+c.calls['2'].answer.selected_branch_id:'未选择'}</option>`).join('');
$('case-select').onchange=e=>select(Number(e.target.value));$('prev').onclick=()=>select(index-1);$('next').onclick=()=>select(index+1);$('language').onclick=()=>{english=!english;$('language').textContent=english?'切换中文译文':'切换英文原文';render()};$('show-reference').onchange=()=>{drawMap('map');drawMap('history-map',true)};
for(const id of ['map-slider','rgb-slider'])$(id).oninput=e=>setHistory(e.target.value);
$('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('play').textContent='播放'}else{$('play').textContent='暂停';timer=setInterval(()=>setHistory((hist+1)%8),1000)}};
function zoomImage(im,title){$('zoom-image').src=im;$('zoom-title').textContent=title;$('zoom').showModal()}
$('main-image').onclick=()=>zoomImage($('main-image').src,`${current().sample_id} · Crossing ${view}`);$('history-image').onclick=()=>zoomImage($('history-image').src,history()[hist].id);$('close-zoom').onclick=()=>$('zoom').close();$('zoom').onclick=e=>{if(e.target===$('zoom'))$('zoom').close()};
$('review-note').oninput=save;$('review-verdict').onchange=save;
$('export-review').onclick=()=>{save();const b=new Blob([JSON.stringify({run_hash:DATA.run_hash,exported_at:new Date().toISOString(),cases:DATA.cases.map(c=>({sample_id:c.sample_id,...(review[c.sample_id]||{verdict:'pending',note:''})}))},null,2)],{type:'application/json'}),url=URL.createObjectURL(b),a=document.createElement('a');a.href=url;a.download='crossing_v002_qwen27b_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$('footer').textContent=`生成于 ${DATA.exported_at} · 原图、地图、译文和字体全部内嵌，断网可用。运行证据 ${DATA.run_hash.slice(0,16)} · 中文为忠实翻译，保留模型判断的错误与不确定性。`;
render();
