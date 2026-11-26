// Display-only filters over frozen model results. Never alter the candidate data.
const modelOrder=Object.keys(B.modelReviews);
const primaryModel=B.primaryModel||'astra';
const modelNames={terra61:"GPT-6.1 Terra Fast v006.1",astra61:'GPT-6 Astra v006.1',terra6:'GPT-6.1 Terra Fast v006',astra6:'GPT-6 Astra v006',memory:'GPT-6 Astra v003',astra3:'GPT-6 Astra v002',astra62:'GPT-6.2 Astra',astra:'GPT-6 Astra',qwen:'Qwen27B',deepseek:'DeepSeek'};
const modelColors={terra61:"#256d5d",astra61:'#0369a1',terra6:'#0f766e',astra6:'#4338ca',memory:'#be123c',astra3:'#c2410c',astra62:'#c2410c',astra:'#0f766e',qwen:'#2563eb',deepseek:'#9333ea'};
let reviewModelKey=primaryModel;
const modelLabel=key=>modelNames[key]+' · '+t('frameCount',{n:B.modelReviews[key].observation_offsets.length});
const modelRecord=key=>B.modelReviews[key].cases.find(item=>item.episode_id===c().episode_id)||null;
const enabledModelKeys=()=>modelOrder.filter(key=>$('remove_'+key).checked&&modelRecord(key));
const removedBy=(key,id)=>{const record=modelRecord(key);return !!record&&!record.final_active_ids.includes(id);};
const primaryVerdicts=B.modelReviews[primaryModel].cases.flatMap(r=>r.decisions).filter(d=>d.needs_model)
  .reduce((counts,d)=>{counts[d.relation]=(counts[d.relation]||0)+1;return counts;},{});
