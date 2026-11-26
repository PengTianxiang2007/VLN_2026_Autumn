"""Build the 42-case local comparison from the archived bilingual route viewer."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / 'outputs/crossing_checkpoint/online_sampling_v002' / HERE.name
OLD = ROOT / 'outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/front_candidates_01'
TRADEOFF = OUT.with_name('run_20261124_02_tradeoffs')


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f'Archived template does not contain one {before[:80]!r}')
    return text.replace(before, after, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tradeoffs', action='store_true')
    args = parser.parse_args()
    dest = (TRADEOFF if args.tradeoffs else OUT) / 'replay'
    html = (OLD / 'index.html').read_text()
    match = re.search(r'(<script id="payload" type="application/json">)(.*?)(</script>)', html, re.S)
    bundle = json.loads(match[2])
    source = {c['episode_id']: c for c in bundle['cases']}
    selected = json.loads((HERE / 'selection.json').read_text())['selected']
    cases = []
    for phase in ('design', 'validation'):
        source_dir = TRADEOFF if args.tradeoffs and phase == 'validation' else OUT
        for result in json.loads((source_dir / f'{phase}.json').read_text())['cases']:
            item = source[result['episode']].copy()
            cases.append(dict(item, case_id=f'C{result["number"]:02}', group=phase,
                              reference_frames=result['reference'], pairs=result['rows'][selected]['pairs'],
                              comparisons=result['rows'] if args.tradeoffs else {}))
    bundle['tag'] = 'jev_online_sampling_v002_dev20_holdout22'
    bundle['cases'] = cases
    scores = [f['jev']['probability_yes'] for c in cases for f in c['frames']]
    bundle['summary'] = dict(valid_calls=len(scores), jev_mean_probability=sum(scores)/len(scores),
                             candidates=sum(len(c['reference_frames']) for c in cases))
    scenes = {c['scene'] for c in cases}
    bundle['maps'] = {k:v for k,v in bundle['maps'].items() if k in scenes}
    keys = {f['image'] for c in cases for f in c['frames']} | {m['image'] for m in bundle['maps'].values()}
    bundle['images'] = {k:os.path.relpath(OLD / bundle['images'][k], dest) for k in keys}
    html = html[:match.start(2)] + json.dumps(bundle, ensure_ascii=False).replace('</', r'<\/') + html[match.end(2):]

    # Static Astra overlay uses original candidate IDs and timestamps.
    registry = """
class AstraReference extends JevOnlineSampler {
  constructor() {super(); this.positions = new Set(c().reference_frames);}
  decide(index, at) {
    const candidate = super.decide(index, at);
    return candidate && this.positions.has(index) ? candidate : null;
  }
}
"""
    anchor = 'const SAMPLING_VERSIONS=Object.freeze(['
    html = replace_once(html, anchor, (ROOT/'core/jev_online_sampler_v002.js').read_text() + '\n' + registry + anchor + """
  {id:'v002',title:'v002Title',description:'v002Description',color:'#bd540d',create:()=>new JevOnlineSamplerV002('MODE')},
  {id:'Astra',title:'astraTitle',description:'astraDescription',color:'#6343af',create:()=>new AstraReference()},
""".replace("'MODE'", json.dumps(selected)))
    if args.tradeoffs:
        html = replace_once(html, anchor, anchor + """
  {id:'plateau',title:'plateauTitle',description:'plateauDescription',color:'#267448',create:()=>new JevOnlineSamplerV002('plateau')},
  {id:'active',title:'activeTitle',description:'activeDescription',color:'#b32649',create:()=>new JevOnlineSamplerV002('active')},
