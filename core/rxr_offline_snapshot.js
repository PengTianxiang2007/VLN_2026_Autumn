/* Frozen RxR node and deviation results. No inference or external requests. */
(() => {
  'use strict';
  const el = id => document.getElementById(id), txt=(id,s)=>el(id).textContent=s;
  const T=s=>lang?(SNAPSHOT.translations[s]??s):s;
  const relations={same:['相同：删除旧候选，保留新候选','Same: remove old candidate, retain new candidate'],different:['不同：两处均保留','Different: retain both'],uncertain:['不确定：两处均保留','Uncertain: retain both'],not_compared:['无需模型比较，直接保留','No model comparison required; retain directly']};
  let caseKey='', detailKey='', choice=0, imageGeneration=0, noteContext='', devChoice=0, devDetailKey='';
  const ownCache=new Map(), pictureTokens={}, notesKey='rxr30_'+SNAPSHOT.created_at+'_notes';
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const nodeList=()=>item.dedup?.nodes||[];
  const devRows=()=>item.deviation?.result.reviews||[];
  const intervals=()=>item.deviation?.intervals||[];
  const verdicts={consistent:['继续','Continue'],deviated:['偏航报警','Deviation alarm'],format_error:['无效回答 · 结论未采纳','Invalid answer · Decision not accepted']};
  const errorLabels={
    'ValueError: Invalid uncertainties':['uncertainties 字段格式不合法。','Invalid uncertainties field format.'],
    'ValueError: Incomplete response: length':['达到输出上限，未形成完整最终回答。','The output limit was reached; no complete final answer was produced.'],
    'ValueError: Instruction quote is not an exact supplied excerpt':['指令引用与提供的英文原文不完全一致。','The instruction quote does not exactly match the supplied English instruction.']
  };
  const verdict=r=>r.status==='ok'?r.answer.verdict:'format_error';
  const bilingual=v=>v==null?L('无','None'):Array.isArray(v)?v.map(bilingual).join('\n'):typeof v==='object'?bilingual(v[lang?'en':'zh']):String(v);
  function summary(){
    const s=SNAPSHOT.summary,n=SNAPSHOT.completed_ids.length,d=SNAPSHOT.deviation_summary||{outcomes:{},calls:0,alarm_cases:0},done=SNAPSHOT.deviation_complete;
    el('snapshotSummary').innerHTML=`<div class="sectionHead" style="padding:0"><h2>${L('有效节点与偏航识别 · 冻结快照','Effective nodes and deviation reviews · Frozen snapshot')}</h2><span class="badge complete">${L('去重','Dedup')} ${n}/30 · ${L('偏航评审','Deviation review')} ${done}/30</span></div><div class="statsGrid">${[[s.candidates,L('原始候选','Original candidates')],[s.retained,L(`有效节点（另加${n}个终止节点）`,`Effective nodes (+${n} terminal nodes)`)],[s.removed,L('去重删除的原始候选','Original candidates removed')],[s.model_calls,L(`模型比较 · ${s.uncertain}次不确定，含${s.errors}次错误`,`Model comparisons · ${s.uncertain} uncertain, including ${s.errors} errors`)]].map(([num,label])=>`<div class="statTile"><strong>${num}</strong><span>${label}</span></div>`).join('')}</div><p>${L(`已完成偏航识别 ${done}/30 条：${d.alarm_cases}条有有效报警，${done-d.alarm_cases}条未报警。共${d.calls}轮，${d.outcomes.format_error||0}轮无效回答；报警数不是识别准确率。`,`Deviation review complete for ${done}/30 cases: ${d.alarm_cases} with accepted alarms and ${done-d.alarm_cases} without alarms. ${d.calls} rounds, including ${d.outcomes.format_error||0} invalid answers; alarm count is not detection accuracy.`)}</p><p class="small">${L('冻结时间','Frozen at')} ${esc(SNAPSHOT.created_at)} · ${SNAPSHOT.coverage_note?esc(bilingual(SNAPSHOT.coverage_note)):L('本页不自动刷新。全部30条展示最终节点；逐次去重的双语详情沿用首4条，其余原始结果可下载。已完成偏航案例展示全部评审原答；其他案例不标作“未偏航”。','This page does not refresh automatically. Final nodes are shown for all 30 cases. Bilingual deduplication details are retained for the first 4; other original results can be downloaded. Completed deviation cases include all review answers; other cases are not labeled as having no deviation.')}</p><p class="small">${L('离线评审没有新导航评分。当前版 / 配对原版 SR 与平均 SPL 均暂无，已评分0条。30条来源轨迹原版 SR 0/30（0%），平均 SPL 0。','Offline review produces no new navigation scores. Current / matched-original SR and mean SPL are unavailable, with 0 newly scored episodes. The 30 source trajectories have original SR 0/30 (0%) and mean SPL 0.')}</p>`;
  }
  function drawNodes({ctx,px,pz}){
    if(el('deviationLayer').checked){
      ctx.save();ctx.strokeStyle='#e02032';ctx.lineWidth=6;ctx.lineCap='round';ctx.lineJoin='round';
      for(const segment of intervals()){
        // Walk every recorded pose; A can precede several nodes after format errors.
        for(let f=segment.from_frame+1;f<=segment.to_frame;f++){
          const a=item.pose[f-1],b=item.pose[f];
          ctx.setLineDash(Math.abs((a[1]+b[1])/2-item.floor.floor)>.85?[3,6]:[]);
          ctx.beginPath();ctx.moveTo(px(a[0]),pz(a[2]));ctx.lineTo(px(b[0]),pz(b[2]));ctx.stroke();
        }
        ctx.setLineDash([]);
        for(const [frame,label] of [[segment.from_frame,'A '+segment.previous_id],[segment.to_frame,'B '+segment.current_id]]){
          const p=item.pose[frame],x=px(p[0]),y=pz(p[2]);ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.lineWidth=2;ctx.strokeStyle='#e02032';ctx.stroke();
          ctx.font='bold 14px sans-serif';ctx.lineWidth=4;ctx.strokeStyle='white';ctx.strokeText(label,x+10,y-11);ctx.fillStyle='#be1025';ctx.fillText(label,x+10,y-11);
        }
        ctx.strokeStyle='#e02032';ctx.lineWidth=6;
      }
      ctx.restore();
    }
    if(!el('effectiveLayer').checked)return;
    for(const n of nodeList()){
      const p=item.pose[n.index],x=px(p[0]),y=pz(p[2]);ctx.beginPath();ctx.arc(x,y,n.terminal_node?5:4.5,0,Math.PI*2);
      ctx.fillStyle=n.terminal_node?'#576a70':'#853ba5';ctx.fill();ctx.strokeStyle='white';ctx.lineWidth=1.3;ctx.stroke();
      if(n.index===step){ctx.beginPath();ctx.arc(x,y,9,0,Math.PI*2);ctx.strokeStyle='#853ba5';ctx.lineWidth=2;ctx.stroke()}
    }
  }
  function plot(){
    const c=el('jevPlot'),ctx=c.getContext('2d'),w=c.width,h=c.height,last=item.pose.length-1,left=40,right=w-20,top=14,bottom=h-30;
    const x=f=>left+(right-left)*f/Math.max(last,1),y=v=>bottom-v*(bottom-top);
    ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);ctx.font='12px sans-serif';ctx.textAlign='right';
    for(const v of [0,.5,1]){ctx.strokeStyle='#e1e9e4';ctx.beginPath();ctx.moveTo(left,y(v));ctx.lineTo(right,y(v));ctx.stroke();ctx.fillStyle='#667b73';ctx.fillText(v.toFixed(1),left-8,y(v)+4)}
    ctx.strokeStyle='#277e6c';ctx.lineWidth=2;ctx.beginPath();item.scores.forEach((v,f)=>{if(f===0)ctx.moveTo(x(f),y(v));else ctx.lineTo(x(f),y(v))});ctx.stroke();
    for(const n of nodeList()){ctx.strokeStyle=n.terminal_node?'#7a878b':'#a674b8';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x(n.index),top);ctx.lineTo(x(n.index),bottom);ctx.stroke()}
    ctx.strokeStyle='#142f38';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x(step),top);ctx.lineTo(x(step),bottom);ctx.stroke();ctx.textAlign='center';ctx.fillStyle='#39574e';
    for(let i=0;i<=4;i++){const f=Math.round(last*i/4);ctx.fillText('F'+f,x(f),h-9)}
  }
  function pictures(parent,refs,token){
    const container=el(parent);container.replaceChildren();pictureTokens[parent]=token;
    for(const im of refs){
      const b=document.createElement('button');b.title=L('查看动作帧 ','View action frame ')+im.frame;
      const label=document.createElement('span');label.textContent=im.label+' · F'+im.frame;
      if(im.missing){const p=document.createElement('span');p.className='missing';p.textContent=L('缺失','Missing');b.append(p,label);b.disabled=true;container.append(b);continue}
      const canvas=document.createElement('canvas');canvas.width=160;canvas.height=120;b.append(canvas,label);b.onclick=()=>jump(im.frame);container.append(b);
      const url='assets/'+item.id+'/'+Math.floor(im.frame/9)+'.jpg';let image=ownCache.get(url);
      if(!image){image=new Image();image.src=url;ownCache.set(url,image);if(ownCache.size>24)ownCache.delete(ownCache.keys().next().value)}
      const paint=()=>{if(token!==pictureTokens[parent]||!image.naturalWidth)return;const f=im.frame%9;canvas.getContext('2d').drawImage(image,(f%3)*640,Math.floor(f/3)*480,640,480,0,0,160,120)};
      if(image.complete)paint();else image.addEventListener('load',paint,{once:true});
    }
  }
  function details(){
    if(!item.dedup?.decisions.length)return;
    const d=item.dedup.decisions[choice],key=item.id+':'+choice+':'+lang;
    if(key===detailKey)return;detailKey=key;imageGeneration++;
    const retained=item.dedup.nodes.some(n=>n.source_id===d.current_id);
    txt('reviewDecision',`${relations[d.relation][lang]} · ${L('本候选最终','This candidate finally ')}${retained?L('保留为有效节点','retained as an effective node'):L('被删除，不再算节点','removed; no longer a node')}`);
    txt('reviewReason',T(d.reason));
    const ready=d.current_frame+5;
    txt('reviewTiming',`A ${d.previous_id||'—'} / F${d.previous_frame??'—'} → B ${d.current_id} / F${d.current_frame} · ${L('候选可确认帧','Candidate confirmation available at')} F${ready} · ${d.elapsed_seconds===undefined?L('程序直接处理','Handled directly by the program'):d.elapsed_seconds.toFixed(2)+' s'} · ${L('本面板展示原始候选评审，不改变最终有效节点清单。','This panel shows original-candidate reviews; it does not change the final effective-node list.')}`);
    const refs=d.request?.images||[];pictures('imagesA',refs.filter(im=>im.label.startsWith('A')),imageGeneration);pictures('imagesB',refs.filter(im=>im.label.startsWith('B')),imageGeneration);
    const a=d.answer;
    el('branchDetails').innerHTML=a?`<h3>${L('对应的分支','Matched branches')}</h3>${a.matched_branches.length?'<ul>'+a.matched_branches.map(m=>`<li>${esc(T(m.description))}<br><span class="small">A: ${esc(m.a_frames.join(', '))} · B: ${esc(m.b_frames.join(', '))}</span></li>`).join('')+'</ul>':`<p>${L('无','None')}</p>`}<div class="notes">${[['a_only',L('仅 A 提供的分支','Branches unique to A')],['b_only',L('仅 B 提供的分支','Branches unique to B')]].map(([k,title])=>`<div><h3>${title}</h3>${a[k].length?'<ul>'+a[k].map(s=>'<li>'+esc(T(s))+'</li>').join('')+'</ul>':`<p>${L('无','None')}</p>`}</div>`).join('')}</div>`:`<p class="small">${L('此候选未调用模型，没有模型输入图或原答。','No model call was made for this candidate, so no model input images or answer exist.')}</p>`;
    txt('rawAnswer',d.raw_content||L('无模型回答','No model answer'));txt('rawRequest',d.request?JSON.stringify(d.request,null,2):L('无模型请求','No model request'));
    el('dedupResponseLink').hidden=!d.raw_response_file;if(d.raw_response_file)el('dedupResponseLink').href=d.raw_response_file;
    el('roundPicker').value=String(choice);loadNote();
  }
  function controls(){
    summary();
    [...el('task').options].forEach(o=>{const c=CASES.find(c=>c.id===o.value);o.textContent=(CASES.indexOf(c)+1)+'/30 · ep '+c.id+' · '+(c.deviation?(c.deviation.intervals.length?L('偏航报警','Deviation alarm'):L('评审完毕·未报警','Reviewed · No alarm')):L('偏航结果待完成','Deviation review pending'))+' · '+L('原版失败 / 当前未评测','Original failed / current unscored')});
    const d=item.dedup,nodes=nodeList(),hasDetails=!!d?.decisions.length;el('nodeButtons').replaceChildren();el('reviewBody').hidden=!hasDetails;el('reviewEmpty').hidden=hasDetails;
    el('dedupRawLink').hidden=!d?.raw_file;if(d?.raw_file)el('dedupRawLink').href=d.raw_file;
    txt('nodeStatus',d?L('以下为最终去重保留清单；点击节点可跳到对应原始观测。','These are the final retained nodes. Click a node to view its original observation.'):L('本案例未纳入本次已完成结果，暂不展示有效节点。原始轨迹与JEV分数仍可查看。','This case is not part of the completed-result snapshot; no effective nodes are shown. Original trajectories and JEV scores remain available.'));
    txt('reviewEmpty',L('本例去重已完成，最终节点见上方。本页逐次双语去重详情沿用首4条；本例完整原始结果可下载。','Deduplication is complete for this case, with final nodes shown above. This page retains bilingual round-by-round dedup details for the first 4 cases; the full original result for this case can be downloaded.'));
    txt('nodeCount',d?`${d.summary.retained} ${L('有效节点','effective nodes')} + 1 ${L('终止节点','terminal node')}`:'—');
    txt('roundCount',d?`${d.summary.candidates} ${L('原始候选','original candidates')} · ${d.summary.model_calls} ${L('模型比较','model comparisons')}`:'—');
    for(const n of nodes){const b=document.createElement('button');b.className=n.terminal_node?'terminalButton':'nodeButton';b.dataset.frame=n.index;b.textContent=`${n.id} · F${n.index}${n.terminal_node?' · '+L('终止','terminal'):''}`;b.title=L('确认可用帧 ','Confirmation available at frame ')+n.emittedAt;b.onclick=()=>{if(n.source_id&&hasDetails){choice=d.decisions.findIndex(r=>r.current_id===n.source_id);detailKey=''}const index=devRows().findIndex(r=>r.node_id===n.id);if(index>=0){devChoice=index;devDetailKey=''}jump(n.index)};el('nodeButtons').append(b)}
    el('roundPicker').replaceChildren(...(d?.decisions||[]).map((r,i)=>new Option(`${String(i+1).padStart(2,'0')} · ${L('原始候选','Original candidate')} ${r.current_id} / F${r.current_frame} · ${relations[r.relation][lang]}`,String(i))));
    txt('dedupPrompt',SNAPSHOT.prompts[lang?'dedup_en':'dedup_zh']);
    txt('deviationPrompt',SNAPSHOT.prompts[lang?'deviation_en':'deviation_zh']||'');
    deviationControls();
  }
  function deviationControls(){
    const d=item.deviation,rows=devRows(),segs=intervals();el('deviationBody').hidden=!d;
    txt('deviationStatus',!d?L('结果待完成','Result pending'):segs.length?L('有效报警','Accepted alarm'):L('评审完成 · 未报警','Review complete · No alarm'));
    txt('deviationOverview',!d?L('冻结时本例尚无完整偏航结果，不能据此判定没有偏航。','No complete deviation result exists for this case at the snapshot time; this does not establish absence of deviation.'):L(`已完成${rows.length}轮：${d.summary.outcomes.consistent||0}轮继续，${d.summary.outcomes.deviated||0}轮有效报警，${d.summary.outcomes.format_error||0}轮无效回答。${segs.length?'在首个有效报警处停止后续评审。':'已走完本例评审流程，未产生有效报警。'}`,`${rows.length} rounds complete: ${d.summary.outcomes.consistent||0} continue, ${d.summary.outcomes.deviated||0} accepted alarms, ${d.summary.outcomes.format_error||0} invalid answers. ${segs.length?'Review stopped at the first accepted alarm.':'The review process finished without an accepted alarm.'}`));
    txt('deviationMapNote',!d?L('偏航：本例结果待完成','Deviation: result pending'):segs.length?L('报警区间：','Alarm interval: ')+segs.map(s=>`${s.previous_id} / F${s.from_frame} → ${s.current_id} / F${s.to_frame}`).join('; '):L('偏航评审已完成，本例无有效报警区间。','Deviation review complete; no accepted alarm interval for this case.'));
    el('devPicker').replaceChildren(...rows.map((r,i)=>new Option(`${i+1} · ${r.previous_id} → ${r.node_id} · F${r.from_frame}–F${r.to_frame} · ${verdicts[verdict(r)][lang]}`,String(i))));
  }
  function deviationDetails(){
    const r=devRows()[devChoice];if(!r)return;
    const key=item.id+':'+devChoice+':'+lang;if(key===devDetailKey)return;devDetailKey=key;
    const accepted=r.status==='ok',a=r.display_answer||{},v=verdict(r);
    txt('devVerdict',verdicts[v][lang]+(accepted?'':L('；原答声称：','; original answer claimed: ')+(verdicts[a.verdict]?.[lang]||a.verdict||'—')));
    txt('devTiming',`A ${r.previous_id} / F${r.from_frame} → B ${r.node_id} / F${r.to_frame} · ${r.elapsed_seconds.toFixed(2)} s · ${r.completed_at}`);
    el('devError').hidden=accepted;
    txt('devError',accepted?'':L('回答未通过校验，本轮不更新累计进度，也不产生红色报警区间。错误：','The answer failed validation. This round does not update accumulated progress or produce a red alarm interval. Error: ')+(errorLabels[r.error]?.[lang]||r.error));
    pictures('devImages',r.images.map(im=>({frame:im.frame,label:im.role==='history'?L('中间观测','Intermediate'):im.role})),++imageGeneration);
    const paragraph=(title,value)=>`<h3>${title}</h3><p class="devText">${esc(bilingual(value))}</p>`;
    el('devAnswer').innerHTML=paragraph(L('输入：A 处已保存的进度','Input: progress saved at A'),r.prior_progress)+
      paragraph(L('本段观察','Segment observations'),a.segment_summary)+paragraph(L('判断理由','Reason'),a.reason)+
      `<h3>${L('指令证据','Instruction evidence')}</h3>`+((a.instruction_evidence||[]).map(q=>`<blockquote class="devText">${esc(q[lang?'quote_en':'quote_zh'])}</blockquote>`).join('')||`<p>${L('无','None')}</p>`)+
      `<h3>${L('画面证据','Visual evidence')}</h3>`+((a.visual_evidence||[]).map(e=>`<p class="devText"><strong>${esc(e.frames.map(f=>'F'+f).join(', '))}</strong> · ${esc(bilingual(e.description))}</p>`).join('')||`<p>${L('无','None')}</p>`)+
      paragraph(L('模型返回的语义进度','Semantic progress returned by the model'),a.semantic_progress)+
      paragraph(L('模型记录的未决事项','Uncertainties recorded by the model'),a.uncertainties?.length===0?null:a.uncertainties)+
      paragraph(L('本轮后系统保存的累计进度','Accumulated progress saved after this round'),r.committed_progress||r.prior_progress)+
      `<p class="small">${L('输入为两个端点和最多五张均匀抽样的中间观测，帧号可能不连续。判断截止于B。展示图来自同一帧，输入原图哈希见实际请求。','Inputs are both endpoints and up to five uniformly sampled intermediate observations; frames may not be consecutive. Review ends at B. Display images come from the same frames; original input hashes are in the actual request.')}</p>`;
    if(!r.display_answer)el('devAnswer').insertAdjacentHTML('afterbegin',`<p class="notice">${L('本轮未形成可解析的最终回答；以下仅保留输入和已有进度，不补写模型结论。','This round produced no parseable final answer. Only its inputs and existing progress are retained below; no model conclusion has been invented.')}</p>`);
    txt('devRawAnswer',r.raw_content||L('本轮未返回最终回答文本；原始服务端响应已保留。','This round returned no final-answer text; the original server response is preserved.'));txt('devRawRequest',JSON.stringify(r.request,null,2));el('devPicker').value=String(devChoice);
    el('devResponseLink').hidden=!r.raw_response_file;if(r.raw_response_file)el('devResponseLink').href=r.raw_response_file;
  }
  function render(){
    const key=item.id+':'+lang;
    if(caseKey!==key){
      const changed=caseKey.split(':')[0]!==item.id;caseKey=key;detailKey='';devDetailKey='';
      if(changed){const rows=item.dedup?.decisions||[];choice=Math.max(0,rows.findLastIndex(r=>r.current_frame<=step));devChoice=Math.max(0,devRows().findIndex(r=>verdict(r)==='deviated'));ownCache.clear()}
      controls();
    }
    for(const b of el('nodeButtons').children)b.setAttribute('aria-current',String(Number(b.dataset.frame)===step));
    const n=nodeList().find(n=>n.index===step),score=item.scores[step];
    txt('currentNode',`${L('当前帧','Current frame')} F${step} · JEV ${score===undefined?L('终止帧未评分','terminal frame unscored'):score.toFixed(3)} · ${n?(n.terminal_node?L('追加终止节点 ','Appended terminal node '):L('有效节点 ','Effective node '))+n.id:L('普通观测，不是有效节点','Ordinary observation, not an effective node')}`);
    plot();details();deviationDetails();if(noteContext!==noteId())loadNote();
  }
  el('effectiveLayer').onchange=()=>map();
  el('deviationLayer').onchange=()=>map();
  function chooseDev(i){if(!devRows().length)return;devChoice=Math.max(0,Math.min(devRows().length-1,i));devDetailKey='';jump(devRows()[devChoice].to_frame)}
  el('devPicker').onchange=e=>chooseDev(Number(e.target.value));el('devPrev').onclick=()=>chooseDev(devChoice-1);el('devNext').onclick=()=>chooseDev(devChoice+1);
  el('devJumpA').onclick=()=>jump(devRows()[devChoice].from_frame);el('devJumpB').onclick=()=>jump(devRows()[devChoice].to_frame);
  el('jevPlot').onclick=e=>{const r=e.currentTarget.getBoundingClientRect(),x=(e.clientX-r.left)*1200/r.width; jump(Math.round((x-40)/1140*(item.pose.length-1)))};
  function choose(i){if(!item.dedup?.decisions.length)return;choice=Math.max(0,Math.min(item.dedup.decisions.length-1,i));detailKey='';jump(item.dedup.decisions[choice].current_frame)}
  el('roundPicker').onchange=e=>choose(Number(e.target.value));el('roundPrev').onclick=()=>choose(choice-1);el('roundNext').onclick=()=>choose(choice+1);el('roundJump').onclick=()=>choose(choice);
  function noteId(){return item.id+':'+step+':'+(item.dedup?.decisions[choice]?.current_id||'none')}
  function notes(){try{return JSON.parse(localStorage.getItem(notesKey)||'{}')}catch{return {}}}
  function loadNote(){noteContext=noteId();el('reviewNote').value=notes()[noteContext]?.note||'';txt('noteFeedback','')}
  el('saveNote').onclick=()=>{const all=notes(),id=noteId();all[id]={episode_id:item.id,frame:step,candidate:item.dedup?.decisions[choice]?.current_id||null,note:el('reviewNote').value,updated_at:new Date().toISOString()};try{localStorage.setItem(notesKey,JSON.stringify(all));txt('noteFeedback',L('已保存到本浏览器','Saved in this browser'))}catch{txt('noteFeedback',L('浏览器存储不可用，请复制意见另存。','Browser storage unavailable; copy the note elsewhere.'))}};
  el('downloadNotes').onclick=()=>{const blob=new Blob([JSON.stringify({snapshot:SNAPSHOT.created_at,notes:Object.values(notes())},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='rxr30_review_notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
  window.RxRSnapshot={render,drawNodes,choose,chooseDev,inspect:()=>({case_id:item.id,frame:step,language:lang,choice,devChoice,intervals:intervals(),deviationLayer:el('deviationLayer').checked,nodes:nodeList().map(n=>({id:n.id,frame:n.index,terminal:n.terminal_node})),completed:SNAPSHOT.completed_ids})};
  caseKey='';render();map();
})();
