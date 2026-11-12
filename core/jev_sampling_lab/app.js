'use strict';
const B=JSON.parse(document.getElementById('payload').textContent),$=id=>document.getElementById(id);
const E=window.JEV_NODE_ELIMINATION_DATA||null;
const D=window.JEV_NODE_DEDUP_DATA||null;
const L={
  zh:{title:'JEV · 滤波与采样',subtitle:'本地离线迭代 · 逐帧回放',cases:'轨迹',all:'全部',failure:'原导航失败',success:'原导航成功',frames:'帧',
    events:'错误事件',trajectories:'不同轨迹',calls:'有效 JEV 反馈',mean:'JEV 平均概率',map:'俯视地图 · JEV 回退点概率',current:'当前观测',
    mapProgress:'地图进度',imageProgress:'画面进度',play:'顺序回放',pause:'暂停',prev:'上一步',next:'下一步',restart:'从头回放',reference:'参考路线',
    plot:'JEV 概率波形',curveTitle:'曲线显示',raw:'JEV 原始概率',filtered:'滤波结果',window:'有效窗口 N',delay:'总延迟 D',
    curveHint:'曲线开关只控制折线显示，采样请在下方单独勾选。',samplingTitle:'采样版本',samplingHint:'勾选某个版本后，采样点才会同步出现在波形图和俯视地图上。',
    samplingOff:'尚未勾选采样版本。',noSamples:'本条轨迹没有已确认的采样点。',sampleCount:'显示 {n} 个点',
    v001Title:'v001 · 在线采样',v001Description:'局部峰 · 双阈值滞回 · 高分区域间隔采样',
    timeline:'当前查看 F{t} · 平滑等待 {s} 步。',sampleDelay:'算法中的采样确认再等待 {h} 步。',
    curvePending:'完整波形用于离线查看；浅灰末尾为滤波尚未确认的部分。',samplesPending:'离线查看完整采样结果；拖动进度条只切换当前帧，节点始终显示。',
    sampleTiming:'候选位置 → 确认时刻',candidate:'候选位置',confirmed:'确认时刻',
    notice:'地图颜色表示 JEV 原始概率；颜色越深，概率越高。波形、地图路线和勾选的采样节点始终完整显示；进度条移动当前帧标记并切换 RGB。',
    source:'34 个错误事件 / 33 条不同轨迹。使用已有 JEV 反馈进行本地回放。',
    probability:'JEV 回退点概率',noScore:'未评分',inputFrames:'本次实际输入',instruction:'原任务指令',
    prompt:'当前 JEV 问题',promptChinese:'中文翻译',promptEnglish:'英文 · 实际模型输入',
    protocol:'输入与回放说明',protocolInput:'JEV 只输入最多最近三帧 t−2,t−1,t 的 RGB，回答一个 fallback_point Noul；不输入任务、动作、位置、地图、成败、标注、参考路线或旧回答。',
    protocolReplay:'完整波形、地图路线和全部采样节点用于离线查看，不随进度条裁剪。采样结果由原在线采样器逐帧回放生成，每次仍只接收当步及之前的反馈，确认时刻保留在节点记录中。网页统一展示整条记录的已确认节点及已有审核结果，不模拟实时到达过程。末尾不足等待步数的结果仍保留待确认。',
    rules:'v001 采样规则',ruleText:'局部峰：平滑值至少 0.45，两侧局部落差至少 0.03。连续 2 帧达到 0.60 进入高分区域，连续 2 帧低于 0.45 退出；区域内每隔至少 5 帧保留候选。起点原始概率至少 0.45 可成为候选。所有点至少间隔 3 帧，先确认的点优先。默认总延迟 5 步；D=0 时停用局部峰分支。',
    rulesNote:'本页沿用已实现的滤波和 v001 采样规则；阈值尚待质量复核。修改 N / D 会逐帧重新回放整条记录。',
    review:'复核',unclassified:'未分类',high:'概率偏高',low:'概率偏低',reasonable:'概率合理',other:'其他',notePlaceholder:'记录本帧判断依据',
    noteHint:'意见保存在当前浏览器，可通过左侧按钮导出。',export:'导出复核意见',footer:'本页完全离线 · 所有资源均在本地',
    caseStats:'已到达 {n} / {total} 帧 · 当前有效 JEV {j} 条',kind_initial:'起点候选',kind_peak:'局部峰',kind_entry:'进入高分区域',kind_plateau:'区域间隔采样'},
  en:{title:'JEV · Filtering and sampling',subtitle:'Local offline iteration · Frame-by-frame replay',cases:'Trajectories',all:'All',failure:'Native failure',success:'Native success',frames:'frames',
    events:'Error events',trajectories:'Unique trajectories',calls:'Valid JEV observations',mean:'Mean JEV probability',map:'Top-down map · JEV fallback probability',current:'Current observation',
    mapProgress:'Map progress',imageProgress:'Image progress',play:'Play',pause:'Pause',prev:'Previous',next:'Next',restart:'Replay from start',reference:'Reference route',
    plot:'JEV probability waveform',curveTitle:'Curve display',raw:'Raw JEV probability',filtered:'Filtered result',window:'Effective window N',delay:'Total delay D',
    curveHint:'Curve switches only control the lines. Enable sampling separately below.',samplingTitle:'Sampling versions',samplingHint:'Check a version to show its sample points on both the waveform and the top-down map.',
    samplingOff:'No sampling version is selected.',noSamples:'No confirmed samples in this trajectory.',sampleCount:'{n} displayed points',
    v001Title:'v001 · Online sampling',v001Description:'Local peaks · Dual-threshold hysteresis · High-region interval sampling',
    timeline:'Viewing F{t} · smoothing lag {s} steps.',sampleDelay:'The algorithm confirms samples after {h} additional steps.',
    curvePending:'Full waveform for offline review; the gray tail is still awaiting filter confirmation.',samplesPending:'Full sampling results for offline review. Moving the slider changes the current frame; all nodes stay visible.',
    sampleTiming:'Candidate frame → confirmation frame',candidate:'Candidate',confirmed:'Confirmed at',
    notice:'Map colors encode raw JEV probability; darker means higher. Full waveforms, map routes and enabled sample nodes stay visible; the slider moves the current-frame markers and switches RGB.',
    source:'34 error events / 33 unique trajectories. Local replay of recorded JEV feedback.',
    probability:'JEV fallback probability',noScore:'Unscored',inputFrames:'Actual model input frames',instruction:'Original task instruction',
    prompt:'Current JEV question',promptChinese:'Chinese translation',promptEnglish:'English · actual model input',
    protocol:'Input and replay notes',protocolInput:'JEV receives up to three recent RGB frames t−2,t−1,t and answers one fallback_point Noul. No instruction, actions, position, map, outcome, annotations, reference route or previous answers are provided.',
    protocolReplay:'Full waveforms, routes and all sample nodes remain visible for offline review. The unchanged online sampler is replayed frame by frame, receiving only feedback up to each input step and preserving original confirmation times. This viewer displays all confirmed nodes and cached reviews from the recording, without simulating their real-time arrival. The unconfirmed tail is not padded.',
    rules:'v001 sampling rules',ruleText:'Local peaks: smoothed value at least 0.45 and local drop on both sides at least 0.03. Enter a high region after 2 consecutive values at least 0.60; exit after 2 consecutive values below 0.45. Keep candidates at least 5 frames apart within the region. An initial raw probability at least 0.45 can produce a candidate. All points are at least 3 frames apart; earlier commits take priority. Default total delay is 5 steps. D=0 disables the local-peak branch.',
    rulesNote:'This page retains the implemented filter and v001 sampling rules; candidate quality still requires review. Changing N / D replays the whole recording frame by frame.',
    review:'Review',unclassified:'Unclassified',high:'Probability too high',low:'Probability too low',reasonable:'Probability reasonable',other:'Other',notePlaceholder:'Record the basis for your judgment',
    noteHint:'Notes stay in this browser; export them with the button on the left.',export:'Export review notes',footer:'Fully offline · All resources are local',
    caseStats:'Received {n} / {total} frames · {j} valid JEV observations so far',kind_initial:'Initial candidate',kind_peak:'Local peak',kind_entry:'High-region entry',kind_plateau:'High-region interval'}
};
Object.assign(L.zh,{
  elimination:'节点消除',eliminationHint:'在勾选的在线采样节点中，仅隐藏模型明确剔除的点；未评估和信息不足的点保留。',
  eliminationOff:'未启用节点消除，显示原始采样结果。',eliminationNeedSampling:'请先勾选一个在线采样版本。',
  eliminationUnavailable:'当前轨迹或采样参数尚未评估，保留全部采样点。本批次：第 1、2、3、4、7 条，N=7、D=5。',
  eliminationCount:'当前 {total} 个候选 · 已审核 {reviewed} 个 · 剔除 {reject} 个 · 信息不足 {uncertain} 个 · 显示 {shown} 个',
  eliminationAudit:'查看节点审核记录',eliminationNode:'候选节点',eliminationPrompt:'节点消除提示词（中文实际输入）',
  eliminationReplay:'本地回放使用已完成的五帧审核结果；模型调用耗时另行显示。',
  decision_keep:'保留',decision_reject:'剔除',decision_uncertain:'信息不足',decision_error:'调用失败',decision_pending:'未评估',
  eliminationReviewed:'已审核',eliminationMissing:'缺失',eliminationCenter:'候选帧',eliminationEmpty:'当前没有可查看的已确认采样点。',
  eliminationLatency:'调用耗时',eliminationSeconds:'秒',eliminationReady:'输入齐备于',eliminationNoResult:'此节点尚无有效的模型结论，保持显示。',
  currentNode:'当前位于节点 · {nodes}',currentNodeRemoved:'当前候选已消除 · {nodes}'
});
Object.assign(L.en,{
  elimination:'Node elimination',eliminationHint:'Hide only explicitly rejected nodes from enabled samplers. Unreviewed and uncertain candidates remain visible.',
  eliminationOff:'Node elimination is off. Original samples are displayed.',eliminationNeedSampling:'Enable an online sampling version first.',
  eliminationUnavailable:'This trajectory or configuration has not been reviewed. All samples remain visible. Batch: cases 1, 2, 3, 4, 7; N=7, D=5.',
  eliminationCount:'{total} candidates · {reviewed} reviewed · {reject} rejected · {uncertain} uncertain · {shown} displayed',
  eliminationAudit:'Inspect node reviews',eliminationNode:'Candidate',eliminationPrompt:'Elimination prompt (Chinese actual input)',
  eliminationReplay:'Local replay uses completed five-frame reviews; API latency is shown separately.',
  decision_keep:'Keep',decision_reject:'Reject',decision_uncertain:'Uncertain',decision_error:'Request failed',decision_pending:'Unreviewed',
  eliminationReviewed:'Reviewed',eliminationMissing:'Missing',eliminationCenter:'Candidate frame',eliminationEmpty:'No confirmed samples to inspect yet.',
  eliminationLatency:'API latency',eliminationSeconds:'s',eliminationReady:'Inputs ready at',eliminationNoResult:'No valid verdict for this node. It remains visible.',
  currentNode:'Current node · {nodes}',currentNodeRemoved:'Current candidate removed · {nodes}'
});

