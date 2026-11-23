'use strict';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
let lang='zh', ci=0, round=0, filter='all', scope='alarms', arm='current', clock=null;
const at={current:0,original:0};
let focus='floor', camera=null;
const show={original:true,current:true,reference:true,node:true,trusted:true,target:true,reviewed:true,alarm:true,local:true,jump:true};
const t=(z,e)=>lang==='zh'?z:e, c=()=>DATA.cases[ci], records=()=>ANSWERS.cases[c().id], r=()=>records()[round];
const name=k=>k==='current'?t('当前版本','Current'):t('原版','Original');
const result=x=>x?t('成功','Success'):t('失败','Failure');
const kind=x=>x.error?'invalid':x.answer?.verdict;
const verdict=x=>({deviated:t('偏航','Deviated'),consistent:t('一致','Consistent'),invalid:t('校验未通过','Validation failed')})[kind(x)]||'—';
const opts=(xs,v)=>xs.map(([k,s])=>'<option value="'+esc(k)+'"'+(String(k)===String(v)?' selected':'')+'>'+esc(s)+'</option>').join('');
const actionName=a=>[t('停止','STOP'),t('前进','Forward'),t('左转','Left'),t('右转','Right')][a]??String(a);
const list=v=>v==null?[]:Array.isArray(v)?v:[v];
const localized=v=>typeof v==='string'?v:v?.[lang]??'';
const field=(s,v)=>v==null||v===''?'':'<div class="brBlock"><strong>'+esc(s)+'</strong><p>'+esc(v)+'</p></div>';
const jump=(f,txt)=>'<button type="button" data-seq="'+f+'">'+esc(txt)+' · F'+f+'</button>';
const details=(title,body)=>'<details><summary>'+esc(title)+'</summary>'+body+'</details>';
const raw=x=>details(t('完整模型原答（逐字）','Verbatim model response'),'<pre class="raw">'+esc(x.raw)+'</pre>');
const names={
 selected:['已实际回退','Physical rollback executed'],no_alternative:['未接管：模型返回空选择和空指令','No takeover: null branch and instruction'],
 invalid_answer:['未接管：选路回答未通过校验','No takeover: branch selection failed validation'],
 input_incomplete:['选路图像不足','Insufficient selection images'],terminal_during_restore:['回退时任务终止','Episode ended during rollback'],
 terminal:['终止时仅评审','Terminal review only'],gateCleared:['复核改判一致','Recheck found consistency'],
 gateInvalid:['复核未通过校验','Recheck failed validation'],superseded:['被后续判断取代','Superseded by a later review']
};
const reasonName=k=>({success:t('成功','Success'),fall:t('跌倒','Fall'),stuck:t('卡住','Stuck'),not_reach_goal:t('未到达目标','Goal not reached')})[k]||k;
function err(s){const z={'Instruction quote is not an exact supplied excerpt':'引用的指令文字与本轮提供的原文不完全一致','Evidence references an unsupplied frame':'证据引用了未提供的帧','Invalid uncertainties':'不确定性字段无效','Invalid visual evidence':'视觉证据字段无效','deviation invalid model response: Incomplete model response':'偏航模型回答不完整','Selected ID is not an eligible alternative':'所选 ID 不是可用的替代支路'};return lang==='zh'?(z[s]||s):s}
function eligibleCases(){
  return DATA.cases.map((v,i)=>({v,i})).filter(({v})=>{
    if(filter==='loss')return v.original.sr>v.current.sr;
    if(filter==='gain')return v.current.sr>v.original.sr;
    if(filter==='rollback')return v.rollbacks>0;
    if(filter==='quiet')return !v.current.sr&&!ANSWERS.cases[v.id].some(q=>kind(q.review)==='deviated');
    return true;
  });
}
function eligibleRounds(){return records().map((v,i)=>({v,i})).filter(({v})=>scope==='all'||(scope==='calls'?!!v.recovery?.second:kind(v.review)==='deviated'))}
function chooseDefaultRound(){
  let rows=eligibleRounds();
  if(!rows.length){scope='all';rows=eligibleRounds()}
  round=(rows.find(x=>x.v.recovery?.rollback)||rows.find(x=>x.v.recovery)||rows[0])?.i??-1;
}
function selectCase(i){
  stop();ci=i;arm='current';at.original=0;scope='alarms';focus='floor';camera=null;chooseDefaultRound();
  at.current=r()?.review.seq??0;render();
}
function status(x){
  if(x.recovery?.rollback){
    const resumed={no_alternative:t('无替代支路','No alternative branch'),invalid_answer:t('选路回答无效','Invalid selection'),input_incomplete:t('选路图像不足','Insufficient selection images')};
    if(resumed[x.outcome])return t('已回退 · ','Rolled back · ')+resumed[x.outcome]+t(' · 从落点续走',' · resumed at checkpoint');
  }
  return x.outcome?t(...names[x.outcome]):verdict(x.review);
}
function head(){
  document.documentElement.lang=lang==='zh'?'zh-CN':'en';$('language').value=lang;
  $('heading').textContent=document.title=t('偏航与回退 · 事件回放','Deviation and rollback replay');
  $('subtitle').textContent='StreamVLN / VLNVerse · Qwen27B · seed 2 · '+new Date(DATA.at).toLocaleString(lang==='zh'?'zh-CN':'en-GB',{timeZone:'Asia/Shanghai',hour12:false})+' UTC+8';
  const n=DATA.cases.length,s=DATA.summary,a=ANSWERS.totals;
  const lossesOnly=DATA.selection==='original_success_current_failure';
  if(lossesOnly){
    $('heading').textContent=document.title=t('原版成功、当前失败 · 事件回放','Original success, current failure · Event replay');
    $('subtitle').textContent+=' · '+t('从 '+DATA.scored+' 条配对评分中筛出 '+n+' 条，技术跳过 '+DATA.skipCount+' 条另计',n+' of '+DATA.scored+' scored pairs match; '+DATA.skipCount+' technical skips excluded');
  }
  const metric=(v)=>s[v].success+'/'+n+' ('+(100*s[v].success/n).toFixed(2)+'%)';
  $('stats').innerHTML=[[metric('current'),name('current')+' SR · SPL '+s.current.spl.toFixed(4)],[metric('original'),name('original')+' SR · SPL '+s.original.spl.toFixed(4)],[a.review+' / '+a.gate,t('节点评审 / 接管前复核','Node reviews / pre-takeover rechecks')],[a.alarms+' / '+(a.twoStage??((a.selected||0)+(a.no_alternative||0)+(a.invalid_answer||0))),t('节点报警 / 两阶段选路','Node alarms / two-stage selections')],[s.rollbacks+' / '+s.handoffs,t('实际回退 / 交还','Physical rollbacks / handoffs')]].map(([v,k])=>'<div class="metric"><strong>'+v+'</strong><span>'+k+'</span></div>').join('');
  $('caseHeader').textContent=t('任务筛选','Case filter');
  const filters=[['all',t('全部任务','All cases')],['loss',t('原版成功 → 当前失败','Original success → current failure')],['gain',t('原版失败 → 当前成功','Original failure → current success')],['rollback',t('发生实际回退','With physical rollback')]];
  if(DATA.cases.some(v=>!v.current.sr&&!ANSWERS.cases[v.id].some(q=>kind(q.review)==='deviated')))filters.push(['quiet',t('当前失败 · 全程无报警','Failed without an alarm')]);
  $('filter').innerHTML=opts(lossesOnly?filters.filter(([key])=>key!=='loss'&&key!=='gain'):filters,filter);
  const choices=eligibleCases().map(({v,i})=>[i,v.id+' · '+name('original')+' '+result(v.original.sr)+' · '+name('current')+' '+result(v.current.sr)]);
  $('caseJump').innerHTML=opts(choices,ci);
  $('download').textContent=t('下载完整离线包','Download offline replay');$('download').hidden=location.protocol==='file:';
  $('scores').textContent=t('下载配对成绩 CSV','Download paired scores (CSV)');$('allAnswers').textContent=t('下载全部调用原答 JSON','Download all model responses (JSON)');
  $('skipHeader').textContent=t('技术跳过','Technical skips')+' · '+DATA.skips.length;
  $('skipHeader').parentElement.hidden=lossesOnly;
  $('skips').innerHTML=DATA.skips.map(s=>'<li>'+esc(s.id)+' · '+(s.reason==='http520'?'JEV HTTP 520':t('回退朝向偏差超限','Rollback yaw drift exceeded limit'))+'</li>').join('');
  $('caseTitle').textContent=t('配对任务','Paired episode');$('eventLabel').textContent=t('节点与事件结果','Node and event outcome');$('caseStats').textContent=name('original')+' '+result(c().original.sr)+' · '+name('current')+' '+result(c().current.sr)+' · '+t('回退','Rollbacks')+' '+c().rollbacks+' · '+t('交还','Handoffs')+' '+c().handoffs;
  $('instruction').textContent=c().instruction[lang];$('roundHeader').textContent=t('事件筛选','Event filter');
  $('roundFilter').innerHTML=opts([['alarms',t('偏航报警','Deviation alarms')],['calls',t('两阶段选路','Two-stage selections')],['all',t('全部节点判断','All node reviews')]],scope);
  const rows=eligibleRounds();$('rounds').innerHTML=opts(rows.map(({v,i})=>[i,'#'+(i+1)+' · A'+v.review.action+' · '+v.review.node+' · '+status(v)]),round);
  if(!rows.length)$('rounds').innerHTML=opts([[-1,t('本任务无此类记录','No matching record')]],-1);
  $('rounds').disabled=!rows.length;
}
function reviewBlock(x){
  const a=x.answer, title=x.kind==='deviation_gate'?t('接管前复核','Pre-takeover recheck'):t('偏航识别','Deviation review');
  let out='<h3>'+title+' · '+esc(verdict(x))+' · A'+x.action+'</h3><div class="brMeta">'+esc(x.id)+' · '+esc(x.previous)+' → '+esc(x.node)+'</div>';
  if(x.error)out+=field(t('校验结果','Validation'),err(x.error));
  if(a){
    out+=field(t('画面与区间描述','Observed segment'),localized(a.segment_summary))+field(t('模型判断理由','Model rationale'),localized(a.reason))+field(t('模型记录的任务进度','Model-reported progress'),localized(a.semantic_progress));
    let evidence=[];
    for(const v of list(a.instruction_evidence))evidence.push(v?.['quote_'+lang]??localized(v));
    for(const v of list(a.visual_evidence))evidence.push((Array.isArray(v?.frames)?'F'+v.frames.join(', F')+' · ':'')+localized(v?.description??v));
    for(const v of list(a.uncertainties))evidence.push(localized(v));
    if(evidence.some(Boolean))out+=details(t('指令、图像证据与不确定性','Instruction, visual evidence and uncertainties'),'<ul>'+evidence.filter(Boolean).map(s=>'<li>'+esc(s)+'</li>').join('')+'</ul>');
  }else if(x.partial){out+=field(t('中断前可读内容（回答无效）','Readable content before truncation (invalid response)'),x.partial[lang])}
  return out+'<div class="inputList">'+x.inputs.map(f=>jump(f,t('输入','Input'))).join('')+'</div>'+raw(x);
}
function actionText(actions){
  const runs=[];
  for(const [i,code] of actions){const last=runs.at(-1);if(last&&last.code===code&&last.end===i-1)last.end=i;else runs.push({start:i,end:i,code})}
  return runs.map(g=>'A'+g.start+(g.end>g.start?'–'+g.end:'')+' '+actionName(g.code)).join(' · ');
}
function evidenceButtons(ids,rec){
  return '<div class="brEvidence">'+(ids||[]).map(id=>'<button data-im="'+rec.images.findIndex(m=>m.camera===id)+'">'+esc(id)+'</button>').join('')+'</div>';
}
function drawRound(){
  const group=r();const rec=group?.recovery;
  $('judgment').innerHTML=group?'<div class="outcome">'+esc(status(group))+'</div>'+reviewBlock(group.review)+(group.gate?reviewBlock(group.gate):''):'<p class="muted">'+t('本任务无所选类型的模型记录。','No model record matches this selection.')+'</p>';
  for(const id of ['branchReview','recoveryInstruction','branchInputs','execution']){$(id).hidden=!rec;$(id).replaceChildren()}
  if(!rec)return;
  if(!rec.second){
    for(const id of ['branchReview','recoveryInstruction','branchInputs'])$(id).hidden=true;
    $('execution').innerHTML=esc(status(group))+(rec.first?raw(rec.first):'');
    return;
  }
  const one=rec.first, two=rec.second,b=lang==='zh'?one.answer:one.english,p=b.previous_attempt;
  const dirs={front:t('正前','Front'),front_left:t('左前','Front left'),left:t('左侧','Left'),front_right:t('右前','Front right'),right:t('右侧','Right'),back:t('后方','Back'),unknown:t('方向不确定','Uncertain direction')};
  const cards=b.branches.map(v=>'<article class="brCard '+(v.id===p.branch_id?'brTaken':'')+'"><h3>'+esc(v.id)+' · '+esc(dirs[v.direction]||v.direction)+'</h3>'+
    field(t('入口描述','Entrance'),v.entrance_description)+field(t('为什么是当前位置的选择','Why it is available here'),v.current_choice_basis)+evidenceButtons(v.evidence_image_ids,rec)+'</article>').join('');
  $('branchReview').innerHTML='<h2>'+t('第一次调用 · 当前有哪些支路','First call · available branches')+'</h2><p class="brMeta">Qwen27B · '+esc(one.id)+' · '+b.branches.length+' '+t('条候选支路','candidate branches')+'</p><div class="brCards">'+cards+'</div>'+
    field(t('模型识别的已走支路','Previously taken branch according to the model'),p.branch_id??t('无法确认','Uncertain'))+field(t('匹配依据','Matching rationale'),p.reason)+evidenceButtons(p.evidence_image_ids,rec)+field(t('不确定性','Uncertainties'),b.uncertainties.join('\n'))+raw(one);
  const sel=two.answer?.selected_branch_id, english=two.answer?.recovery_instruction_en;
  const alternative=b.branches.find(v=>v.id===sel);
  $('recoveryInstruction').innerHTML='<h2>'+t('第二次调用 · 选择与局部纠错指令','Second call · selected branch and local instruction')+'</h2><p class="brMeta">Qwen27B · '+esc(two.id)+'</p>'+
    field(t('模型返回的支路','Returned branch'),sel??'null')+(alternative?field(t('该编号对应的入口','Entrance for that ID'),alternative.entrance_description):'')+
    field(t('模型返回的纠错指令','Returned recovery instruction'),(lang==='zh'?two.zh:english)??'null')+
    (lang==='zh'&&english?details('实际英文指令','<p>'+esc(english)+'</p>'):'')+
    (two.error?field(t('校验结果','Validation'),err(two.error)):'')+field(t('执行结果','Execution outcome'),status(group))+raw(two);
  const labels=[t('左 70°','Left 70°'),t('正前','Front'),t('右 70°','Right 70°'),'C+2','C+5','C+8','C+10'];
  function images(begin,end){return '<div class="brImages brImages'+(end-begin)+'">'+rec.images.slice(begin,end).map((im,j)=>'<button data-im="'+(begin+j)+'"><img loading="lazy" src="media/'+c().id+'/'+im.file+'" alt="'+esc(im.camera)+'"><strong>'+labels[begin+j]+'</strong><span>'+esc(im.camera)+' · F'+im.seq+'</span></button>').join('')+'</div>'}
  $('branchInputs').innerHTML='<h3>'+t('实际输入图像','Actual input images')+'</h3><p class="brMeta">'+t('第一次调用使用全部七张图；第二次调用使用前三张节点图。点击图片定位同一次导航的观测帧。','The first call used all seven images. The second used the first three checkpoint views. Select an image to locate its observation in this run.')+'</p>'+images(0,3)+images(3,7);
  if(rec.rollback){
    const rb=rec.rollback,h=rec.handoff;
    if(rec.status!=='selected'){$('execution').textContent=status(group);return}
    $('execution').innerHTML='<h2>'+t('实际回退与导航动作','Physical rollback and navigation actions')+'</h2><p>'+[jump(rb.target,t('回退点','Checkpoint')),jump(rb.seq,t('回退前','Before rollback')),jump(rb.after,t('回退后','After rollback')),...(h?[jump(h.seq,t('交还','Handoff'))]:[])].join(' ')+'</p>'+
       field(t('局部执行','Local execution'),rec.localActions.length+' '+t('个动作','actions')+' · '+(rec.localStop?t('局部策略发出 STOP，交还原任务','Local policy emitted STOP and handed back'):h?t('达到局部动作预算后交还','Handed back at the local action budget'):t('任务在局部纠错期间结束','Episode ended during local recovery')))+
       details(t('展开局部策略的实际动作序列','Local policy action sequence'),'<p class="actionList">'+esc(actionText(rec.localActions))+'</p>')+
       (h?details(t('交还后原策略的动作（至下一次接管或终止）','Original-policy actions after handoff until next takeover or termination'),'<p class="actionList">'+esc(actionText(rec.resumedActions)||'—')+'</p>'):'')+
       field(t('整条任务终局','Episode outcome'),result(c().current.sr)+' · '+reasonName(c().current.end)+' · NE '+c().current.ne.toFixed(2)+' m');
  }else{$('execution').innerHTML='<p class="outcome">'+t('这次选路没有执行物理回退或局部导航。','No physical rollback or local navigation followed this selection.')+'</p>'}
}
const colors={original:'#4c77a4',current:'#216f65',reference:'#726c55',node:'#566878',trusted:'#087365',target:'#29599b',
  reviewed:'#bd741a',alarm:'#c34037',local:'#813d99',jump:'#8a663c'};
