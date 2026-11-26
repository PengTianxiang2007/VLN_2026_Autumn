const overlays = {nodes:true, alarm:true, target:true, referenceEvent:false};
const colors = {nodes:'#187e70', alarm:'#c53038', target:'#533a92', referenceEvent:'#c77a12'};
const layerNames = {nodes:['有效节点','Effective checkpoints'], alarm:['偏航段','Alarm segment'],
  target:['回退目标','Rollback target'], referenceEvent:['事后错选区间','Annotated error interval']};
let currentCase = null, roundIndex = 0, candidateIndex = 0;
const localized = pair => pair[lang];
const verdictLabel = v => v==='deviated' ? text('偏航','Deviated') : text('继续','Consistent');
const actionNames = {append_current:['保留新节点','Retained'],replace_previous:['替换上一节点','Replaced previous'],
  reject_current:['未通过筛选','Rejected'],unreviewed:['未评审','Unreviewed']};
function element(tag, content, cls) {
  const e=document.createElement(tag);
  if(content!==undefined) e.textContent=content;
  if(cls) e.className=cls;
  return e;
}
function button(content, callback, selected, cls) {
  const b=element('button',content,cls);
  b.type='button'; b.onclick=callback;
  if(selected!==undefined) b.setAttribute('aria-pressed',String(selected));
  return b;
}
function section(id, title, detail) {
  const root=$(id), header=element('div',undefined,'cardhead'), body=element('div',undefined,'inside');
  header.append(element('h2',title),element('small',detail)); root.replaceChildren(header,body);return body;
}
function field(parent, title, content) {
  const block=element('div',undefined,'field');block.append(element('h3',title));
  if(Array.isArray(content)){
    if(content.length){
      const list=element('ul');content.forEach(t=>list.append(element('li',t)));block.append(list);
    } else block.append(element('p',text('无','None')));
  }else block.append(element('p',content));
  parent.append(block);
}
function fold(parent,title,content) {
  const details=element('details');details.append(element('summary',title),element('pre',content));parent.append(details);
}
function openFrame(f) {
  $('mode').value='front';slot=0;jump(f);
}
function gallery(parent, frames, citations, refs) {
  const row=element('div',undefined,'evidence');
  for(const f of frames){
    const b=button('',()=>openFrame(f)), img=new Image();
    img.src=task.front[f];img.alt='F'+f;img.loading='lazy';
    b.dataset.evidenceFrame=f;b.dataset.cited=citations.has(f);
    b.title=(refs?.[f]||[]).join(' / ');
    b.append(img,element('span','F'+f));
    if(citations.has(f)) b.append(element('small',text('原答引用','Cited in answer')));
    row.append(b);
  }
  parent.append(row);
}
function markCurrent(){
  for(const b of document.querySelectorAll('[data-evidence-frame]'))
    b.setAttribute('aria-current',String(Number(b.dataset.evidenceFrame)===step));
}
function drawReviewMap() {
  const group=$('reviewMap');group.replaceChildren();
  function shape(name,attrs) {
    const n=document.createElementNS('http://www.w3.org/2000/svg',name);putAttrs(n,attrs);group.append(n);return n;
  }
  function line(a,b,color,width,dash) {
    const n=shape('polyline',{points:task.robot.slice(a,b+1).map(p=>xy(p).join(',')).join(' '),
      stroke:color,'stroke-width':width,fill:'none'});
    if(dash)n.setAttribute('stroke-dasharray',dash);
  }
  const alarm=task.reviews.find(r=>r.answer.verdict==='deviated');
  if(overlays.alarm && alarm)line(alarm.a,alarm.b,colors.alarm,6);
  if(overlays.referenceEvent)for(const e of task.events)line(...e.interval,colors.referenceEvent,4,'4 5');
  if(overlays.nodes)for(const n of task.candidates.filter(n=>task.active.includes(n.id))){
    const [x,y]=xy(task.robot[n.frame]);
    const circle=shape('circle',{cx:x,cy:y,r:5*symbolScale,fill:colors.nodes,stroke:'#fff','stroke-width':1.5,class:'node'});
    const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=n.id+' · F'+n.frame;
    circle.append(title);circle.onclick=()=>selectRound(task.reviews.findIndex(r=>r.b===n.frame));
  }
  if(overlays.target && alarm) {
    const [x,y]=xy(task.robot[alarm.a]);shape('circle',{cx:x,cy:y,r:9*symbolScale,fill:'none',stroke:colors.target,'stroke-width':3,'pointer-events':'none'});
  }
}
function layers() {
  const row=$('reviewLayers');row.replaceChildren();
  for(const key of Object.keys(overlays)){
    const label=element('label'), input=element('input'), chip=element('span',undefined,'layer-chip');
    input.type='checkbox';input.checked=overlays[key];input.id='layer_'+key;chip.style.background=colors[key];
    input.onchange=()=>{overlays[key]=input.checked;drawReviewMap();};
    label.append(input,chip,document.createTextNode(localized(layerNames[key])));row.append(label);
  }
  drawReviewMap();
}
function selectRound(i) {
  if(i<0)return;
  roundIndex=i;
  const f=task.reviews[i].b;
  candidateIndex=task.candidates.findIndex(c=>c.frame===f);
  renderReview();openFrame(f);
}
function selectCandidate(i) {
  candidateIndex=i;
  const f=task.candidates[i].frame, j=task.reviews.findIndex(r=>r.b===f);
  if(j>=0)roundIndex=j;
  renderReview();openFrame(f);
}
function candidatePanel() {
  const processed=task.candidates.filter(n=>n.action).length;
  const body=section('screening',text('回退点筛选','Checkpoint screening'),
    text('已筛选 ','Reviewed ')+processed+' / '+task.candidates.length+text(' 个原始候选',' raw candidates'));
  const choices=element('div',undefined,'rounds');
  task.candidates.forEach((n,i)=>choices.append(button(n.id+' · F'+n.frame,()=>selectCandidate(i),i===candidateIndex)));
  body.append(choices);
  const n=task.candidates[candidateIndex], action=localized(actionNames[n.action||'unreviewed']);
  body.append(element('strong',n.id+' · F'+n.frame+'　'+action));
  if(!n.action){body.append(element('p',text('首次报警后停止本例筛选，此候选没有模型回答。','Screening stopped at the first alarm. This candidate has no model response.')));return;}
  const a=n.answer[lang], cols=element('div',undefined,'fields');
  field(cols,text('资格判断','Eligibility rationale'),a.eligibility_reason);
  field(cols,text('与上一节点的关系','Relation to the previous checkpoint'),a.reason);body.append(cols);
  body.append(element('p',text('本轮筛选前 → 筛选后的有效节点','Effective checkpoints before → after this screening')+'　'+
    (n.before.join(' / ')||'∅')+' → '+(n.after.join(' / ')||'∅'),'roundnote'));
  body.append(element('h3',text('本轮筛选实际上传的前视图','Front images attached to this screening call'),'section-title'));
  gallery(body,n.images,new Set());
  fold(body,text('完整筛选回答（中文译文）','Full original screening answer'),JSON.stringify(a,null,2));
}
function renderReview() {
  if(currentCase!==task.id){
    currentCase=task.id;roundIndex=task.reviews.length-1;
    candidateIndex=task.candidates.findIndex(c=>c.frame===task.reviews[roundIndex].b);
    step=task.reviews[roundIndex].b;
  }
  for(const [i,t] of tasks.entries()){
    const state=t.rollback ? text('偏航报警','Alarm') : text('未报警','No alarm');
    $('task').options[i].text='C'+String(t.number).padStart(2,'0')+' · '+state+' · '+t.id;
  }
  layers();
  const body=section('reviews',text('同会话偏航评审','Same-thread deviation reviews'),
    task.reviews.length+text(' 轮 · 偏航调用新增图片 0 张',' rounds · 0 new image attachments'));
  const final=task.reviews[task.reviews.length-1], event=task.events[0];
  const timing=task.rollback
    ? text('首次报警区间','First alarm interval')+' F'+final.a+'–F'+final.b
    : text('未报警，最后评审到','No alarm. Last reviewed frame')+' F'+final.b;
  body.append(element('p',timing+'　·　'+text('事后归因的错选区间','Retrospective error interval')+
    ' F'+event.interval[0]+'–F'+event.interval[1],'roundnote'));
  const row=element('div',undefined,'rounds');
  task.reviews.forEach((r,i)=>{
    const label=(r.a===r.b ? text('初始化 ','Init ')+'F'+r.b : 'F'+r.a+' → F'+r.b);
    const alarm=r.answer.verdict==='deviated';
    row.append(button(label+(alarm ? ' · '+verdictLabel('deviated'):''),()=>selectRound(i),i===roundIndex,alarm?'alarm':''));
  });
  body.append(row);
  const r=task.reviews[roundIndex], a=r.answer, l=lang?'en':'zh', meta=element('div',undefined,'roundmeta');
  meta.append(element('strong',a.previous_id+' → '+a.current_id),
    element('span',verdictLabel(a.verdict),a.verdict==='deviated'?'verdict alarm':'verdict'),
    element('small',text('会话轮次 ','Thread turn ')+r.turn));body.append(meta);
  if(r.rollback)body.append(element('p',text('记录的回退目标（离线）','Recorded rollback target (offline)')+'　'+r.rollback,'roundnote'));
  const cols=element('div',undefined,'fields');
  field(cols,text('本段实际行进','Observed movement'),a.segment_summary[l]);
  field(cols,text('判断理由','Rationale'),a.reason[l]);
  field(cols,text('A 处传入进度','Progress supplied at A'),localized(r.prior));
  field(cols,text('本轮返回进度','Progress returned this round'),a.semantic_progress?.[l]||text('报警，本轮进度为 null。','Alarm. Progress is null for this round.'));
  field(cols,text('指令原文证据','Instruction evidence'),a.instruction_evidence.map(e=>e['quote_'+l]));
  field(cols,text('视觉证据','Visual evidence'),a.visual_evidence.map(e=>e.frames.map(f=>'F'+f).join(', ')+'　'+e.description[l]));
  field(cols,text('仍待确认','Uncertainties'),a.uncertainties.map(e=>e[l]));body.append(cols);
  body.append(element('h3',text('本轮允许引用的历史前视图','Historical front images available to this review'),'section-title'));
  gallery(body,Object.keys(r.refs).map(Number),new Set(a.visual_evidence.flatMap(e=>e.frames)),r.refs);
  fold(body,text('查看本轮实际提示词的中文译文','View the exact prompt sent'),localized(r.prompt));
  fold(body,text('完整双语原答（JSON）','Full verbatim bilingual answer (JSON)'),r.raw);
  candidatePanel();markCurrent();
}
drawRoutes();setLayers();localize();
