const metricsPanel = document.createElement('section');
metricsPanel.id = 'samplerMetrics';
metricsPanel.innerHTML = `<div class="metricTitle"><h2 data-i18n="metricHeading"></h2>
<select id="metricScope" aria-label="统计范围 / Metric scope">
<option value="validation" data-i18n="metricValidation"></option>
<option value="design" data-i18n="metricDesign"></option>
<option value="all" data-i18n="metricAll"></option>
<option value="current" data-i18n="metricCurrent"></option></select></div>
<p id="metricContext"></p><div class="metricScroll"><table><thead><tr></tr></thead><tbody></tbody></table></div>
<p data-i18n="metricDefinition"></p>`;
$('stats').after(metricsPanel);
Object.assign(L.zh, {
  metricHeading:'采样版本指标', metricValidation:'验证集', metricDesign:'设计集', metricAll:'全部轨迹', metricCurrent:'当前轨迹',
  metricVersion:'采样版本', metricCoverage:'覆盖率', metricPrecision:'采纳率', metricHits:'匹配数', metricCount:'候选数',
  metricMiss:'漏采数', metricExtra:'未匹配候选', metricContext:'{scope} · {n} 条轨迹 · {r} 个 Astra 参考点',
  metricDefinition:'同一轨迹内相差不超过 3 步的候选与 Astra 参考点一对一匹配。覆盖率 = 匹配数 ÷ 参考点数，采纳率 = 匹配数 ÷ 候选数。按所选范围汇总计数后计算比例；分母为零时显示「—」。'
});
Object.assign(L.en, {
  metricHeading:'Sampling metrics by version', metricValidation:'Validation set', metricDesign:'Design set', metricAll:'All trajectories', metricCurrent:'Current trajectory',
  metricVersion:'Sampler', metricCoverage:'Coverage', metricPrecision:'Acceptance', metricHits:'Matches', metricCount:'Candidates',
  metricMiss:'Missed references', metricExtra:'Unmatched candidates', metricContext:'{scope} · {n} trajectories · {r} Astra reference points',
  metricDefinition:'Candidates and Astra reference points match one-to-one within ±3 steps on the same trajectory. Coverage = matches / references. Acceptance = matches / candidates. Rates use pooled counts in the selected scope; a zero denominator is shown as “—”.'
});
function renderSamplerMetrics() {
  const scope = $('metricScope').value;
  const cases = scope === 'current' ? [c()] : B.cases.filter(item => scope === 'all' || item.group === scope);
  const references = cases.reduce((total,item)=>total+item.reference_frames.length,0);
  const scopeKey = {validation:'metricValidation', design:'metricDesign', all:'metricAll', current:'metricCurrent'}[scope];
  const scopeName = scope === 'current' ? c().case_id+' · '+t(c().group) : t(scopeKey);
  $('metricContext').textContent = t('metricContext',{scope:scopeName,n:cases.length,r:references});
  const head = metricsPanel.querySelector('thead tr'), body = metricsPanel.querySelector('tbody');
  head.replaceChildren();body.replaceChildren();
  for (const key of ['metricVersion','metricCoverage','metricPrecision','metricHits','metricCount','metricMiss','metricExtra']) {
    const th=document.createElement('th');th.scope='col';th.textContent=t(key);head.append(th);
  }
  const percent = (hits,total)=>total ? (100*hits/total).toFixed(2)+'%' : '—';
  for (const id of LAYER_ORDER.filter(id=>id!=='Astra')) {
    const version=SAMPLING_VERSIONS.find(v=>v.id===id);
    const key={v001:'baseline',v002:'near'}[id] || id;
    let hits=0, count=0;
    for (const item of cases) {
      const row=item.comparisons[key]; hits+=row.pairs.length;count+=row.frames.length;
    }
    const tr=body.insertRow(),label=document.createElement('th');
    label.scope='row';label.textContent=t(version.title);label.style.borderLeft='4px solid '+version.color;tr.append(label);
    for (const value of [percent(hits,references),percent(hits,count),hits,count,references-hits,count-hits]) {
      tr.insertCell().textContent=value;
    }
  }
}
$('metricScope').onchange=renderSamplerMetrics;
updateLanguage();