Object.assign(L.zh,{
  dedup:'节点去重',dedupHint:'与上一个已建立节点相隔不超过 8 步，且确认看到同一组分支时，删除旧节点、保留新节点。',
  dedupOff:'未启用节点去重。',dedupAudit:'查看逐节点去重记录',dedupPair:'当前候选',dedupPrompt:'去重提示词（中文实际输入）',
  dedupUnavailable:'当前采样节点或参数与本批输入不一致，尚无适用的去重结果，保留当前节点。已评估全部 34 条，N=7、D=5。',
  dedupCount:'原有 {total} 个 · 去掉旧节点 {removed} 个 · 去重后 {retained} 个 · 模型调用 {calls} 次',
  dedupReplay:'各 case 独立并行；每个 case 依次取已有采样节点，等待判断并更新状态后再处理下一个。此处展示完整结果，不受进度条影响。',
  dedupEvents:'按顺序建立与替换的记录',relation_same:'重复，替换旧节点',relation_different:'不同，保留两者',relation_uncertain:'不确定，保留两者',relation_not_compared:'直接建立',
  dedupEmpty:'当前没有适用的去重记录。',dedupGap:'步数差',dedupMatched:'对应分支',dedupAOnly:'仅 A 提供',dedupBOnly:'仅 B 提供',
  currentDedup:'当前节点已去重 · {nodes}'
});
Object.assign(L.en,{
  dedup:'Node deduplication',dedupHint:'Compare with the last established node within 8 steps. Identical branch information replaces the old node with the new one.',
  dedupOff:'Node deduplication is off.',dedupAudit:'Inspect sequential decisions',dedupPair:'Current candidate',dedupPrompt:'Deduplication prompt (actual Chinese input)',
  dedupUnavailable:'No applicable run for these candidates or parameters. Preserve current nodes. All 34 cases evaluated; N=7, D=5.',
  dedupCount:'{total} original · {removed} old nodes removed · {retained} retained · {calls} model calls',
  dedupReplay:'Independent cases run in parallel. Within each case, consume existing nodes sequentially and commit each decision before proceeding. Full results remain visible at every slider position.',
  dedupEvents:'Sequential establishment and replacement log',relation_same:'Same: replace previous',relation_different:'Different: keep both',relation_uncertain:'Uncertain: keep both',relation_not_compared:'Establish directly',
  dedupEmpty:'No applicable deduplication record.',dedupGap:'Step gap',dedupMatched:'Matched branch',dedupAOnly:'A only',dedupBOnly:'B only',
  currentDedup:'Current node replaced · {nodes}'
});
// Each enabled version owns a cached offline replay of its streaming sampler.
const SAMPLING_VERSIONS=Object.freeze([
  Object.freeze({id:'v001',title:'v001Title',description:'v001Description',color:'#0891b2',create:options=>new JevOnlineSampler(options)})
]);
let lang='zh',ci=0,index=0,timer=null,drawEpoch=0,sampleHitPoints=[];
const t=(key,values={})=>Object.entries(values).reduce((s,[k,v])=>s.replaceAll('{'+k+'}',String(v)),L[lang][key]??key);
const c=()=>B.cases[ci],row=()=>c().frames[index],options=()=>({window:Number($('filterWindow').value),delay:Number($('streamDelay').value)});
const jev=frame=>{const p=frame.jev?.probability_yes;return Number.isFinite(p)&&p>=0&&p<=1?p:null;};
const filterSessions=new Map(),sampleSessions=new Map(),mapCache=new Map(),fullCurveCache=new Map();
const prefixKey=()=>ci+':'+$('filterWindow').value+':'+$('streamDelay').value;
function filterSession(){
  const key=prefixKey();let session=filterSessions.get(key);
  if(!session||session.cursor>index){session={model:new JevOnlineFilter(options()),cursor:-1,values:[],records:[]};filterSessions.set(key,session);}
  while(session.cursor<index){const frame=++session.cursor,result=session.model.push(jev(c().frames[frame]),frame);
    if(result){session.values[result.index]=result.value;session.records.push(result);}}
  return session;
}
// Offline overview only. Never pass these full-trajectory values to a sampler.
function fullCurve(){
  const key=prefixKey();let values=fullCurveCache.get(key);
  if(!values){
    values=[];const model=new JevOnlineFilter(options());
    for(const frame of c().frames){const result=model.push(jev(frame),frame.frame);if(result)values[result.index]=result.value;}
    Object.freeze(values);fullCurveCache.set(key,values);
  }
  return values;
}
function fullSampling(version){
  const key=version.id+':'+prefixKey();let session=sampleSessions.get(key);
  if(!session){
    session={model:version.create(options()),cursor:-1,nodes:[]};
    // Offline presentation only: call the unchanged streaming algorithm in order.
    // Do not flush the tail or recompute/replace previously emitted nodes.
    for(const frame of c().frames){const result=session.model.push(jev(frame),frame.frame);session.cursor=frame.frame;if(result.node)session.nodes.push(result.node);}
    Object.freeze(session.nodes);sampleSessions.set(key,session);
  }
  return session;
}
// Decisions belong to an exact sampler configuration and exact image window.
// They only affect display; the online sampler and its immutable nodes are untouched.
function eliminationCase(version){
  if(!E||E.source_tag!==B.tag||E.sampler_version!==version.id)return null;
  if(Object.entries(options()).some(([key,value])=>E.sampler_config[key]!==value))return null;
  return E.cases.find(item=>item.case_index===ci&&item.episode_id===c().episode_id&&item.real_episode_id===c().real_episode_id)||null;
}
function nodeReview(version,node){
  const item=eliminationCase(version),record=item?.nodes.find(value=>value.index===node.index&&value.id===node.id&&value.emittedAt===node.emittedAt);
  if(!record||record.ready_at_frame>=c().frames.length)return null;
  if(record.images.some(image=>image.missing?!!c().frames[image.frame]:c().frames[image.frame]?.image!==image.image_id))return null;
  return record;
}
const reviewDecision=record=>record?.status==='ok'?record.answer.decision:record?.status==='error'?'error':'pending';
const eliminationVersionName=()=>E?(lang==='zh'?E.display_name_zh:E.display_name_en)||E.elimination_version||'v001':'';
function displayState(){
  const filter=filterSession();
  const versions=SAMPLING_VERSIONS.filter(v=>$('sample_'+v.id).checked).map(version=>{
    const session=fullSampling(version),allNodes=session.nodes;
    const upstreamNodes=$('nodeElimination').checked?allNodes.filter(node=>reviewDecision(nodeReview(version,node))!=='reject'):allNodes;
    const dedupRecord=dedupCase(version,upstreamNodes);
    const nodes=$('nodeDeduplication').checked&&dedupRecord?upstreamNodes.filter(node=>dedupRecord.final_active_ids.includes(node.id)):upstreamNodes;
    return {version,nodes,allNodes,upstreamNodes,dedupRecord,state:session.model.state()};
  });
  return {values:fullCurve(),filter:filter.model.state(),versions};
}
function renderCurrentNode(state){
  const active=state.versions.flatMap(({version,nodes})=>nodes.filter(node=>node.index===index).map(node=>nodeLabel(node,version,state.versions.length)));
  const removed=!active.length&&$('nodeElimination').checked?state.versions.flatMap(({version,allNodes})=>allNodes.filter(node=>node.index===index&&reviewDecision(nodeReview(version,node))==='reject').map(node=>nodeLabel(node,version,state.versions.length))):[];
  const replaced=!active.length&&$('nodeDeduplication').checked?state.versions.flatMap(({dedupRecord})=>(dedupRecord?.decisions||[]).filter(d=>d.action==='replace_previous'&&d.previous_frame===index).map(d=>`${d.previous_id} → ${d.current_id}`)):[];
  const badge=$('currentNodeStatus');badge.hidden=!active.length&&!removed.length&&!replaced.length;
  badge.dataset.state=active.length?'node':removed.length?'removed':replaced.length?'deduplicated':'none';
  badge.textContent=active.length?t('currentNode',{nodes:active.join(' / ')}):removed.length?t('currentNodeRemoved',{nodes:removed.join(' / ')}):replaced.length?t('currentDedup',{nodes:replaced.join(' / ')}):'';
  $('rgb').classList.toggle('isNode',active.length>0);
}
function renderElimination(state){
  const entries=state.versions.flatMap(({version,allNodes})=>allNodes.map(node=>({version,node,record:nodeReview(version,node)})));
  const reviewed=entries.filter(entry=>entry.record?.status==='ok'),reject=reviewed.filter(entry=>entry.record.answer.decision==='reject').length;
  const uncertain=reviewed.filter(entry=>entry.record.answer.decision==='uncertain').length;
  const status=!state.versions.length?t('eliminationNeedSampling'):!state.versions.some(({version})=>eliminationCase(version))?t('eliminationUnavailable'):
    t('eliminationCount',{total:entries.length,reviewed:reviewed.length,reject,uncertain,shown:state.versions.reduce((sum,v)=>sum+v.nodes.length,0)});
  $('eliminationStatus').textContent=(E?eliminationVersionName()+' · ':'')+(!$('nodeElimination').checked?t('eliminationOff')+' ':'')+status;
  const select=$('eliminationNode'),selected=select.value;select.replaceChildren();
  for(const entry of entries){const option=document.createElement('option');option.value=`${ci}:${entry.version.id}:${entry.node.index}`;
    option.textContent=`${entry.node.id} · F${entry.node.index} · ${t('decision_'+reviewDecision(entry.record))}`;select.append(option);}
  if([...select.options].some(option=>option.value===selected))select.value=selected;
  const chosen=entries[select.selectedIndex];$('eliminationEvidence').replaceChildren();$('eliminationRoutes').replaceChildren();
  $('eliminationPrompt').textContent=E?.prompt_zh||'';
  if(!chosen){$('eliminationReason').textContent=t('eliminationEmpty');$('eliminationMeta').textContent='';return;}
  const record=chosen.record;$('eliminationReason').textContent=record?.answer?.reason||record?.error||t('eliminationNoResult');
  $('eliminationMeta').textContent=record?`${eliminationVersionName()} · ${E.model} · ${t('eliminationReady')} F${record.ready_at_frame}`+(Number.isFinite(record.elapsed_seconds)?` · ${t('eliminationLatency')} ${record.elapsed_seconds} ${t('eliminationSeconds')}`:''):'';
  for(const route of record?.answer?.routes||[]){const li=document.createElement('li');li.textContent=`${route.description} (${route.evidence_frames.join(', ')})`;$('eliminationRoutes').append(li);}
  for(const frame of record?.images||[]){const figure=document.createElement('figure'),caption=document.createElement('figcaption');
    caption.textContent=`${frame.label} · `+(frame.missing?t('eliminationMissing'):`F${frame.frame}`)+(frame.label==='F0'?' · '+t('eliminationCenter'):'');
    if(frame.label==='F0')figure.className='candidateFrame';
    if(!frame.missing){const link=document.createElement('a'),img=document.createElement('img');link.href=B.images[frame.image_id];link.target='_blank';link.rel='noopener';img.src=link.href;img.alt=caption.textContent;img.loading='lazy';link.append(img);figure.append(link);}
    figure.append(caption);$('eliminationEvidence').append(figure);}
}
function dedupCase(version,nodes){
  if(!D||D.source_tag!==B.tag||D.sampler_version!==version.id)return null;
  if(Object.entries(options()).some(([key,value])=>D.sampler_config[key]!==value))return null;
  const record=D.cases.find(item=>item.case_index===ci&&item.episode_id===c().episode_id&&item.real_episode_id===c().real_episode_id);
  if(!record||record.nodes.length!==nodes.length)return null;
  if(record.nodes.some((n,i)=>n.id!==nodes[i].id||n.index!==nodes[i].index||n.emittedAt!==nodes[i].emittedAt||n.images.some(im=>im.missing?!!c().frames[im.frame]:c().frames[im.frame]?.image!==im.image_id)))return null;
  return record;
}
function renderDedup(state){
  const record=state.versions.find(v=>v.dedupRecord)?.dedupRecord;
  $('dedupStatus').textContent=(!$('nodeDeduplication').checked?t('dedupOff')+' ':'')+(!state.versions.length?t('eliminationNeedSampling'):!record?t('dedupUnavailable'):t('dedupCount',{total:record.summary.candidates,removed:record.summary.removed,retained:record.summary.retained,calls:record.summary.model_calls}));
  const select=$('dedupDecision'),selected=select.value;select.replaceChildren();
  for(const d of record?.decisions||[]){const option=document.createElement('option');option.value=`${ci}:${d.current_id}`;option.textContent=`${d.previous_id||'—'} → ${d.current_id} · F${d.current_frame} · ${t('relation_'+d.relation)}`;select.append(option);}
  if([...select.options].some(o=>o.value===selected))select.value=selected;
  for(const id of ['dedupEvidence','dedupBranches','dedupEvents'])$(id).replaceChildren();
  $('dedupPrompt').textContent=D?.prompt_zh||'';
  for(const d of record?.decisions||[]){const li=document.createElement('li');li.textContent=`${d.current_id} / F${d.current_frame}: ${t('relation_'+d.relation)}`+(d.action==='replace_previous'?` (${d.previous_id} → ${d.current_id})`:'')+` · [${d.active_ids_after.join(', ')}]`;$('dedupEvents').append(li);}
  const d=record?.decisions[select.selectedIndex];
  $('dedupReason').textContent=d?.reason||t('dedupEmpty');
  $('dedupMeta').textContent=d?`${d.previous_id||'—'} → ${d.current_id} · ${t('dedupGap')}: ${d.step_gap??'—'}`+(d.needs_model?` · ${D.model} · ${d.elapsed_seconds} ${t('eliminationSeconds')}`:''):'';
  if(!d)return;
  for(const branch of d.answer?.matched_branches||[]){const li=document.createElement('li');li.textContent=`${t('dedupMatched')}: ${branch.description} (${branch.a_frames.join(', ')} ↔ ${branch.b_frames.join(', ')})`;$('dedupBranches').append(li);}
  for(const [key,label]of [['a_only','dedupAOnly'],['b_only','dedupBOnly']])for(const desc of d.answer?.[key]||[]){const li=document.createElement('li');li.textContent=`${t(label)}: ${desc}`;$('dedupBranches').append(li);}
  if(!d.needs_model)return;
  for(const [group,id]of [['A',d.previous_id],['B',d.current_id]]){
    const node=record.nodes.find(n=>n.id===id),heading=document.createElement('p'),row=document.createElement('div');
    heading.className='muted';heading.textContent=`${group} · ${id} · F${node.index}`;row.className='dedupEvidenceRow';
    for(const im of node.images){const figure=document.createElement('figure'),caption=document.createElement('figcaption');
      const label=group+im.label.slice(1);caption.textContent=`${label} · `+(im.missing?t('eliminationMissing'):`F${im.frame}`);
      if(im.label==='F0')figure.className='candidateFrame';
      if(!im.missing){const link=document.createElement('a'),img=document.createElement('img');link.href=B.images[im.image_id];link.target='_blank';link.rel='noopener';img.src=link.href;img.alt=caption.textContent;img.loading='lazy';link.append(img);figure.append(link);}
      figure.append(caption);row.append(figure);
    }
    $('dedupEvidence').append(heading,row);
  }
}

