const localText=(zh,en)=>lang==='zh'?zh:en;
const selectedRound=new Map();
let panelKey='';
function caseSummary(v){
  const r=v.rounds[v.rounds.length-1];
  if(v.group==='initOnly')return localText('终止帧仅初始化，无相邻节点可判定','Terminal initialization only; no adjacent checkpoints to assess')+' · F'+v.end;
  const status=v.terminalReviewed?localText('已评审真实终止帧','Terminal frame reviewed'):localText('先报警，未调用终止轮','Alarm occurred before terminal review');
  return (v.alarm?localText('报警区间','Alarm interval')+' F'+r.a+' → F'+r.b:localText('未报警','No alarm'))+' · '+status+' F'+v.end;
}
function routeLayer(ctx,xy){
  if(!$('showAlarm'))return;
  const v=c(), r=v.rounds.find(r=>r.answer.verdict==='deviated');
  function line(a,b,color,dash,width){
    ctx.save();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.beginPath();
    for(let i=a;i<=b;i++){const point=xy(v.frames[i].position);i===a?ctx.moveTo(...point):ctx.lineTo(...point);}
    ctx.stroke();ctx.restore();
  }
  function marker(f,label,color,radius){
    const [x,y]=xy(v.frames[f].position);ctx.save();ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();
    ctx.arc(x,y,radius,0,2*Math.PI);ctx.stroke();ctx.font='bold 12px system-ui';
    const tx=Math.max(2,Math.min(ctx.canvas.clientWidth-30,x+radius)),ty=Math.max(14,y-4);
    ctx.strokeStyle='#fff';ctx.lineWidth=3;ctx.strokeText(label,tx,ty);ctx.fillStyle=color;ctx.fillText(label,tx,ty);ctx.restore();
  }
  if(r&&$('showAlarm').checked)line(r.a,r.b,'#eb1834',[],7);
  if($('showAnnotation').checked)for(const [a,b] of v.referenceErrors)line(a,b,'#b17608',[3,5],3);
  if($('showEnd').checked)marker(v.end,'END','#263a4c',7);
  if(r&&$('showTarget').checked)marker(r.a,'A','#066848',10);
}
function roundPlot(ctx,x,top,bottom){
  if(!$('showAlarm'))return;
  const v=c(), r=v.rounds.find(r=>r.answer.verdict==='deviated');
  ctx.save();
  if(r&&$('showAlarm').checked){ctx.fillStyle='rgba(235,24,52,.16)';ctx.fillRect(x(r.a),top,Math.max(2,x(r.b)-x(r.a)),bottom-top);}
  if($('showEnd').checked){ctx.fillStyle='#263a4c';ctx.fillText('END',x(v.end)-22,top+11);}
  ctx.restore();
}
function make(tag,value,cls){
  const item=document.createElement(tag);
  if(value!==undefined)item.textContent=value;
  if(cls)item.className=cls;
  return item;
}
function jump(f){stop();seek(f);}
function reviewPanel(){
  const root=$('routeReviews');
  if(!$('showAlarm'))return;
  const v=c(), i=selectedRound.get(ci)??v.rounds.length-1, r=v.rounds[i], a=r.answer;
  const key=[ci,i,lang].join('/');
  if(panelKey!==key){
    panelKey=key;
    root.replaceChildren(make('h3',localText('Codex 逐轮偏航评审','Codex deviation reviews')));
    const picker=make('div',undefined,'reviewPicks');root.append(picker);
    v.rounds.forEach((rr,j)=>{
      const label=(rr.terminal?'END · ':'')+(rr.a===rr.b?localText('初始化 ','Init ')+'F'+rr.b:'F'+rr.a+' → F'+rr.b);
      const btn=make('button',label+(rr.answer.verdict==='deviated'?' · '+localText('偏航','Alarm'):''));
      btn.type='button';btn.dataset.round=j;btn.classList.toggle('alarm',rr.answer.verdict==='deviated');
      btn.setAttribute('aria-pressed',String(j===i));
      btn.onclick=()=>{selectedRound.set(ci,j);jump(rr.b);};picker.append(btn);
    });
    const verdict=r.a===r.b?localText('初始化','Initialization'):a.verdict==='deviated'?localText('偏航','Deviated'):localText('继续','Consistent');
    root.append(make('strong',a.previous_id+' → '+a.current_id+' · '+verdict));
    root.append(make('p',localText('本轮补图 '+r.added.length+' 张', 'New attachments in this review: '+r.added.length)+
      (r.terminal?' · '+localText('终止原生前视图已在上一轮入会话','The terminal front RGB was supplied in the preceding turn'):'')+
      (a.verdict==='deviated'?' · '+localText('回退目标 ','Rollback target ')+a.previous_id:''),'muted'));
    const cols=make('div',undefined,'reviewFields');root.append(cols);
    function field(title,value){
      const block=make('section');block.append(make('h4',title),make('p',value||localText('无','None')));cols.append(block);
    }
    field(localText('本段实际行进','Observed movement'),a.segment_summary[lang]);
    field(localText('判断理由','Rationale'),a.reason[lang]);
    field(localText('A 处传入的进度','Prior progress at A'),r.prior[lang==='zh'?0:1]);
    field(localText('本轮返回的进度','Returned progress'),a.semantic_progress?.[lang]||localText('报警，进度为 null','Alarm; progress is null'));
    field(localText('指令证据','Instruction evidence'),a.instruction_evidence.map(q=>q['quote_'+lang]).join('\n'));
    field(localText('视觉证据','Visual evidence'),a.visual_evidence.map(q=>q.frames.map(f=>'F'+f).join(', ')+' · '+q.description[lang]).join('\n'));
    field(localText('仍待确认','Uncertainties'),a.uncertainties.map(q=>q[lang]).join('\n'));
    root.append(make('h4',localText('本轮可引用的前视图','Front views available in this round')));
    const images=make('div',undefined,'reviewGallery'),cited=new Set(a.visual_evidence.flatMap(e=>e.frames));
    for(const [frame,ids] of Object.entries(r.refs)){
      const f=Number(frame), img=new Image(), btn=make('button');
      img.src=B.images[v.frames[f].image];img.alt='F'+frame;img.loading='lazy';
      btn.dataset.reviewFrame=f;btn.title=ids.join(' / ');btn.onclick=()=>jump(f);
      const source=r.added.includes(f)?localText(' · 本轮补图',' · added this round'):localText(' · 历史观测',' · earlier observation');
      btn.append(img,make('span','F'+f+source+(cited.has(f)?localText(' · 已引用',' · cited'):'')));images.append(btn);
    }
    root.append(images);
    function details(title,body){const d=make('details');d.append(make('summary',title),make('pre',body));root.append(d);}
    details(localText('本轮提示词（中文翻译）','Exact prompt sent'),r.prompts[lang==='zh'?0:1]);
    details(localText('完整双语原答','Verbatim bilingual answer'),r.raw);
    const screening=make('details');screening.append(make('summary',localText('v002 原始候选与筛选结果','v002 raw candidates and screening decisions')));
    const actions={append_current:localText('保留','Retained'),replace_previous:localText('替换','Replaced'),reject_current:localText('未通过','Rejected'),unreviewed:localText('停审后未评','Unreviewed after alarm')};
    for(const n of v.samples){const btn=make('button',n.id+' · F'+n.index+' · '+actions[n.action]+
      (n.action==='replace_previous'?' '+n.previous:''));btn.onclick=()=>jump(n.index);screening.append(btn);}
    root.append(screening);
  }
  root.querySelectorAll('[data-review-frame]').forEach(b=>b.setAttribute('aria-current',String(Number(b.dataset.reviewFrame)===index)));
}
function setupTerminalReplay(){
  Object.assign(L.zh,{title:'Codex 偏航评审 · 终止节点',subtitle:'JEV v002 精简档 · GPT-6 Astra 常规档 · seed 2',source:B.cases.length+' 条冻结轨迹 · 原生前视',initOnly:'仅初始化',rawActive:'v002 精简 · 原始候选',effectiveNodes:'Astra · 有效节点',roundsLabel:'偏航评审轮数',alarmsLabel:'报警轨迹',alarmed:'已报警',quiet:'未报警',baselineWin:'原版成功',baselineFail:'原版失败',unscored:'本版未作导航评分',layerKey:'圆点为 v002 原始候选，紫色菱形为本轮保留的有效节点。红线沿实际轨迹连接报警端点，A 标出回退目标。',notice:'偏航判断只引用同会话已有前视图。尚未报警时，提交终止观测后评审至 END。',footer:'本轮为离线评审。当前版与配对原版的导航 SR、平均 SPL 均暂无，已评分 0 条。',showAlarm:'偏航段',showTarget:'回退目标 A',showEnd:'终止帧 END',showAnnotation:'事后错选区间',download:'下载离线回放'});
  Object.assign(L.en,{title:'Codex deviation reviews · Terminal checkpoint',subtitle:'JEV v002 Lean · GPT-6 Astra standard · seed 2',source:B.cases.length+' frozen trajectories · native front view',initOnly:'Initialization only',rawActive:'v002 Lean · Raw candidates',effectiveNodes:'Astra · Effective checkpoints',roundsLabel:'Deviation reviews',alarmsLabel:'Trajectories with alarms',alarmed:'Alarm',quiet:'No alarm',baselineWin:'Baseline succeeded',baselineFail:'Baseline failed',unscored:'Current navigation unscored',layerKey:'Circles mark raw v002 candidates and purple diamonds mark retained checkpoints. Red follows the actual path between alarm endpoints. A marks the rollback target.',notice:'Reviews cite front views already in the thread. Cases without an earlier alarm receive the terminal observation and a review through END.',footer:'Offline reviews. Current and paired baseline navigation SR and mean SPL are unavailable (0 scored episodes for each).',showAlarm:'Alarm segment',showTarget:'Rollback target A',showEnd:'Terminal frame END',showAnnotation:'Retrospective error interval',download:'Download offline replay'});
  L.zh.notice='逐轮展示可用的历史前视图和实际补图。采用六帧规则的评审，在相邻观测相距超过六帧时补图。尚未报警的轨迹继续评审至 END。';
  L.en.notice='Each review shows the earlier front views and any new attachments. Under the six-frame rule, additional views fill gaps longer than six frames. Reviews continue to END unless an earlier alarm occurs.';
  for(const id of ['showAlarm','showTarget','showEnd','showAnnotation']){
    const label=make('label',undefined,'samplingOption'),input=make('input'),caption=make('strong');
    input.type='checkbox';input.id=id;input.checked=id!=='showAnnotation';input.onchange=draw;caption.dataset.i18n=id;
    label.append(input,caption);$('samplingVersions').append(label);
  }
  $('sample_Astra').checked=true;
  for(const el of ['filterWindow','streamDelay'])$(el).disabled=true;
  $('filters').value='all';updateLanguage();selectCase(0);
}
