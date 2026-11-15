'use strict';
const B = JSON.parse(document.getElementById('payload').textContent);
const $ = id => document.getElementById(id);

const L = {
  zh: {
    title: '人工错误选择点 · JEV v004 × Qwen4B',
    events: '34 个错误选择点',
    all: '全部',
    qwen1: 'Qwen 1 分',
    qwen5: 'Qwen 5 分',
    jevHigh: 'JEV ≥ 0.75',
    jevLow: 'JEV < 0.60',
    reused: '精确复用',
    newCall: '新调用',
    export: '导出复核意见',
    eventHint: '点击错误点切换双地图、RGB、三帧模型输入、分数和原始结果。',
    searchPlaceholder: '搜索 episode 或 frame',
    qwenMap: 'Qwen4B · 1–5 分',
    jevMap: 'JEV v004 · P(回退点)',
    qwenScore: 'Qwen4B 分数',
    jevProbability: 'JEV 回退概率',
    latency: '调用延迟',
    provenance: '结果来源',
    current: '当前观测与判断',
    history: '实际模型输入帧',
    rawResult: '原始结果 JSON',
    review: '人工复核',
    likely: '像潜在回退点',
    uncertain: '不确定',
    unlikely: '不像潜在回退点',
    context: '需要结合路线上下文',
    notePlaceholder: '记录本错误点的局部空间与判断依据',
    noteHint: '意见仅保存在当前浏览器。',
    prompt: 'JEV v004 提示词（英文实际输入与完整中文翻译）',
    promptEnglish: 'English · actual model input',
    promptChinese: '中文翻译',
    protocol: '协议与解释边界',
    protocolText: '本批只包含人工标定的 34 个错误选择点；地图上的彩色短段和圆形位置标点仅用于定位该点。JEV 输入严格为 t-2,t-1,t RGB，不包含任务、动作、位置、地图、错误标签、成败、参考路线或旧回答。Qwen 与 JEV 量纲不同，页面只作描述性对照，不计算准确率、优劣或因果结论。',
    mapHint: '灰色线为实际轨迹；彩色短段为错误点前后各 4 帧；圆形标点为错误选择位置。左侧颜色只表示 Qwen 1–5 分，右侧只表示 JEV 原始 yes 概率。',
    plotTitle: '34 个错误选择点 · 双轴折线与滑动窗口',
    qwenRaw: 'Qwen 原始分数',
    jevRaw: 'JEV 原始概率',
    smoothing: '平滑方式',
    none: '不平滑',
    gaussian: '高斯滤波',
    ema: '指数移动平均 EMA',
    moving: '滑动平均',
    windowLabel: '滑动窗口',
    qwenSmoothed: 'Qwen 平滑线',
    jevSmoothed: 'JEV 平滑线',
    plotHint: '横轴按人工事件文件中的固定顺序排列，不是单条 episode 的连续动作序列。滑动窗口只用于观察 34 个点的整体起伏，不能解释为部署时因果滤波。点击折线图任意位置可跳转到对应错误点。',
    plotSummary: '窗口 {window} · {mode} · 当前 E{index}：{episode} F{frame}',
    instruction: '原任务指令',
    imageInfo: '当前第 {frame} 帧；三帧输入为 {inputs}',
    qwenShort: 'Qwen {score} 分',
    reusedShort: '旧结果精确复用',
    newShort: '本次新调用',
    currentPoint: '错误选择点',
    runInfo: '34 个错误选择点 · 33 条 episode · JEV 1.14 v004 × 最初 Qwen4B · 29 新调用 + 5 精确复用',
    notice: '所有点均为人工标记的错误分支选择。JEV 当前候选检测的平均 yes 概率为 0.762；Qwen4B 均分 3.353。两者量纲不同，不能直接相减或据此宣称哪个模型更准确。',
    eventsMetric: '错误选择点',
    completeMetric: '有效结果',
    provenanceMetric: '新调用 / 复用',
    qwenMeanMetric: 'Qwen 平均分',
    jevMeanMetric: 'JEV 平均概率',
    highMetric: 'JEV ≥ 0.75',
    footer: '离线页面 · JEV 1.14 · 页面加载不发起外部请求',
    generated: '生成于',
    rawNote: 'Noul 输出只有概率，没有自然语言理由。',
    eventStats: '{scene} · frame {frame} · {provenance}',
    scenario: '场景',
    frame: '帧',
    qwen: 'Qwen',
    jev: 'JEV'
  },
  en: {
    title: 'Human-labeled wrong choices · JEV v004 × Qwen4B',
    events: '34 wrong choices',
    all: 'All',
    qwen1: 'Qwen score 1',
    qwen5: 'Qwen score 5',
    jevHigh: 'JEV ≥ 0.75',
    jevLow: 'JEV < 0.60',
    reused: 'Exact reuse',
    newCall: 'New calls',
    export: 'Export review notes',
    eventHint: 'Select a wrong-choice point to update both maps, RGB, actual model inputs, scores, and raw result.',
    searchPlaceholder: 'Search episode or frame',
    qwenMap: 'Qwen4B · score 1–5',
    jevMap: 'JEV v004 · P(fallback point)',
    qwenScore: 'Qwen4B score',
    jevProbability: 'JEV fallback probability',
    latency: 'API latency',
    provenance: 'Result source',
    current: 'Current observation and decision',
    history: 'Actual model input frames',
    rawResult: 'Raw result JSON',
    review: 'Human review',
    likely: 'Likely potential fallback point',
    uncertain: 'Uncertain',
    unlikely: 'Unlikely potential fallback point',
    context: 'Needs route context',
    notePlaceholder: 'Record the local spatial evidence for this wrong choice',
    noteHint: 'Notes are stored only in this browser.',
    prompt: 'JEV v004 prompt (actual English input and complete Chinese translation)',
    promptEnglish: 'English · actual model input',
    promptChinese: 'Chinese translation',
    protocol: 'Protocol and interpretation boundary',
    protocolText: 'This batch contains only the 34 human-labeled wrong choices. The colored route segment and circular position marker are display aids for locating each event. JEV receives only exact t-2,t-1,t RGB inputs, with no task, action, position, map, wrong-choice label, outcome, reference route, or prior answer. Qwen and JEV use different scales; this page provides descriptive comparison only and makes no accuracy, superiority, or causal claim.',
    mapHint: 'The gray line is the actual trajectory, the colored segment spans four frames on each side of the event, and the circular marker is the wrong-choice position. The left color encodes only Qwen score 1–5; the right color encodes only raw JEV yes probability.',
    plotTitle: '34 wrong choices · dual-axis lines and sliding window',
    qwenRaw: 'Raw Qwen score',
    jevRaw: 'Raw JEV probability',
    smoothing: 'Smoothing',
    none: 'None',
    gaussian: 'Gaussian filter',
    ema: 'Exponential moving average',
    moving: 'Moving average',
    windowLabel: 'Sliding window',
    qwenSmoothed: 'Smoothed Qwen line',
    jevSmoothed: 'Smoothed JEV line',
    plotHint: 'The x-axis follows the fixed order in the human event file; it is not a continuous action sequence within one episode. The sliding window is only for viewing the aggregate pattern across the 34 points and must not be interpreted as causal deployment-time filtering. Click anywhere on the chart to select the corresponding wrong choice.',
    plotSummary: 'Window {window} · {mode} · Current E{index}: {episode} F{frame}',
    instruction: 'Original task instruction',
    imageInfo: 'Current frame {frame}; model inputs are {inputs}',
    qwenShort: 'Qwen score {score}',
    reusedShort: 'Exact reused result',
    newShort: 'New call in this run',
    currentPoint: 'Wrong-choice point',
    runInfo: '34 wrong choices · 33 episodes · JEV 1.14 v004 × original Qwen4B · 29 new calls + 5 exact reuses',
    notice: 'Every point is a human-labeled wrong branch choice. JEV candidate detection has mean yes probability 0.762; Qwen4B has mean score 3.353. The scales differ and cannot be subtracted directly or used to claim that one model is more accurate.',
    eventsMetric: 'Wrong choices',
    completeMetric: 'Valid results',
    provenanceMetric: 'New / reused',
    qwenMeanMetric: 'Qwen mean score',
    jevMeanMetric: 'JEV mean probability',
    highMetric: 'JEV ≥ 0.75',
    footer: 'Offline page · JEV 1.14 · no external requests on load',
    generated: 'Generated',
    rawNote: 'A Noul output contains only probabilities and has no natural-language rationale.',
    eventStats: '{scene} · frame {frame} · {provenance}',
    scenario: 'Scene',
    frame: 'Frame',
    qwen: 'Qwen',
    jev: 'JEV'
  }
};

