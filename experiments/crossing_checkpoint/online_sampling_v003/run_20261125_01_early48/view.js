const samplerNames={v001:['v001 原版（默认）','v001 Original (default)'],coverage:['v003 覆盖优先（候选）','v003 Higher coverage (candidate)'],active:['v002 精简（候选）','v002 Lean (candidate)'],wrong:['历史错选帧','Historical wrong-choice frame']};
const oldTitle={zh:'早期 48 条 Crossing 错选 · 三版采样',en:'Early 48 Crossing errors · Three samplers'};
for(const [language,i] of [['zh',0],['en',1]]){
  Object.assign(L[language],{
    title:oldTitle[language],subtitle:['seed 2 原始录像 · 冻结参数逐步回放','Original seed 2 recordings · Streaming replay with frozen settings'][i],
    source:['早期 48 条 Crossing 错选归因轨迹','Original 48 Crossing failure trajectories'][i],
    candidateCount:['历史错选参考帧','Historical wrong-choice frames'][i],
    layerInfo:['分色圆点为各版采样位置，紫色菱形为原轨迹标记的错选帧。悬停查看帧号。','Colored sectors show sampler positions; purple diamonds mark historical wrong-choice frames. Hover to inspect frames.'][i],
    summaryTitle:['历史错选位置覆盖','Coverage of historical wrong-choice locations'][i],
    note48:['每条轨迹只有一个已归因错选帧。命中按同轨迹 ±3 步计算。这批轨迹没有完整的 Astra 回退点参考集，采纳率暂无。','Each trajectory has one attributed wrong-choice frame. A hit is within ±3 steps on that trajectory. Astra acceptance is unavailable because these recordings have no complete Astra checkpoint reference set.'][i],
    layerTitle:['俯视地图图层','Top-down map layers'][i],kind_wrong:['历史错选','Historical wrong choice'][i],
    allCases:['本批已完成轨迹','Completed trajectories'][i],currentOnly:['当前轨迹','Current trajectory'][i],
    missing48:['缺少完整 JEV 分数','Incomplete JEV scores'][i],
    progress48:['完成','Completed'][i],
    eligible48:['可评分帧','Eligible frames'][i]
  });
  for(const [key,names] of Object.entries(samplerNames))L[language]['name_'+key]=names[i];
}
const metricPanel=document.createElement('section');
metricPanel.id='metrics48';
metricPanel.innerHTML='<div><h2 data-i18n="summaryTitle"></h2><select id="scope48"><option value="all" data-i18n="allCases"></option><option value="current" data-i18n="currentOnly"></option></select></div><p id="sizes48"></p><table></table><p data-i18n="note48"></p>';
$('stats').after(metricPanel);
const layerPanel=document.createElement('fieldset');layerPanel.id='mapLayers';
layerPanel.innerHTML='<legend data-i18n="layerTitle"></legend><p data-i18n="layerInfo"></p>';
document.querySelector('.mapGrid').before(layerPanel);layerPanel.append($('samplingVersions'));
$('jevMap').addEventListener('mousemove',inspectMapPoint);
$('jevMap').addEventListener('mouseleave',()=>{$('jevMap').title='';});
function render48(){
  const en=lang==='en',cs=$('scope48').value==='all'?B.cases:[c()];
  const table=metricPanel.querySelector('table');table.replaceChildren();
  const header=table.insertRow();
  for(const k of en?['Sampler','Candidates','Matched / references','Coverage','Missed','Astra acceptance']:['采样版本','候选数','命中 / 错选参考帧','错选覆盖率','漏采数','Astra 采纳率']){
    const th=document.createElement('th');th.textContent=k;header.append(th);
  }
  for(const key of ['v001','coverage','active']){
    const count=cs.reduce((n,x)=>n+x.points[key].length,0);
    const hit=cs.filter(x=>x.points[key].some(n=>Math.abs(n.index-x.wrong_frame)<=3)).length;
    const tr=table.insertRow();
    for(const val of [t('name_'+key),count,hit+'/'+cs.length,(100*hit/cs.length).toFixed(2)+'%',cs.length-hit,'—'])tr.insertCell().textContent=val;
  }
  $('sizes48').textContent=t('progress48')+' '+B.cases.length+'/48 · '+t('eligible48')+' '+B.summary.valid_calls+'/4506'+
    (B.missing.length?' · '+t('missing48')+' '+B.missing.join(', '):'');
}
$('scope48').onchange=render48;
for(const version of SAMPLING_VERSIONS)$('sample_'+version.id).checked=true;
updateLanguage();
