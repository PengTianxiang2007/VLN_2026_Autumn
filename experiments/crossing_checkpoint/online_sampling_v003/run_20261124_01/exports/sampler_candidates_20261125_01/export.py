"""Feature the original sampler and the two designated candidates in the metrics replay."""
from pathlib import Path
import json
import runpy

HERE=Path(__file__).resolve().parent
previous_export=HERE.parent/'map_metrics_20261125_01'
base=runpy.run_path(str(previous_export/'export.py'))


def transform(html):
    # LAYER_ORDER drives the metric rows and the map controls, not the sampler.
    original=['v001','v002','plateau','active','coverage','p60','p70','strict','Astra']
    featured=['v001','coverage','active']
    reordered=featured+[key for key in original if key not in featured]
    key='const LAYER_ORDER='+json.dumps(original)
    assert html.count(key)==1
    html=html.replace(key,'const LAYER_ORDER='+json.dumps(reordered))
    default="$('sample_p60').checked=true; $('sample_Astra').checked=true;"
    assert html.count(default)==1
    html=html.replace(default,"for (const id of ['v001','coverage','active','Astra']) $('sample_'+id).checked=true;")
    marker='</body>'
    assert html.count(marker)==1
    js="""
Object.assign(L.zh,{
  v001Title:'v001 原版（默认）',rank_coverage:'v003 覆盖优先（候选）',activeTitle:'v002 精简（候选）',
  featuredSamplers:'JEV 采样版本',fixedSampler:'原版 · 当前默认',candidateSampler:'候选版本',
  originalName:'v001 原版',coverageName:'v003 覆盖优先',leanName:'v002 精简'});
Object.assign(L.en,{
  v001Title:'v001 Original (default)',rank_coverage:'v003 Higher coverage (candidate)',activeTitle:'v002 Lean (candidate)',
  featuredSamplers:'JEV samplers',fixedSampler:'Original · Current default',candidateSampler:'Candidate',
  originalName:'v001 Original',coverageName:'v003 Higher coverage',leanName:'v002 Lean'});
const shortlist=document.createElement('section');
shortlist.id='featuredSamplers';
shortlist.innerHTML='<h2 data-i18n="featuredSamplers"></h2>';
for (const [id,role,name] of [['v001','fixedSampler','originalName'],['coverage','candidateSampler','coverageName'],['active','candidateSampler','leanName']]) {
  const card=document.createElement('div');
  card.style.borderLeftColor=LAYER_COLORS[id];
  const status=document.createElement('span'), title=document.createElement('strong');
  status.dataset.i18n=role; title.dataset.i18n=name;
  card.append(status,title); shortlist.append(card);
}
$('stats').before(shortlist);
updateLanguage();
"""
    css="""<style>
#featuredSamplers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;padding:12px clamp(12px,3vw,36px);background:#f4f7fa}
#featuredSamplers h2{grid-column:1/-1;margin:0;font-size:17px}
#featuredSamplers div{padding:8px 12px;background:white;border-left:4px solid}
#featuredSamplers span,#featuredSamplers strong{display:block}#featuredSamplers span{color:#445563;font-size:13px}
@media(max-width:620px){#featuredSamplers{grid-template-columns:1fr}}
</style>"""
    return html.replace('</head>',css+'</head>').replace(marker,'<script>'+js+'</script>'+marker)


if __name__=='__main__':
    pub=base['PUB']
    base['write_export'](HERE.name,previous_export.name,pub/'jev_sampling_astra_map_metrics42_web_20261125_01',
                         pub/'jev_sampler_candidates42_web_20261125_01',transform)