let lang = 'zh';
let selected = 0;
const mapCache = new Map();
const t = key => L[lang][key] || key;
const current = () => B.events[selected];

function pointColor(score) {
  const palette = {
    1: [204, 235, 231],
    2: [125, 204, 194],
    3: [63, 168, 164],
    4: [20, 123, 128],
    5: [7, 95, 102]
  };
  return palette[score] || '#9aa5b1';
}

function qwenColor(score) {
  const value = pointColor(score);
  return Array.isArray(value) ? `rgb(${value.join(',')})` : value;
}

function jevColor(probability) {
  if (!Number.isFinite(probability)) return '#9aa5b1';
  const low = [244, 217, 199];
  const high = [139, 29, 29];
  return `rgb(${low.map((value, index) => Math.round(
    value + (high[index] - value) * probability
  )).join(',')})`;
}

function canvas(id) {
  const element = $(id);
  const box = element.getBoundingClientRect();
  const dpr = devicePixelRatio || 1;
  element.width = Math.max(1, Math.round(box.width * dpr));
  element.height = Math.max(1, Math.round(box.height * dpr));
  const context = element.getContext('2d');
  context.scale(dpr, dpr);
  return { context, width: box.width, height: box.height };
}

function mapImage(scene) {
  const key = B.maps[scene].image;
  if (!mapCache.has(key)) {
    const image = new Image();
    image.onload = () => drawMaps();
    image.src = B.images[key];
    mapCache.set(key, image);
  }
  return mapCache.get(key);
}