const coverageText=modelOrder.map(k=>modelNames[k]+' ('+B.modelReviews[k].observation_offsets.length+') '+B.modelReviews[k].coverage+'/'+B.cases.length).join(' · ');
Object.assign(L.zh,{
  title:'回退点去重 · 多版本对照',subtitle:B.cases.length+' 条 VLNVerse 错误轨迹 · 同一批原始候选',source:'原生前视 · '+modelOrder.map(k=>modelNames[k]+' '+B.modelReviews[k].observation_offsets.length+' 帧').join(' / '),
  comparisonTitle:'按模型选择去重显示',comparisonHelp:'勾选后隐藏该模型判为重复的原始候选。全部取消可看原始候选；多选隐藏删除集合的并集，组合显示不代表任一模型的实际输出。',
  removeModel:'去掉 {model} 判为重复的候选',reviewModelLabel:'查看模型原答：',rawCandidatesButton:'取消全部去重',
  modelName:'模型',frameCount:'{n} 帧',inputWindow:'每端输入',coverage:'本页覆盖',caseKept:'本例保留 / 原始候选',pageKept:'已覆盖样本保留 / 原始候选',callsHeader:'比较次数',
  notReviewed:'未评审',kept:'保留',removed:'已去重删除',candidateTableTitle:'逐候选对照与跳转',candidateHeader:'原始候选',frameHeader:'动作步',displayHeader:'当前显示',visible:'显示',hidden:'隐藏',
  rawAnswerLabel:'原始模型 JSON（原样保留；译文见上方说明）',rawMode:'显示全部 {n} 个原始候选。',
  singleMode:'按 {model}：{total} 个原始候选 → {kept} 个有效节点，删除 {removed} 个。',
  multiMode:'组合显示（{models}）：删除并集 {removed} 个，显示 {kept}/{total} 个候选。请在表格查看各模型实际结果。',
  missingCoverage:'本例没有该模型的去重评审；不执行隐藏，也不将缺失记录视为保留结论。',
  missingRequested:'当前勾选的模型在本例均未评审，显示全部 {n} 个原始候选。',
  currentCandidate:'当前原始候选 · {nodes}',currentRemovedCandidate:'当前原始候选已去重删除 · {nodes}',
  dedupUnavailable:'本例无该模型的去重记录。',dedupPrompt:'去重提示词（中文实际输入）',
  footer:'仅展示离线第一轮去重；无新导航评分。覆盖（括号为每端帧数）：'+coverageText+'。'+(primaryModel==='astra3'?'三帧版与旧五帧版均使用 GPT-6 Astra / medium，只改变观测窗口；候选减少量不是去重准确率。':'各版本的模型和输入窗口见对照表；候选减少量不是去重准确率。'),
  samplingHint:'地图、波形和当前帧提示同步应用上方勾选。被删除项仅作为原始候选供对照。',
  sourceStats:modelNames[primaryModel]+' · '+B.modelReviews[primaryModel].observation_offsets.length+' 帧保留',pairCount:modelNames[primaryModel]+' · '+B.modelReviews[primaryModel].observation_offsets.length+' 帧比较',latency:'调用耗时',
  notice:`${modelNames[primaryModel]} · ${B.modelReviews[primaryModel].observation_offsets.length} 帧：相同 ${primaryVerdicts.same||0} 对，不同 ${primaryVerdicts.different||0} 对，不确定 ${primaryVerdicts.uncertain||0} 对。地图颜色表示原始 JEV 概率；各模型去重显示由下方勾选控制。`,
});
Object.assign(L.en,{
  title:'Checkpoint deduplication · Model-version comparison',subtitle:B.cases.length+' VLNVerse failure trajectories · Identical raw candidates',source:'Native front views · '+modelOrder.map(k=>modelNames[k]+' '+B.modelReviews[k].observation_offsets.length+' frames').join(' / '),
  comparisonTitle:'Choose model-based deduplication filters',comparisonHelp:'Hide raw candidates marked redundant by each checked model. Uncheck all to show raw candidates. Multiple selections hide the union of removed candidates; this combination is not any single model’s actual output.',
  removeModel:'Hide candidates marked redundant by {model}',reviewModelLabel:'Inspect model response:',rawCandidatesButton:'Clear all deduplication filters',
  modelName:'Model',frameCount:'{n} frames',inputWindow:'Input per endpoint',coverage:'Coverage on this page',caseKept:'This case: retained / raw',pageKept:'Covered cases: retained / raw',callsHeader:'Comparisons',
  notReviewed:'Not reviewed',kept:'Retained',removed:'Removed by deduplication',candidateTableTitle:'Candidate-by-candidate comparison and navigation',candidateHeader:'Raw candidate',frameHeader:'Action step',displayHeader:'Current display',visible:'Visible',hidden:'Hidden',
  rawAnswerLabel:'Original model JSON (unchanged; translations appear above)',rawMode:'Showing all {n} raw candidates.',
  singleMode:'{model}: {total} raw candidates → {kept} effective nodes; {removed} removed.',
  multiMode:'Combined display ({models}): union removes {removed}; showing {kept}/{total} candidates. See each model’s actual results in the table.',
  missingCoverage:'This model did not review this case. No candidates are hidden, and missing results are not treated as retention decisions.',
  missingRequested:'None of the checked models reviewed this case. Showing all {n} raw candidates.',
  currentCandidate:'Current raw candidate · {nodes}',currentRemovedCandidate:'Current raw candidate removed by deduplication · {nodes}',
  dedupUnavailable:'No deduplication record from this model for this case.',dedupPrompt:'Deduplication prompt (English translation)',
  footer:'Offline first-stage deduplication only; no new navigation scores. Coverage (frames per endpoint in parentheses): '+coverageText+'. '+(primaryModel==='astra3'?'Both the three-frame and historical five-frame versions use GPT-6 Astra / medium; only the observation window changed. Candidate reduction is not deduplication accuracy.':'See the table for each version’s model and input window. Candidate reduction is not deduplication accuracy.'),
  samplingHint:'The map, waveform and current-frame badge follow the filters above. Removed items appear only as raw candidates for comparison.',
  sourceStats:modelNames[primaryModel]+' · '+B.modelReviews[primaryModel].observation_offsets.length+' frames retained',pairCount:modelNames[primaryModel]+' · '+B.modelReviews[primaryModel].observation_offsets.length+' frames comparisons',latency:'Call latency',
  notice:`${modelNames[primaryModel]} · ${B.modelReviews[primaryModel].observation_offsets.length} frames: ${primaryVerdicts.same||0} same, ${primaryVerdicts.different||0} different, ${primaryVerdicts.uncertain||0} uncertain. Map colors encode raw JEV probability; the checkboxes below control model-based deduplication display.`,
});
if(['memory','terra6','astra61','terra61'].includes(primaryModel)){
  Object.assign(L.zh,{
    comparisonHelp:'勾选后隐藏该版本排除的候选。v003 会排除重复及不符合回退点定义的候选。全部取消可查看原始候选，多选时隐藏各版本排除集合的并集。',
    removeModel:'隐藏 {model} 排除的候选',removed:'已排除',callsHeader:'候选评审次数',inputWindow:'每候选观测偏移',
    dedupCount:'{total} 个原始候选 · 排除 {removed} 个 · 保留 {retained} 个 · 候选评审 {calls} 次',
    dedupEvents:'按顺序处理候选的记录',
    dedupReplay:'每条轨迹在独立会话中按时间顺序处理原始候选，程序更新保留清单后指定下一轮对照。这里展示完整结果，地图与画面进度条同步切换当前帧。',
    dedupPrompt:'本轮提示词',initializationPrompt:'会话初始化',eligibility_eligible:'符合回退点定义',
    eligibility_not_eligible:'不符合回退点定义',eligibility_uncertain:'回退点资格不确定',
    historicalImages:'历史会话图像',newImages:'本轮新增图像',skip_duplicate:'重复，跳过当前候选',
    reject_current:'不符合定义，排除当前候选',append_current:'保留当前候选',
    sourceStats:'GPT-6 Astra v003 保留',pairCount:'GPT-6 Astra v003 候选评审',
    notice:`GPT-6 Astra v003 已完成 ${B.summary.comparisons} 次候选评审。每例先初始化，每个候选只上传一次图像，再引用指定的历史回退点。地图颜色表示原始 JEV 概率。`,
    footer:'离线候选筛选。v003 使用会话历史，先判断回退点资格，再判断支路差异。重复时保留旧节点，不确定时保留并标记。各版本原始候选相同，筛选协议存在差异。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。',
  });
  Object.assign(L.en,{
    comparisonHelp:'Checked versions hide their excluded candidates. v003 excludes duplicates and candidates that fail the checkpoint definition. Uncheck all to inspect raw candidates. Multiple selections hide the union of exclusions.',
    removeModel:'Hide candidates excluded by {model}',removed:'Excluded',callsHeader:'Candidate reviews',inputWindow:'Observation offsets per candidate',
    dedupCount:'{total} raw candidates · {removed} excluded · {retained} retained · {calls} candidate reviews',
    dedupEvents:'Sequential candidate decisions',
    dedupReplay:'Each trajectory reviews raw candidates chronologically in its own conversation. The application updates the retained list and specifies the next comparison target. Full results are displayed while the synchronized sliders select the current frame.',
    dedupPrompt:'Prompt for this turn',initializationPrompt:'Conversation initialization',eligibility_eligible:'Meets the checkpoint definition',
    eligibility_not_eligible:'Does not meet the checkpoint definition',eligibility_uncertain:'Uncertain checkpoint eligibility',
    historicalImages:'Images from conversation history',newImages:'New images in this turn',skip_duplicate:'Duplicate, skip current candidate',
    reject_current:'Ineligible, exclude current candidate',append_current:'Retain current candidate',
    sourceStats:'GPT-6 Astra v003 retained',pairCount:'GPT-6 Astra v003 candidate reviews',
    notice:`GPT-6 Astra v003 completed ${B.summary.comparisons} candidate reviews. Each case starts with initialization. Each candidate supplies its images once and refers to the specified historical checkpoint. Map colors encode raw JEV probability.`,
    footer:'Offline candidate screening. v003 uses conversation history to assess checkpoint eligibility and then branch differences. Duplicates preserve the older checkpoint. Uncertain candidates are retained and marked. All versions share the raw candidates and use different screening protocols. Current and paired baseline SR and mean SPL are unavailable, with 0 scored episodes.',
  });
}
if(['terra6','astra61','terra61'].includes(primaryModel)){
  const label=modelNames[primaryModel], n=B.summary.comparisons;
  Object.assign(L.zh,{
    comparisonHelp:'勾选版本可隐藏它排除的候选。全部取消可查看原始候选，同时勾选多个版本会隐藏各自排除项的并集。',
    sourceStats:label+' 保留',pairCount:label+' 候选评审',
    notice:label+' 完成 '+n+' 次候选评审。Astra v006 使用相同规则，覆盖 '+B.modelReviews.astra6.coverage+'/'+B.cases.length+' 例。地图颜色表示原始 JEV 概率。',
    footer:'v006 先判断回退点资格，再判断是否属于同一次局部选路。重复时保留后一个。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。',
    replace_previous:'重复，以当前候选替换上一回退点'
  });
  Object.assign(L.en,{
    comparisonHelp:'Check a version to hide its exclusions. Clear all filters to see the raw candidates. Selecting multiple versions hides their combined exclusions.',
    sourceStats:label+' retained',pairCount:label+' candidate reviews',
    notice:label+' completed '+n+' candidate reviews. Astra v006 follows the same rules for '+B.modelReviews.astra6.coverage+' of '+B.cases.length+' trajectories. Map colors show the original JEV probability.',
    footer:'v006 assesses checkpoint eligibility and whether observations represent the same local route decision. A duplicate replaces its predecessor. Current and paired baseline SR and mean SPL are unavailable (0 scored episodes).',
    replace_previous:'Duplicate, replace the previous checkpoint with this candidate'
  });
}
if(['astra61','terra61'].includes(primaryModel)){
  const label=modelNames[primaryModel];
  L.zh.notice=label+' 逐一检查左、前、右方向，再判断回退点资格。共 '+B.summary.comparisons+' 个原始候选。';
  L.en.notice=label+' examines left, forward and right before assessing eligibility across '+B.summary.comparisons+' raw candidates.';
}
const initializationPanel=document.createElement('details'),initializationHeading=document.createElement('summary'),initializationText=document.createElement('pre');
initializationPanel.append(initializationHeading,initializationText);$('dedupPrompt').parentElement.after(initializationPanel);
initializationText.style.whiteSpace='pre-wrap';
for(const key of modelOrder){
  const label=document.createElement('label'),input=document.createElement('input'),span=document.createElement('span');
  input.type='checkbox';input.id='remove_'+key;input.checked=key===primaryModel;input.autocomplete='off';
  span.id='label_'+key;label.style.borderColor=modelColors[key];label.append(input,span);$('modelFilters').append(label);
  input.onchange=()=>{stop();const checked=enabledModelKeys();if(checked.length===1){reviewModelKey=checked[0];$('reviewModel').value=reviewModelKey;}D=B.modelReviews[reviewModelKey];draw();};
  const option=document.createElement('option');option.value=key;option.textContent=modelLabel(key);$('reviewModel').append(option);
}
$('reviewModel').onchange=()=>{stop();reviewModelKey=$('reviewModel').value;D=B.modelReviews[reviewModelKey];$('dedupDecision').value='';draw();};
$('showRawCandidates').onclick=()=>{for(const key of modelOrder)$('remove_'+key).checked=false;draw();};
const baseDisplayState=displayState;
displayState=function(){
  D=B.modelReviews[reviewModelKey];
  const keys=enabledModelKeys();$('nodeDeduplication').checked=keys.length>0;
  const state=baseDisplayState();
  for(const entry of state.versions){
    entry.nodes=entry.upstreamNodes.filter(node=>!keys.some(key=>removedBy(key,node.id)));
    entry.version={...entry.version,color:keys.length===1?modelColors[keys[0]]:'#64748b'};
  }
  return state;
};
renderCurrentNode=function(state){
  const all=state.versions.flatMap(v=>v.allNodes).filter(n=>n.index===index);
  const shown=state.versions.flatMap(v=>v.nodes).filter(n=>n.index===index);
  const badge=$('currentNodeStatus'),keys=enabledModelKeys();
  badge.hidden=!all.length;badge.dataset.state=shown.length?'node':all.length?'deduplicated':'none';
  const label=shown.length?(keys.length===1?'currentNode':'currentCandidate'):'currentRemovedCandidate';
  badge.textContent=all.length?t(label,{nodes:all.map(n=>n.id).join(' / ')}):'';
  $('rgb').classList.toggle('isNode',shown.length>0);
};
const baseRenderDedup=renderDedup;
renderDedup=function(state){
  baseRenderDedup(state);
  const record=modelRecord(reviewModelKey),decision=record?.decisions[$('dedupDecision').selectedIndex];
  if(!record)$('dedupStatus').textContent=t('missingCoverage');
  $('rawAnswer').hidden=!decision?.needs_model;
  $('rawAnswerText').textContent=decision?.raw_text||'';
  initializationPanel.hidden=!D.initialization_en;
  if(D.initialization_en){
    initializationHeading.textContent=t('initializationPrompt');
    initializationText.textContent=lang==='zh'?D.initialization_zh:D.initialization_en;
    $('dedupPrompt').textContent=decision?(lang==='zh'?decision.prompt_zh:decision.prompt_en):(lang==='zh'?D.prompt_zh:D.prompt_en);
    const verdict=d=>t('eligibility_'+d.eligibility)+' · '+t(d.action);
    [...$('dedupDecision').options].forEach((option,i)=>{const d=record.decisions[i];option.textContent=`${d.previous_id||'—'} → ${d.current_id} · F${d.current_frame} · ${verdict(d)}`;});
    [...$('dedupEvents').children].forEach((li,i)=>{const d=record.decisions[i];li.textContent=`${d.current_id} / F${d.current_frame} · ${verdict(d)} · [${d.active_ids_after.join(', ')}]`;});
    if(decision?.answer){
      const li=document.createElement('li');li.textContent=t('eligibility_'+decision.eligibility)+' · '+wording(decision.answer.eligibility_reason);
      $('dedupBranches').prepend(li);
    }
    for(const heading of $('dedupEvidence').querySelectorAll('p')){
      heading.textContent+=' · '+t(heading.textContent.startsWith('A ')||decision?.current_images_from_history?'historicalImages':'newImages');
    }
  }
  for(const row of document.querySelectorAll('.dedupEvidenceRow'))row.style.gridTemplateColumns='repeat('+row.children.length+',minmax(0,1fr))';
};
function tableRow(table,values,header=false){
  const tr=document.createElement('tr');for(const value of values){const td=document.createElement(header?'th':'td');
    if(value instanceof Node)td.append(value);else td.textContent=value;tr.append(td);}table.append(tr);return tr;
}
function updateComparison(state){
  const keys=enabledModelKeys(),raw=modelRecord(primaryModel).nodes;
  for(const key of modelOrder){
    const record=modelRecord(key);$('remove_'+key).disabled=!record;
    [...$('reviewModel').options].find(o=>o.value===key).textContent=modelLabel(key);
    $('label_'+key).textContent=t('removeModel',{model:modelLabel(key)})+(!record?' · '+t('notReviewed'):'');
  }
  const hidden=raw.filter(n=>keys.some(key=>removedBy(key,n.id))).length;
  const requested=modelOrder.filter(k=>$('remove_'+k).checked);
  $('combinationStatus').textContent=keys.length===1?t('singleMode',{model:modelLabel(keys[0]),total:raw.length,kept:raw.length-hidden,removed:hidden}):
    keys.length>1?t('multiMode',{models:keys.map(k=>modelLabel(k)).join(' + '),total:raw.length,kept:raw.length-hidden,removed:hidden}):
    t(requested.length?'missingRequested':'rawMode',{n:raw.length});
  const summary=$('modelSummary');summary.replaceChildren();tableRow(summary,[t('modelName'),t('inputWindow'),t('coverage'),t('caseKept'),t('pageKept'),t('callsHeader')],true);
  for(const key of modelOrder){const model=B.modelReviews[key],record=modelRecord(key);
    tableRow(summary,[modelNames[key],model.observation_offsets.join(', '),model.coverage+'/'+B.cases.length,record?record.summary.retained+'/'+record.summary.candidates:t('notReviewed'),
      model.summary.retained+'/'+model.summary.candidates,record?record.summary.model_calls:'—']);}
  const table=$('candidateComparison');table.replaceChildren();tableRow(table,[t('candidateHeader'),t('frameHeader'),...modelOrder.map(k=>modelLabel(k)),t('displayHeader')],true);
  for(const node of raw){
    const jump=document.createElement('button');jump.textContent=node.id;jump.onclick=()=>{stop();seek(node.index);};
    const cells=modelOrder.map(key=>{const span=document.createElement('span'),record=modelRecord(key);
      const label=!record?'notReviewed':removedBy(key,node.id)?'removed':'kept';span.textContent=t(label);span.className=!record?'unreviewed':label;return span;});
    tableRow(table,[jump,'F'+node.index,...cells,t(keys.some(k=>removedBy(k,node.id))?'hidden':'visible')]);
  }
}
const baseDraw=draw;
draw=function(){baseDraw();updateComparison(displayState());};
// Keep both sliders and the current trajectory/frame unchanged when switching models.
window.JEV_LAB.displayState=()=>displayState();window.JEV_LAB.draw=()=>draw();
window.JEV_LAB.comparison={models:B.modelReviews,enabled:enabledModelKeys,review:()=>reviewModelKey};
L.zh.retainedCount=L.zh.sourceStats;L.en.retainedCount=L.en.sourceStats;
$('dedupAudit').open=true;
updateLanguage();
