const deepseekDeviation = (() => {
  const toggle = $('deepseekDeviation');
  toggle.onchange = () => draw();
  const record = () => B.deepseekReviews[c().episode_id];
  const active = () => toggle.checked ? record()?.interval : null;
  function updateLabel() {
    const r = record();
    let text;
    if (!r) text = lang === 'zh' ? '本组仅评审 C01–C29' : 'This run covers C01–C29';
    else if (r.interval) text = 'F'+r.interval.from_frame+' → F'+r.interval.to_frame;
    else text = lang === 'zh' ? '未判出明确偏航' : 'No explicit deviation detected';
    if (r?.errors) text += lang === 'zh' ? ' · '+r.errors+' 次回答校验失败' : ' · '+r.errors+' invalid responses';
    toggle.parentElement.title = text;
  }
  function map(ctx,xy) {
    const r = active();
    if (!r) return;
    const frames = c().frames;
    ctx.save();
    ctx.strokeStyle = '#7024ac'; ctx.lineWidth = 3.5;
    ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.setLineDash([6,4]);
    ctx.beginPath();
    for (let i=r.from_frame;i<=r.to_frame;i++) {
      const [x,y]=xy(frames[i].position);
      if (i===r.from_frame) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.stroke(); ctx.setLineDash([]);
    for (const [f,label] of [[r.from_frame,'A'],[r.to_frame,'B']]) {
      const [x,y]=xy(frames[f].position);
      ctx.beginPath(); ctx.arc(x,y,8,0,2*Math.PI); ctx.lineWidth=2.5;ctx.stroke();
      const offset=label==='A'?-10:9;
      const tx=Math.max(2,Math.min(ctx.canvas.clientWidth-12,x+offset));
      const ty=Math.max(14,Math.min(ctx.canvas.clientHeight-3,y+18));
      ctx.font='bold 12px CrossingSans,sans-serif';ctx.lineWidth=3;ctx.strokeStyle='#fff';
      ctx.strokeText(label,tx,ty);ctx.fillStyle='#7024ac';ctx.fillText(label,tx,ty);ctx.strokeStyle='#7024ac';
    }
    ctx.restore();
  }
  function plot(ctx,x,top,bottom) {
    const r = active();
    if (!r) return;
    const left=x(r.from_frame), right=x(r.to_frame);
    ctx.save();ctx.fillStyle='rgba(117,49,172,.13)';
    ctx.fillRect(left,top,Math.max(2,right-left),bottom-top);
    ctx.strokeStyle='#7024ac';ctx.lineWidth=3;ctx.setLineDash([]);
    ctx.beginPath();ctx.moveTo(left,top+1);ctx.lineTo(right,top+1);ctx.stroke();ctx.restore();
  }
  return {updateLabel,map,plot};
})();
