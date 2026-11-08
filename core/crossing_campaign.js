function renderRunChoices(){
  const groups={development:[],validation:[]};
  for(const data of Object.values(B.runs))groups[data.summary.split==='validation'?'validation':'development'].push(data);
  for(const [split,runs] of Object.entries(groups)){
    $(split+'Group').hidden=!runs.length;
    if(!runs.length)continue;
    const first=runs[0],same=runs.every(d=>JSON.stringify(Object.keys(d.cases).sort())===JSON.stringify(Object.keys(first.cases).sort())&&d.summary.processed===first.summary.processed);
    $(split+'Info').textContent=(split==='development'?'开发集':'独立验证集')+' · '+runs.length+' 个版本 · '+(same?`${Object.keys(first.cases).length} 条轨迹 / 每版 ${first.summary.processed} 个观测`:'各版样本数量见版本说明');
  }
  $('campaignGroups').classList.toggle('singleGroup',!groups.development.length||!groups.validation.length);
  $('campaignTitle').textContent=groups.development.length&&groups.validation.length?'开发版本对照 · 独立验证':'Crossing '+(groups.development.length?'开发迭代':'独立验证')+'复核';
  $('campaignInfo').textContent=`本文件包含 ${Object.keys(B.runs).length} 个已完成版本；成绩、观测和复核说明对应各自的实际运行。`;
  $('bookmarks').parentElement.hidden=!B.bookmarks.length;
  for(const id of ['developmentRuns','validationRuns'])$(id).replaceChildren();
  for(const [tag,data] of Object.entries(B.runs)){
    const m=data.summary.metrics['1.0'],b=document.createElement('button');b.className='runChoice'+(D.tag===tag?' active':'');b.dataset.run=tag;b.setAttribute('aria-pressed',String(D.tag===tag));
    const title=document.createElement('strong'),score=document.createElement('span'),count=document.createElement('small'),bar=document.createElement('div'),fill=document.createElement('i');
    title.textContent=B.labels[tag];score.className='runScore';score.textContent='F1 '+pct(m.f1);count.textContent=`TP ${m.tp} · FP ${m.fp} · FN ${m.fn}`;bar.className='runMeter';fill.style.width=(m.f1*100)+'%';bar.append(fill);b.append(title,score,count,bar);b.onclick=()=>selectRun(tag);
    $(data.summary.split==='validation'?'validationRuns':'developmentRuns').append(b);
  }
  $('runDescription').textContent=B.descriptions[D.tag];
}
function renderCaseReview(){
  const row=B.case_notes[D.tag]?.[cid];$('caseReview').replaceChildren();
  const label=document.createElement('strong');label.textContent='离线复核说明';$('caseReview').append(label);
  const p=document.createElement('p');p.textContent=row?.text||'点击地图 C/P 点或下方匹配事件核对画面、原始回答和当时存档。可在本地填写并导出复核意见。';$('caseReview').append(p);
  for(const frame of row?.frames||[]){const b=document.createElement('button');b.textContent='观测 '+frame;b.onclick=()=>jump(frame);$('caseReview').append(b)}
}
function selectRun(tag){
  if(!Object.hasOwn(B.runs,tag))throw new Error('Unknown run: '+tag);
  const previous=cid,frame=snap()?.frame??0;stop();D=B.runs[tag];const preserve=Object.hasOwn(D.cases,previous);cid=preserve?previous:Object.keys(D.cases)[0];
  $('filters').value='all';$('eventFilter').value='all';renderSummary();renderRunChoices();select(cid);if(preserve)jump(frame);
}
function chooseBookmark(bookmark){selectRun(bookmark.tag);select(bookmark.episode);jump(bookmark.frame);$('selectedEvent').textContent=bookmark.title+'。'+bookmark.note;$('detail').scrollIntoView({block:'nearest'})}
for(const bookmark of B.bookmarks){const b=document.createElement('button');b.textContent=bookmark.title;b.onclick=()=>chooseBookmark(bookmark);$('bookmarks').append(b)}
$('rgb').onclick=()=>{$('largeImage').src=snap().image;$('largeImage').alt=$('rgb').alt;$('imageDialog').showModal()};
$('closeImage').onclick=()=>$('imageDialog').close();
$('imageFrame').oninput=e=>{stop();seek(Number(e.target.value))};
$('export').textContent='导出当前版本复核意见';
window.CROSSING_REVIEW={get data(){return D},bundle:B,selectRun,chooseBookmark,select,seek,jump,events,chooseEvent,annotationLayers,choosePrior,chooseCurrent,state:()=>({tag:D.tag,episode_id:cid,index,frame:snap().frame,selected:selected?.key??null})};
selectRun(B.initial);
document.fonts.ready.then(()=>draw());
