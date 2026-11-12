/* New review layer over the user's unchanged JEV sampling laboratory template. */
(function(){
  'use strict';
  const G=window.JEV_GUARD_DATA||{cases:[],summary:{}};
  const byId=id=>document.getElementById(id);
  const text={
    zh:{title:'JEV · 偏航判断与语义进度',subtitle:'34 个案例离线评审 · 有效节点连续编号 · 含终止节点 · DeepSeek',
      notice:'红色高亮表示模型判定偏航的 A→B 实际路径。每条在首次明确偏航后停止评审；后续画面为原始录像，未执行真实回退。所有判断仍需人工复核。',
      source:'完整 34 个案例，来自 33 条独立轨迹、9 个场景。本次补跑剩余 22 条，已有 12 条结果原样复用。第 32、33 个案例对应同一条轨迹。',
      samplingHint:'节点直接读取冻结的有效节点列表，按 S01、S02…连续编号。',
      dedupHint:'复用已有去重结果：8步内分支信息相同则删除旧节点、保留新节点。此次没有新增去重模型调用。',
      dedupUnavailable:'没有匹配的原去重缓存。',
      footer:'本地离线可视化 · 浏览网页不调用 API · 不代表真实恢复或导航成功率',
      header:'节点与联合评审',nodeHelp:'点击节点查看该次判断、语义进度及实际输入观测。',
      panel:'节点审阅信息',choose:'选择节点',at:'位置',ready:'可用',original:'原编号',scene:'场景',
      consistent:'未判偏航',deviated:'明确偏航',uncertain:'证据不足',error:'请求或格式错误',pending:'未评审',initialization:'首节点初始化',
      retained:'去重后保留',replaced:'最终被替换',state:'本次判定',segment:'本段实际经历',reason:'判断依据',
      prior:'此前可信语义进度',progress:'截至该节点的语义进度',noProgress:'本节点没有提交新的可信进度。',
      frozen:'此前进度保持不变',unreviewed:'本轮在首次偏航后停止评审，此处仅保留原录像与缓存节点。',
      noRecord:'该节点尚无本轮有效评审。',modeInit:'首个有效节点的单图初始化；此前路线进度尚未确认，不计入路段通过。',
      interval:'评审区间',rollback:'记录的回退目标',rollbackNote:'仅为回退请求，本轮没有执行真实回退。',
      evidence:'本次实际输入 · 端点 + 均匀最多5张中间观测',evidenceHelp:'图像按时间排序；点击可同步查看 RGB 和地图。所有输入不晚于 B 中心。',
      instructionEvidence:'任务依据',visualEvidence:'视觉证据',uncertainties:'尚未确认',
      prompt:'查看联合评审提示词',raw:'原始请求与响应',request:'请求元数据',response:'实际原始响应',
      overlay:'显示偏航路径红色高亮',jump:'跳到首次偏航',noDeviation:'本条未输出明确偏航',
      facts:'本次新调用',valid:'有效回答',cases:'案例 / 场景',nodes:'有效节点',deviations:'偏航判定',
      reused:'复用原结果',history:'中间观测',roleA:'节点 A',roleB:'节点 B',roleStart:'首节点 A=B',
      frozenConfig:'评审绑定 N=7、D=5 的已有节点缓存。',stop:'首次偏航后的节点未继续调用模型',
      conclusion:'原始模型结论，尚无独立逐段真值',showAll:'所有历史建立事件',
      elapsed:'请求耗时',seconds:'秒',running:'评审结果尚未打包。',download:'下载实验汇总',
      notLive:'完整结果用于离线审阅；滑条只改变当前观测，不模拟API实时返回。'},
    en:{title:'JEV · Deviation & semantic progress',subtitle:'34-case offline review · Consecutive effective nodes · Terminal node included · DeepSeek',
      notice:'Red highlights the actual A-to-B path judged deviated by the model. Review stops at the first explicit deviation per case. Later frames are the original recording; no physical rollback was executed. Predictions require human review.',
      source:'All 34 cases from 33 distinct trajectories and 9 scenes. Only the remaining 22 cases are new; 12 prior cases are reused unchanged. Cases 32 and 33 share one trajectory.',
      samplingHint:'Nodes are read from the frozen effective-node list and numbered S01, S02, and so on.',
      dedupHint:'Reuse existing decisions: identical branch information within 8 steps replaces the older node. No new deduplication model calls were made.',
      dedupUnavailable:'No matching original deduplication cache.',
      footer:'Local offline viewer · No API calls from this page · Not a measure of recovery or navigation success',
      header:'Nodes & joint review',nodeHelp:'Select a node to inspect its verdict, semantic progress and actual input observations.',
      panel:'Node review',choose:'Select node',at:'Position',ready:'Available',original:'Original case',scene:'Scene',
      consistent:'Consistent',deviated:'Deviated',uncertain:'Uncertain',error:'Request / format error',pending:'Not reviewed',initialization:'Initialization',
      retained:'Retained after deduplication',replaced:'Later replaced',state:'Verdict',segment:'Observed segment',reason:'Rationale',
      prior:'Prior confirmed semantic progress',progress:'Semantic progress through this node',noProgress:'No new confirmed progress was committed at this node.',
      frozen:'Prior progress remains unchanged',unreviewed:'Review stopped at the first deviation. Only original frames and cached nodes are shown here.',
      noRecord:'No valid review is available for this node.',modeInit:'One-image initialization at the first effective node. Prior route progress is unconfirmed; not counted as a passed segment.',
      interval:'Reviewed interval',rollback:'Recorded rollback target',rollbackNote:'A request only; no physical rollback was performed.',
      evidence:'Actual input · endpoints + up to 5 uniform intermediate views',evidenceHelp:'Chronological observations. Select an image to synchronize RGB and map. Inputs never exceed the B center.',
      instructionEvidence:'Instruction evidence',visualEvidence:'Visual evidence',uncertainties:'Unresolved questions',
      prompt:'Inspect the joint-review prompt',raw:'Raw request and response',request:'Request metadata',response:'Actual raw response',
      overlay:'Highlight deviated paths in red',jump:'Jump to first deviation',noDeviation:'No explicit deviation returned for this case',
      facts:'New calls this run',valid:'Valid answers',cases:'Cases / scenes',nodes:'Effective nodes',deviations:'Deviation verdicts',
      reused:'Reused original result',history:'Intermediate',roleA:'Node A',roleB:'Node B',roleStart:'First node A=B',
      frozenConfig:'Reviews are bound to the existing N=7, D=5 node cache.',stop:'Nodes after the first deviation were not sent to the model',
      conclusion:'Original model verdicts; no independent segment ground truth',showAll:'All historical node events',
      elapsed:'Request latency',seconds:'s',running:'Review results have not been packed yet.',download:'Download experiment results',
      notLive:'Full results are shown for offline inspection. Sliders change observations, not API response availability.'}
  };
  // Only replace intended template labels; keys such as raw/prompt/cases also
  // exist in the original JEV interface and must keep their original meanings.
  for(const language of ['zh','en'])for(const key of ['title','subtitle','notice','source','samplingHint','dedupHint','dedupUnavailable','footer'])L[language][key]=text[language][key];
  L.zh.kind_terminal='终止节点';L.en.kind_terminal='Terminal node';
  L.zh.v001Title='有效节点';L.en.v001Title='Effective nodes';
  L.zh.v001Description='固定节点列表 · 连续编号';L.en.v001Description='Frozen node list · Consecutive IDs';
  L.zh.samplingTitle='节点显示';L.en.samplingTitle='Node display';
  L.zh.rulesNote='本轮使用已固定的有效节点；N / D 不可修改。';L.en.rulesNote='This run uses fixed effective nodes; N / D cannot be changed.';
  L.zh.protocolReplay='完整波形与录像用于离线审阅，节点固定为本轮有效节点。移动滑条只改变当前观测，模型输入严格截止当前评审节点。';
  L.en.protocolReplay='Full waveforms and recordings are available for offline inspection. Nodes are the fixed effective nodes of this run. Sliders change the observation; model inputs end at the reviewed node.';
  const tr=k=>text[lang][k]||k;
  const bi=v=>v&&typeof v==='object'?(v[lang]||v.zh||v.en||''):typeof v==='string'?v:'';
  const sourceCase=()=>D.cases.find(v=>v.case_index===ci);
  const reviewedCase=()=>G.cases.find(v=>v.case_number===c().original_case_number);
  const reviews=()=>reviewedCase()?.reviews||[];
  const status=r=>!r?'pending':r.status!=='ok'?'error':r.mode==='initialization'?'initialization':r.answer.verdict;
  const rawUrls=new Map();
  function rawUrl(path){
    if(!window.JEV_GUARD_FILES||!Object.hasOwn(window.JEV_GUARD_FILES,path))return path;
    if(!rawUrls.has(path))rawUrls.set(path,URL.createObjectURL(new Blob([JSON.stringify(window.JEV_GUARD_FILES[path],null,2)],{type:'application/json'})));
    return rawUrls.get(path);
  }
  function errorMessage(r){
    if(!r?.error)return '';
    if(r.error.includes('ConnectTimeout'))return lang==='zh'?'连接请求超时，未收到有效回答；进度保持不变。':'The connection timed out without a valid answer; progress was not advanced.';
    if(r.error.includes('JSONDecodeError'))return lang==='zh'?'模型响应未通过 JSON 解析；原始响应保留，进度保持不变。':'The response could not be parsed as JSON. The raw response is retained and progress was not advanced.';
    return lang==='zh'?'模型返回字段格式未通过校验；原始响应保留，进度保持不变。':'The returned fields failed format validation. The raw response is retained and progress was not advanced.';
  }
  let selected=null,lastCase=-1,lastFrame=-1,pinned=false;
  function nodeForFrame(){
    const nodes=sourceCase()?.nodes||[],exact=nodes.find(n=>n.index===index);
    if(exact)return exact.id;
    const red=reviews().find(r=>r.answer?.verdict==='deviated'&&r.from_frame<=index&&index<=r.to_frame);
    return red?.node_id||nodes.filter(n=>n.index<=index).at(-1)?.id||nodes[0]?.id;
  }
  function choose(id){selected=id;pinned=true;const n=sourceCase()?.nodes.find(x=>x.id===id);if(n){stop();seek(n.index);}}
  function put(id,value){byId(id).textContent=value||'—';}
  function paragraph(parent,value,className=''){const p=document.createElement('p');p.className=className;p.textContent=value;parent.append(p);return p;}
  function heading(parent,value){const h=document.createElement('h4');h.textContent=value;parent.append(h);return h;}
  function refreshStatic(){
    document.querySelectorAll('[data-guard]').forEach(el=>el.textContent=tr(el.dataset.guard));
    byId('guardPromptText').textContent=G['prompt_'+lang]||'';
    const s=G.summary||{},metrics=[['cases',`${B.cases.length} / ${new Set(B.cases.map(x=>x.scene)).size}`],
      ['nodes',D.cases.reduce((v,c)=>v+c.nodes.length,0)],
      ['facts',`${s.new_calls??0} (${tr('valid')} ${s.new_valid??0})`],['deviations',s.deviations??0]];
    byId('stats').replaceChildren();
    for(const [label,value]of metrics){const box=document.createElement('div'),strong=document.createElement('strong'),span=document.createElement('span');box.className='metric';strong.textContent=value;span.textContent=tr(label);box.append(strong,span);byId('stats').append(box);}
    byId('guardSummaryLink').textContent=tr('download');
    byId('guardSummaryLink').href=rawUrl('run/results.json');
    for(const input of [byId('filterWindow'),byId('streamDelay')]){input.disabled=true;input.title=tr('frozenConfig');}
  }
  function render(){
    if(!byId('guardPanel'))return;
    if(lastCase!==ci){selected=null;pinned=false;lastCase=ci;lastFrame=-1;}
    if(!selected||(!pinned&&lastFrame!==index))selected=nodeForFrame();
    lastFrame=index;
    const cached=sourceCase(),record=reviewedCase(),node=cached?.nodes.find(n=>n.id===selected),r=reviews().find(v=>v.node_id===selected),s=status(r);
    refreshStatic();
    put('guardTaskTitle',lang==='zh'?'完整任务指令（中文翻译）':'Complete task instruction');
    put('guardTask',lang==='zh'?c().instruction_zh:c().instruction_en);
    const select=byId('guardNode');select.replaceChildren();byId('guardNodes').replaceChildren();
    for(const n of cached?.nodes||[]){
      const review=reviews().find(v=>v.node_id===n.id),st=status(review),kept=cached.final_active_ids.includes(n.id);
      const option=document.createElement('option');option.value=n.id;option.textContent=`${n.id} · F${n.index} · ${tr(st)}`+(n.terminal_node?(lang==='zh'?' · 终止':' · Terminal'):'');select.append(option);
      const button=document.createElement('button');button.className='guard-node '+st+(selected===n.id?' selected':'');
      button.dataset.node=n.id;button.setAttribute('aria-label',`${n.id} F${n.index} ${tr(st)}`);
      button.textContent=`${n.id} · F${n.index}`+(n.terminal_node?(lang==='zh'?' · 终止':' · End'):'');button.title=`${tr(st)} ·`;button.onclick=()=>choose(n.id);byId('guardNodes').append(button);
    }
    if(selected)select.value=selected;
    const deviation=reviews().find(v=>v.answer?.verdict==='deviated');
    byId('guardJump').disabled=!deviation;byId('guardJump').title=deviation?`${deviation.previous_id} F${deviation.from_frame} → ${deviation.node_id} F${deviation.to_frame}`:tr('noDeviation');
    byId('guardBadge').className='guard-badge '+s;put('guardBadge',tr(s));
    put('guardNodeMeta',node?`${tr('original')} ${c().original_case_number} · ${node.id} · ${tr('at')} F${node.index} · ${tr('ready')} F${node.emittedAt}`:'');
    if(node?.terminal_node)byId('guardNodeMeta').textContent+=(lang==='zh'?' · 终止节点':' · Terminal node');
    byId('guardNodeMeta').textContent+=(G.reused_case_numbers?.includes(c().original_case_number)?(lang==='zh'?' · 复用上一轮结果':' · Reused prior result'):(lang==='zh'?' · 本次新增评审':' · New review'));
    put('guardInterval',r?`${r.previous_id} F${r.from_frame} → ${r.node_id} F${r.to_frame}`:tr('noRecord'));
    put('guardSegment',r?.answer?bi(r.answer.segment_summary):errorMessage(r)||tr(record?.stop_node?'unreviewed':'noRecord'));
    put('guardReason',r?.answer?bi(r.answer.reason):errorMessage(r));
    put('guardPrior',r?bi(r.prior_progress):'');
    put('guardProgress',r?.answer?.semantic_progress?bi(r.answer.semantic_progress):tr('noProgress'));
    byId('guardProgressBox').dataset.state=s;
    put('guardLatency',r?`${tr('elapsed')}: ${r.elapsed_seconds} ${tr('seconds')}`:'');
    byId('guardInit').hidden=r?.mode!=='initialization';
    byId('guardRollback').hidden=!r?.rollback_target;
    if(r?.rollback_target)put('guardRollback',`${tr('rollback')}: ${r.rollback_target.node_id} / F${r.rollback_target.frame}。 ${tr('rollbackNote')}`);
    const proof=byId('guardProof');proof.replaceChildren();
    if(r?.answer){
      heading(proof,tr('instructionEvidence'));
      for(const q of r.answer.instruction_evidence)paragraph(proof,lang==='zh'?q.quote_zh:q.quote_en,'guard-quote');
      heading(proof,tr('visualEvidence'));
      for(const e of r.answer.visual_evidence)paragraph(proof,`${e.frames.map(f=>'F'+f).join(', ')} · ${bi(e.description)}`);
      if(r.answer.uncertainties.length){heading(proof,tr('uncertainties'));for(const u of r.answer.uncertainties)paragraph(proof,bi(u));}
    }
    const images=byId('guardEvidence');images.replaceChildren();
    for(const im of r?.images||[]){const button=document.createElement('button'),img=document.createElement('img'),label=document.createElement('span');
      button.className='guard-image '+im.role;img.src=B.images[im.image_id];img.alt=`${im.role} F${im.frame}`;img.loading='lazy';
      label.textContent=(im.role==='A'?tr('roleA'):im.role==='B'?tr('roleB'):im.role==='A=B'?tr('roleStart'):tr('history'))+' · F'+im.frame;
      button.append(img,label);button.onclick=()=>{pinned=true;stop();seek(im.frame);};images.append(button);
    }
    put('guardEvidenceMeta',r?`${r.previous_id} F${r.from_frame} → ${r.node_id} F${r.to_frame} · ${r.images.length} RGB`:tr('noRecord'));
    byId('guardRaw').hidden=!r;
    if(r){byId('guardRequest').href=rawUrl(r.request_file);byId('guardResponse').href=rawUrl(r.response_file);}
    // A selected reviewed node remains inspectable even if later removed by deduplication.
    byId('guardPanel').dataset.node=selected||'';byId('guardPanel').dataset.verdict=s;
  }
  function drawMap({ctx,xy}){
    if(!byId('guardOverlay')?.checked)return;
    ctx.save();ctx.setLineDash([]);ctx.lineCap='round';ctx.lineJoin='round';
    for(const r of reviews().filter(v=>v.answer?.verdict==='deviated')){
      for(const [color,width]of [['#fff',10],['#ef233c',6]]){
        ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();
        for(let f=r.from_frame;f<=r.to_frame;f++){const p=xy(c().frames[f].position);f===r.from_frame?ctx.moveTo(...p):ctx.lineTo(...p);}ctx.stroke();
      }
      for(const [frame,label]of [[r.from_frame,'A'],[r.to_frame,'B']]){const[x,y]=xy(c().frames[frame].position);
        ctx.beginPath();ctx.arc(x,y,6,0,Math.PI*2);ctx.fillStyle='#ef233c';ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke();
        const lx=x+(label==='A'?-14:8),ly=y-16;
        ctx.font='bold 12px CrossingSans,sans-serif';ctx.lineWidth=3;ctx.strokeStyle='#fff';ctx.strokeText(label,lx,ly);ctx.fillStyle='#be123c';ctx.fillText(label,lx,ly);
      }
    }
    ctx.restore();
  }
  function drawBands({ctx,x,y,top,axisY}){
    if(!byId('guardOverlay')?.checked)return;
    ctx.save();for(const r of reviews().filter(v=>v.answer?.verdict==='deviated')){ctx.fillStyle='rgba(239,35,60,.12)';ctx.fillRect(x(r.from_frame),top,Math.max(2,x(r.to_frame)-x(r.from_frame)),axisY-top);ctx.strokeStyle='#ef233c';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(x(r.from_frame),axisY+2);ctx.lineTo(x(r.to_frame),axisY+2);ctx.stroke();}ctx.restore();
  }
  window.GuardUI={render,drawMap,drawBands,choose,language:refreshStatic,
    debug:()=>({caseNumber:c().original_case_number,selected,verdict:byId('guardPanel').dataset.verdict,
      redIntervals:reviews().filter(r=>r.answer?.verdict==='deviated').map(r=>({from:r.from_frame,to:r.to_frame,edges:r.to_frame-r.from_frame})),
      reviewed:reviews().length,allNodes:sourceCase().nodes.length,retained:sourceCase().final_active_ids.length,
      imageFrames:(reviews().find(r=>r.node_id===selected)?.images||[]).map(im=>im.frame)})};
  byId('guardNode').onchange=e=>choose(e.target.value);
  byId('guardJump').onclick=()=>{const r=reviews().find(v=>v.answer?.verdict==='deviated');if(r)choose(r.node_id);};
  byId('guardOverlay').onchange=draw;
  for(const id of ['frame','imageFrame'])byId(id).addEventListener('input',()=>{pinned=false;},true);
  for(const id of ['prev','next','play','restart'])byId(id).addEventListener('click',()=>{pinned=false;},true);
  byId('sample_v001').checked=true;byId('sample_v001').disabled=true;
  updateLanguage();draw();
})();