function createVersionControls(){
  for(const version of SAMPLING_VERSIONS){
    const label=document.createElement('label');label.className='samplingOption';
    const input=document.createElement('input');input.type='checkbox';input.id='sample_'+version.id;input.checked=false;input.dataset.version=version.id;
    const body=document.createElement('span');body.className='samplingCopy';
    const title=document.createElement('strong');title.dataset.i18n=version.title;
    const description=document.createElement('span');description.className='muted';description.dataset.i18n=version.description;
    const count=document.createElement('span');count.id='count_'+version.id;count.className='sampleCount';
    body.append(title,description);label.append(input,body,count);label.style.setProperty('--sample-color',version.color);
    $('samplingVersions').append(label);input.onchange=()=>{stop();draw();};
  }
}
function stop(){if(timer!==null)clearInterval(timer);timer=null;$('play').textContent=t('play');}
function canvas(id){const el=$(id),box=el.getBoundingClientRect(),dpr=window.devicePixelRatio||1;el.width=Math.round(box.width*dpr);el.height=Math.round(box.height*dpr);const ctx=el.getContext('2d');ctx.scale(dpr,dpr);return {ctx,w:box.width,h:box.height};}
function mapImage(scene,onload){
  const existing=mapCache.get(scene);if(existing){if(existing.complete)onload();else existing.addEventListener('load',onload,{once:true});return;}
  const image=new Image();mapCache.set(scene,image);image.onload=onload;image.src=B.images[B.maps[scene].image];
}
function jevColor(value){if(value===null)return '#9aa5b1';const light=[250,224,199],dark=[139,29,29];return 'rgb('+light.map((x,i)=>Math.round(x+(dark[i]-x)*value)).join(',')+')';}
function nodeLabel(node,version,selectedCount){return selectedCount>1?version.id+'·'+node.id:node.id;}
function drawMap(state){
  const {ctx,w,h}=canvas('jevMap'),geometry=B.maps[c().scene].geometry,image=mapCache.get(c().scene);
  const scale=Math.min(w/geometry.width,h/geometry.height),ox=(w-geometry.width*scale)/2,oy=(h-geometry.height*scale)/2;
  const xy=p=>[ox+(p[0]-geometry.low[0])/geometry.resolution*scale,oy+(geometry.high[1]-p[1])/geometry.resolution*scale];
  ctx.clearRect(0,0,w,h);if(image?.complete&&image.naturalWidth)ctx.drawImage(image,ox,oy,geometry.width*scale,geometry.height*scale);
  if($('reference').checked&&c().reference_path?.length){ctx.strokeStyle='#d19a2c';ctx.lineWidth=3;ctx.setLineDash([7,5]);ctx.beginPath();c().reference_path.forEach((p,i)=>i?ctx.lineTo(...xy(p)):ctx.moveTo(...xy(p)));ctx.stroke();}
  ctx.lineCap='round';ctx.lineJoin='round';ctx.lineWidth=5;
  for(let i=0;i<c().frames.length-1;i++){const value=jev(c().frames[i]);ctx.strokeStyle=jevColor(value);ctx.setLineDash(value===null?[5,4]:[]);ctx.beginPath();ctx.moveTo(...xy(c().frames[i].position));ctx.lineTo(...xy(c().frames[i+1].position));ctx.stroke();}
  ctx.setLineDash([]);ctx.font='bold 10px CrossingSans,sans-serif';ctx.textBaseline='middle';
  for(const {version,nodes} of state.versions)for(const node of nodes){
    const [x,y]=xy(c().frames[node.index].position),label=nodeLabel(node,version,state.versions.length);
    ctx.beginPath();ctx.arc(x,y,4,0,2*Math.PI);ctx.fillStyle=version.color;ctx.fill();ctx.lineWidth=1.5;ctx.strokeStyle='#fff';ctx.stroke();
    ctx.lineWidth=2.5;ctx.strokeText(label,x+5,y-6);ctx.fillText(label,x+5,y-6);
  }
  ctx.textBaseline='alphabetic';const [x,y]=xy(row().position);ctx.beginPath();ctx.arc(x,y,7,0,2*Math.PI);ctx.fillStyle='#e11d48';ctx.fill();ctx.lineWidth=2;ctx.strokeStyle='#fff';ctx.stroke();
}
function drawPlot(state){
  const {ctx,w,h}=canvas('scorePlot'),margin={left:36,right:28,top:16,bottom:29},last=Math.max(1,c().frames.length-1);
  const x=i=>margin.left+i/last*(w-margin.left-margin.right),y=p=>h-margin.bottom-p*(h-margin.top-margin.bottom),axisY=y(0);
  ctx.clearRect(0,0,w,h);ctx.font='11px CrossingSans,sans-serif';
  const curveEnd=state.values.length-1;
  if($('showFiltered').checked&&curveEnd<last){ctx.fillStyle='#edf2f7';ctx.fillRect(x(Math.max(0,curveEnd+1)),margin.top,Math.max(1,x(last)-x(Math.max(0,curveEnd+1))),axisY-margin.top);}
  for(let i=0;i<=4;i++){const v=i/4;ctx.strokeStyle='#e3e9ef';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(margin.left,y(v));ctx.lineTo(w-margin.right,y(v));ctx.stroke();ctx.fillStyle='#65788a';ctx.fillText(String(v),4,y(v)+4);}
  function line(getter,color,width){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();let active=false;
    for(let i=0;i<c().frames.length;i++){const p=getter(i);if(p===null||p===undefined){active=false;continue;}active?ctx.lineTo(x(i),y(p)):ctx.moveTo(x(i),y(p));active=true;}ctx.stroke();}
  if($('showRawJev').checked)line(i=>jev(c().frames[i]),'#b33a3a',2);
  if($('showFiltered').checked)line(i=>state.values[i],'#2563eb',3);
  sampleHitPoints=[];
  for(const {version,nodes}of state.versions){ctx.strokeStyle=version.color;ctx.fillStyle=version.color;ctx.lineWidth=1;ctx.font='9px CrossingSans,sans-serif';
    for(const node of nodes){const px=x(node.index),label=nodeLabel(node,version,state.versions.length);
      ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(px,y(node.value));ctx.lineTo(px,axisY);ctx.stroke();ctx.setLineDash([]);
      ctx.beginPath();ctx.arc(px,axisY,3,0,2*Math.PI);ctx.fill();ctx.fillText(label,Math.max(margin.left,Math.min(w-margin.right-16,px-8)),axisY+13);
      sampleHitPoints.push({x:px,y:axisY,node,version,label});}}
  ctx.strokeStyle='#111';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x(index),margin.top);ctx.lineTo(x(index),axisY);ctx.stroke();
}
function draw(){
  const state=displayState(),epoch=++drawEpoch;
  $('nodeEliminationTop').setAttribute('aria-pressed',String($('nodeElimination').checked));
  $('nodeDeduplicationTop').setAttribute('aria-pressed',String($('nodeDeduplication').checked));
  renderCurrentNode(state);
  mapImage(c().scene,()=>{if(epoch===drawEpoch)drawMap(state);});drawPlot(state);
  const f=state.filter;$('filterWindowValue').value=$('filterWindow').value;$('streamDelayValue').value=$('streamDelay').value;
  $('timeline').textContent=t('timeline',{t:index,f:f.filteredThrough<0?'—':'F'+f.filteredThrough,s:f.lookahead})+(state.versions.length?' '+t('sampleDelay',{h:f.confirmation}):'');
  $('pendingHint').textContent=state.versions.length?t('samplesPending'):$('showFiltered').checked?t('curvePending'):'';
  $('samplingStatus').textContent=state.versions.length?'':t('samplingOff');$('sampleEvents').replaceChildren();
  for(const version of SAMPLING_VERSIONS){const selected=state.versions.find(v=>v.version.id===version.id),count=$('count_'+version.id);count.textContent=selected?t('sampleCount',{n:selected.nodes.length}):'';count.hidden=!selected;}
  for(const {version,nodes} of state.versions){const p=document.createElement('p');p.className='muted';p.style.color=version.color;
    p.textContent=version.id+' · '+(nodes.length?t('sampleTiming')+' · '+nodes.map(n=>`${n.id}: F${n.index} → F${n.emittedAt}`).join(' · '):t('noSamples'));$('sampleEvents').append(p);}
  renderElimination(state);renderDedup(state);
}
const noteKey=(item=c(),frame=row())=>`jev-sampling-lab:${B.tag}:${item.episode_id}:${frame.frame}`;
function readNote(item,frame){try{return JSON.parse(localStorage.getItem(noteKey(item,frame))||'{}')}catch{return {}}}
function loadNote(){const note=readNote(c(),row());$('category').value=note.category||'';$('note').value=note.note||'';}
function seek(value){
  const target=Number(value);if(!Number.isFinite(target))return;
  index=Math.max(0,Math.min(c().frames.length-1,Math.round(target)));const current=row(),p=jev(current);
  $('frame').value=index;$('imageFrame').value=index;$('step').textContent=`${t('current')} ${index} · ${index+1}/${c().frames.length}`;$('imageStep').textContent=$('step').textContent;
  $('rgb').src=B.images[current.image];$('jevValue').textContent=p===null?t('noScore'):`${(p*100).toFixed(1)}%`;
  $('inputInfo').textContent=current.jev?t('inputFrames')+': '+current.jev.image_frames.join(', '):'—';$('history').replaceChildren();
  for(const frame of current.jev?.image_frames||[]){const button=document.createElement('button'),img=document.createElement('img'),label=document.createElement('span');img.src=B.images[c().frames[frame].image];img.alt='F'+frame;label.textContent='F'+frame;button.append(img,label);button.onclick=()=>{stop();seek(frame);};$('history').append(button);}
  $('caseStats').textContent=t('caseStats',{n:index+1,total:c().frames.length,j:c().frames.slice(0,index+1).filter(f=>jev(f)!==null).length});loadNote();draw();
}
function renderCases(){
  $('cases').replaceChildren();for(const [i,item]of B.cases.entries()){
    if($('filters').value!=='all'&&item.group!==$('filters').value)continue;
    const reviewed=E?.cases.find(entry=>entry.case_index===i),done=reviewed?.nodes.filter(node=>node.status==='ok').length||0;
    const button=document.createElement('button');button.className=i===ci?'active':'';button.textContent=`${i+1}. ${item.episode_id}\n${t(item.group==='success'?'success':'failure')} · ${item.frames.length} ${t('frames')}`+(reviewed?` · ${t('eliminationReviewed')} ${done}/${reviewed.nodes.length}`:'');button.onclick=()=>selectCase(i);$('cases').append(button);
  }
}
function updateLanguage(){
  for(const el of document.querySelectorAll('[data-i18n]'))el.textContent=t(el.dataset.i18n);
  document.title=t('title');document.documentElement.lang=lang==='zh'?'zh-CN':'en';$('note').placeholder=t('notePlaceholder');
  $('instruction').textContent=t('instruction')+': '+(lang==='zh'?c().instruction_zh:c().instruction_en);
  $('promptChinese').textContent=B.prompt_zh;$('promptEnglish').textContent=B.prompt_en;$('stats').replaceChildren();
  const values=[['events',B.cases.length],['trajectories',new Set(B.cases.map(v=>v.real_episode_id)).size],['calls',B.summary.valid_calls],['mean',B.summary.jev_mean_probability.toFixed(3)]];
  for(const [label,value]of values){const box=document.createElement('div'),strong=document.createElement('strong'),span=document.createElement('span');box.className='metric';strong.textContent=value;span.textContent=t(label);box.append(strong,span);$('stats').append(box);}
  stop();renderCases();seek(index);
}
function selectCase(n){
  stop();ci=n;index=Number.isInteger(c().initial_index)?c().initial_index:0;$('title').textContent=c().episode_id;
  for(const id of ['frame','imageFrame'])$(id).max=c().frames.length-1;
  if($('filters').value!=='all'&&$('filters').value!==c().group)$('filters').value='all';updateLanguage();
}
function resetParameters(){stop();filterSessions.clear();sampleSessions.clear();fullCurveCache.clear();draw();}
createVersionControls();
for(const id of ['frame','imageFrame'])$(id).oninput=e=>{stop();seek(e.target.value);};
$('prev').onclick=()=>{stop();seek(index-1);};$('next').onclick=()=>{stop();seek(index+1);};
$('restart').onclick=()=>{stop();filterSessions.clear();seek(0);};
$('play').onclick=()=>{if(timer!==null){stop();return;}if(index===c().frames.length-1)seek(0);$('play').textContent=t('pause');timer=setInterval(()=>{if(index===c().frames.length-1){stop();return;}seek(index+1);},400);};
for(const id of ['showRawJev','showFiltered','reference'])$(id).onchange=draw;
$('nodeDeduplication').onchange=()=>{stop();draw();};$('dedupDecision').onchange=draw;
$('nodeDeduplicationTop').onclick=()=>{$('nodeDeduplication').checked=!$('nodeDeduplication').checked;stop();draw();};
$('nodeElimination').onchange=()=>{stop();draw();};$('eliminationNode').onchange=draw;
$('nodeEliminationTop').onclick=()=>{$('nodeElimination').checked=!$('nodeElimination').checked;stop();draw();};
for(const id of ['filterWindow','streamDelay'])$(id).oninput=resetParameters;
$('language').onchange=()=>{lang=$('language').value;updateLanguage();};
$('filters').onchange=()=>{const group=$('filters').value;renderCases();if(group!=='all'&&c().group!==group){const first=B.cases.findIndex(item=>item.group===group);if(first>=0)selectCase(first);}};
$('scorePlot').onmousemove=e=>{const b=$('scorePlot').getBoundingClientRect(),hit=sampleHitPoints.find(p=>Math.abs(p.x-(e.clientX-b.left))<10&&Math.abs(p.y-(e.clientY-b.top))<25);
  $('scorePlot').title=hit?`${hit.version.id} ${hit.node.id} · ${t('candidate')} F${hit.node.index} · ${t('confirmed')} F${hit.node.emittedAt} · ${t('kind_'+hit.node.kind)}`:'';};
