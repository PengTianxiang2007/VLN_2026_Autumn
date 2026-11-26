"""Export the local map-layer replay and a portable ZIP using existing WebP assets."""
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
RUN = ROOT/'outputs/crossing_checkpoint/online_sampling_v003'/HERE.parents[1].name
OLD = RUN/'replay'
ASSETS = ROOT/'outputs/visualization_publishing/jev_route53_sampling_v001_web_20261118_01'
DEST = RUN/'exports'/HERE.name
LAYER_IDS = ['v001','v002','plateau','active','coverage','p60','p70','strict','Astra']
COLORS = ['#007680','#a65e08','#3f8421','#c93c76','#334aa6','#cc3e0c','#1684b8','#613744','#54218b']


def replace_once(text, token, value):
    if text.count(token) != 1:
        raise ValueError('Unexpected archived template: '+token[:100])
    return text.replace(token,value)


def main():
    html = (OLD/'index.html').read_text()
    # Move the actual controls rather than creating a second set of checkboxes.
    setup = """
const controls = $('samplingVersions'), panel=document.createElement('fieldset');
panel.id='mapLayers';
panel.innerHTML='<legend data-i18n="mapLayers"></legend><p data-i18n="layerKey"></p>';
document.querySelector('.mapGrid').before(panel);
panel.append(controls);
for (const id of LAYER_ORDER) controls.append($('sample_'+id).closest('label'));
$('jevMap').addEventListener('mousemove',inspectMapPoint);
$('jevMap').addEventListener('mouseleave',()=>{$('jevMap').title='';});
Object.assign(L.zh,{title:'JEV 采样点与 GPT-6 Astra 参考点',mapLayers:'俯视地图图层',
  layerKey:'实心圆表示采样点，同位置用不同颜色的扇区表示各版本。紫色菱形表示 Astra 参考点。悬停可查看版本、编号和轨迹帧。',
  v001Title:'v001 原版',v002Title:'v002 保守',plateauTitle:'v002 均衡',activeTitle:'v002 精简',astraTitle:'◇ GPT-6 Astra 参考点'});
Object.assign(L.en,{title:'JEV samples and GPT-6 Astra references',mapLayers:'Top-down map layers',
  layerKey:'Filled circles mark samples. Colored sectors show versions at the same position. A purple diamond marks an Astra reference. Hover for versions, IDs and frames.',
  v001Title:'v001 Original',v002Title:'v002 Conservative',plateauTitle:'v002 Balanced',activeTitle:'v002 Lean',astraTitle:'◇ GPT-6 Astra references'});
updateLanguage();
"""
    html = replace_once(html,'</body>','<script>'+setup+'</script></body>')
    css = """
#mapLayers{margin:10px 0;padding:8px 12px 10px;border:1px solid #c8d3df;border-radius:7px}
#mapLayers legend{font-weight:700}#mapLayers p{font-size:12px;margin:0 0 7px}
#mapLayers #samplingVersions{display:flex;gap:5px;flex-wrap:wrap}
#mapLayers .samplingOption{padding:4px 7px;border-left:4px solid var(--sample-color)}
#mapLayers .samplingCopy .muted,#mapLayers .sampleCount{display:none}
"""
    html=replace_once(html,'</head>','<style>'+css+'</style></head>')
    keys=json.dumps(LAYER_IDS)
    palette=json.dumps(dict(zip(LAYER_IDS,COLORS)))
    # Override the display color in the registry so map, key and waveform agree.
    html=replace_once(html,'const SAMPLING_VERSIONS=Object.freeze([','const LAYER_ORDER='+keys+', LAYER_COLORS='+palette+';\nconst SAMPLING_VERSIONS=Object.freeze([')
    html=replace_once(html,']);\nlet lang=','].map(v=>({...v,color:LAYER_COLORS[v.id]})));\nlet lang=')
    start=html.index("  ctx.setLineDash([]);ctx.font=",html.index('function drawMap(state)'))
    end=html.index('\n}',start)
    html=html[:start]+"""  ctx.setLineDash([]);
  const [x,y]=xy(row().position);
  ctx.beginPath();ctx.arc(x,y,12,0,2*Math.PI);ctx.lineWidth=2;ctx.strokeStyle='#e11d48';ctx.stroke();
  paintMapLayers(ctx,xy,state);"""+html[end:]
    html=replace_once(html,'function drawMap(state){',(HERE/'map_layers.js').read_text()+'\nfunction drawMap(state){')
    payload=re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
    bundle=json.loads(payload[1])
    bundle['tag']='jev_sampling_map_layers_20261125_01'
    maps={m['image'] for m in bundle['maps'].values()}
    images={key:(f'maps/{key}.png' if key in maps else f'front/{key}.webp') for key in bundle['images']}
    def render(paths):
        bundle['images']=paths
        data=json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')
        return html[:payload.start(1)]+data+html[payload.end(1):]
    DEST.mkdir(parents=True,exist_ok=False)
    (DEST/'index.html').write_text(render({k:os.path.relpath(ASSETS/name,DEST) for k,name in images.items()}))
    archive=DEST/'jev_sampling_map_layers.zip'
    with zipfile.ZipFile(archive,'x') as z:
        z.writestr('index.html',render(images),zipfile.ZIP_DEFLATED)
        z.write(OLD/'FONT_LICENSE.txt','FONT_LICENSE.txt',zipfile.ZIP_DEFLATED)
        for name in sorted(set(images.values())):
            z.write(ASSETS/name,name)
    print(len(bundle['cases']),len(images),archive.stat().st_size,hashlib.sha256((DEST/'index.html').read_bytes()).hexdigest())


if __name__=='__main__':
    main()