function obsControls(){
  $('observationHeader').textContent=t('逐帧观测','Frame playback');$('arm').innerHTML=opts([['current',name('current')],['original',name('original')]],arm);
  $('rgbLabel').textContent=t('图像帧','Image frame');$('mapLabel').textContent=t('地图帧','Map frame');
  $('mapTitle').textContent=t('节点与实际轨迹','Checkpoints and trajectories');$('waveTitle').textContent=t('JEV 信号与有效节点','JEV signal and retained nodes');
  $('eventTitle').textContent=t('本次事件','Selected event');$('evidenceTitle').textContent=t('偏航判断与执行记录','Review and execution log');
  const presets={floor:t('完整底图','Full floor plan'),case:t('适配全程','Fit routes'),event:t('定位当前事件','Fit event')};
  for(const button of $('mapTools').querySelectorAll('[data-fit]'))button.textContent=presets[button.dataset.fit];
  for(const [id,title] of [['mapMinus',t('缩小','Zoom out')],['mapPlus',t('放大','Zoom in')]]){
    $(id).title=title;$(id).setAttribute('aria-label',title);
  }
  $('gestureHint').textContent=t('滚轮或双指缩放，拖动平移。','Use the wheel or pinch to zoom. Drag to pan.');
  $('mapHint').textContent=t('橙线是模型评审的区间；红线从被判偏航的节点起，至同段下一节点、回退前或结束。两条线均按模型记录着色。点击节点查看对应评审。','Orange is the reviewed interval. Red runs from the flagged node to the next node, rollback or end of that leg. Both reflect model judgments. Select a node to inspect its review.');
  const titles={original:name('original'),current:name('current'),reference:t('参考路线','Reference'),node:t('有效节点 ○','Retained nodes ○'),trusted:t('可信存档点 ●','Trusted checkpoints ●'),target:t('实际回退点 ◆','Used checkpoints ◆'),reviewed:t('当轮评审区间','Reviewed interval'),alarm:t('报警节点后轨迹','After flagged node'),local:t('局部纠错','Local recovery'),jump:t('物理回退跳转','Rollback jump')};
  $('layers').innerHTML=Object.keys(show).map(k=>'<label><input type="checkbox" data-layer="'+k+'" '+(show[k]?'checked':'')+'><span style="color:'+colors[k]+'">━</span> '+titles[k]+'</label>').join('');
  $('close').textContent=t('关闭','Close');$('play').textContent=clock?t('暂停','Pause'):t('播放','Play');
}
const cache=new Map();
function drawFrame(){
  const caseId=c().id,selArm=arm,s=c()[arm],f=at[arm],slot=f%16,path='media/'+caseId+'/'+s.sheets[Math.floor(f/16)];
  for(const el of [$('imageFrame'),$('mapFrame')]){el.max=s.count-1;el.value=f}
  $('step').textContent='F'+f+' / '+(s.count-1)+(s.local?.includes(f)?' · '+t('局部纠错','Local recovery'):'');
  $('armStats').textContent=result(s.sr)+' · SPL '+s.spl.toFixed(3)+' · NE '+s.ne.toFixed(2)+' m · '+reasonName(s.end);
  let im=cache.get(path);if(!im){im=new Image();im.src=path;cache.set(path,im);if(cache.size>8)cache.delete(cache.keys().next().value)}
  const ctx=$('rgb').getContext('2d');const paint=()=>{if(c().id===caseId&&arm===selArm&&at[arm]===f)ctx.drawImage(im,(slot%4)*480,Math.floor(slot/4)*360,480,360,0,0,480,360)};
  if(im.complete&&im.naturalWidth)paint();else{ctx.clearRect(0,0,480,360);im.addEventListener('load',paint,{once:true})}
  map();
}
function nodeRound(n){
  return records().findIndex(x=>x.review.leg===n[2]&&x.review.node===n[3]);
}
function trustedNode(n){
  const review=records()[nodeRound(n)]?.review;
  return review&&!review.terminal&&kind(review)==='consistent';
}
function eventStages(){
  const group=r();if(!group)return [];
  const q=group.review, rb=group.recovery?.rollback, h=group.recovery?.handoff;
  const alarm=kind(q)==='deviated', pts=[];
  const add=(key,title,frame,layer,short,node='')=>pts.push({key,title,frame,layer,short,node});
  if(q.previous!==q.node)add('anchor',t('上次可信节点','Last trusted node'),q.inputs[0],'trusted','A',q.previous);
  add('node',alarm?t('被判偏航的节点','Flagged node'):t('评审节点','Reviewed node'),q.inputs.at(-1),alarm?'alarm':'node','B',q.node);
  add('report',alarm?t('发出报警','Alarm issued'):t('给出判断','Verdict issued'),q.seq,alarm?'alarm':'node','R');
  if(group.gate)add('gate',t('接管前复核','Recheck'),group.gate.inputs.at(-1),'reviewed','G');
  if(rb){
    add('before',t('回退前','Before rollback'),rb.seq,'jump','P');
    add('target',t('回退目标','Rollback target'),rb.target,'target','T',rb.node);
    if(rb.after>rb.seq)add('landing',t('实际落点','Actual landing'),rb.after,'target','L');
    if(h)add('handoff',t('交还原策略','Handoff'),h.seq,'local','H');
    else if(c().current.local.includes(rb.after))add('localEnd',t('局部末次观测','Last local observation'),lastLocal(rb),'local','E');
  }
  return pts;
}
function lastLocal(rb){
  let end=rb.after;const local=new Set(c().current.local);
  while(local.has(end+1))end++;
  return end;
}
const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
function frameThumb(mark){
  const z=c().current,f=mark.frame,slot=f%16,page=Math.floor(f/16),rows=Math.min(4,Math.ceil((z.count-page*16)/4));
  const src='media/'+c().id+'/'+z.sheets[page];
  const style="background-image:url('"+src+"');background-size:400% "+(rows*100)+"%;background-position:"+(slot%4*100/3)+"% "+(rows>1?Math.floor(slot/4)*100/(rows-1):0)+"%";
  return '<button class="shot" data-seq="'+f+'" aria-current="'+(arm==='current'&&at.current===f)+'"><span class="thumb" style="'+style+'"></span><small>'+esc(mark.title)+' · F'+f+'</small></button>';
}
function drawEvent(){
  const buttons=records().flatMap((record,i)=>{
    const rb=record.recovery?.rollback;
    if(!rb)return [];
    const landed=rb.after>rb.seq, frame=landed?rb.after:rb.target;
    const label=t('第 '+rb.number+' 次回退','Rollback '+rb.number);
    const where=landed?t('落点','Landing'):t('存档点（无落点观测）','Checkpoint (no landing observation)');
    return ['<button data-rollback="'+i+'" data-frame="'+frame+'">'+label+' · '+esc(rb.node)+' · '+where+' F'+frame+'</button>'];
  });
  $('rollbackJumps').innerHTML=buttons.length?buttons.join(''):'<span>'+t('本任务无实际回退','No physical rollback in this episode')+'</span>';
  const group=r(), q=group?.review, rec=group?.recovery, rb=rec?.rollback, marks=eventStages();
  const used=c().events.filter(e=>e.type==='rollback'), allNodes=c().nodes;
  $('nodeTitle').textContent=t('全部有效节点','All retained nodes')+' '+allNodes.length+' · '+t('可信存档点','Trusted checkpoints')+' '+allNodes.filter(trustedNode).length+' · '+t('实际回退目标','Used checkpoints')+' '+new Set(used.map(e=>e.target)).size;
  $('nodeList').innerHTML=allNodes.map(n=>{
    const isTarget=used.some(e=>e.target===n[0]),i=nodeRound(n);
    const label=(n[4]?t('终止','Terminal'):isTarget?t('实际回退点','Used checkpoint'):trustedNode(n)?t('可信','Trusted'):t('有效','Retained'))+' '+n[3];
    return '<button class="'+(isTarget?'target ':'')+(i===round?'active':'')+'" data-review="'+i+'" data-nodeframe="'+n[0]+'">'+t('段','Leg ')+(n[2]+1)+' · '+esc(label)+' · F'+n[0]+'</button>';
  }).join('');
  $('stages').innerHTML=marks.map(m=>'<button style="--mark:'+colors[m.layer]+'" data-seq="'+m.frame+'"><b>'+m.short+'</b> '+esc(m.title)+' '+esc(m.node)+' · F'+m.frame+'</button>').join('');
  $('eventStatus').textContent=group?status(group):t('无对应记录','No matching record');
  if(!q){$('eventSummary').textContent=t('可切换到全部节点判断查看本任务。','Select all node reviews to inspect this case.');$('branchQuick').replaceChildren();return}
  const motion=q.motion;
  let facts='<div class="summaryline"><b>'+t('导航段','Leg')+' '+(q.leg+1)+' · '+esc(q.previous)+' → '+esc(q.node)+'</b>　'+
       t('评审图像','Review images')+' F'+q.inputs[0]+'–F'+q.inputs.at(-1)+'　'+t('给出判断','Verdict')+' F'+q.seq+' / A'+q.action+'</div>';
  if(motion)facts+='<p>'+t('评审区间实测','Measured in reviewed interval')+' · '+motion.actions[1]+' '+actionName(1)+' / '+motion.actions[2]+' '+actionName(2)+' / '+motion.actions[3]+' '+actionName(3)+' · '+t('距区间起点最远','Max. offset from start')+' '+motion.maxOffset.toFixed(2)+' m</p>';
  const snapshots=marks.filter(m=>['node','report','landing','handoff','localEnd'].includes(m.key));
  facts+='<div class="stepshots">'+snapshots.map(frameThumb).join('')+'</div>';
  if(rb&&rb.after>rb.seq){
    const points=c().current.points, end=rec.handoff?.seq??lastLocal(rb), goal=c().reference.at(-1);
    facts+='<div class="summaryline">'+t('实际回到','Returned to')+' <b>'+esc(rb.node)+' · F'+rb.target+'</b>　'+t('落点与存档点水平差','Landing offset')+' '+dist(points[rb.after],points[rb.target]).toFixed(2)+' m<br>'+
      t('距目标的水平直线距离','Horizontal distance to goal')+' · '+t('落点','Landing')+' '+dist(points[rb.after],goal).toFixed(2)+' m'+
      (rec.status==='selected'?' → '+(rec.handoff?t('交还','Handoff'):t('末次局部观测','Last local observation'))+' '+dist(points[end],goal).toFixed(2)+' m':'')+'</div>';
  }
  $('eventSummary').innerHTML=facts;
  if(!rec){
    $('branchQuick').innerHTML='<p class="summaryline">'+t('两阶段选路未进入，实际回退 0 次。','No two-stage branch selection or physical rollback for this review.')+'</p>';
    return;
  }
  if(!rec.second){$('branchQuick').textContent=status(group);return}
  const first=lang==='zh'?rec.first.answer:rec.first.english, second=rec.second;
  const tried=first.previous_attempt.branch_id, chosen=second.answer?.selected_branch_id;
  const dirs={front:t('正前','Ahead'),front_left:t('左前','Front left'),front_right:t('右前','Front right'),left:t('左侧','Left'),right:t('右侧','Right'),back:t('后方','Behind'),unknown:t('不确定','Uncertain')};
  const branches=first.branches.map(b=>{
    const picked=chosen===b.id, prior=tried===b.id, rejected=picked&&!!second.error;
    const badges=[prior?t('模型判为已走','Judged previously taken'):'',picked?(rejected?t('模型选择 · 被拒','Returned · rejected'):t('选中纠错','Chosen for recovery')):''].filter(Boolean);
    return '<article class="branchrow '+(rejected?'invalid':picked?'chosen':prior?'taken':'')+'"><h3>'+esc(b.id)+' · '+esc(dirs[b.direction]??b.direction)+badges.map(v=>'<span class="badge">'+v+'</span>').join('')+'</h3><p>'+esc(b.entrance_description)+'</p>'+evidenceButtons(b.evidence_image_ids,rec)+'</article>';
  }).join('');
  const decision=chosen??t('未选支路','No branch selected');
  const instruction=lang==='zh'?second.zh:second.answer?.recovery_instruction_en;
  const views=rec.images.slice(0,3).map((im,i)=>'<button data-im="'+i+'"><img loading="lazy" src="media/'+esc(c().id)+'/'+esc(im.file)+'" alt="'+esc(im.camera)+'"><small>'+[t('左 70°','Left 70°'),t('正前','Front'),t('右 70°','Right 70°')][i]+'</small></button>').join('');
  $('branchQuick').innerHTML='<h3>'+t('选路时使用的存档点三视图','Checkpoint views used for branch selection')+' · F'+rec.images[0].seq+'</h3><div class="brImages brImages3">'+views+'</div><h3>'+t('回退目标处识别的支路','Branches identified at the target')+' · '+first.branches.length+'</h3>'+branches+
    '<div class="quickInstruction"><b>'+t('已走支路 → 模型选择','Previously taken → model selection')+'</b>　'+esc(tried??t('不确定','Uncertain'))+' → '+esc(decision)+
    (instruction?'<p>'+esc(instruction)+'</p>':'')+(second.error?'<p>'+esc(err(second.error))+'</p>':'')+'</div>'+details(t('已走支路匹配依据','Why the model identified the prior branch'),'<p>'+esc(first.previous_attempt.reason)+'</p>');
}
function map(){
  const cs=c(),g=DATA.maps[cs.scene],p=cs.current.points,marks=eventStages(),group=r(),rb=group?.recovery?.rollback;
  const jumps=cs.events.filter(x=>x.type==='rollback');
  const alarmEnd=(n,i)=>cs.nodes[i+1]?.[2]===n[2]?cs.nodes[i+1][0]:(jumps.find(e=>e.leg===n[2])?.seq??p.length-1);
  const nidx=cs.nodes.findIndex(n=>n[2]===group?.review.leg&&n[3]===group.review.node);
  let bounds=[...cs.reference,...p,...cs.original.points];
  if(focus==='event'&&marks.length){
    let start=Math.min(...marks.map(m=>m.frame)),end=Math.max(...marks.map(m=>m.frame));
    if(nidx>=0&&kind(group.review)==='deviated')end=Math.max(end,alarmEnd(cs.nodes[nidx],nidx));
    bounds=p.slice(start,end+1);
  }
  if(!camera){
    if(focus==='floor'){
      bounds.push([g.low[0],g.high[1]],[g.low[0]+g.width*g.resolution,g.high[1]-g.height*g.resolution]);
    }
    const xs=bounds.map(v=>v[0]),ys=bounds.map(v=>v[1]),xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
    camera={x:(xmin+xmax)/2,y:(ymin+ymax)/2,scale:Math.min(710/Math.max(3,xmax-xmin),350/Math.max(2.2,ymax-ymin))};
  }
  const {scale}=camera;
  const xy=v=>[380+(v[0]-camera.x)*scale,197-(v[1]-camera.y)*scale];
  for(const button of $('mapTools').querySelectorAll('[data-fit]'))button.setAttribute('aria-pressed',String(focus===button.dataset.fit));
  for(const button of $('rollbackJumps').querySelectorAll('button')){
    button.setAttribute('aria-current',String(arm==='current'&&round===Number(button.dataset.rollback)&&at.current===Number(button.dataset.frame)));
  }
  const [left,top]=xy([g.low[0],g.high[1]]);
  let svg='<image href="maps/'+cs.scene+'.png" x="'+left+'" y="'+top+'" width="'+g.width*g.resolution*scale+'" height="'+g.height*g.resolution*scale+'" opacity=".65" preserveAspectRatio="none"/>';
  function path(arr,key,w,dash='',alpha=1){
    if(!show[key]||arr.length<2)return;
    svg+='<polyline fill="none" stroke-linecap="round" stroke-linejoin="round" stroke="'+colors[key]+'" stroke-width="'+w+'" stroke-dasharray="'+dash+'" opacity="'+alpha+'" points="'+arr.map(v=>xy(v).map(x=>x.toFixed(1)).join(',')).join(' ')+'"/>';
  }
  path(cs.reference,'reference',2.3,'6 4');path(cs.original.points,'original',2.4);
  let start=0;
  for(const e of jumps){path(p.slice(start,e.seq+1),'current',3);start=e.after}
  path(p.slice(start),'current',3);
  const alarmSet=new Set(records().filter(x=>kind(x.review)==='deviated').map(x=>x.review.leg+'/'+x.review.node));
  cs.nodes.forEach((n,i)=>{if(alarmSet.has(n[2]+'/'+n[3]))path(p.slice(n[0],alarmEnd(n,i)+1),'alarm',4.3,'',i===nidx?1:.45)});
  for(const e of jumps){
    if(e.after>e.seq){
      path([p[e.seq],p[e.after]],'jump',3,'4 5',rb===undefined||rb.seq===e.seq?1:.55);
      path(p.slice(e.after,lastLocal(e)+1),'local',4.4,'',rb?.seq===e.seq?1:.58);
    }
  }
  if(group)path(p.slice(group.review.inputs[0],group.review.inputs.at(-1)+1),'reviewed',4,'3 4');
  cs.nodes.forEach(n=>{
    const target=jumps.some(e=>e.target===n[0]),drawTarget=target&&show.target;
    const trusted=show.trusted&&trustedNode(n);
    if(!show.node&&!drawTarget&&!trusted)return;
    const incident=drawTarget?records().findIndex(q=>q.recovery?.rollback?.target===n[0]):-1;
    const index=drawTarget&&rb?.target===n[0]?round:incident>=0?incident:nodeRound(n);
    const [x,y]=xy(p[n[0]]),attr='class="mapmark" data-review="'+index+'" data-nodeframe="'+n[0]+'"';
    svg+='<g '+attr+'><title>'+esc(n[3])+' · F'+n[0]+'</title><circle cx="'+x+'" cy="'+y+'" r="8" fill="transparent"/>'+
      (drawTarget?'<path d="M'+x+' '+(y-6)+'l6 6 -6 6 -6 -6z" fill="'+colors.target+'" stroke="white"/>':
       n[4]?'<rect x="'+(x-4)+'" y="'+(y-4)+'" width="8" height="8" fill="white" stroke="'+colors.node+'"/>':
       '<circle cx="'+x+'" cy="'+y+'" r="3.6" fill="'+(trusted?colors.trusted:'white')+'" stroke="'+(trusted?colors.trusted:colors.node)+'" stroke-width="1.5"/>')+'</g>';
  });
  const [gx,gy]=xy(cs.reference.at(-1));svg+='<text x="'+gx+'" y="'+gy+'" fill="#8e421c" font-size="16">★</text>';
  const visible=marks.filter(m=>show[m.layer]); const used=[];
  visible.forEach(m=>{
    const [x,y]=xy(p[m.frame]);if(x<0||x>760||y<0||y>394)return;
    const offsets=[[16,-23],[16,21],[-28,-23],[-28,21],[36,0],[-45,0],[16,-47],[-28,47],[38,42]];
    let label;
    for(const [dx,dy] of offsets){
      label=[Math.min(741,Math.max(16,x+dx)),Math.min(380,Math.max(14,y+dy))];
      if(!used.some(([a,b])=>Math.abs(a-label[0])<25&&Math.abs(b-label[1])<24))break;
    }
    used.push(label);const [lx,ly]=label,ink=colors[m.layer];
    svg+='<g class="mapmark" data-seq="'+m.frame+'"><title>'+esc(m.title)+' · F'+m.frame+'</title>'+
      '<path d="M'+x+' '+y+' L'+lx+' '+ly+'" fill="none" stroke="'+ink+'" stroke-width="1.5"/><circle cx="'+x+'" cy="'+y+'" r="3" fill="'+ink+'"/>'+
      '<rect x="'+(lx-10)+'" y="'+(ly-10)+'" width="20" height="20" rx="5" fill="'+ink+'" stroke="white"/><text x="'+lx+'" y="'+(ly+4)+'" fill="white" text-anchor="middle" font-size="12" font-weight="bold">'+m.short+'</text></g>';
  });
  if(show[arm]){
    const [x,y]=xy(cs[arm].points[at[arm]]);svg+='<circle cx="'+x+'" cy="'+y+'" r="7" fill="none" stroke="#162731" stroke-width="2" pointer-events="none"/>';
  }
  $('map').innerHTML=svg;
  const wx=i=>1+498*i/Math.max(1,p.length-1);let wave='';
  for(const [col,ink] of [[1,'#b05754'],[2,'#265bae']]){let last=-2,pts=[];const flush=()=>{if(pts.length)wave+='<polyline points="'+pts.join(' ')+'" stroke="'+ink+'" fill="none" stroke-width="1.5"/>';pts=[]};for(const row of cs.jev){if(row[0]!==last+1||row[col]==null)flush();if(row[col]!=null)pts.push(wx(row[0])+','+(64-58*row[col]));last=row[0]}flush()}
  wave+=cs.nodes.map(n=>'<path d="M'+wx(n[0])+' 61v9" stroke="'+colors.node+'" stroke-width="2"/>').join('');
  $('wave').innerHTML=wave+'<path d="M'+wx(at.current)+' 0v70" stroke="#263a49"/>';
  for(const b of $('eventSummary').querySelectorAll('.shot'))b.setAttribute('aria-current',arm==='current'&&Number(b.dataset.seq)===at.current);
}
function render(){head();obsControls();drawRound();drawEvent();drawFrame()}
function stop(){if(clock){clearInterval(clock);clock=null}$('play').textContent=t('播放','Play')}
function go(f,a=arm){stop();if(arm!==a){arm=a;obsControls()}at[arm]=Math.max(0,Math.min(f,c()[arm].count-1));drawFrame()}
function fitMap(preset){
  focus=preset;camera=null;map();
}
function moveCamera(from,to,factor){
  const g=DATA.maps[c().scene];
  const floorScale=Math.min(710/(g.width*g.resolution),350/(g.height*g.resolution));
  const scale=Math.max(floorScale/3,Math.min(Math.max(1000,floorScale*80),camera.scale*factor));
  camera={
    x:camera.x+(from.x-380)/camera.scale-(to.x-380)/scale,
    y:camera.y-(from.y-197)/camera.scale+(to.y-197)/scale,
    scale
  };
  focus='manual';map();
}
const mapCenter={x:380,y:197};
const mapSvg=$('map'), pointers=new Map();
let dragged=false;
function svgPoint(e){
  return new DOMPoint(e.clientX,e.clientY).matrixTransform(mapSvg.getScreenCTM().inverse());
}
function gesture(){
  const [first,second]=pointers.values();
  if(!second)return {center:first,span:0};
  return {center:{x:(first.x+second.x)/2,y:(first.y+second.y)/2},
          span:Math.hypot(first.x-second.x,first.y-second.y)};
}
mapSvg.addEventListener('wheel',e=>{
  e.preventDefault();
  const atPointer=svgPoint(e), unit=e.deltaMode===1?16:e.deltaMode===2?394:1;
  const amount=Math.max(-1,Math.min(1,e.deltaY*unit*0.002));
  moveCamera(atPointer,atPointer,Math.exp(-amount));
},{passive:false});
mapSvg.addEventListener('pointerdown',e=>{
  if(e.button!==0||pointers.size>=2)return;
  if(!pointers.size)dragged=false;
  pointers.set(e.pointerId,svgPoint(e));
  if(pointers.size===2){
    dragged=true;
    for(const id of pointers.keys())mapSvg.setPointerCapture(id);
  }
});
mapSvg.addEventListener('pointermove',e=>{
  if(!pointers.has(e.pointerId))return;
  const before=gesture(), point=svgPoint(e), previous=pointers.get(e.pointerId);
  if(!dragged&&Math.hypot(point.x-previous.x,point.y-previous.y)<3)return;
  dragged=true;mapSvg.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId,point);
  const after=gesture();
  moveCamera(before.center,after.center,before.span>0&&after.span>0?after.span/before.span:1);
});
for(const end of ['pointerup','pointercancel','lostpointercapture']){
  window.addEventListener(end,e=>{
    if(end==='lostpointercapture'&&e.target!==mapSvg)return;
    pointers.delete(e.pointerId);
  });
}
mapSvg.addEventListener('click',e=>{
  if(dragged){dragged=false;e.stopImmediatePropagation()}
},true);
$('mapTools').onclick=e=>{
  const button=e.target.closest('button');
  if(!button)return;
  if(button.dataset.fit)fitMap(button.dataset.fit);
  else moveCamera(mapCenter,mapCenter,button.id==='mapPlus'?1.5:1/1.5);
};
function pickRound(i,frame){
  stop();round=i;arm='current';
  if(focus==='manual')focus='event';
  if(focus==='event')camera=null;
  at.current=frame??r()?.review.seq??0;render();
}
$('language').onchange=e=>{stop();$('dialog').close();lang=e.target.value;render()};
$('caseJump').onchange=e=>selectCase(Number(e.target.value));
$('filter').onchange=e=>{filter=e.target.value;selectCase(eligibleCases()[0].i)};
$('roundFilter').onchange=e=>{scope=e.target.value;pickRound(eligibleRounds()[0]?.i??-1)};
$('rounds').onchange=e=>pickRound(Number(e.target.value));$('arm').onchange=e=>go(at[e.target.value],e.target.value);
$('rollbackJumps').onclick=e=>{
  const button=e.target.closest('button[data-rollback]');
  if(!button)return;
  focus='event';
  pickRound(Number(button.dataset.rollback),Number(button.dataset.frame));
};
for(const id of ['imageFrame','mapFrame'])$(id).oninput=e=>go(Number(e.target.value));
$('restart').onclick=()=>go(0);$('end').onclick=()=>go(c()[arm].count-1);$('prev').onclick=()=>go(at[arm]-1);$('next').onclick=()=>go(at[arm]+1);
$('play').onclick=()=>{if(clock)return stop();if(at[arm]===c()[arm].count-1)at[arm]=0;$('play').textContent=t('暂停','Pause');clock=setInterval(()=>{if(at[arm]>=c()[arm].count-1)return stop();at[arm]++;drawFrame()},220)};
$('layers').onchange=e=>{show[e.target.dataset.layer]=e.target.checked;map()};
document.addEventListener('click',e=>{const b=e.target.closest('[data-review],[data-im],[data-seq]');if(!b)return;
  if(b.dataset.review!==undefined){scope='all';pickRound(Number(b.dataset.review));go(Number(b.dataset.nodeframe),'current');return}
  if(b.dataset.seq!==undefined){go(Number(b.dataset.seq),'current');return}
  const im=r()?.recovery?.images[Number(b.dataset.im)];if(!im)return;go(im.seq,'current');$('large').src='media/'+c().id+'/'+im.file;$('caption').textContent=im.camera+' · F'+im.seq;$('dialog').showModal();
});
$('close').onclick=()=>$('dialog').close();document.addEventListener('visibilitychange',()=>{if(document.hidden)stop()});
const params=new URLSearchParams(location.search);
const requested=params.get('case');
const requestedIndex=DATA.cases.findIndex(v=>v.id===requested);
selectCase(requestedIndex>=0?requestedIndex:Math.max(0,DATA.cases.findIndex(v=>v.rollbacks>0&&v.original.sr>v.current.sr)));
if(requestedIndex>=0&&params.has('event')){
  const index=records().findIndex(item=>item.review.id===params.get('event'));
  if(index>=0){scope='all';pickRound(index)}
}
