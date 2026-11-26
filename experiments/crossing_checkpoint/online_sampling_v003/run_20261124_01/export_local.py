"""Add the frozen v003 modes to the existing bilingual 42-trajectory local replay."""
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUTPUTS=ROOT/'outputs/crossing_checkpoint'
OLD=OUTPUTS/'online_sampling_v002/run_20261124_02_tradeoffs/replay'
OUT=OUTPUTS/'online_sampling_v003'/HERE.name
DEST=OUT/'replay'
read=lambda p:json.loads(p.read_text())


def insert_once(html, token, extra):
    if html.count(token)!=1:
        raise ValueError('Unexpected template: '+token)
    return html.replace(token,extra+token)


def main():
    html=(OLD/'index.html').read_text()
    match=re.search(r'(<script id="payload" type="application/json">)(.*?)(</script>)',html,re.S)
    bundle=json.loads(match[2])
    profiles=read(HERE/'profiles.json')['profiles']
    labels={'coverage':('覆盖优先','Higher coverage'),'p60':('60% 目标','60% target'),
            'p70':('70% 目标','70% target'),'strict':('严格筛选','Strict selection')}
    rows={}
    for phase in ('design','validation'):
        for c in read(OUT/(phase+'_profiles.json'))['cases']:
            rows[c['episode']]=c
    for c in bundle['cases']:
        result=rows[c['episode_id']]
        assert result['reference']==c['reference_frames']
        c['comparisons'].update({k:result['rows'][k] for k in profiles})
    bundle['tag']='jev_online_sampling_v003_42'
    # Same directory depth as the frozen page, so image URLs remain relative to the same source.
    html=html[:match.start(2)]+json.dumps(bundle,ensure_ascii=False).replace('</',r'<\/')+html[match.end(2):]
    token='const SAMPLING_VERSIONS=Object.freeze(['
    definitions=(ROOT/'core/jev_online_sampler_v003.js').read_text()+'\nconst rankProfiles='+json.dumps(profiles)+';\n'
    html=insert_once(html,token,definitions)
    colors=['#057a73','#d9480f','#2454a6','#94324e']
    registry=[dict(id=k,title='rank_'+k,description='rank_hint',color=color) for k,color in zip(profiles,colors)]
    html=html.replace(token,token+'\n  ...'+json.dumps(registry)+'.map(v=>({...v,create:()=>new JevOnlineSamplerV003(rankProfiles[v.id])})),')
    oldtip="[['near','v002Title'],['plateau','plateauTitle'],['active','activeTitle']]"
    assert html.count(oldtip)==1
    html=html.replace(oldtip,json.dumps([[k,'rank_'+k] for k in profiles]))
    translations=''
    for i,lang in enumerate(['zh','en']):
        words={'rank_'+k:'v003 · '+v[i] for k,v in labels.items()}
        words.update(title=['JEV 采纳率与覆盖率','JEV precision and reference coverage'][i],
                     pairs=['v002 保守版候选 → Astra 参考帧','v002 conservative candidate → Astra reference'][i],
                     rank_hint=['沿用 5 步延迟；名称中的百分比为设计目标。','Five-step delay; percentages in profile names denote design targets.'][i])
        translations+='Object.assign(L.'+lang+','+json.dumps(words,ensure_ascii=False)+');\n'
    token="$('sample_v002').checked=true; $('sample_Astra').checked=true; updateLanguage();"
    assert html.count(token)==1
    html=html.replace(token,translations+"$('sample_p60').checked=true; $('sample_Astra').checked=true; updateLanguage();")
    DEST.mkdir(exist_ok=False)
    (DEST/'index.html').write_text(html)
    shutil.copy2(OLD/'FONT_LICENSE.txt',DEST/'FONT_LICENSE.txt')


if __name__=='__main__': main()
