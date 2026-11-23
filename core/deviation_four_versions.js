/* Archived review versions; selection changes presentation only. */
(() => {
  const words = {
    zh: {layers:'偏航区间叠加',limit:'最多同时勾选三组',details:'查看逐轮回答',reviewed:'已评审',rounds:'轮',nodes:'有效节点',
      unavailable:'未评审：DeepSeek v003 仅覆盖 C01–C29',noAlarm:'未触发有效偏航报警',noneSelected:'尚未勾选偏航区间',
      consistent:'一致',deviated:'偏航',uncertain:'不确定',format_error:'格式校验失败',noCall:'未评审',
      heading:'逐轮偏航判断',currentInstruction:'原始任务指令',summary:'本段实际观察',reason:'判断理由',
      images:'实际输入帧 · 同帧压缩展示副本',imageHint:'点击图片可定位地图与画面；原始输入 PNG 哈希保留在下载数据中。',
      instruction:'本轮指令证据',visual:'视觉证据',prior:'调用前 · A 的可信进度',after:'调用后 · 已保存的可信进度',
      doubts:'模型列出的未决事项',raw:'模型原答（逐字）',save:'下载本轮原答',prompt:'实际中文 Prompt',
      zip:'下载全部版本完整精简离线包',json:'下载本版本逐轮回答 JSON',none:'无',history:'中间观测',
      partial:'以下仅展示截断原答中可读出的内容，整份回答未被采纳。',comments:'原答中的附加文字（展示翻译）',
      init:'单帧初始化',segment:'区间审查',available:'节点可用时间',rollback:'回退目标',progress:'模型返回的进度',
      stopped:'首次有效偏航后，此节点没有发出模型请求。',invalid:'校验失败，本轮未提交为有效判定；可信锚点和进度沿用上一轮。',
      model:'模型原答判定',accepted:'系统采纳结果',parse:'原答无法解析为 JSON。请查看下方逐字原答。',
      source:'本轮回答来源',official:'DeepSeek 官方接口',gateway:'历史网关回答（接续时复用）',local:'本地 Qwen',
      short:'暂无结构化字段',tracks:'偏航区间 · 点击定位帧',empty:'未评审',coverage:'该版本评审任务'},
    en: {layers:'Deviation overlays',limit:'Select at most three layers',details:'Inspect round answers',reviewed:'Reviewed',rounds:'rounds',nodes:'effective nodes',
      unavailable:'Not reviewed: DeepSeek v003 covers C01–C29 only',noAlarm:'No accepted deviation alarm',noneSelected:'No deviation layers selected',
      consistent:'Consistent',deviated:'Deviated',uncertain:'Uncertain',format_error:'Format error',noCall:'Not reviewed',
      heading:'Deviation reviews by round',currentInstruction:'Original task instruction',summary:'Observed segment',reason:'Rationale',
      images:'Actual input frames · same-frame compressed display copies',imageHint:'Select an image to locate its frame. Original input PNG hashes are retained in the downloadable data.',
      instruction:'Instruction evidence',visual:'Visual evidence',prior:'Before the call · trusted progress at A',after:'After the call · committed progress',
      doubts:'Unresolved matters reported by the model',raw:'Verbatim model answer',save:'Download verbatim answer',prompt:'English prompt translation',
      zip:'Download compact offline archive of all versions',json:'Download this version’s round data (JSON)',none:'None',history:'Intermediate',
      partial:'Only readable contents of the truncated response are shown. The answer was not accepted.',comments:'Additional text in the original answer',
      init:'Single-frame initialization',segment:'Segment review',available:'Available at',rollback:'Rollback target',progress:'Progress returned by the model',
      stopped:'No model call was made at this node after the first accepted deviation.',invalid:'Validation failed. This round was not accepted as a valid verdict; the prior anchor and progress were retained.',
      model:'Verdict in original answer',accepted:'Accepted outcome',parse:'The original answer could not be parsed as JSON. See the verbatim response below.',
      source:'Response source',official:'Official DeepSeek API',gateway:'Historical gateway response (reused during continuation)',local:'Local Qwen',
      short:'No structured field available',tracks:'Deviation intervals · click to locate a frame',empty:'Not reviewed',coverage:'Cases reviewed by this version'}
  };
  const tr = key => words[lang === 'zh' ? 'zh' : 'en'][key];
  const versions = B.reviewVersions, keys = Object.keys(versions);
  const params = new URLSearchParams(location.search);
  const chosen = new Set(B.defaultLayers || ['qwen_v003','qwen_v005','deepseek_v005']);
  if (params.has('layers')) { chosen.clear(); for(const key of params.get('layers').split(',')) if(versions[key] && chosen.size<3) chosen.add(key); }
  let active = versions[params.get('model')] ? params.get('model') : (B.defaultReview || 'deepseek_v005');
  let selected, previousCase, lastFrame, rendered, explicit=false;
  const make = (tag,text,cls) => { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; };
  const text = value => {
    if(value===null || value===undefined)return tr('none');
    if(Array.isArray(value))return value.length?value.map(text).join('\n'):tr('none');
    if(typeof value==='object')return value[lang]===undefined?tr('short'):text(value[lang]);
    return String(value);
  };
  const group = key => versions[key].cases[c().episode_id];
  const intervals = key => versions[key].intervals[c().episode_id] || [];
  const selectedKeys = () => keys.filter(key=>chosen.has(key));
  const root=$('v4Review'), controls=$('comparisonControls'), tracks=$('comparisonTracks');
  $('guardOverlay').closest('label').style.display='none';
  const style=make('style');style.textContent=`
    #stats{grid-template-columns:repeat(5,minmax(0,1fr))}
    #comparisonControls{border:1px solid #c4d2df;background:#f7fafc;border-radius:8px;padding:12px;margin:12px 0}
    .comparisonOptions{display:flex;flex-wrap:wrap;gap:9px;margin:8px 0}.comparisonOption{display:flex;align-items:center;gap:6px;border:1px solid var(--layer);border-radius:6px;background:white;padding:7px 9px;font-size:13px}
    .comparisonOption input{accent-color:var(--layer)}.comparisonOption:has(input:checked){box-shadow:inset 0 -3px var(--layer)}.comparisonOption small{font-size:11px;color:#526577}
    #reviewVersion{float:none;position:static;max-width:100%;margin-left:8px;color:#17324b}.comparisonHelp{font-size:12px;color:#526577;margin:5px 0}
    #comparisonTracks{margin:8px 0 16px}.comparisonTrack{display:grid;grid-template-columns:132px 1fr;gap:8px;align-items:center;margin:6px 0}.comparisonTrack>button:first-child{font-size:12px;background:#fff;border:1px solid var(--layer);color:var(--layer);padding:5px;border-radius:4px}
    .comparisonRail{position:relative;display:block;width:100%;height:29px;padding:0;border:1px solid #cad4df;border-radius:4px;background:#f0f3f6;overflow:hidden;color:#3c5062;text-align:center;font-size:11px}
    .comparisonRail .band{position:absolute;top:0;height:100%;opacity:.3;pointer-events:none}.comparisonRail .caption{position:relative;pointer-events:none}.comparisonRail .cursor{position:absolute;top:0;bottom:0;width:2px;background:#172d40;pointer-events:none}
    #comparisonEmpty{padding:8px;color:#607489;font-size:13px}#v4Raw pre{max-height:32rem}.comparisonMissing{background:#f1f5f9;padding:12px;border-radius:6px}
    @media(max-width:900px){#stats{grid-template-columns:repeat(3,minmax(0,1fr))}}
    @media(max-width:650px){#stats{grid-template-columns:repeat(2,minmax(0,1fr))}.comparisonTrack{grid-template-columns:105px 1fr}.comparisonOption{width:100%;box-sizing:border-box}}
  `;document.head.append(style);
  const heading=make('strong'), help=make('p',undefined,'comparisonHelp'), optionBox=make('div',undefined,'comparisonOptions');
  controls.append(heading,optionBox,help);
  const checks=new Map(), statusTexts=new Map();
  for(const key of keys){
    const v=versions[key],label=make('label',undefined,'comparisonOption');label.style.setProperty('--layer',v.color);
    const input=make('input');input.type='checkbox';input.dataset.layer=key;input.checked=chosen.has(key);
    const name=make('span',v.label),status=make('small');label.append(input,name,status);optionBox.append(label);
    checks.set(key,input);statusTexts.set(key,status);
    input.onchange=()=>{
      if(input.checked){if(chosen.size>=3){input.checked=false;return;}chosen.add(key);}else chosen.delete(key);
      syncControls();draw();syncURL();
    };
  }
  const detailLabel=make('label'),detailCaption=make('span'),select=make('select');select.id='reviewVersion';
  for(const key of keys)select.add(new Option(versions[key].label,key));select.value=active;
  detailLabel.append(detailCaption,select);controls.append(detailLabel);
  select.onchange=()=>selectReview(select.value);

  function syncURL(){
    if(!/^https?:$/.test(location.protocol))return;
    const target=new URL(location.href);target.searchParams.set('model',active);target.searchParams.set('layers',selectedKeys().join(','));
    target.searchParams.set('case',String(ci+1));target.searchParams.set('frame',String(index));history.replaceState(null,'',target);
  }
  function status(key){
    if(!group(key))return tr('unavailable');
    const ranges=intervals(key);return ranges.length?ranges.map(r=>'F'+r.from_frame+' → F'+r.to_frame).join(' · '):tr('noAlarm');
  }
  function syncControls(){
    heading.textContent=tr('layers');help.textContent=tr('limit')+' · '+chosen.size+'/3';detailCaption.textContent=tr('details');
    for(const key of keys){
      const input=checks.get(key);input.checked=chosen.has(key);input.disabled=!input.checked && chosen.size>=3;
      statusTexts.get(key).textContent=group(key)?status(key):tr('empty');input.closest('label').title=status(key);
    }
    tracks.replaceChildren();tracks.setAttribute('aria-label',tr('tracks'));
    if(!chosen.size){const e=make('div',tr('noneSelected'));e.id='comparisonEmpty';tracks.append(e);return;}
    const last=Math.max(1,c().frames.length-1);
    for(const key of selectedKeys()){
      const v=versions[key],line=make('div',undefined,'comparisonTrack');line.dataset.track=key;line.style.setProperty('--layer',v.color);
      const name=make('button',v.label);name.type='button';name.onclick=()=>selectReview(key);
      const rail=make('button',undefined,'comparisonRail');rail.type='button';rail.title=status(key);rail.disabled=!group(key);
      for(const r of intervals(key)){
        const band=make('span',undefined,'band');band.style.left=(100*r.from_frame/last)+'%';band.style.width=Math.max(.5,100*(r.to_frame-r.from_frame)/last)+'%';band.style.background=v.color;rail.append(band);
      }
      rail.append(make('span',status(key),'caption'));const cursor=make('span',undefined,'cursor');cursor.style.left=(100*index/last)+'%';rail.append(cursor);
      rail.onclick=e=>{const rect=rail.getBoundingClientRect();stop();seek((e.clientX-rect.left)/rect.width*last);};line.append(name,rail);tracks.append(line);
    }
  }
  window.MultiDeviation={
    selected: selectedKeys,
    drawMap({ctx,xy}){
      const list=selectedKeys();ctx.save();ctx.lineCap='round';ctx.lineJoin='round';ctx.setLineDash([]);
      list.forEach((key,lane)=>{
        const v=versions[key],width=4+(list.length-1-lane)*4;
        for(const r of intervals(key)){
          ctx.strokeStyle=v.color;ctx.lineWidth=width;ctx.beginPath();
          for(let f=r.from_frame;f<=r.to_frame;f++){const p=xy(c().frames[f].position);f===r.from_frame?ctx.moveTo(...p):ctx.lineTo(...p);}ctx.stroke();
          for(const [f,label]of [[r.from_frame,'A'],[r.to_frame,'B']]){
            const [x,y]=xy(c().frames[f].position);ctx.beginPath();ctx.arc(x,y,5+(list.length-1-lane)*3,0,2*Math.PI);ctx.lineWidth=2;ctx.strokeStyle=v.color;ctx.stroke();
            const short=(key.startsWith('qwen')?'Q':'D')+v.version.replace(/^v0*/,'')+' '+label;
            ctx.font='bold 11px CrossingSans,sans-serif';ctx.lineWidth=3;ctx.strokeStyle='#fff';ctx.strokeText(short,x+12,y-14+lane*13);ctx.fillStyle=v.color;ctx.fillText(short,x+12,y-14+lane*13);
          }
        }
      });ctx.restore();
    },
    drawBands({ctx,x,top,axisY}){
      ctx.save();selectedKeys().forEach((key,lane)=>{
        for(const r of intervals(key)){
          ctx.fillStyle=versions[key].color;ctx.globalAlpha=.08;ctx.fillRect(x(r.from_frame),top,Math.max(2,x(r.to_frame)-x(r.from_frame)),axisY-top);
          ctx.globalAlpha=1;ctx.fillRect(x(r.from_frame),top+lane*6,Math.max(2,x(r.to_frame)-x(r.from_frame)),3);
        }
      });ctx.restore();
    }
  };
  function block(parent,title,body){const section=make('section',undefined,'v4block');section.append(make('h4',title));if(body!==undefined)section.append(make('p',body));parent.append(section);return section;}
  function go(node,frame){explicit=true;selected=node;try{stop();seek(frame);}finally{explicit=false;}}
  function renderReview(g){
    root.replaceChildren();root.append(make('h3',versions[active].label+' · '+tr('heading')));
    block(root,tr('currentInstruction'),c()['instruction_'+lang]);
    if(!g){root.append(make('p',tr('unavailable'),'comparisonMissing'));return;}
    root.append(make('p',tr('reviewed')+' '+g.rounds.length+' '+tr('rounds')+' / '+g.nodes.length+' '+tr('nodes'),'muted'));
    const buttons=make('div',undefined,'v4rounds');buttons.id='v4RoundList';root.append(buttons);
    for(const n of g.nodes){const r=g.rounds.find(r=>r.current_id===n.id);const outcome=r?r.outcome:'noCall';const b=make('button',n.id+' · '+tr(outcome),'v4pill '+outcome);b.type='button';b.dataset.round=n.id;b.setAttribute('aria-pressed',String(n.id===selected));b.title='F'+n.index;b.onclick=()=>go(n.id,n.index);buttons.append(b);}
    const r=g.rounds.find(r=>r.current_id===selected);
    if(!r){block(root,tr('noCall'),tr('stopped'));}
    else{
      const ans=r.answer || r.display_partial,head=make('div',undefined,'v4roundhead');head.append(make('strong',r.previous_id+' (F'+r.from_frame+') → '+r.current_id+' (F'+r.to_frame+')'),make('span',tr(r.outcome),'v4pill '+r.outcome));root.append(head);
      root.append(make('p',tr(r.mode==='initialization'?'init':'segment')+' · '+tr('available')+' F'+r.available_at_frame,'muted'));
      const source=r.endpoint==='local'?'local':r.endpoint==='https://api.deepseek.com'?'official':'gateway';
      root.append(make('p',tr('source')+' · '+tr(source),'muted'));
      if(r.validation_error){block(root,tr('accepted')+' · '+tr('format_error'),text(r.validation_error_text || r.validation_error)+'\n'+tr('invalid'));if(ans?.verdict)root.append(make('p',tr('model')+' · '+(tr(ans.verdict)||ans.verdict)));}
      if(!r.answer && r.display_partial)block(root,tr('format_error'),tr('partial'));
      if(ans){
        const facts=make('div',undefined,'v4cols');root.append(facts);block(facts,tr('summary'),text(ans.segment_summary));block(facts,tr('reason'),text(ans.reason));
      }else block(root,tr('format_error'),tr('parse'));
      const imageBlock=block(root,tr('images'),tr('imageHint')),strip=make('div',undefined,'v4images');imageBlock.append(strip);
      for(const im of r.images){const b=make('button');b.type='button';b.dataset.inputFrame=im.frame;b.onclick=()=>go(selected,im.frame);const img=make('img');img.src=im.file;img.alt='F'+im.frame;b.append(img,make('span',(im.role==='history'?tr('history'):im.role)+' · F'+im.frame));b.title=im.sha256;strip.append(b);}
      if(ans){
        const evidence=make('div',undefined,'v4cols');root.append(evidence);const quotes=block(evidence,tr('instruction')),visuals=block(evidence,tr('visual'));
        for(const q of ans.instruction_evidence||[])quotes.append(make('p',q['quote_'+lang]));if(!ans.instruction_evidence?.length)quotes.append(make('p',tr('none')));
        for(const v of ans.visual_evidence||[])visuals.append(make('p',(v.frames||[]).map(f=>'F'+f).join(', ')+' · '+text(v.description)));
      }
      const states=make('div',undefined,'v4cols');root.append(states);block(states,tr('prior')+' · '+r.previous_id,text(r.prior_progress));block(states,tr('after')+' · '+r.progress_anchor.id,text(r.committed_progress));
      if(ans){block(root,tr('progress'),ans.semantic_progress===null?'null':text(ans.semantic_progress));block(root,tr('doubts'),text(ans.uncertainties));}
      if(ans?.comments){const notes=make('details');notes.append(make('summary',tr('comments')),make('pre',text(ans.comments)));root.append(notes);}
      if(r.rollback_target)root.append(make('p',tr('rollback')+' · '+r.rollback_target.node_id+' (F'+r.rollback_target.frame+')','v4rollback'));
      const raw=make('details');raw.id='v4Raw';raw.append(make('summary',tr('raw')),make('pre',r.raw_answer));const save=make('button',tr('save'));save.type='button';save.onclick=()=>{const u=URL.createObjectURL(new Blob([r.raw_answer],{type:'text/plain;charset=utf-8'}));const a=make('a');a.href=u;a.download=active+'_'+g.case_id+'_'+r.current_id+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};raw.append(save);root.append(raw);
    }
    const prompt=make('details');prompt.id='v4Prompt';prompt.append(make('summary',versions[active].label+' · '+tr('prompt')),make('pre',versions[active]['prompt_'+lang]));root.append(prompt);
    const links=make('div',undefined,'v4links');root.append(links);
    for(const [href,label]of [[versions[active].archiveFile,tr('zip')],[versions[active].answersFile,tr('json')]]){if(location.protocol==='file:' && href.endsWith('.zip'))continue;const a=make('a',label);a.href=href;a.download='';links.append(a);}
  }
  function show(){
    syncControls();const g=group(active);
    if(g&&(previousCase!==ci || (!explicit&&lastFrame!==index)))selected=(g.nodes.find(n=>n.index>=index)||g.nodes[g.nodes.length-1]).id;
    previousCase=ci;lastFrame=index;const token=[active,ci,lang,selected].join('/');if(token!==rendered){rendered=token;renderReview(g);}
    root.querySelectorAll('[data-input-frame]').forEach(e=>e.setAttribute('aria-current',String(Number(e.dataset.inputFrame)===index)));
  }
  window.syncV4Review=show;
  function selectReview(key){active=key;B.v4=versions[key];select.value=key;rendered=null;previousCase=undefined;
    const releases=[...new Set(keys.map(k=>versions[k].version))].join(' / ');
    Object.assign(L.zh,{title:'多版本偏航区间对比',subtitle:'Qwen / DeepSeek · '+releases+' · 最多叠加三组',source:'原生前视 · 多版本对比',v4coverage:'该版本评审任务',v4calls:'评审轮数',v4alarm:'有效报警轨迹',v4invalid:'格式失败',notice:'当前详情：'+versions[key].label+'。'+keys.length+' 组独立勾选，最多同时显示三组偏航区间。DeepSeek v003 仅覆盖 C01–C29。图片为同帧 WebP 展示副本；地图与参考路线不属于模型输入。',footer:'多版本偏航识别对比 · 历史结果原样保留'});
    Object.assign(L.en,{title:'Multi-version deviation comparison',subtitle:'Qwen / DeepSeek · '+releases+' · Up to three overlays',source:'Native front RGB · Multi-version comparison',v4coverage:'Cases reviewed by this version',v4calls:'Review rounds',v4alarm:'Accepted alarm cases',v4invalid:'Format errors',notice:'Answer details: '+versions[key].label+'. Select up to three of '+keys.length+' independent deviation overlays. DeepSeek v003 covers C01–C29 only. Images are same-frame WebP display copies. Maps and reference paths were not model inputs.',footer:'Multi-version deviation comparison · Historical results preserved'});
    updateLanguage();syncURL();
  }
  selectReview(active);
  if(/^\d+$/.test(params.get('frame')||''))seek(Number(params.get('frame')));
})();
