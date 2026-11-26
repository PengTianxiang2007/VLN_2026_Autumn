const astraCases = B.cases;
const astraById = new Map(astraCases.map(v => [v.case_id, v]));
const modelCases = {
  astra: astraCases,
  terra: B.terra.map(v => ({...astraById.get(v.case_id), checkpointReview: null, ...v}))
};
const originalTag = B.tag;

function setModel(model) {
  const id = c().case_id;
  B.cases = modelCases[model];
  B.summary = B.modelStats[model];
  B.tag = model === 'astra' ? originalTag : originalTag + '_terra_xhigh';
  selectedRound.clear();
  filterSessions.clear();
  sampleSessions.clear();
  fullCurveCache.clear();
  panelKey = '';
  const astra = model === 'astra', name = astra ? 'Astra' : 'Terra';
  const detail = astra ? 'GPT-6 Astra · medium' : 'GPT-6.1 Terra · xhigh';
  Object.assign(L.zh, {
    modelLabel: '评审模型', partial: '仅复判建点',
    subtitle: 'JEV v002 精简档 · ' + detail + ' · seed 2',
    effectiveNodes: name + ' · 有效节点',
    source: astra ? '43 例 · C01、C27 展示后续复判' : '39 例已完成 · C02、C15、C31、C39 已取消'
  });
  Object.assign(L.en, {
    modelLabel: 'Review model', partial: 'Checkpoint review only',
    subtitle: 'JEV v002 Lean · ' + detail + ' · seed 2',
    effectiveNodes: name + ' · Effective checkpoints',
    source: astra ? '43 cases · C01 and C27 show their later reviews' : '39 completed · C02, C15, C31 and C39 cancelled'
  });
  const group = $('filters').querySelector('[value=partial]');
  group.hidden = !astra;
  if (!astra && $('filters').value === 'partial') $('filters').value = 'all';
  selectCase(Math.max(0, B.cases.findIndex(v => v.case_id === id)));
}

function checkpointPanel(root, v) {
  const d = v.checkpointReview, key = 'checkpoint/' + ci + '/' + lang;
  if (panelKey !== key) {
    panelKey = key;
    const t = (zh, en) => localText(zh, en);
    const fields = d[lang];
    root.replaceChildren(make('h3', t('S04 · 候选资格复判', 'S04 · Checkpoint eligibility review')));
    root.append(make('strong', t('F38 · 已保留为回退点', 'F38 · Retained as a recovery checkpoint')),
      make('p', t('本分支沿用 S01–S03 的判断，只复判了 S04。地图后续部分展示原始轨迹；本分支的偏航评审到此尚未进行。',
        'This branch inherits the S01–S03 decisions and reassesses only S04. The rest of the map shows the recorded trajectory. This branch ends before any deviation review.')));
    for (const [title, value] of [
      [t('判断理由','Rationale'), fields.reason],
      [t('局部路线与可见证据','Local routes and visual evidence'), fields.eligibility_reason],
      [t('两条可选路线','Available branches'), fields.branches.join('\n')]
    ]) root.append(make('h4', title), make('p', value));
    const gallery = make('div', undefined, 'reviewGallery');
    for (const f of d.frames) {
      const button = make('button'), img = new Image();
      img.src = B.images[v.frames[f].image]; img.alt = 'F' + f;
      button.dataset.reviewFrame = f; button.onclick = () => jump(f);
      button.append(img, make('span', 'F' + f)); gallery.append(button);
    }
    root.append(gallery);
    for (const [title, value] of [[t('本轮提示词（中文翻译）','Exact prompt sent'), fields.prompt],
                                  [t('完整回答（中文翻译）','Verbatim answer'), fields.raw]]) {
      const el = make('details'); el.append(make('summary', title), make('pre', value)); root.append(el);
    }
  }
  root.querySelectorAll('[data-review-frame]').forEach(b => b.setAttribute('aria-current', String(+b.dataset.reviewFrame === index)));
}
