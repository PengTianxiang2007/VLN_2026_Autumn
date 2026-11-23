/* Round details for the frozen Route53 replay. The replay owns case, frame and language. */
(() => {
  const zh = {
    heading:'逐轮偏航判断', noCall:'未评审', consistent:'一致', deviated:'偏航', uncertain:'不确定',
    format_error:'格式校验失败', reviewed:'已评审', rounds:'轮', nodes:'有效节点', raw:'模型原答（逐字）',
    model:'模型判定', accepted:'系统判定', init:'单帧初始化', segment:'区间审查', available:'节点可用时间',
    images:'实际输入的前视 RGB', imageHint:'点击输入帧可定位地图与画面。', history:'中间观测',
    summary:'本段实际观察', reason:'判断理由', instruction:'本轮指令证据', visual:'视觉证据',
    prior:'调用前 · A 的可信进度', after:'调用后 · 已保存的可信进度', doubts:'模型列出的未决事项',
    rollback:'回退目标', anchor:'当前可信节点', none:'无', progress:'模型返回的进度',
    stopped:'首次有效偏航后，此节点没有发出模型请求。', prompt:'实际中文 Prompt',
    save:'下载本轮原答', currentInstruction:'原始任务指令', returned:'模型原样返回',
    invalid:'校验失败，可信锚点和进度沿用上一轮。',
    partial:'以下只展示截断原答中可读出的内容，整份回答未被采纳。原始文本完整保留在下方。',
    missing:'原答未提供可读取的完整内容。', comments:'原答中的附加文字（展示翻译）',
    compact:'图片为同帧同分辨率 WebP 展示副本；清单保留实际输入 PNG 的 SHA256。',
    zip:'下载离线回放与全部原答', summaryFile:'下载逐轮回答 JSON', endpoint:'选中轮次', reviewModel:'模型与版本'
  };
  const en = {
    heading:'Deviation reviews by round', noCall:'Not reviewed', consistent:'Consistent', deviated:'Deviated', uncertain:'Uncertain',
    format_error:'Format error', reviewed:'Reviewed', rounds:'rounds', nodes:'effective nodes', raw:'Verbatim model answer',
    model:'Model verdict', accepted:'Accepted verdict', init:'Single-frame initialization', segment:'Segment review', available:'Available at',
    images:'Actual front RGB inputs', imageHint:'Select a frame to locate it in the map and replay.', history:'Intermediate',
    summary:'Observed segment', reason:'Rationale', instruction:'Instruction evidence', visual:'Visual evidence',
    prior:'Before the call · trusted progress at A', after:'After the call · committed progress', doubts:'Unresolved issues reported by the model',
    rollback:'Rollback target', anchor:'Trusted anchor', none:'None', progress:'Progress returned by the model',
    stopped:'No model call was made at this node after the first accepted deviation.', prompt:'English prompt translation',
    save:'Download verbatim answer', currentInstruction:'Original task instruction', returned:'As returned by the model',
    invalid:'Validation failed. The previous anchor and progress were retained.',
    partial:'Only readable contents from the truncated answer are shown below. The answer was not accepted. The full original text is preserved below.',
    missing:'No complete readable content was returned.', comments:'Additional text in the original answer',
    compact:'Images are same-frame, same-resolution WebP display copies. The manifest retains the actual input PNG SHA256.',
    zip:'Download offline replay and all answers', summaryFile:'Download round data (JSON)', endpoint:'Selected round', reviewModel:'Model and version'
  };
  const t4 = key => (lang === 'zh' ? zh : en)[key];
  const text4 = value => value == null ? t4('missing') : Array.isArray(value) ? value.map(text4).join('\n') || t4('none') : typeof value === 'object' ? text4(value[lang]) : String(value);
  const root = $('v4Review');
  const make = (tag, value, cls) => {
    const element = document.createElement(tag);
    if (value !== undefined) element.textContent = value;
    if (cls) element.className = cls;
    return element;
  };
  function block(parent, title, body) {
    const box = make('section', undefined, 'v4block');
    box.append(make('h4', title));
    if (body !== undefined) box.append(make('p', body));
    parent.append(box);
    return box;
  }
  function choice(parent, label, action, cls) {
    const button = make('button', label, cls);
    button.type = 'button';
    button.onclick = action;
    parent.append(button);
    return button;
  }
  let previousCase, lastFrame, selected, rendered, explicit = false;
  function go(node, frame) {
    explicit = true;
    selected = node;
    try { stop(); seek(frame); } finally { explicit = false; }
  }
  function show() {
    const group = B.v4.cases[c().episode_id], nodes = group.nodes;
    if (previousCase !== ci || (!explicit && lastFrame !== index)) {
      selected = (nodes.find(n => n.index >= index) || nodes[nodes.length-1]).id;
    }
    previousCase = ci; lastFrame = index;
    const key = [B.v4.modelId, ci, lang, selected].join('/');
    if (rendered !== key) {
      rendered = key;
      render(group);
    }
    root.querySelectorAll('[data-input-frame]').forEach(b => {
      b.setAttribute('aria-current', String(Number(b.dataset.inputFrame) === index));
    });
  }
  function render(group) {
    const node = group.nodes.find(n => n.id === selected);
    const r = group.rounds.find(v => v.current_id === selected);
    root.replaceChildren();
    root.append(make('h3', t4('heading')), make('p', t4('reviewed')+' '+group.rounds.length+' '+t4('rounds')+' / '+group.nodes.length+' '+t4('nodes'), 'muted'));
    block(root, t4('currentInstruction'), c()['instruction_'+lang]);
    const buttons = make('div', undefined, 'v4rounds');
    buttons.id='v4RoundList'; root.append(buttons);
    for (const n of group.nodes) {
      const record = group.rounds.find(v => v.current_id === n.id);
      const status = record ? record.outcome : 'noCall';
      const b = choice(buttons, n.id+' · '+t4(status), () => go(n.id,n.index), 'v4pill '+status);
      b.dataset.round=n.id; b.setAttribute('aria-pressed', String(n.id===selected)); b.title='F'+n.index;
    }
    if (!r) {
      block(root, node.id+' · F'+node.index, t4('stopped'));
    } else {
      const ans=r.answer || r.display_partial || {};
      const head = make('div', undefined, 'v4roundhead');
      head.append(make('strong', r.previous_id+' (F'+r.from_frame+') → '+r.current_id+' (F'+r.to_frame+')'),
                  make('span', t4(r.outcome),'v4pill '+r.outcome));
      root.append(head, make('p', t4(r.mode==='initialization'?'init':'segment')+' · '+t4('available')+' F'+r.available_at_frame,'muted'));
      if (r.validation_error) root.append(make('p', (ans.verdict?t4('model')+' · '+t4(ans.verdict)+'\n':'')+text4(r.validation_error_text || r.validation_error)+'\n'+t4('invalid'), 'v4error'));
      if (!r.answer) root.append(make('p',t4('partial'),'v4error'));
      const facts = make('div', undefined, 'v4cols');root.append(facts);
      block(facts,t4('summary'),text4(ans.segment_summary)); block(facts,t4('reason'),text4(ans.reason));
      const evidence=block(root,t4('images'));
      evidence.append(make('p',t4('imageHint'),'muted'));
      if(B.v4.compact_inputs) evidence.append(make('p',t4('compact'),'muted'));
      const strip=make('div',undefined,'v4images'); evidence.append(strip);
      for (const img of r.images) {
        const b=choice(strip,'',()=>go(selected,img.frame));
        b.dataset.inputFrame=img.frame;
        const picture=make('img');picture.alt='F'+img.frame;picture.src=(B.v4Originals || B.v4.originals)[img.sha256];
        b.append(picture,make('span',(img.role==='history'?t4('history'):img.role)+' · F'+img.frame));
        b.title=img.sha256;
      }
      const supporting=make('div',undefined,'v4cols'); root.append(supporting);
      const quotes=block(supporting,t4('instruction'));
      for(const q of ans.instruction_evidence || []) quotes.append(make('p',q['quote_'+lang]));
      if (!ans.instruction_evidence?.length) quotes.append(make('p',t4('none')));
      const visuals=block(supporting,t4('visual'));
      for(const v of ans.visual_evidence || []) visuals.append(make('p',v.frames.map(f=>'F'+f).join(', ')+' · '+text4(v.description)));
      const states=make('div',undefined,'v4cols'); root.append(states);
      block(states,t4('prior')+' · '+r.previous_id,r.prior_progress[lang]);
      block(states,t4('after')+' · '+r.progress_anchor.id,r.committed_progress[lang]);
      block(root,t4('progress'),ans.semantic_progress===null?'null':text4(ans.semantic_progress));
      if (r.rollback_target) root.append(make('p',t4('rollback')+' · '+r.rollback_target.node_id+' (F'+r.rollback_target.frame+')','v4rollback'));
      block(root,t4('doubts'),text4(ans.uncertainties));
      if(ans.comments){const notes=make('details');notes.append(make('summary',t4('comments')),make('pre',text4(ans.comments)));root.append(notes);}
      const raw=make('details');raw.id='v4Raw';
      raw.append(make('summary', t4('raw')));
      const pre=make('pre',r.raw_answer); raw.append(pre);
      choice(raw,t4('save'),()=>{
        const url=URL.createObjectURL(new Blob([r.raw_answer],{type:'text/plain;charset=utf-8'}));
        const link=make('a');link.href=url;link.download=B.v4.modelId+'_'+group.case_id+'_'+r.current_id+'.txt';link.click();
        setTimeout(()=>URL.revokeObjectURL(url),1000);
      });
      root.append(raw);
    }
    const template=make('details');template.id='v4Prompt';
    template.append(make('summary',(B.v4.version || 'v004')+' · '+t4('prompt')),make('pre',B.v4['prompt_'+lang]));root.append(template);
    if (location.protocol==='http:' || location.protocol==='https:') {
      const links=make('div',undefined,'v4links');root.append(links);
      for(const [href,key] of [[B.v4.archiveFile,'zip'],[B.v4.answersFile,'summaryFile']]) {
        const label=(key==='summaryFile'?B.v4.modelName+' · ':'')+t4(key);
        const a=make('a',label);a.href=href;a.download='';links.append(a);
      }
    }
  }
  window.syncV4Review=show;
  const primary = B.v4.modelId;
  const models = new Map([[primary,{review:B.v4, intervals:B.deviationReviews, tag:B.tag}],
                           ...Object.entries(B.v4Alternatives || {})]);
  function selectModel(key) {
    const entry = models.get(key);
    B.v4=entry.review; B.deviationReviews=entry.intervals; B.tag=entry.tag;
    const name = B.v4.modelName, version = B.v4.version || 'v004';
    const cohortZh=B.v4.partial?'本次已完成 '+B.v4.totals.cases+' 条轨迹':B.v4.totals.cases+' 条离线轨迹';
    const cohortEn=B.v4.partial?B.v4.totals.cases+' completed trajectories in this release':B.v4.totals.cases+' offline trajectories';
    Object.assign(L.zh,{reviewModel:zh.reviewModel,title:name+' 偏航识别 · '+version,subtitle:cohortZh+' · 子任务进度与地标约束',source:'原生前视 · '+name+' '+version,showDeviation:name+' '+version+' 偏航区间',v4calls:'模型调用',v4alarm:'报警轨迹',v4invalid:'格式失败',notice:'本次包含 '+B.v4.totals.cases+' 条已完成样本。地图和参考路线用于离线回放。每轮模型收到的前视图和累计进度可在逐轮判断中查看。',footer:name+' '+version+' 偏航识别 · Qwen 去重 v001 · JEV 采样 v001'});
    Object.assign(L.en,{reviewModel:en.reviewModel,title:name+' deviation review · '+version,subtitle:cohortEn+' · Subtask progress and landmark constraints',source:'Native front RGB · '+name+' '+version,showDeviation:name+' '+version+' deviation intervals',v4calls:'Model calls',v4alarm:'Flagged trajectories',v4invalid:'Format errors',notice:'This release contains '+B.v4.totals.cases+' completed cases. The map and reference path are for offline replay. Each round shows the actual front views and cumulative progress supplied to the model.',footer:name+' '+version+' deviation review · Qwen deduplication v001 · JEV sampling v001'});
    if (B.v4.originalRounds) {
      L.zh.v4calls='回放采用轮数';
      L.en.v4calls='Rounds used in replay';
      L.zh.notice='原实验有 '+B.v4.originalRounds+' 份回答。修复后的校验器按首次有效报警停止，各轨迹合计采用 '+B.v4.totals.calls+' 轮。';
      L.en.notice='The original run produced '+B.v4.originalRounds+' answers. Replay with the corrected validator stops at the first accepted alarm and uses '+B.v4.totals.calls+' rounds across the six trajectories.';
    }
    updateLanguage();
  }
  const requested = new URLSearchParams(location.search);
  const initial = models.has(requested.get('model')) ? requested.get('model') : primary;
  if (models.size > 1) {
    const label=make('label'); label.id='v4ModelChoice';
    const caption=make('span'); caption.dataset.i18n='reviewModel';
    const control=make('select'); control.id='v4Model';
    for (const [key, entry] of models) control.add(new Option(entry.review.modelName+' '+(entry.review.version || 'v004'),key));
    control.value=initial;
    label.append(caption,control); document.querySelector('header').append(label);
    control.onchange=()=>{
      selectModel(control.value);
      if (location.protocol==='http:' || location.protocol==='https:') {
        const target=new URL(location.href);
        target.searchParams.set('model',control.value);
        target.searchParams.set('case',String(ci+1));
        target.searchParams.set('frame',String(index));
        history.replaceState(null,'',target);
      }
    };
  }
  $('guardOverlay').checked=true;
  selectModel(initial);
  if (/^\d+$/.test(requested.get('frame') || '')) seek(Number(requested.get('frame')));
})();
