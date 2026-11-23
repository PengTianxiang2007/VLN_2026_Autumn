/* Archived observations at retained checkpoints; presentation only. */
(() => {
  const data = B.nodeMultiview;
  const root = document.getElementById('nodeMultiview');
  const words = {
    zh: {
      title:'存档节点 · 多视角',
      scope:'376 个保留存档节点 · 53 个终止节点 · 47 个 v006 回退目标',
      hint:'图像来自该节点当时的真实采集，角度相对当步机器人朝向。180°为左前／正前／右前三视图，360°为八方向图组。点击图片可放大。',
      note:'辅助视图仅用于查看。模型评审仍使用原生前视；v006 回退目标是离线评审记录，未执行实际回退。',
      previous:'上一个节点', next:'下一个节点', mode:'视角', half:'180° · 三视图', full:'360° · 八方向',
      seventy:'±70° · 三视图', no70:'此节点未采集 ±70° 视图。',
      hint70:'按该节点记录的相机位姿重新采集，角度相对原生相机朝向。依次为左 70°、正前 0°、右 70°。点击图片可放大。',
      target:'定位 v006 回退目标', noTarget:'本轨迹 v006 未指定回退目标',
      checkpoint:'保留存档节点', terminal:'终止节点', targetBadge:'v006 回退目标',
      ordinary:'当前帧不是保留存档节点或终止节点。请选择下方节点查看对应多视角。',
      confirmed:'节点确认于', alarm:'v006 报警于', position:'机器人位置', heading:'机器人朝向',
      original:'640 × 480 · 同帧展示副本', close:'关闭大图', failed:'图像加载失败',
      openTarget:'查看回退点多视角', list:'保留节点与终止节点', current:'当前帧',
      directions:['正前','左前','正左','左后','正后','右后','正右','右前']
    },
    en: {
      title:'Checkpoint views',
      scope:'376 retained checkpoints · 53 terminal nodes · 47 v006 rollback targets',
      hint:'Views were captured at this node. Angles are relative to the robot heading at that step. The 180° group contains front-left, front and front-right views; the 360° group contains eight directions. Select an image to enlarge it.',
      note:'Auxiliary views are for inspection only. Reviews still use native front RGB. The v006 rollback targets are offline review records; no physical rollback was performed.',
      previous:'Previous node', next:'Next node', mode:'Views', half:'180° · Three views', full:'360° · Eight directions',
      seventy:'±70° · Three views', no70:'No ±70° views were captured at this node.',
      hint70:'New views rendered at the recorded camera pose, relative to the native camera heading. Ordered left 70°, front 0°, right 70°. Select an image to enlarge it.',
      target:'Go to v006 rollback target', noTarget:'No v006 rollback target for this trajectory',
      checkpoint:'Retained checkpoint', terminal:'Terminal node', targetBadge:'v006 rollback target',
      ordinary:'This frame is not a retained checkpoint or terminal node. Select a node below to inspect its views.',
      confirmed:'Node confirmed at', alarm:'v006 alarm at', position:'Robot position', heading:'Robot heading',
      original:'640 × 480 · Same-frame display copy', close:'Close enlarged view', failed:'Image failed to load',
      openTarget:'Inspect rollback views', list:'Retained and terminal nodes', current:'Current frame',
      directions:['Front','Front-left','Left','Rear-left','Rear','Rear-right','Right','Front-right']
    }
  };
  const tr = key => words[lang === 'zh' ? 'zh' : 'en'][key];
  const el = (tag, text, cls) => {
    const value = document.createElement(tag);
    if (text !== undefined) value.textContent = text;
    if (cls) value.className = cls;
    return value;
  };
  let mode = '180', renderKey, modalView = null;
  const dialog = el('dialog', undefined, 'mvDialog');
  dialog.id = 'mvDialog';
  const close = el('button'); close.type = 'button'; close.id = 'mvClose';
  const caption = el('h3'); caption.id = 'mvDialogCaption';
  const enlarged = el('img'); enlarged.id = 'mvEnlarged';
  dialog.append(close, caption, enlarged); document.body.append(dialog);
  close.onclick = () => dialog.close();
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('keydown', event => event.stopPropagation());
  dialog.addEventListener('close', () => { modalView = null; });
  const group = () => data.cases[c().episode_id];
  const angle = yaw => (yaw > 0 ? '+' : '') + (yaw === -180 ? 180 : yaw) + '°';
  const viewsFor = node => mode === '70' ? node.views70 : node.views;
  const viewLabel = (node, id) => tr('directions')[id]+' · '+angle(viewsFor(node)[id].yaw);
  const button = (text, fn, id) => {
    const item = el('button', text); item.type = 'button'; item.onclick = fn;
    if (id) item.id = id;
    return item;
  };
  function jump(frame) { stop(); seek(frame); }
  function showModal(node, id) {
    modalView = {node, id, mode, episode:c().episode_id};
    enlarged.src = viewsFor(node)[id].image;
    caption.textContent = c().episode_id+' · '+node.id+' · F'+node.index+' · '+viewLabel(node,id);
    enlarged.alt = caption.textContent;
    close.textContent = tr('close');
    dialog.showModal();
  }
  function enhanceRollbackLink() {
    const line = document.querySelector('#v4Review .v4rollback');
    if (!line || line.querySelector('[data-mv-rollback-link]')) return;
    const match = line.textContent.match(/\(F(\d+)\)/);
    if (!match) return;
    const link = button(tr('openTarget'), () => {
      jump(Number(match[1])); root.scrollIntoView({block:'nearest', behavior:'smooth'});
    });
    link.dataset.mvRollbackLink = match[1]; line.append(link);
  }
  function sync() {
    enhanceRollbackLink();
    const g = group();
    const key = [c().episode_id,index,lang,mode].join('/');
    if (renderKey === key) return;
    renderKey = key;
    if (dialog.open && modalView && (modalView.episode !== c().episode_id || modalView.node.index !== index || modalView.mode !== mode)) dialog.close();
    if (dialog.open && modalView) {
      caption.textContent = c().episode_id+' · '+modalView.node.id+' · F'+modalView.node.index+' · '+viewLabel(modalView.node,modalView.id);
      enlarged.alt = caption.textContent; close.textContent = tr('close');
    }
    root.replaceChildren(); root.setAttribute('aria-label',tr('title'));
    root.append(el('h3',tr('title')),el('p',tr('scope'),'mvScope'));
    const tools = el('div',undefined,'mvTools');
    const previous = [...g.nodes].reverse().find(n => n.index < index);
    const next = g.nodes.find(n => n.index > index);
    const prevButton = button(tr('previous'), () => jump(previous.index), 'mvPrevious');
    const nextButton = button(tr('next'), () => jump(next.index), 'mvNext');
    prevButton.disabled = !previous; nextButton.disabled = !next;
    const selector = el('select'); selector.id = 'mvMode'; selector.setAttribute('aria-label',tr('mode'));
    selector.add(new Option(tr('half'),'180')); selector.add(new Option(tr('full'),'360'));
    selector.add(new Option(tr('seventy'),'70')); selector.value = mode;
    selector.onchange = () => { mode = selector.value; sync(); };
    tools.append(prevButton,nextButton,selector); root.append(tools);
    const rollback = button(g.rollback ? tr('target')+' · '+g.rollback.node_id+' · F'+g.rollback.frame : tr('noTarget'),
      () => jump(g.rollback.frame), 'mvRollback');
    rollback.disabled = !g.rollback; root.append(rollback);
    const list = el('div',undefined,'mvNodes'); list.id = 'mvNodes'; list.setAttribute('aria-label',tr('list'));
    for (const n of g.nodes) {
      const isTarget = g.rollback?.frame === n.index;
      const label = n.id+' · F'+n.index+(n.terminal_node ? ' · '+tr('terminal') : '')+(isTarget ? ' · '+tr('targetBadge') : '');
      const item = button(label, () => jump(n.index)); item.dataset.mvNode = n.id; item.dataset.frame = n.index;
      item.setAttribute('aria-pressed', String(n.index === index));
      item.className = (n.terminal_node?'mvTerminal ':'')+(isTarget?'mvTarget':''); list.append(item);
    }
    root.append(list);
    const node = g.nodes.find(n => n.index === index);
    const status = el('p',undefined,'mvStatus'); status.id = 'mvStatus'; status.setAttribute('role','status');
    if (!node) {
      status.textContent = tr('current')+' F'+index+' · '+tr('ordinary'); root.append(status);
    } else {
      root.dataset.nodeFrame = String(node.index);
      status.textContent = node.id+' · F'+node.index+' · '+tr(node.terminal_node?'terminal':'checkpoint')+
        (g.rollback?.frame === node.index ? ' · '+tr('targetBadge')+' · '+tr('alarm')+' F'+g.rollback.alarm_frame : '');
      root.append(status);
      const metadata = el('p',tr('position')+' XYZ: '+node.position.map(n=>n.toFixed(3)).join(', ')+' m · '+
        tr('heading')+': '+node.heading_deg.toFixed(1)+'° · '+tr('confirmed')+' F'+node.emittedAt,'mvMeta');
      root.append(metadata,el('p',tr(mode === '70' ? 'hint70' : 'hint'),'mvHint'));
      if (mode === '70' && !node.views70) {
        root.append(el('p',tr('no70'),'mvMissing'));
      } else {
      const grid = el('div',undefined,'mvGrid mvMode'+mode); grid.id = 'mvGrid';
      for (const id of mode === '360' ? [0,1,2,3,4,5,6,7] : [1,0,7]) {
        const item = button('', () => showModal(node,id)); item.dataset.mvView = String(id);
        const im = el('img'); im.src = viewsFor(node)[id].image; im.alt = node.id+' · F'+node.index+' · '+viewLabel(node,id);
        im.width = 640; im.height = 480; im.decoding = 'async';
        im.onerror = () => { item.classList.add('mvFailed'); item.querySelector('span').textContent = viewLabel(node,id)+' · '+tr('failed'); };
        item.append(im,el('span',viewLabel(node,id))); grid.append(item);
      }
      root.append(grid,el('p',tr('original'),'mvMeta'));
      }
    }
    if (!node) delete root.dataset.nodeFrame;
    root.append(el('p',tr('note'),'mvNote'));
  }
  const originalSync = window.syncV4Review;
  window.syncV4Review = () => { originalSync(); sync(); };
  window.NodeMultiview = {sync, jump, data};
  sync();
})();