function projectFactory(width, height, geometry) {
  const scale = Math.min(width / geometry.width, height / geometry.height);
  const offsetX = (width - geometry.width * scale) / 2;
  const offsetY = (height - geometry.height * scale) / 2;
  return {
    scale,
    offsetX,
    offsetY,
    project(point) {
      return [
        offsetX + (point[0] - geometry.low[0]) / geometry.resolution * scale,
        offsetY + (geometry.high[1] - point[1]) / geometry.resolution * scale
      ];
    }
  };
}

function drawPath(context, positions, project, color, width, limit) {
  context.strokeStyle = color;
  context.lineWidth = width;
  context.beginPath();
  let active = false;
  for (let index = 0; index < Math.min(positions.length, limit); index += 1) {
    const point = project(positions[index]);
    if (active) context.lineTo(point[0], point[1]);
    else context.moveTo(point[0], point[1]);
    active = true;
  }
  context.stroke();
}

function drawMap(id, mode) {
  const event = current();
  const map = B.maps[event.scene];
  const image = mapImage(event.scene);
  const { context, width, height } = canvas(id);
  const geometry = map.geometry;
  const projection = projectFactory(width, height, geometry);
  context.clearRect(0, 0, width, height);
  context.fillStyle = '#f3f6f9';
  context.fillRect(0, 0, width, height);
  if (image.complete && image.naturalWidth) {
    context.drawImage(
      image,
      projection.offsetX,
      projection.offsetY,
      geometry.width * projection.scale,
      geometry.height * projection.scale
    );
  }

  const trajectory = B.trajectories[event.episode_id];
  context.lineCap = 'round';
  context.lineJoin = 'round';
  drawPath(context, trajectory, projection.project, '#a8b4bf', 2.2, trajectory.length);

  const start = Math.max(0, event.frame - 4);
  const end = Math.min(trajectory.length - 1, event.frame + 4);
  const color = mode === 'qwen' ? qwenColor(event.qwen_score) : jevColor(event.jev_probability);
  context.lineCap = 'round';
  context.strokeStyle = color;
  context.lineWidth = 5;
  context.beginPath();
  for (let index = start; index <= end; index += 1) {
    const point = projection.project(trajectory[index]);
    if (index === start) context.moveTo(point[0], point[1]);
    else context.lineTo(point[0], point[1]);
  }
  context.stroke();

  const marker = projection.project(event.position);
  context.beginPath();
  context.arc(marker[0], marker[1], 7, 0, Math.PI * 2);
  context.fillStyle = color;
  context.fill();
  context.lineWidth = 2;
  context.strokeStyle = '#fff';
  context.stroke();
  context.font = 'bold 11px sans-serif';
  context.fillStyle = '#17344e';
  context.fillText(
    (mode === 'qwen' ? 'Q' : 'J') + String(event.frame).padStart(3, '0'),
    marker[0] + 9,
    marker[1] - 8
  );
}

function drawMaps() {
  drawMap('qwenMap', 'qwen');
  drawMap('jevMap', 'jev');
}

