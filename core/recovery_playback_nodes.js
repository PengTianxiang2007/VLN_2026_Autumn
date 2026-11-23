// The checkpoint IDs and frames here are the committed v006 review sequence.
Object.assign(L.zh, {
  showPoints: '显示有效节点',
  curveHint: '曲线开关控制 JEV 原始概率与滤波结果的显示。',
  protocolReplay: '地图和波形上的节点来自 v006 的有效节点清单。菱形标记终止节点。拖动进度条可查看任意帧的实际观测。'
});
Object.assign(L.en, {
  showPoints: 'Show effective nodes',
  curveHint: 'The curve controls show or hide the raw and filtered JEV probabilities.',
  protocolReplay: 'The map and waveform use the effective node list from v006. The diamond marks the terminal node. Move either slider to view the recorded observation at any frame.'
});

const nodeColor = '#0891b2';

function displayState() {
  const sequence = B.reviewNodes[c().episode_id];
  return {
    nodes: $('showCheckpoints').checked ? sequence.filter(node => !node.terminal_node) : [],
    terminalNode: c().terminal_node,
    values: fullCurve(),
    filter: filterSession().model.state()
  };
}

function renderCurrentNode(state) {
  const node = state.nodes.find(node => node.index === index);
  const badge = $('currentNodeStatus');
  badge.hidden = !node;
  badge.dataset.state = node ? 'node' : 'none';
  badge.textContent = node ? (lang === 'zh' ? '当前节点' : 'Current node') + ' · ' + node.id : '';
  $('rgb').classList.toggle('isNode', Boolean(node));
}
