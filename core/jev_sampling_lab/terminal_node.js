L.zh.effectiveCount = '有效节点（含终止）';
L.en.effectiveCount = 'Nodes including terminal';
const terminalText = () => lang === 'zh' ? '终止节点' : 'Terminal node';
function renderTerminal(node) {
  const label = terminalText()+' · F'+node.index;
  const jump = $('terminalStep');
  jump.textContent = label;
  jump.onclick = () => { stop(); seek(node.index); };
  if (index !== node.index) return;
  const badge = $('currentNodeStatus');
  badge.hidden = false;
  badge.dataset.state = 'node';
  badge.textContent = label+' · '+(lang === 'zh' ? '偏航评审编号 ' : 'Review ID ')+node.id;
  $('rgb').classList.add('isNode');
  $('jevValue').textContent = lang === 'zh' ? '终止帧无 JEV 评分' : 'Terminal frame has no JEV score';
}
function drawTerminal(ctx,x,y,w,h) {
  const label = lang === 'zh' ? '终点' : 'END';
  ctx.save();
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(x,y-8); ctx.lineTo(x+8,y); ctx.lineTo(x,y+8); ctx.lineTo(x-8,y); ctx.closePath();
  ctx.lineWidth=5; ctx.strokeStyle='#fff'; ctx.stroke();
  ctx.lineWidth=2.5; ctx.strokeStyle='#00675d'; ctx.stroke();
  ctx.font='bold 12px CrossingSans,sans-serif'; ctx.textBaseline='middle';
  const tx=Math.max(2,Math.min(w-ctx.measureText(label).width-2,x+10)), ty=Math.max(9,Math.min(h-9,y-12));
  ctx.lineWidth=3; ctx.strokeStyle='#fff'; ctx.strokeText(label,tx,ty);
  ctx.fillStyle='#00564e'; ctx.fillText(label,tx,ty);
  ctx.restore();
}