function smoothSeries(values, mode, windowSize) {
  if (mode === 'none') return values.map(() => null);
  const width = Math.max(1, Math.min(values.length, Number(windowSize) || 1));
  if (mode === 'ema') {
    const alpha = 2 / (width + 1);
    const result = [];
    values.forEach((value, index) => {
      result.push(index === 0 ? value : alpha * value + (1 - alpha) * result[index - 1]);
    });
    return result;
  }
  if (mode === 'moving') {
    const radius = Math.floor(width / 2);
    return values.map((_, index) => {
      const start = Math.max(0, index - radius);
      const end = Math.min(values.length, index + radius + 1);
      const slice = values.slice(start, end);
      return slice.reduce((sum, value) => sum + value, 0) / slice.length;
    });
  }
  const radius = Math.floor(width / 2);
  const sigma = Math.max(0.5, width / 6);
  return values.map((_, index) => {
    let weighted = 0;
    let total = 0;
    for (let offset = -radius; offset <= radius; offset += 1) {
      const source = index + offset;
      if (source < 0 || source >= values.length) continue;
      const weight = Math.exp(-(offset * offset) / (2 * sigma * sigma));
      weighted += values[source] * weight;
      total += weight;
    }
    return total ? weighted / total : values[index];
  });
}

function drawSeries(context, values, xOf, yOf, color, width, dashed) {
  context.strokeStyle = color;
  context.lineWidth = width;
  context.setLineDash(dashed ? [7, 5] : []);
  context.beginPath();
  values.forEach((value, index) => {
    if (!Number.isFinite(value)) return;
    const x = xOf(index);
    const y = yOf(value);
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.stroke();
  context.setLineDash([]);
}

function drawPlot() {
  const { context, width, height } = canvas('scorePlot');
  const events = B.events;
  const margin = { left: 44, right: 48, top: 18, bottom: 32 };
  const plotWidth = Math.max(1, width - margin.left - margin.right);
  const plotHeight = Math.max(1, height - margin.top - margin.bottom);
  const xOf = index => margin.left + (
    events.length <= 1 ? 0.5 : index / (events.length - 1)
  ) * plotWidth;
  const yQwen = value => margin.top + (5 - value) / 4 * plotHeight;
  const yJev = value => margin.top + (1 - value) * plotHeight;
  const qwenRaw = events.map(event => event.qwen_score);
  const jevRaw = events.map(event => event.jev_probability);
  const windowSize = Number($('filterWindow').value);
  const mode = $('smoothingMode').value;
  const qwenSmooth = smoothSeries(qwenRaw, mode, windowSize);
  const jevSmooth = smoothSeries(jevRaw, mode, windowSize);

  context.clearRect(0, 0, width, height);
  context.font = '11px sans-serif';
  context.fillStyle = '#52677a';
  for (let score = 1; score <= 5; score += 1) {
    const y = yQwen(score);
    context.strokeStyle = '#e3e9ef';
    context.beginPath();
    context.moveTo(margin.left, y);
    context.lineTo(width - margin.right, y);
    context.stroke();
    context.fillText(String(score), 8, y + 4);
  }
  for (let probability = 0; probability <= 1; probability += 0.25) {
    const y = yJev(probability);
    context.fillText(probability.toFixed(2), width - margin.right + 7, y + 4);
  }
  context.fillStyle = '#13845c';
  context.fillText(t('qwen'), 8, 12);
  context.fillStyle = '#b33a3a';
  context.fillText(t('jev'), width - margin.right + 7, 12);

  const tickIndexes = new Set([0, 4, 9, 14, 19, 24, 29, events.length - 1]);
  tickIndexes.forEach(index => {
    if (index < 0 || index >= events.length) return;
    const x = xOf(index);
    context.fillStyle = '#52677a';
    context.fillText(`E${String(index + 1).padStart(2, '0')}`, x - 10, height - 10);
  });

  if ($('showQwenRaw').checked) {
    drawSeries(context, qwenRaw, xOf, yQwen, '#13845c', 2.2, false);
  }
  if ($('showJevRaw').checked) {
    drawSeries(context, jevRaw, xOf, yJev, '#b33a3a', 2.2, false);
  }
  if (mode !== 'none') {
    drawSeries(context, qwenSmooth, xOf, yQwen, '#3156a3', 2.6, true);
    drawSeries(context, jevSmooth, xOf, yJev, '#7b5f9e', 2.6, true);
  }

  if ($('showQwenRaw').checked) {
    qwenRaw.forEach((value, index) => {
      context.beginPath();
      context.arc(xOf(index), yQwen(value), 2.4, 0, Math.PI * 2);
      context.fillStyle = '#13845c';
      context.fill();
    });
  }
  if ($('showJevRaw').checked) {
    jevRaw.forEach((value, index) => {
      context.beginPath();
      context.arc(xOf(index), yJev(value), 2.4, 0, Math.PI * 2);
      context.fillStyle = '#b33a3a';
      context.fill();
    });
  }

  const x = xOf(selected);
  context.strokeStyle = '#17344e';
  context.lineWidth = 1.5;
  context.setLineDash([3, 3]);
  context.beginPath();
  context.moveTo(x, margin.top);
  context.lineTo(x, height - margin.bottom);
  context.stroke();
  context.setLineDash([]);
  const event = current();
  $('plotSummary').textContent = t('plotSummary')
    .replace('{window}', windowSize)
    .replace('{mode}', t(mode))
    .replace('{index}', String(selected + 1).padStart(2, '0'))
    .replace('{episode}', event.episode_id)
    .replace('{frame}', event.frame);
}

function filterMatches(event) {
  const filter = $('filters').value;
  if (filter === 'qwen1' && event.qwen_score !== 1) return false;
  if (filter === 'qwen5' && event.qwen_score !== 5) return false;
  if (filter === 'jevHigh' && event.jev_probability < 0.75) return false;
  if (filter === 'jevLow' && event.jev_probability >= 0.60) return false;
  if (filter === 'reused' && event.provenance !== 'reused_exact_request') return false;
  if (filter === 'newCall' && event.provenance !== 'new_call') return false;
  const query = $('search').value.trim().toLowerCase();
  if (!query) return true;
  return `${event.episode_id} f${event.frame} ${event.scene}`.toLowerCase().includes(query);
}

function renderEvents() {
  $('events').replaceChildren();
  B.events.forEach((event, index) => {
    if (!filterMatches(event)) return;
    const button = document.createElement('button');
    const title = document.createElement('strong');
    const details = document.createElement('span');
    button.dataset.index = String(index);
    button.className = index === selected ? 'active' : '';
    title.textContent = `${event.episode_id} · F${event.frame}`;
    details.textContent =
      `${t('qwenShort').replace('{score}', event.qwen_score)} · ` +
      `JEV ${(event.jev_probability * 100).toFixed(1)}% · ` +
      (event.provenance === 'reused_exact_request' ? t('reusedShort') : t('newShort'));
    button.append(title, details);
    button.onclick = () => select(index);
    $('events').append(button);
  });
}

function updateSide() {
  const event = current();
  const qwen = `${event.qwen_score} / 5`;
  const probability = `${(event.jev_probability * 100).toFixed(1)}%`;
  $('qwenValue').textContent = qwen;
  $('jevValue').textContent = probability;
  $('latencyValue').textContent = `${Number(event.latency_seconds).toFixed(2)} s`;
  $('provenanceValue').textContent =
    event.provenance === 'reused_exact_request' ? t('reused') : t('newCall');
  $('qwenValueSide').textContent = qwen;
  $('jevValueSide').textContent = probability;
  $('eventTitle').textContent = `${event.episode_id} · F${event.frame}`;
  $('caseStats').textContent = t('eventStats')
    .replace('{scene}', event.scene)
    .replace('{frame}', event.frame)
    .replace(
      '{provenance}',
      event.provenance === 'reused_exact_request' ? t('reused') : t('newCall')
    );
  $('rgb').src = B.images[event.current_image];
  $('imageInfo').textContent = t('imageInfo')
    .replace('{frame}', event.frame)
    .replace('{inputs}', event.input_frames.map(frame => `F${frame.frame}`).join(', '));
  $('history').replaceChildren();
  event.input_frames.forEach((frame, index) => {
    const button = document.createElement('button');
    const image = document.createElement('img');
    const label = document.createElement('span');
    image.src = B.images[frame.image];
    label.textContent = `F${frame.frame}`;
    button.className = index === event.input_frames.length - 1 ? 'active' : '';
    button.append(image, label);
    $('history').append(button);
  });
  $('instruction').textContent =
    `${t('instruction')}：\n中文：${event.instruction_zh}\nEnglish: ${event.instruction_en}`;
  $('raw').textContent = JSON.stringify({
    event_id: event.event_id,
    episode_id: event.episode_id,
    frame: event.frame,
    image_frames: event.input_frames.map(frame => frame.frame),
    qwen4b_score: event.qwen_score,
    jev_v004: {
      probability_yes: event.jev_probability,
      probability_no: event.jev_probability_no,
      model: event.model,
      request_sha256: event.request_sha256,
      provenance: event.provenance
    },
    raw_result: event.raw_result
  }, null, 2);
  try {
    const saved = JSON.parse(
      localStorage.getItem(`jev-wrong34:${B.tag}:${event.event_id}`) || '{}'
    );
    $('category').value = saved.category || 'uncertain';
    $('note').value = saved.note || '';
  } catch {
    $('category').value = 'uncertain';
    $('note').value = '';
  }
}

function select(index) {
  if (index < 0 || index >= B.events.length) return;
  selected = index;
  updateSide();
  renderEvents();
  drawMaps();
  drawPlot();
}

function renderStats() {
  const summary = B.summary;
  const cards = [
    [summary.events, t('eventsMetric')],
    [`${summary.complete_events}/${summary.expected_events}`, t('completeMetric')],
    [`${summary.new_calls_requested} / ${summary.reused_events}`, t('provenanceMetric')],
    [summary.mean_qwen_score.toFixed(3), t('qwenMeanMetric')],
    [summary.mean_jev_probability.toFixed(3), t('jevMeanMetric')],
    [String(summary.high_jev_count), t('highMetric')]
  ];
  $('stats').replaceChildren();
  cards.forEach(([value, label]) => {
    const card = document.createElement('div');
    const strong = document.createElement('strong');
    const span = document.createElement('span');
    card.className = 'metric';
    strong.textContent = value;
    span.textContent = label;
    card.append(strong, span);
    $('stats').append(card);
  });
}

function updateLanguage() {
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach(element => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  });
  $('title').textContent = t('title');
  $('runInfo').textContent = t('runInfo');
  $('notice').textContent = t('notice');
  $('promptEnglish').textContent = B.prompt_en;
  $('promptChinese').textContent = B.prompt_zh;
  $('footer').textContent = `${t('footer')} · ${t('generated')} ${B.generated_at}`;
  renderStats();
  renderEvents();
  updateSide();
  drawPlot();
}

$('language').onchange = () => {
  lang = $('language').value;
  updateLanguage();
  drawMaps();
};
$('filters').onchange = () => {
  const first = B.events.findIndex(filterMatches);
  if (first >= 0) select(first);
  else renderEvents();
};
$('search').oninput = () => {
  const first = B.events.findIndex(filterMatches);
  if (first >= 0) select(first);
  else renderEvents();
};
$('smoothingMode').onchange = () => drawPlot();
$('filterWindow').oninput = () => {
  $('filterWindowValue').textContent = $('filterWindow').value;
  drawPlot();
};
for (const id of ['showQwenRaw', 'showJevRaw']) $(id).onchange = () => drawPlot();
$('scorePlot').onclick = event => {
  const rect = $('scorePlot').getBoundingClientRect();
  const left = 44;
  const right = 48;
  const relative = Math.max(0, Math.min(1, (
    event.clientX - rect.left - left
  ) / Math.max(1, rect.width - left - right)));
  select(Math.round(relative * (B.events.length - 1)));
};

$('category').onchange = $('note').oninput = () => {
  const event = current();
  try {
    localStorage.setItem(
      `jev-wrong34:${B.tag}:${event.event_id}`,
      JSON.stringify({ category: $('category').value, note: $('note').value })
    );
  } catch {}
};

$('export').onclick = () => {
  const notes = [];
  B.events.forEach(event => {
    try {
      const value = JSON.parse(
        localStorage.getItem(`jev-wrong34:${B.tag}:${event.event_id}`) || '{}'
      );
      if (value.note || value.category) {
        notes.push({
          event_id: event.event_id,
          episode_id: event.episode_id,
          frame: event.frame,
          ...value
        });
      }
    } catch {}
  });
  const anchor = document.createElement('a');
  anchor.href = URL.createObjectURL(new Blob([
    JSON.stringify({ tag: B.tag, notes }, null, 2)
  ], { type: 'application/json' }));
  anchor.download = 'wrong_choices34_review.json';
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
};

window.WRONG_CHOICES_REVIEW = {
  bundle: B,
  select,
  drawMaps,
  drawPlot,
  smoothSeries,
  qwenColor,
  jevColor,
  state: () => ({
    index: selected,
    event_id: current().event_id,
    smoothing: $('smoothingMode').value,
    window: Number($('filterWindow').value)
  })
};

updateLanguage();
select(0);
