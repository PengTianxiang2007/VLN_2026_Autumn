/* Data/display adapter for a recorded serial run. The JEV lab app is unchanged. */
(()=>{
 'use strict';
 const R=JSON.parse(document.getElementById('serial-evidence').textContent);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const tr=v=>v&&typeof v==='object'?(v[lang]??JSON.stringify(v)):v;
 const T={
  title:['JEV · 串行联调回放','JEV · Serial integration replay'],
  subtitle:['沿用原JEV滤波与采样模板 · 本次仿真真实记录 · '+R.run,'Original JEV filtering and sampling template · recorded simulation · '+R.run],
  source:['本次仅1条仿真任务、40帧有效JEV；任务失败，未触发回退纠错。','One simulation episode and 40 valid JEV observations. The task failed without triggering recovery.'],
  events:['已完成任务','Completed tasks'],failure:['本次导航失败','Navigation failed'],success:['本次导航成功','Navigation succeeded'],
  notice:['地图按JEV原始概率着色。完整波形、轨迹与勾选节点始终显示；拖动进度条只改变当前帧。勾选“显示回退点”显示7个候选，再勾选“节点去重”只显示S05、S07；参考轨迹仅供事后对照。','Map colors encode raw JEV probabilities. Full waveforms, trajectories and enabled nodes remain visible as the slider moves the current frame. Enable “Show checkpoints” for all 7 candidates, then enable deduplication to retain S05 and S07. Reference routes are retrospective context only.'],
  v001Title:['v001 · 建立的回退点','v001 · Established checkpoint candidates'],
  rulesNote:['本次实际参数固定为N=7、D=5。采样按同一冻结代码顺序回放并与运行日志逐点核验；开关只改变展示，不重新调用模型。','This run used fixed N=7 and D=5. Samples are replayed with the same frozen code and checked against runtime logs. Switches affect display only and make no model calls.'],
  dedupUnavailable:['没有与当前点位和参数匹配的本次去重结果。','No deduplication result from this run matches these nodes and parameters.'],
  dedupReplay:['使用本次仿真保存的6次去重原答；逐节点比较后删除旧点、保留新点。去重前后点位同步作用于地图和波形，完整结果不随回放进度裁剪。','Uses the six deduplication answers saved during this simulation. Nodes were processed sequentially, replacing the old node with the new one when matched. Deduplication affects both map and waveform; complete results remain visible at every playback frame.'],
  dedupPrompt:['去重提示词 · 随语言切换','Deduplication prompt · follows display language'],
  footer:['沿用原JEV模板 · 全部来自已保存实验记录 · 展示开关不改变实验输入、决策或评分。','Original JEV template · saved experiment evidence only · display switches do not change inputs, decisions or scoring.'],
  showPoints:['显示回退点','Show checkpoints'],showOriginal:['历史原始轨迹','Historical original trajectory'],showAnnotations:['历史人工点','Historical annotations'],
  result:['本次结果','Run result'],resultNote:['导航失败：NE 8.543米，40个动作（含STOP）；回退0次、纠错0次、记忆交还0次。5次“一致”为A=B初始化，另2次路段评审为“不确定”。完整纠错闭环未验证。','Navigation failed: NE 8.543 m, 40 actions including STOP; zero rollbacks, corrections or memory handoffs. Five consistent verdicts were A=B initializations; two segment reviews were uncertain. The full recovery cycle remains unverified.'],
  reviews:['本次偏航评审与语义进度','Deviation reviews and semantic progress'],reviewPick:['选择评审节点','Review node'],reviewJump:['跳到确认帧','Go to confirmation frame'],
  initialized:['初始化 A=B','Initialization A=B'],segment:['路段评审','Segment review'],consistent:['一致','Consistent'],uncertain:['不确定','Uncertain'],deviated:['偏航','Deviated'],
  actual:['实际经历','Observed segment'],reason:['判断依据','Reason'],prior:['输入的此前语义进度','Prior progress supplied'],progress:['本次累计语义进度','Cumulative semantic progress'],none:['无','None'],noProgress:['本次未提交新的语义进度。','No new semantic progress was committed.'],
  instructionEvidence:['任务引用','Instruction evidence'],visualEvidence:['视觉依据','Visual evidence'],uncertainties:['尚未确认的问题','Unresolved questions'],inputs:['本次实际输入帧','Actual input frames'],prompt:['完整提示词','Complete prompt'],raw:['原始请求与回答','Original request and answer'],
  rawNote:['JSON保留原始语言与字段；自然语言双语展示见上方正文与提示词。','JSON retains original languages and fields; bilingual natural-language content appears above.'],
  currentAction:['本帧之后动作','Action after this frame'],forward:['前进','Forward'],left:['左转','Left'],right:['右转','Right'],stop:['停止','STOP'],
  terminalNote:['末帧是STOP前观测；停止后的独立终止RGB未采集。','The last frame is the pre-STOP observation; no separate terminal RGB was captured.'],
  currentJev:['本帧JEV原始记录','JEV record for this frame'],exportEvidence:['导出53次请求与评分','Export 53 calls and metrics'],
  noExplanation:['JEV仅返回概率，没有文字理由；完整问题与判定条件见地图下方提示词。','JEV returned a probability only, without a textual explanation. The full question and criteria are available below the map.']
 };
 for(const [key,value] of Object.entries(T)){L.zh[key]=value[0];L.en[key]=value[1]}
 const style=document.createElement('style');style.textContent=`
  .serial-result{border-left:4px solid #c58317;padding:9px 12px;background:#fff7e8;margin:12px 0;font-size:13px}
  .serial-section{margin-top:18px;border-top:1px solid #d9e2eb;padding-top:15px}.serial-section select{max-width:100%}
  .serial-answer{background:#f5f8fb;border:1px solid #d9e2eb;padding:12px;border-radius:7px;font-size:13px}
  .serial-answer p{white-space:pre-wrap}.serial-answer ul{padding-left:20px}.serial-thumbs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px}
  .serial-thumbs a{display:block;min-width:0;font-size:11px;text-align:center}.serial-thumbs img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain}
  .parameterOptions input:disabled{opacity:.7}.trajectoryActions label{font-weight:bold;font-size:13px}.serial-action{font-size:12px;color:#65788a}
  @media(max-width:760px){.serial-thumbs{grid-template-columns:repeat(3,minmax(0,1fr))}.trajectoryActions{gap:7px}}
 `;document.head.append(style);
 $('eliminationControls').hidden=true;$('nodeEliminationTop').hidden=true;$('nodeElimination').checked=false;
 $('filterWindow').disabled=$('streamDelay').disabled=true;
 // An alias beside the map exposes the existing version checkbox, not a new
 // sampling implementation. The original checkbox continues to work normally.
 const quick=document.createElement('label');quick.className='eliminationOption';quick.innerHTML='<input id="showCheckpoints" type="checkbox"><span data-i18n="showPoints"></span>';
 document.querySelector('.trajectoryActions').prepend(quick);
 const controls=$('reference').closest('.controls');
 for(const [id,key]of [['showHistorical','showOriginal'],['showHuman','showAnnotations']]){
  const label=document.createElement('label');label.innerHTML=`<input id="${id}" type="checkbox"> <span data-i18n="${key}"></span>`;controls.append(label);
 }
 $('reference').checked=true;
 const result=document.createElement('p');result.className='serial-result';result.dataset.i18n='resultNote';$('caseStats').after(result);
 const action=document.createElement('p');action.className='serial-action';action.id='serialAction';$('inputInfo').before(action);
 const current=document.createElement('details');current.innerHTML='<summary data-i18n="currentJev"></summary><p class="muted" data-i18n="noExplanation"></p><pre id="serialJevRaw"></pre>';$('history').after(current);
 const review=document.createElement('section');review.className='serial-section';review.id='serialReview';review.innerHTML=`<h2 data-i18n="reviews"></h2><p class="muted" data-i18n="resultNote"></p><div class="controls"><label for="serialReviewPick" data-i18n="reviewPick"></label><select id="serialReviewPick"></select><button id="serialReviewJump" data-i18n="reviewJump"></button></div><p class="muted" id="serialReviewMeta"></p><div class="serial-answer" id="serialReviewAnswer"></div><h3 data-i18n="inputs"></h3><div class="serial-thumbs" id="serialReviewImages"></div><details><summary data-i18n="prompt"></summary><pre id="serialReviewPrompt"></pre></details><details><summary data-i18n="raw"></summary><p class="muted" data-i18n="rawNote"></p><pre id="serialReviewRaw"></pre></details><button id="serialExport" data-i18n="exportEvidence"></button>`;
 $('jevMap').closest('section.panel').append(review);
 const calls=R.requests.filter(q=>q.stage==='deviation');let reviewIndex=0;
 const part=(key,value)=>`<h3>${t(key)}</h3><p>${esc(tr(value))}</p>`;
 const list=(key,values)=>`<h3>${t(key)}</h3>`+(values.length?`<ul>${values.map(v=>`<li>${esc(tr(v))}</li>`).join('')}</ul>`:`<p>${t('none')}</p>`);
 function renderSerialReview(){
  const call=calls[reviewIndex],a=call.answer,m=call.metadata;
  $('serialReviewPick').innerHTML=calls.map((q,i)=>`<option value="${i}">${q.metadata.current_id} · F${q.metadata.current_frame} → F${q.frame} · ${t(q.answer.verdict)}</option>`).join('');$('serialReviewPick').value=reviewIndex;
  $('serialReviewMeta').textContent=`${m.previous_id} F${m.previous_frame} → ${m.current_id} F${m.current_frame} · ${t(m.mode==='initialization'?'initialized':'segment')} · ${t('confirmed')}: F${call.frame} · ${call.latency_seconds.toFixed(1)} s`;
  $('serialReviewAnswer').innerHTML=part('actual',a.segment_summary)+part('reason',a.reason)+part('prior',call.prior_progress)+part('progress',a.semantic_progress||t('noProgress'))+
   list('instructionEvidence',a.instruction_evidence.map(q=>q[lang==='zh'?'quote_zh':'quote_en']))+
   list('visualEvidence',a.visual_evidence.map(v=>tr(v.description)+' ('+v.frames.map(f=>'F'+f).join(', ')+')'))+list('uncertainties',a.uncertainties);
  $('serialReviewImages').innerHTML=call.images.map(im=>`<a href="${B.images[String(im.image)]}" target="_blank" rel="noopener"><img src="${B.images[String(im.image)]}" alt="F${im.frame}">${esc(im.label)}</a>`).join('');
  $('serialReviewPrompt').textContent=R.prompts.deviation[lang];$('serialReviewRaw').textContent=JSON.stringify({request:call.raw_request,answer:call.raw_answer},null,2);
 }
 const nativeDedup=renderDedup;
 renderDedup=function(state){
  nativeDedup(state);$('dedupPrompt').textContent=D?.[lang==='zh'?'prompt_zh':'prompt_en']||'';
  const record=state.versions.find(v=>v.dedupRecord)?.dedupRecord,d=record?.decisions[$('dedupDecision').selectedIndex];
  if(!d)return;const a=d.display_answer;
  $('dedupReason').textContent=tr(a.reason);$('dedupBranches').replaceChildren();
  for(const b of a.matched_branches||[]){const li=document.createElement('li');li.textContent=`${t('dedupMatched')}: ${tr(b.description)} (${b.a_frames.join(', ')} ↔ ${b.b_frames.join(', ')})`;$('dedupBranches').append(li)}
  for(const [key,label]of [['a_only','dedupAOnly'],['b_only','dedupBOnly']])for(const desc of a[key]||[]){const li=document.createElement('li');li.textContent=t(label)+': '+tr(desc);$('dedupBranches').append(li)}
 };
 const nativeMap=drawMap;
 drawMap=function(state){
  nativeMap(state);const cv=$('jevMap'),ctx=cv.getContext('2d'),g=B.maps[c().scene].geometry,w=cv.getBoundingClientRect().width,h=cv.getBoundingClientRect().height,scale=Math.min(w/g.width,h/g.height),ox=(w-g.width*scale)/2,oy=(h-g.height*scale)/2;
  const xy=p=>[ox+(p[0]-g.low[0])/g.resolution*scale,oy+(g.high[1]-p[1])/g.resolution*scale];
  ctx.save();if($('showHistorical').checked){ctx.strokeStyle='#d17c29';ctx.globalAlpha=.7;ctx.lineWidth=2;ctx.setLineDash([4,5]);ctx.beginPath();R.historical.forEach((p,i)=>i?ctx.lineTo(...xy(p)):ctx.moveTo(...xy(p)));ctx.stroke();ctx.globalAlpha=1;ctx.setLineDash([])}
  if($('showHuman').checked){ctx.font='bold 11px CrossingSans,sans-serif';for(const point of R.annotations){const [x,y]=xy(point.position);ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fillStyle='#2563eb';ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=3;ctx.strokeText(point.id,x-27,y-8);ctx.fillText(point.id,x-27,y-8)}}ctx.restore();
 };
 const nativeDraw=draw;
 draw=function(){nativeDraw();$('showCheckpoints').checked=$('sample_v001').checked;const f=R.frames[index],code={0:'stop',1:'forward',2:'left',3:'right'}[f.action];$('serialAction').textContent=t('currentAction')+': '+t(code)+(index===R.frames.length-1?' · '+t('terminalNote'):'');$('serialJevRaw').textContent=JSON.stringify(R.requests[f.request].raw_answer,null,2);renderSerialReview()};
 const nativeLanguage=updateLanguage;
 updateLanguage=function(){nativeLanguage();$('promptChinese').hidden=lang!=='zh';$('promptChinese').previousElementSibling.hidden=lang!=='zh';$('promptEnglish').hidden=lang!=='en';$('promptEnglish').previousElementSibling.hidden=lang!=='en';renderSerialReview()};
 $('showCheckpoints').onchange=()=>{$('sample_v001').checked=$('showCheckpoints').checked;stop();draw()};
 $('showHistorical').onchange=$('showHuman').onchange=draw;
 $('serialReviewPick').onchange=()=>{reviewIndex=Number($('serialReviewPick').value);renderSerialReview()};
 $('serialReviewJump').onclick=()=>{stop();seek(calls[reviewIndex].frame)};
 $('serialExport').onclick=()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify({run:R.run,episode_id:R.id,summary:R.summary,metrics:R.metrics,requests:R.requests,nodes:R.nodes},null,2)],{type:'application/json'}));a.href=url;a.download=R.run+'_evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)};
 // Original app's API points to original functions; export the final draw for checks.
 window.JEV_LAB.draw=draw;window.SERIAL_JEV={data:R,reviewCalls:calls,review:i=>{reviewIndex=i;renderSerialReview()},
  state:()=>({lang,reviewIndex,mapSamples:sampleHitPoints.map(h=>({id:h.node.id,index:h.node.index,emittedAt:h.node.emittedAt,x:h.x,y:h.y}))})};
 updateLanguage();
})();
