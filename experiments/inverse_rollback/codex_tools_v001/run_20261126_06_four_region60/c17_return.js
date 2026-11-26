(() => {
  const d = RECOVERY_C17_DATA;
  const label = (zh, en) => lang === 'zh' ? zh : en;
  const panel = document.createElement('section');
  panel.id = 'C17-return';
  panel.style.cssText = 'border:1px solid #7fa9aa;border-radius:8px;padding:12px;margin:12px 0';
  panel.innerHTML = '<h3></h3><p class="timing"></p><img class="front" width="640" height="480" style="width:100%;height:auto;display:block" alt="RGB"><p class="caption"></p><input class="scrub" style="width:100%" type="range" min="0"><div class="buttons"><button type="button"></button> <button type="button"></button> <button type="button"></button></div><details><summary></summary><p class="prompt" style="white-space:pre-line"></p><div class="notes"></div></details>';
  const q = s => panel.querySelector(s);
  $('observationPanel').prepend(panel);
  const layer = document.createElement('label'), toggle = document.createElement('input'), legend=document.createElement('span');
  toggle.type='checkbox'; toggle.checked=true; layer.append(toggle,legend); $('mapLayers').append(layer);
  const shortcut = document.createElement('a');
  shortcut.href='#C17-return'; shortcut.style.cssText='display:inline-block;margin-top:6px;color:inherit;text-decoration:underline'; document.querySelector('header').append(shortcut);
  const scrub=q('.scrub'), [back,play,forward]=panel.querySelectorAll('.buttons button');
  scrub.max=d.rows.length-1;
  let pos=0, timer=null;
  const active=()=>c().case_id==='C17' && $('reviewModel').value==='astra';
  const actions={start:['起点','Start'],observe:['主动观察','Observe'],forward:['前进','Forward'],turn_left:['左转','Turn left'],turn_right:['右转','Turn right'],finish_return:['声明到达','Declare arrival']};
  function frame(i){
    pos=Math.max(0,Math.min(d.rows.length-1,i)); scrub.value=pos;
    const r=d.rows[pos];q('.front').src=d.folder+'/'+r.image;
    q('.caption').textContent=label('移动 ','Move ')+r.move+'/60 · '+label(...actions[r.action])+' · '+label('调用 ','Call ')+pos+'/'+(d.rows.length-1)+' · '+r.utc.slice(11,19)+' UTC';
    q('.front').alt=q('.caption').textContent;
    back.disabled=pos===0; forward.disabled=pos===d.rows.length-1;
  }
  function pause(){clearInterval(timer);timer=null;play.textContent=label('播放','Play');}
  function show(i){frame(i);draw();}
  function render(){
    panel.hidden=layer.hidden=!active();
    shortcut.textContent=label('C17 · 实走回退','C17 · Physical return');
    if(!active()){pause();return;}
    q('h3').textContent=label('C17 实走回退 · F91 → S09（F68）','C17 physical return · F91 → S09 (F68)');
    q('.timing').textContent=label('模型在第 55/60 步声明到达，停点距 F68 为 1.32 米。摆位 7 分 27 秒，回退 8 分 44 秒，总计 16 分 11 秒。','The model declared arrival at move 55/60, ending 1.32 m from F68. Placement took 7m 27s, the return 8m 44s, and the full attempt 16m 11s.');
    legend.textContent=label(' C17 实走回退轨迹与当前位置',' C17 return path and current position');
    q('summary').textContent=label('回退指令与分支发言','Return prompt and branch messages');
    q('.prompt').textContent=label(...d.prompt);
    q('.notes').replaceChildren(...d.notes.map(([call,zh,en])=>{const p=document.createElement('p');p.textContent=label('调用 ','Call ')+call+' · '+label(zh,en);return p;}));
    back.textContent=label('上一步','Previous');forward.textContent=label('下一步','Next');play.textContent=timer?label('暂停','Pause'):label('播放','Play');
    scrub.setAttribute('aria-label',label('实走回退进度','Physical return timeline'));frame(pos);
  }
  scrub.oninput=()=>{pause();show(+scrub.value);};
  back.onclick=()=>{pause();show(pos-1);};forward.onclick=()=>{pause();show(pos+1);};
  play.onclick=()=>{if(timer){pause();return;} if(pos===d.rows.length-1)show(0);play.textContent=label('暂停','Pause');timer=setInterval(()=>{show(pos+1);if(pos===d.rows.length-1)pause();},450);};
  toggle.onchange=draw;
  const previousLayers=paintMapLayers;
  paintMapLayers=function(ctx,xy,state){
    previousLayers(ctx,xy,state);
    if(!active()||!toggle.checked)return;
    ctx.save();ctx.lineJoin='round';ctx.lineCap='round';
    function trace(points,color,width,dash){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.beginPath();points.forEach((r,i)=>i?ctx.lineTo(...xy(r.p)):ctx.moveTo(...xy(r.p)));ctx.stroke();}
    trace(d.rows,'#24999e',2,[4,3]);trace(d.rows.slice(0,pos+1),'#007985',3.5,[]);
    const r=d.rows[pos],[x,y]=xy(r.p);ctx.translate(x,y);ctx.rotate(-r.heading);ctx.fillStyle='#007985';ctx.strokeStyle='white';ctx.lineWidth=1.6;ctx.setLineDash([]);ctx.beginPath();ctx.moveTo(9,0);ctx.lineTo(-6,-5);ctx.lineTo(-3,0);ctx.lineTo(-6,5);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();
  };
  const priorUpdate=updateLanguage;
  updateLanguage=function(){priorUpdate();render();};
  function openReturn(){if($('reviewModel').value!=='astra'){$('reviewModel').value='astra';setModel('astra');}selectCase(B.cases.findIndex(v=>v.case_id==='C17'));panel.scrollIntoView({block:'start'});}
  shortcut.onclick=e=>{e.preventDefault();history.replaceState(null,'','#C17-return');openReturn();};
  render();if(location.hash==='#C17-return')openReturn();else draw();
})();