$('scorePlot').onclick=e=>{const b=$('scorePlot').getBoundingClientRect();stop();seek((e.clientX-b.left-36)/Math.max(1,b.width-64)*(c().frames.length-1));};
$('note').oninput=()=>{try{localStorage.setItem(noteKey(),JSON.stringify({note:$('note').value,category:$('category').value}));}catch{}};$('category').onchange=$('note').oninput;
$('export').onclick=()=>{const notes=[];for(const item of B.cases)for(const frame of item.frames){const n=readNote(item,frame);if(n.note||n.category)notes.push({episode_id:item.episode_id,frame:frame.frame,...n});}
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({tag:B.tag,notes},null,2)],{type:'application/json'}));a.download='jev_sampling_review_notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
window.addEventListener('resize',draw);document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();stop();seek(index+(e.key==='ArrowLeft'?-1:1));}});
window.JEV_LAB={bundle:B,versions:SAMPLING_VERSIONS,select:selectCase,seek,draw,displayState,filterSession,nodeReview,eliminationData:E,dedupData:D,
  state:()=>({caseIndex:ci,frame:index,enabled:SAMPLING_VERSIONS.filter(v=>$('sample_'+v.id).checked).map(v=>v.id),samplingSessions:sampleSessions.size})};
selectCase(0);
// Optional local review link; ordinary opens retain all existing default switches.
const query=new URLSearchParams(location.search),requestedCase=Number(query.get('case'));
if(Number.isInteger(requestedCase)&&requestedCase>=1&&requestedCase<=B.cases.length)selectCase(requestedCase-1);
if(query.get('sampling')==='v001')$('sample_v001').checked=true;
if(query.get('dedup')==='1')$('nodeDeduplication').checked=true;
if(query.get('eliminate')==='1')$('nodeElimination').checked=true;
if(query.get('frame')==='last')seek(c().frames.length-1);else draw();
