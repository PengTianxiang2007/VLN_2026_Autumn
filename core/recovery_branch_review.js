/* Presentation of the first recovery call; no inference or correction actions. */
(() => {
  const data = B.branchReview, root = $('branchReview'), inputs = $('branchInputs');
  const records = Object.values(data.cases);
  const count = records.length, imageCount = records.reduce((n,r)=>n+r.input.images.length,0);
  const hasDeepSeek = records.some(record => record.deepseek);
  const models = [
    {id:'qwen', name:'Qwen27B · v1'},
    ...(hasDeepSeek ? [{id:'deepseek', name:'DeepSeek Flash · v1'}] : []),
    ...(data.comparison ? [{id:'comparison', name:'Qwen27B · v1.1'}] : []),
  ];
  const paired=Boolean(data.qwenInstruction);
  const selections = new Set(data.instruction && !paired ? ['deepseek'] : models.filter(m=>m.id!=='comparison').map(m=>m.id));
  if(new URLSearchParams(location.search).get('branchVersion')==='1.1')selections.add('comparison');
  const modelTitle=hasDeepSeek?'Qwen27B / DeepSeek Flash':'Qwen27B';
  const W = {
    zh: {title:'Recovery · 第一次调用', subtitle:modelTitle+' · v006 回退节点 · 固定七图 · '+count+' 例',
      notice:'本次仅识别当前可直接选择的支路，以及此前实际走过哪条。上游 v006 已判该次尝试需纠正；这里的匹配不等于独立证明这条支路违反任务。未输入完整任务指令，未生成 recovery 指令，未执行导航。',
      heading:'模型识别 · 当前有哪些支路', previous:'此前走过、被上游判需纠正的支路', uncertain:'无法确认此前走了哪一条',
      current:'当前直接选择', reason:'此前支路的匹配依据', basis:'为什么属于当前选择', evidence:'证据', doubts:'模型保留的不确定性',
      inputTitle:'本次实际输入 · 7 张图', inputHint:'前三张为 C 处左 +70°／正前 0°／右 −70°。后四张为 C+2、+5、+8、+10 当时真实朝向的前视。点击可放大，同时定位地图；RGB 回放仍显示该帧原生前视。',
      empty:'模型没有列出可确认的当前支路', selected:'此前走过 · 上游判需纠正', other:'模型列出的其他当前支路', none:'无',
      checkpoint:'定位回退节点', viewing:'当前回放帧', fixed:'以下回答始终对应本轨迹的回退节点 C，不随回放帧重新推理。',
      raw:'完整原答（逐字保留）', prompt:'实际中文 Prompt', schema:'实际输出 Schema', historical:'上游 v006 偏航记录（历史上下文）',
      download:'下载本次完整离线包', json:'下载全部原答与结果 JSON', close:'关闭大图',
      instruction:'原任务指令（仅供查看，未输入本次调用）',inputFrames:'JEV 历史输入帧（非本次七图）', frames:'图像输入', valid:'格式有效', matched:'已匹配支路', unknown:'匹配不确定',
      invalid:'该回答未通过格式检查，不能当作有效支路匹配。', rawHint:'结构化区域完整展示原答的自然语言内容；原始 JSON 保持原样。',
      source:'v006 回退节点 · 第一次调用', footer:'Recovery branch review v001 · 模型原答保留 · 展示翻译不改变实验输入与结论',
      labels:['C · 左 +70°','C · 正前 0°','C · 右 −70°','C+2 · 实际前视','C+5 · 实际前视','C+8 · 实际前视','C+10 · 实际前视'],
      dirs:{front:'正前',front_left:'左前',left:'左侧',front_right:'右前',right:'右侧',back:'后方',unknown:'方向不确定'}},
    en: {title:'Recovery · First call',subtitle:modelTitle+' · v006 rollback nodes · Seven images · '+count+' cases',
      notice:'This call identifies choices available directly at the current node and the branch previously taken. Upstream v006 marked this attempt for correction; matching a branch does not independently establish an instruction violation. No full task instruction was supplied, no recovery instruction was generated, and no navigation was run.',
      heading:'Model inventory · Branches available now',previous:'Previously taken branch · attempt flagged upstream',uncertain:'Previously taken branch could not be identified',
      current:'Direct choice now',reason:'Evidence for the previously taken branch',basis:'Why this is a current choice',evidence:'Evidence',doubts:'Uncertainties reported by the model',
      inputTitle:'Actual inputs · Seven images',inputHint:'First: C at left +70°, front 0°, right −70°. Then: actual front views at C+2, C+5, C+8, C+10, with their own headings. Select to enlarge and locate the map frame; RGB playback continues to show that frame’s native front view.',
      empty:'The model listed no identifiable current branch',selected:'Previously taken · flagged upstream',other:'Other current branch listed by the model',none:'None',
      checkpoint:'Go to rollback node',viewing:'Playback frame',fixed:'This answer always refers to this trajectory’s rollback node C; moving the playback does not run inference.',
      raw:'Full verbatim answer',prompt:'English translation of the actual prompt',schema:'Actual output schema',historical:'Upstream v006 deviation reviews (historical context)',
      download:'Download the complete offline archive',json:'Download answers and results for all cases (JSON)',close:'Close enlarged image',
      instruction:'Original task instruction (display only; not supplied to this call)',inputFrames:'Historical JEV input frames (not this call’s seven images)',frames:'Input images',valid:'Valid format',matched:'Branch identified',unknown:'Match uncertain',
      invalid:'This answer failed format checks and cannot be used as a valid branch match.',rawHint:'All natural-language fields are displayed above with faithful translations. The raw JSON is unchanged.',
      source:'v006 rollback targets · First call',footer:'Recovery branch review v001 · Original answers preserved · Display translations do not alter inputs or conclusions',
      labels:['C · Left +70°','C · Front 0°','C · Right −70°','C+2 · Native front','C+5 · Native front','C+8 · Native front','C+10 · Native front'],
      dirs:{front:'Front',front_left:'Front-left',left:'Left',front_right:'Front-right',right:'Right',back:'Back',unknown:'Unknown direction'}}
  };
  const w = () => W[lang];
  let instructionPanel;
  if(data.instruction){
    instructionPanel=document.createElement('section');instructionPanel.id='recoveryInstruction';root.before(instructionPanel);
    Object.assign(W.zh,{title:'Recovery · 局部 R2R 指令',subtitle:'DeepSeek Flash · v006 回退节点 · '+count+' 例',
      notice:'第一次调用用七图识别支路与上次的选择。第二次调用使用回退节点三图、DeepSeek 的支路判断、原指令和该节点保存的任务进度，生成替代选择与一句局部指令。', heading:'第一次调用 · 当前支路与上次的选择',
      instruction:'原任务指令（第二次调用输入）',inputTitle:'第一次调用的七图',source:'v006 回退节点 · 两阶段 Recovery',footer:'DeepSeek Flash · Recovery 第二次调用 v001 · 离线生成结果'});
    Object.assign(W.en,{title:'Recovery · Local R2R instructions',subtitle:'DeepSeek Flash · v006 rollback nodes · '+count+' cases',
      notice:'Call one used seven images to identify branches and the previous choice. Call two used three rollback views, the DeepSeek branch judgment, the original instruction and the progress saved at the node to select an alternative and generate a local instruction.',heading:'First call · Available branches and previous choice',
      instruction:'Original task instruction (input to call two)',inputTitle:'Seven images supplied to call one',source:'v006 rollback nodes · Two-stage recovery',footer:'DeepSeek Flash · Recovery second call v001 · Offline generation results'});
    if(paired){
      Object.assign(W.zh,{subtitle:modelTitle+' · v006 回退节点 · '+count+' 例',footer:'Recovery v001 · 两阶段同模型对照',
        notice:'每个模型先用七张图识别当前支路和上次选择，再结合节点三图、原指令和保存的进度，在自己的支路清单中选择替代项并生成局部指令。支路编号仅在同一模型的同一案例内有效。'});
      Object.assign(W.en,{subtitle:modelTitle+' · v006 rollback nodes · '+count+' cases',footer:'Recovery v001 · Same-model two-stage comparison',
        notice:'Each model identifies branches and the previous choice from seven images. It then uses three node views, the original instruction and saved progress to select from its own alternatives and write a local instruction. Branch IDs belong to one model and one case.'});
    }
  }
  const el = (tag, text, cls) => {const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
  const button = (label, fn) => {const b=el('button',label);b.type='button';b.onclick=fn;return b;};
  const block = (parent,title,value) => {const d=el('div',undefined,'brBlock');d.append(el('strong',title),el('p',value));parent.append(d);};
  const dialog=el('dialog',undefined,'brDialog');dialog.id='branchImageDialog';
  const image=el('img'),caption=el('p'),close=button('',()=>dialog.close());dialog.append(close,caption,image);document.body.append(dialog);
  let key=null, modal=null;
  const jump = frame => {stop();seek(frame);};
  if(instructionPanel){
    $('observationRollback').onclick=()=>jump(data.cases[c().episode_id].input.checkpoint_step);
  }
  function showImage(im,i) {jump(im.actual_step);modal={im,i};image.src=im.display;caption.textContent=im.image_id+' · F'+im.actual_step+' · '+w().labels[i];image.alt=caption.textContent;close.textContent=w().close;if(!dialog.open)dialog.showModal();}
  function evidence(parent, ids, record) {
    const box=el('div',undefined,'brEvidence');box.append(el('span',w().evidence+': '));
    for(const id of ids){const i=record.input.images.findIndex(im=>im.image_id===id);if(i>=0)box.append(button(id,()=>showImage(record.input.images[i],i)));}
    parent.append(box);
  }
  function details(parent,label,text,id){const d=el('details');if(id)d.id=id;d.append(el('summary',label),el('pre',text));parent.append(d);}
  function renderChoice(panel, record, firstCall, modelId){
    const zh=lang==='zh', word=(cn,en)=>zh?cn:en;
    const inventory=zh?firstCall.result.answer:firstCall.translation,ctx=record.input.context;
    const output=record.result.answer;
    const cards=el('div',undefined,'brCards');
    for(const [role,id,label] of [['previous',ctx.previous_attempt.branch_id,word('上次走过 · 已排除','Previously taken · excluded')],
      ['selected',output.selected_branch_id,word('本次选择 · 替代支路','Selected alternative')]]){
      const branch=inventory.branches.find(b=>b.id===id);
      const card=el('article',undefined,'brCard '+(role==='previous'?'brTaken':'riSelected'));card.dataset.role=role;
      card.append(el('span',label,'brBadge'),el('h3',branch?branch.id+' · '+w().dirs[branch.direction]:word('无法确定','Undetermined')));
      if(branch)card.append(el('p',branch.entrance_description));cards.append(card);
    }
    panel.append(cards);
    const command=el('div',undefined,'riCommand');command.dataset.role='command';
    command.append(el('span',word('局部 R2R 指令','Local R2R instruction')),el('strong',
      (zh?record.instruction_zh:output.recovery_instruction_en)??word('无可执行指令','No executable instruction')));
    panel.append(command);
    details(panel,word('第二次调用 · 逐字原答','Second call · Verbatim response'),record.result.raw_answer,'instructionRaw-'+modelId);
  }
  function renderInstruction(r){
    const panel=instructionPanel, record=r.instruction, item=record.input, ctx=item.context;
    const zh=lang==='zh', word=(cn,en)=>zh?cn:en;
    $('observationRollback').textContent=word('回到回退点','Go to rollback point')+' · F'+item.checkpoint_step;
    panel.replaceChildren();panel.dataset.case=item.case_id;
    const header=el('div',undefined,'brHeader');
    header.append(el('h2',word('第二次调用 · 局部恢复指令','Second call · Local recovery instruction')),
      button(item.case_id+' · '+item.node_id+' · F'+item.checkpoint_step,()=>jump(item.checkpoint_step)));
    panel.append(header);
    const choices=el('div',undefined,'brModelPanels');
    for(const model of models){
      const qwen=model.id==='qwen', result=qwen?r.qwenInstruction:r.instruction;
      if(model.id==='comparison'||!result||(paired&&!selections.has(model.id)))continue;
      const view=el('section',undefined,'brModelPanel');view.dataset.instructionModel=model.id;
      view.append(el('h3',model.name));renderChoice(view,result,qwen?r:r.deepseek,model.id);choices.append(view);
    }
    if(!choices.children.length)choices.append(el('p',word('勾选模型以查看恢复指令。','Select a model to view its recovery instruction.')));
    panel.append(choices);
    const progress=zh?ctx:item.progress_en;
    block(panel,word('当前任务 · Current','Current task'),progress.Current);
    block(panel,word('已完成 · Completed','Completed'),progress.Completed);
    block(panel,word('原任务指令','Original task instruction'),zh?record.task_zh:ctx.instruction_en);
    panel.append(el('h3',word('第二次调用的三张输入图','Three images supplied to call two')));
    const pictures=el('div',undefined,'brImages brImages3');
    for(const [i,im] of r.input.images.slice(0,3).entries()){
      const b=button('',()=>showImage(im,i)), pic=el('img');pic.alt=w().labels[i];pic.src=im.display;
      b.dataset.stageTwoImage=im.image_id;b.append(pic,el('strong',w().labels[i]));pictures.append(b);
    }
    panel.append(pictures);
    details(panel,word('第二次调用 · 实际中文 Prompt','Second call · English translation of the prompt'),data.instruction['prompt_'+lang],'instructionPrompt');
  }
  function modelAnswer(root, r, id, spec){
      const answer=lang==='zh'?r.result.answer:r.translation;
      const prev=answer?.previous_attempt, identified=r.result.status==='ok'&&prev?.status==='identified';
      const banner=el('div',undefined,'brVerdict '+(identified?'brIdentified':'brUncertain'));banner.dataset.role='verdict';
      banner.append(el('span',w().previous),el('strong',identified?prev.branch_id:w().uncertain));root.append(banner);
      if(r.result.status!=='ok')root.append(el('p',w().invalid,'brInvalid'));
      const grid=el('div',undefined,'brCards');grid.classList.add('branchCards');
      for(const b of answer?.branches||[]){
        const taken=identified&&b.id===prev.branch_id,card=el('article',undefined,'brCard'+(taken?' brTaken':''));card.dataset.branch=b.id;card.dataset.taken=String(taken);
        card.append(el('h3',b.id+' · '+w().dirs[b.direction]),el('span',taken?w().selected:w().other,'brBadge'),el('p',b.entrance_description));
        block(card,w().basis,b.current_choice_basis);evidence(card,b.evidence_image_ids,r);grid.append(card);
      }
      if(!answer?.branches?.length)grid.append(el('p',w().empty));root.append(grid);
      if(prev){const reason=el('div',undefined,'brReason');block(reason,w().reason,prev.reason);evidence(reason,prev.evidence_image_ids,r);root.append(reason);}
      if(answer.view_candidates){
        const audit=el('section'); audit.classList.add('branchCandidateAudit');
        audit.append(el('h3',lang==='zh'?'逐视图候选入口':'Candidate entrances by view'));
        for(const [view,cs] of Object.entries(answer.view_candidates))block(audit,view,cs.map(x=>x.id+' · '+x.description).join('\n')||w().none);
        audit.append(el('h3',lang==='zh'?'跨图匹配与去重':'Cross-view matching and deduplication'));
        for(const g of answer.candidate_groups)block(audit,g.candidate_ids.join(' + ')+' → '+(g.branch_id??(lang==='zh'?'排除':'Excluded')),g.reason);
        root.append(audit);
      }
      block(root,w().doubts,answer?.uncertainties?.length?answer.uncertainties.join('\n'):w().none);
    details(root,w().raw,r.result.raw_answer||r.result.error,'branchRaw-'+id);
    details(root,w().prompt,spec['prompt_'+lang],'branchPrompt-'+id);
    details(root,w().schema,JSON.stringify(spec.schema,null,2));
  }
  function sync() {
    const r=data.cases[c().episode_id], token=c().episode_id+'/'+lang+'/'+[...selections].join(',');
    if(token!==key){
      if(dialog.open)dialog.close();key=token;
      root.replaceChildren();inputs.replaceChildren();
      if(instructionPanel)renderInstruction(r);
      root.dataset.case=r.input.case_id;root.dataset.checkpoint=String(r.input.checkpoint_step);
      const head=el('div',undefined,'brHeader');
      head.append(el('h2',w().heading),button(w().checkpoint+' · '+r.input.node_id+' · F'+r.input.checkpoint_step,()=>jump(r.input.checkpoint_step)));root.append(head);
      const bar=el('fieldset',undefined,'brSelectors');
      bar.append(el('legend',lang==='zh'?'勾选要查看的模型结果':'Select model results'));
      const available=id=>id==='qwen'?r:r[id];
      for(const model of models){
        const label=el('label'), check=el('input');
        check.type='checkbox';check.dataset.model=model.id;
        check.disabled=!available(model.id);check.checked=!check.disabled&&selections.has(model.id);
        check.onchange=()=>{if(check.checked)selections.add(model.id);else selections.delete(model.id);sync();};
        label.append(check,document.createTextNode(model.name));bar.append(label);
      }
      if(paired)instructionPanel.querySelector('.brHeader').after(bar);
      else root.append(bar);
      if(data.comparison){
        const shortcuts=el('div',undefined,'brEvidence');shortcuts.append(el('span',lang==='zh'?'v1.1 对照':'v1.1 comparison'));
        for(const [i,cs] of B.cases.entries())if(data.cases[cs.episode_id].comparison){
          shortcuts.append(button(data.cases[cs.episode_id].input.case_id,()=>{selections.add('comparison');window.JEV_LAB.select(i);sync();}));
        }
        root.append(shortcuts);
      }
      root.append(el('p',r.input.case_id+' · C = '+r.input.node_id+' / F'+r.input.checkpoint_step+' · '+w().fixed,'brMeta'));
      const panels=el('div',undefined,'brModelPanels');root.append(panels);
      for(const model of models){
        if(!selections.has(model.id)||!available(model.id))continue;
        const panel=el('section',undefined,'brModelPanel');panel.dataset.modelPanel=model.id;
        const n=available(model.id).result.answer.branches.length;
        panel.append(el('h3',model.name+' · '+n+(lang==='zh'?' 条支路':(n===1?' branch':' branches'))));panels.append(panel);
        modelAnswer(panel,{...available(model.id),input:r.input},model.id,model.id==='comparison'?data.comparison:data);
      }
      if(!panels.children.length)panels.append(el('p',lang==='zh'?'勾选模型以查看本例回答。':'Select a model to see its answer for this case.'));
      inputs.append(el('h3',w().inputTitle),el('p',w().inputHint,'brMeta'));
      for(const [begin,end] of [[0,3],[3,7]]){const grid=el('div',undefined,'brImages brImages'+(end-begin));
        for(let i=begin;i<end;i++){const im=r.input.images[i],b=button('',()=>showImage(im,i));b.dataset.branchImage=im.image_id;const pic=el('img');pic.src=im.display;pic.alt=im.image_id+' · '+w().labels[i];pic.width=640;pic.height=480;pic.loading='lazy';b.append(pic,el('strong',w().labels[i]),el('span',im.image_id+' · F'+im.actual_step));grid.append(b);}inputs.append(grid);}
      const links=el('div',undefined,'brLinks');for(const [href,label] of [[data.archive,w().download],[data.answers,w().json]]){if(location.protocol==='file:'&&href.endsWith('.zip'))continue;const a=el('a',label);a.href=href;a.download='';links.append(a);}inputs.append(links);
      $('upstreamSummary').textContent=w().historical;
    }
    for(const item of inputs.querySelectorAll('[data-branch-image]')){const im=r.input.images.find(x=>x.image_id===item.dataset.branchImage);item.setAttribute('aria-current',String(im.actual_step===index));}
    const instructionCount=(field,name)=>[records.filter(r=>r[field].result.answer.selected_branch_id).length,name+(lang==='zh'?' · 生成指令':' · local instructions')];
    const stats=data.instruction?[[count,t('trajectories')],[3,lang==='zh'?'第二阶段每例图数':'Images per second call'],...(paired?[instructionCount('qwenInstruction','Qwen27B')]:[]),instructionCount('instruction','DeepSeek')]:
      [[count,t('trajectories')],[imageCount,w().frames],[records.length,'Qwen27B · v1'],...(hasDeepSeek?[[records.filter(r=>r.deepseek).length,'DeepSeek Flash · v1']]:[]),...(data.comparison?[[records.filter(r=>r.comparison).length,'Qwen27B · v1.1']]:[])];
    $('stats').replaceChildren();for(const [n,label] of stats){const box=el('div',undefined,'metric');box.append(el('strong',n),el('span',label));$('stats').append(box);}
    $('title').textContent=r.input.case_id+' · '+c().episode_id;
  }
  for(const locale of ['zh','en'])for(const name of ['title','subtitle','notice','instruction','inputFrames','source','footer'])L[locale][name]=W[locale][name];
  const prior=window.syncV4Review;window.syncV4Review=()=>{prior();sync();};
  window.BranchReview={sync,data};updateLanguage();
})();
