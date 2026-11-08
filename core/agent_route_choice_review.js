'use strict';
const $ = id => document.getElementById(id);
let selectedCase = 0, selectedModel = DATA.models.length ? 0 : -1, index = 0, timer = null, stage = DATA.models.length ? 2 : 1;
const directions = {front:'正前方',front_left:'左前方',front_right:'右前方',left:'左侧',right:'右侧',back:'后方',back_left:'左后方',back_right:'右后方',unknown:'不确定'};
const incoming = {yes:'是',no:'否',unknown:'不确定'};
const coverage = {complete:'完整',partial:'部分',insufficient:'不足'};
const confidence = {high:'高',medium:'中',low:'低'};
const node = (tag, text, className) => {const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el;};
const direction = value => directions[value] || value || '未选择';
const maps = {};
for (const [scene, data] of Object.entries(DATA.scenes)) {
  const image = new Image(); image.src = data.image; image.onload = () => drawMap(); maps[scene] = image;
}
$('runInfo').textContent = '选择一条样本，直接查看判断画面、模型列出的支路和最终选择。';
$('model').add(new Option('只看输入', '-1'));
DATA.models.forEach((m, i) => $('model').add(new Option(m.name + (m.response_count ? ' · 已返回回答' : ' · 暂无回答'), String(i))));
$('model').value = String(selectedModel);
DATA.cases.forEach((c, i) => {const b = document.createElement('button'); b.textContent = c.sample_id + '\n' + DATA.labels[i].episode_id; b.onclick = () => select(i); $('cases').append(b);});
function current() {return DATA.cases[selectedCase];}
function model() {return selectedModel >= 0 ? DATA.models[selectedModel] : null;}
function slot(call) {return model()?.calls[current().sample_id]?.[String(call)];}
function timeline() {const c = current(); const cp = c.images.find(im => im.frame === c.checkpoint_frame); return [...c.images.map(im => ({...im, reset: false})), {...cp, reset: true}];}
function noteKey() {return ['agent-route-choice', DATA.prepared_manifest_sha256, model()?.manifest_sha256 || 'inputs', current().sample_id, stage].join(':');}
function stop() {if (timer) clearInterval(timer); timer = null; $('play').textContent = '顺序回放';}
function select(i) {stop(); selectedCase = i; const c = current(); index = stage === 2 ? timeline().length - 1 : c.images.findIndex(im => im.frame === c.checkpoint_frame); $('advancedDetails').open = false; render(); window.scrollTo(0, 0);}
function errorReason() {
  const m = model(), a = slot(2)?.parsed;
  if (a?.selected_branch_id && a.excluded_branch_ids?.includes(a.selected_branch_id)) return `模型已排除 ${a.selected_branch_id}，却又选择同一支路；译文保留原始矛盾。`;
  if (m?.provider_errors?.['1113']) return 'GLM账户余额不足或无可用资源包（1113），没有产生模型回答。';
  return m?.case_statuses[current().sample_id]?.error || '回答未通过协议校验。';
}
function renderOverview() {
  const m = model();
  const metrics = [[DATA.cases.length, '固定样本'], [m?.response_count || 0, '实际返回响应'], [m?.validated_samples || 0, '双调用通过协议校验'], [m?.invalid_samples || 0, '存在无效回答的样本'], ['待复核', '语义正确率']];
  $('stats').replaceChildren();
  for (const [value, label] of metrics) {const el = node('div', undefined, 'metric'); el.append(node('b', String(value)), node('span', label)); $('stats').append(el);}
  const blocked = DATA.models.filter(item => !item.response_count).map(item => item.name + (item.provider_errors?.['1113'] ? '：账户无额度，0次回答。' : '：暂无模型回答。')).join(' ');
  $('batchNotice').textContent = '中文为已保存回答的忠实翻译，原始错误不作修正。协议有效不代表选路正确。地图、任务中文译文和历史标签仅供复核，不是额外发送给模型的证据。 ' + blocked;
  Array.from($('cases').children).forEach((button, i) => {
    const c = DATA.cases[i], status = m?.case_statuses[c.sample_id]?.phase;
    const invalid = m && Object.values(m.calls[c.sample_id]).some(s => s.raw_content !== null && !s.validated);
    button.classList.toggle('invalid', !!invalid); button.classList.toggle('empty', !!m && !m.calls[c.sample_id]['1'].raw_content);
    const choice = m?.calls[c.sample_id]['2'].parsed;
    button.replaceChildren(node('span', `样本 ${String(i + 1).padStart(2, '0')}`, 'case-number'), node('span', choice?.selected_branch_id ? `${invalid ? '矛盾 · ' : ''}选 ${choice.selected_branch_id} · ${direction(choice.selected_direction)}` : m ? '暂无选择' : '查看判断帧', 'case-choice'));
    button.title = DATA.labels[i].episode_id;
  });
}
function evidence(ids, call = stage) {
  const wrap = node('div');
  for (const id of ids || []) {
    const b = node('button', id, 'evidence'); b.title = '查看证据画面，保留当前回答';
    b.onclick = () => {const n = current().images.findIndex(im => im.id === id); if (n >= 0) {stop(); stage = call; index = n; $('advancedDetails').open = true; render(); $('rgb').scrollIntoView({block:'center'});}};
    wrap.append(b);
  }
  return wrap;
}
function renderDecisionView() {
  const c = current(), cp = c.images.find(im => im.frame === c.checkpoint_frame);
  const image = $('checkpointImage');
  if (image.dataset.sha256 !== cp.sha256) image.src = DATA.images[cp.sha256];
  image.dataset.sha256 = cp.sha256; image.dataset.imageId = cp.id; image.dataset.frame = String(cp.frame);
  $('checkpointFrame').textContent = `原始帧 ${cp.frame} · ${cp.id}`;
  $('checkpointCaption').textContent = '两次判断时的当前视角：Crossing 离线复位帧。';
  const context = c.images.filter(im => im.phase === 'checkpoint_context').length;
  $('checkpointInputs').textContent = `模型还看到了此前 ${context - 1} 张画面；第二次判断另附 ${c.images.length - context} 张走错过程画面。上图就是两次调用共同指定的“当前画面”。`;
  const first = slot(1), second = slot(2), inv = first?.answer_zh || first?.parsed, choice = second?.parsed;
  const chosen = inv?.branches?.find(b => b.id === choice?.selected_branch_id);
  const translatedChoice = second?.answer_zh || choice;
  const invalid = !!choice && !second.validated;
  $('choiceBanner').classList.toggle('invalid', invalid);
  $('chosenHeading').textContent = choice?.selected_branch_id ? `${choice.selected_branch_id} · ${direction(choice.selected_direction)}` : choice ? '没有选择支路' : '暂无模型选择';
  $('chosenPlace').textContent = chosen ? chosen.landmark : choice?.status === 'insufficient_evidence' ? '模型认为证据不足，未给出选路。' : model()?.provider_errors?.['1113'] ? 'GLM账户无额度，未返回判断。' : '当前没有第二次调用的回答。';
  const excluded = (choice?.excluded_branch_ids || []).map(id => {const b = inv?.branches?.find(b => b.id === id); return `${id}${b ? ' · ' + direction(b.direction) + ' · ' + b.landmark : ''}`;});
  $('excludedHeading').textContent = choice ? '模型排除：' + (excluded.join('；') || '未排除任何支路') : '';
  $('choiceWarning').textContent = invalid ? '注意：' + errorReason() : '';
  $('branchHeading').textContent = inv ? `第一次判断：模型列出 ${inv.branches.length} 条支路` : '第一次判断：暂无支路清单';
  $('branchCards').replaceChildren();
  for (const b of inv?.branches || []) {
    const selected = choice?.selected_branch_id === b.id, rejected = choice?.excluded_branch_ids?.includes(b.id);
    const card = node('article', undefined, 'branch-card' + (selected ? ' selected' : '') + (rejected ? ' excluded' : '') + (selected && rejected ? ' conflict' : ''));
    card.dataset.branchId = b.id; card.dataset.direction = b.direction; card.dataset.selected = String(selected); card.dataset.excluded = String(!!rejected);
    const top = node('div', undefined, 'branch-card-top'); top.append(node('span', b.id, 'branch-id'), node('span', direction(b.direction), 'branch-dir'));
    if (selected) top.append(node('span', '最终选择', 'branch-flag chosen'));
    if (rejected) top.append(node('span', '模型排除', 'branch-flag rejected'));
    card.append(top, node('p', b.landmark), node('p', '模型认为通向：' + b.destination_hypothesis, 'destination'));
    if (b.incoming !== 'no') card.append(node('p', b.incoming === 'yes' ? '模型标为来路（之前走来的方向）' : '模型不确定这是否是来路', 'return-tag'));
    const source = node('details'); source.append(node('summary', '查看模型依据的画面'), evidence(b.evidence_ids, 1)); card.append(source);
    $('branchCards').append(card);
  }
  if (!inv) $('branchCards').append(node('p', model()?.provider_errors?.['1113'] ? 'GLM未返回回答，无法展示支路。' : '尚无第一次回答。'));
  $('wrongReasonText').textContent = translatedChoice?.error_reason || '暂无回答。';
  $('selectedRouteText').textContent = translatedChoice?.route_description || '暂无回答。';
}
function renderAnswer() {
  const s = slot(stage), translated = $('language').value === 'zh', a = translated && s?.answer_zh ? s.answer_zh : s?.parsed;
  $('answer').replaceChildren();
  $('rawAnswer').textContent = s?.raw_content || '未产生原始响应。';
  $('answerStatus').className = s?.raw_content ? (s.validated ? 'valid' : 'invalid') : '';
  $('answerStatus').textContent = s?.raw_content ? (s.validated ? '协议校验通过 · 选路是否正确待复核' : '未通过协议校验 · ' + errorReason()) : model() ? errorReason() : '输入预览，未选择模型结果。';
  if (!s?.raw_content) {$('answer').append(node('p', '暂无回答。')); return;}
  if (!translated || !s.answer_zh) {$('answer').append(node('pre', s.raw_content)); return;}
  function section(title, value, ids) {
    const box = node('div', undefined, 'answer-section'); box.append(node('h3', title));
    if (Array.isArray(value)) {const list = node('ul'); for (const v of value) list.append(node('li', v)); box.append(list);} else box.append(node('p', value));
    if (ids) box.append(evidence(ids)); $('answer').append(box);
  }
  if (stage === 1) {
    section('场景概述', a.view_summary);
    for (const b of a.branches) section(`${b.id} · ${direction(b.direction)} · 来路：${incoming[b.incoming]}`, `地标：${b.landmark}\n可能通向：${b.destination_hypothesis}`, b.evidence_ids);
    section('支路覆盖（模型自报）', coverage[a.coverage] || a.coverage);
  } else {
    section('模型识别的错误支路', a.wrong_branch_id || '未识别', a.wrong_branch_evidence_ids);
    section('模型给出的走错原因', a.error_reason);
    section('模型引用的任务片段（中文译文）', a.instruction_evidence);
    section('排除与重新选择', `排除：${a.excluded_branch_ids.join('、') || '无'}\n改选：${a.selected_branch_id || '未选择'} · ${direction(a.selected_direction)}\n回答状态：${a.status === 'selected' ? '给出选择' : '证据不足，弃答'}`);
    section('模型建议的路线', a.route_description, a.selection_evidence_ids);
    section('模型自报置信度', confidence[a.confidence] || a.confidence);
  }
  section('模型说明的不确定性', a.uncertainties.length ? a.uncertainties : '未列出。');
}
function renderBranches() {
  const first = slot(1), second = slot(2), inv = first?.answer_zh || first?.parsed, choice = second?.parsed;
  const binding = model()?.bindings[current().sample_id];
  $('inventoryBinding').textContent = binding ? (binding.matches ? '已核验：第二次请求完整携带第一次的实际支路清单，清单哈希一致。' : '警告：两次调用的清单传递未通过核验。') : '第二次调用尚无可核验的支路清单传递记录。';
  $('inventoryBinding').title = binding?.inventory_sha256 || '';
  $('decisionSummary').textContent = choice ? `模型判错：${choice.wrong_branch_id || '未识别'} → 排除：${choice.excluded_branch_ids?.join('、') || '无'} → 改选：${choice.selected_branch_id || '未选择'}（${direction(choice.selected_direction)}）\n` + (second.validated ? '协议有效；是否选对仍待语义复核。' : '无效回答：' + errorReason()) : model() ? errorReason() : '选择一个模型，查看两次判断。';
  $('decisionSummary').style.borderLeft = choice && !second.validated ? '4px solid #cf4150' : '4px solid #2377bb';
  $('branchTable').replaceChildren();
  if (!inv?.branches) return;
  const table = node('table'), header = node('tr'); for (const title of ['支路 / 朝向', '第一次：可能通向', '第二次：处理']) header.append(node('th', title)); table.append(header);
  for (const b of inv.branches) {
    const row = node('tr'); row.append(node('td', `${b.id} · ${direction(b.direction)}\n来路：${incoming[b.incoming]}`), node('td', b.destination_hypothesis));
    const flags = node('td'); if (choice?.excluded_branch_ids?.includes(b.id)) flags.append(node('span', '判错并排除', 'flag red')); if (choice?.selected_branch_id === b.id) flags.append(node('span', second.validated ? '模型改选' : '又被选择（矛盾）', 'flag ' + (second.validated ? 'blue' : 'red')));
    if (!flags.children.length) flags.textContent = '—'; row.append(flags); table.append(row);
  }
  $('branchTable').append(table);
}
function render() {
  const c = current(), label = DATA.labels[selectedCase], frames = timeline(), im = frames[index];
  renderOverview();
  $('title').textContent = `样本 ${String(selectedCase + 1).padStart(2, '0')} / ${DATA.cases.length}`;
  $('caseSource').textContent = label.episode_id;
  $('instruction').textContent = DATA.instructions_zh?.[c.sample_id] || c.instruction;
  $('instructionOriginal').textContent = c.instruction;
  for (const id of ['frame', 'imageFrame']) {$(id).max = String(frames.length - 1); $(id).value = String(index);}
  $('step').textContent = `回放 ${index + 1}/${frames.length} · 原帧 ${im.frame}` + (im.reset ? ' · 虚拟复位到 P' : im.phase === 'wrong_attempt' ? ' · 历史错误经历' : ' · 存档前观测');
  $('rgb').src = DATA.images[im.sha256];
  $('state').textContent = `第 ${stage} 次调用` + (stage === 2 ? ' · 当前方向仍以存档帧为准' : ' · 不输入任务与错误片段');
  $('imageInfo').textContent = `当前查看 ${im.id}${im.reset ? '（虚拟复位）' : ''}；以下回答针对存档帧 F${String(c.checkpoint_frame).padStart(4, '0')}，浏览证据不会重新调用模型。`;
  renderDecisionView(); renderAnswer(); renderBranches();
  const visible = c.images.filter(image => stage === 2 || image.phase === 'checkpoint_context');
  $('history').replaceChildren();
  visible.forEach(image => {const b = document.createElement('button'); b.classList.toggle('active', image.id === im.id); const thumb = document.createElement('img'); thumb.src = DATA.images[image.sha256]; thumb.alt = image.id; const caption = document.createElement('span'); caption.textContent = image.id; b.append(thumb, caption); b.onclick = () => {stop(); index = c.images.findIndex(x => x.id === image.id); render();}; $('history').append(b);});
  const actionNames = {FORWARD:'前进',LEFT:'左转',RIGHT:'右转',STOP:'停止',WAIT:'等待'};
  const describeActions = rows => rows.map(r => `${r.frame}：${actionNames[r.action] || r.action}`).join(' → ');
  $('actions').textContent = '接近阶段：\n' + describeActions(c.approach_actions) + (stage === 2 ? '\n\n历史错误尝试：\n' + describeActions(c.attempt_actions) : '');
  $('labels').textContent = `正确路线：${label.expected_route}\n历史错误：${label.wrong_route}`;
  $('labels').style.whiteSpace = 'pre-wrap';
  $('limits').textContent = '使用原 seed2 同一次录像，回到人工标定的决策帧；未执行物理复位。第一调用只看存档前最多四张 RGB，第二调用增加最多四张错误经历 RGB。地图和本页标签只供复核。支路清单缺漏、视角不足和任务进度不明确均允许报告证据不足。';
  try {$('note').value = localStorage.getItem(noteKey()) || '';} catch {$('note').value = '';}
  $('notesStatus').textContent = '';
  for (const [i, b] of Array.from($('cases').children).entries()) b.classList.toggle('active', i === selectedCase);
  drawMap();
}
function drawMap() {
  const canvas = $('map'); if (!canvas || !DATA.cases.length) return;
  canvas.width = 720; canvas.height = 480; const ctx = canvas.getContext('2d'); ctx.clearRect(0, 0, 720, 480);
  const c = current(), label = DATA.labels[selectedCase], im = timeline()[index], scene = DATA.scenes[label.scene];
  const points = [...label.trajectory.map(r => r.position), ...label.reference_path, label.crossing.position];
  let xy;
  if (scene && maps[label.scene]?.complete && maps[label.scene].naturalWidth) {
    const g = scene.geometry, scale = Math.min(700 / g.width, 460 / g.height), ox = (720 - g.width * scale) / 2, oy = (480 - g.height * scale) / 2;
    ctx.drawImage(maps[label.scene], ox, oy, g.width * scale, g.height * scale);
    xy = p => [ox + (p[0] - g.low[0]) / g.resolution * scale, oy + (g.high[1] - p[1]) / g.resolution * scale];
  } else {
    const xs = points.map(p => p[0]), ys = points.map(p => p[1]); const xmin = Math.min(...xs) - 1, ymin = Math.min(...ys) - 1;
    const scale = Math.min(680 / (Math.max(...xs) - xmin + 1), 440 / (Math.max(...ys) - ymin + 1));
    xy = p => [20 + (p[0] - xmin) * scale, 460 - (p[1] - ymin) * scale];
  }
  function line(ps, color, dash = []) {if (!ps.length) return; ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.setLineDash(dash); ps.forEach((p, i) => {const q = xy(p); i ? ctx.lineTo(...q) : ctx.moveTo(...q);}); ctx.stroke(); ctx.setLineDash([]);}
  line(label.reference_path, '#9aa5b3');
  line(label.trajectory.filter(r => r.frame <= (im.reset ? c.wrong_end_frame : im.frame)).map(r => r.position), '#259279');
  if (im.reset) line([label.trajectory.at(-1).position, label.checkpoint_position], '#c58317', [8, 7]);
  for (const [p, color, name] of [[label.crossing.position, '#2377bb', label.crossing_id], [label.checkpoint_position, '#c58317', 'P']]) {
    const q = xy(p); ctx.fillStyle = color; ctx.beginPath(); ctx.arc(...q, 6, 0, Math.PI * 2); ctx.fill(); ctx.font = '16px sans-serif'; ctx.fillText(name, q[0] + 9, q[1] - 8);
  }
  const row = label.trajectory.find(r => r.frame === im.frame); if (row) {ctx.fillStyle = '#cf4150'; ctx.beginPath(); ctx.arc(...xy(row.position), 5, 0, Math.PI * 2); ctx.fill();}
}
$('model').onchange = () => {stop(); selectedModel = Number($('model').value); render();};
$('checkpointImage').onclick = () => {const image = $('checkpointImage'); $('checkpointLarge').src = image.src; $('checkpointDialogTitle').textContent = `样本 ${selectedCase + 1} · Crossing判断画面 · ${image.dataset.imageId}`; $('checkpointDialog').showModal();};
$('checkpointImage').onkeydown = event => {if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); $('checkpointImage').click();}};
$('closeCheckpoint').onclick = () => $('checkpointDialog').close();
$('language').onchange = render;
for (const id of ['frame', 'imageFrame']) $(id).oninput = () => {stop(); index = Number($(id).value); render();};
$('prev').onclick = () => {stop(); index = Math.max(0, index - 1); render();};
$('next').onclick = () => {stop(); index = Math.min(timeline().length - 1, index + 1); render();};
$('call1').onclick = () => {stop(); stage = 1; index = current().images.findIndex(im => im.frame === current().checkpoint_frame); render();};
$('call2').onclick = () => {stop(); stage = 2; index = timeline().length - 1; render();};
$('play').onclick = () => {if (timer) return stop(); if (index >= timeline().length - 1) index = 0; timer = setInterval(() => {if (index >= timeline().length - 1) return stop(); index++; render();}, 800); $('play').textContent = '暂停';};
$('note').oninput = () => {try {localStorage.setItem(noteKey(), $('note').value); $('notesStatus').textContent = '已保存在当前浏览器';} catch {$('notesStatus').textContent = '浏览器无法保存；请复制意见';}};
$('export').onclick = () => {const notes = []; try {for (let i = 0; i < localStorage.length; i++) {const key = localStorage.key(i); if (key.startsWith('agent-route-choice:' + DATA.prepared_manifest_sha256 + ':')) notes.push({key, note: localStorage.getItem(key)});}} catch {} const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify({prepared_manifest_sha256: DATA.prepared_manifest_sha256, notes}, null, 2)], {type: 'application/json'})); a.download = 'route_choice_notes.json'; a.click(); URL.revokeObjectURL(a.href);};
select(0);