""")
    html = html.replace('value="failure" data-i18n="failure"', 'value="design" data-i18n="design"')
    html = html.replace('value="success" data-i18n="success"', 'value="validation" data-i18n="validation"')
    html = replace_once(html, "${i+1}. ${item.episode_id}", "${item.case_id} · ${item.episode_id}")
    html = html.replace("t(item.group==='success'?'success':'failure')", 't(item.group)')
    html = replace_once(html, "loadNote();draw();", """$('caseStats').textContent += ' · ' + t(c().group) + ' · ' + t('pairs') + ' ' +
  c().pairs.map(([a,b]) => 'F'+a+' → F'+b).join(', ');loadNote();draw();""")
    labels = """
Object.assign(L.zh,{title:'JEV 流式采样对照',source:'20 条设计轨迹 · 22 条留出轨迹',candidateCount:'Astra 参考点',
  design:'设计集',validation:'验证集',pairs:'新版候选 → Astra 参考位置',v002Title:'v002 · 邻近合并',
  v002Description:'与上个已发候选相距最多 3 步时跳过。',astraTitle:'Astra v006.1 · 参考回退点',
  astraDescription:'显示 Astra 最终保留的原版候选。时间标记沿用原始候选确认帧。',
  subtitle:'同轨迹 ±3 步一对一匹配 · 本地离线回放',samplingHint:'分别勾选原版、新版或 Astra 参考点，在地图和波形上对照。'});
Object.assign(L.en,{title:'JEV streaming sampler comparison',source:'20 design episodes · 22 holdout episodes',candidateCount:'Astra references',
  design:'Design',validation:'Holdout',pairs:'New candidate → Astra reference',v002Title:'v002 · Nearby consolidation',
  v002Description:'Skip proposals within three steps of the last emitted candidate.',astraTitle:'Astra v006.1 · Reference checkpoints',
  astraDescription:'Original candidates retained by Astra. Times refer to the original sampler confirmations.',
  subtitle:'Within-episode one-to-one matching at ±3 steps · Local replay',samplingHint:'Toggle the original sampler, new sampler and Astra references on the map and score plot.'});
"""
    if args.tradeoffs:
        labels += """
Object.assign(L.zh,{title:'三种 JEV 流式采样规则',v002Title:'保守 · 邻近合并',plateauTitle:'均衡 · 高分区间隔候选后移',
  activeTitle:'精简 · 高分区候选后移',plateauDescription:'仅高分区内的间隔候选可后移 2 步作为代表。',
  activeDescription:'高分区活动时各类候选均可后移 2 步作为代表。',missed:'漏采参考帧',agreement:'匹配数 / 候选数',none:'无'});
Object.assign(L.en,{title:'Three streaming JEV sampling rules',v002Title:'Conservative · Nearby consolidation',
  plateauTitle:'Balanced · Shift interval proposals',activeTitle:'Lean · Shift high-region proposals',
  plateauDescription:'Only interval proposals inside a high region may move two steps later.',
  activeDescription:'All proposal types in an active high region may move two steps later.',
  missed:'Missed reference frames',agreement:'Matches / candidates',none:'None'});
"""
        html = replace_once(html, 'loadNote();draw();', """
  for (const [mode,label] of [['near','v002Title'],['plateau','plateauTitle'],['active','activeTitle']]) {
    const r=c().comparisons[mode], found=new Set(r.pairs.map(pair=>pair[1]));
    const missed=c().reference_frames.filter(f=>!found.has(f));
    $('caseStats').append(document.createElement('br'),t(label)+' · '+t('agreement')+' '+r.pairs.length+'/'+r.frames.length+
      ' · '+t('missed')+' '+(missed.map(f=>'F'+f).join(', ')||t('none')));
  }
  loadNote();draw();""")
    html = replace_once(html, "$('sample_v001').checked=true; updateLanguage();",
                        labels + "$('sample_v002').checked=true; $('sample_Astra').checked=true; updateLanguage();")
    dest.mkdir(exist_ok=False)
    (dest/'index.html').write_text(html)
    shutil.copy2(OLD/'FONT_LICENSE.txt', dest/'FONT_LICENSE.txt')


if __name__ == '__main__':
    main()
