// Each enabled sampler contributes its own sector. The reference always has a
// separate outline, including when no sampler has selected the same position.
let mapTargets = [];

function paintMapLayers(ctx, project, state) {
  const locations = new Map();
  for (const {version, nodes} of state.versions) {
    for (const node of nodes) {
      const [x,y] = project(c().frames[node.index].position);
      const key = [Math.round(x*2),Math.round(y*2)].join(',');
      if (!locations.has(key)) locations.set(key,{x,y,points:new Map()});
      const points = locations.get(key).points;
      if (!points.has(version)) points.set(version,[]);
      points.get(version).push(node);
    }
  }
  mapTargets = [...locations.values()];
  for (const {x,y,points} of mapTargets) {
    const layers = [...points.keys()].filter(layer => layer.id !== 'Astra');
    ctx.lineWidth = 1;
    layers.forEach((layer,i) => {
      const start = Math.PI * (2*i/layers.length - .5);
      ctx.beginPath();
      ctx.moveTo(x,y);
      ctx.arc(x,y,5.5,start,start + 2*Math.PI/layers.length);
      ctx.closePath(); ctx.fillStyle=layer.color;ctx.fill();ctx.strokeStyle='#fff';ctx.stroke();
    });
    if ([...points.keys()].some(layer=>layer.id==='Astra')) {
      ctx.beginPath();ctx.moveTo(x,y-9);ctx.lineTo(x+9,y);ctx.lineTo(x,y+9);ctx.lineTo(x-9,y);ctx.closePath();
      ctx.strokeStyle='#fff';ctx.lineWidth=4;ctx.stroke();
      ctx.strokeStyle='#54218b';ctx.lineWidth=2;ctx.stroke();
    }
  }
}

function inspectMapPoint(event) {
  const map = $('jevMap'), rect = map.getBoundingClientRect();
  const x=event.clientX-rect.left, y=event.clientY-rect.top;
  const hits=mapTargets.filter(point=>Math.hypot(point.x-x,point.y-y)<=10);
  map.title=hits.flatMap(hit=>[...hit.points.entries()].map(([layer,nodes])=>
    t(layer.title)+' · '+nodes.map(n=>n.id+' F'+n.index).join(', '))).join('\n');
}
