"""Display scored native front frames and pre-deduplication v001 nodes locally."""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import jev_node
from core.agent_route_choice import read
from export_oracle_distance_replay import add_font


def prompt(language):
    context = getattr(jev_node, 'COMPACT_FALLBACK_CONTEXT_' + language)
    question = getattr(jev_node, 'COMPACT_FALLBACK_INSTRUCTIONS_' + language)
    criteria = getattr(jev_node, 'COMPACT_FALLBACK_CRITERIA_' + language)
    return '\n\n'.join([context, question, 'true — ' + criteria['true'], 'false — ' + criteria['false']])


def export(run, replay, dest):
    data = read(run/'manifest.json')
    dataset = Path(data['dataset'])
    summary = read(run/'summary.json')
    source = (replay/'tasks.js').read_text()
    if not source.startswith('const REPLAY = '):
        raise ValueError('Unknown source replay format')
    display = json.loads(source[len('const REPLAY = '):].strip().removesuffix(';'))
    images, maps, cases = {}, {}, []
    total = 0.0
    scored = 0
    for scene, geometry in display['maps'].items():
        images[scene] = os.path.relpath(replay/'maps'/(scene+'.png'), dest)
        maps[scene] = dict(image=scene, geometry=geometry)
    for task in display['tasks']:
        eid = task['id']
        scores = read(run/'episodes'/eid/'scores.json')
        with (dataset/'inputs'/eid/'observations.jsonl').open() as rows:
            front = [json.loads(row)['native_front'] for row in rows]
        if not len(scores)+1 == len(front) == len(task['robot']):
            raise ValueError('Front, score and pose lengths disagree for ' + eid)
        frames = []
        for t, probability in enumerate(scores):
            image = front[t]
            images[image['sha256']] = os.path.relpath(dataset/image['image'],dest)
            frames.append(dict(frame=t, position=task['robot'][t][:3], image=image['sha256'],
                               jev=dict(probability_yes=probability,image_frames=list(range(max(0,t-2),t+1)))))
        cases.append(dict(episode_id=eid,real_episode_id=eid,scene=task['scene'],group='failure',
                          instruction_zh=task['instruction'][0],instruction_en=task['instruction'][1],
                          reference_path=task['reference'],frames=frames))
        total += sum(scores)
        scored += len(scores)
    if len(cases)!=summary['episodes'] or scored!=summary['scored']:
        raise ValueError('Viewer inputs disagree with completed run')
    payload = dict(tag='route53_'+run.name,images=images,maps=maps,cases=cases,
                   prompt_zh=prompt('ZH'),prompt_en=prompt('EN'),
                   summary=dict(valid_calls=scored,jev_mean_probability=total/scored,candidates=summary['candidates']))
    package = ROOT/'core/jev_sampling_lab'
    html = (package/'template.html').read_text()
    html = html.replace('@@PAYLOAD_JSON@@',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
    html = re.sub(r'@font-face\{font-family:CrossingSans;src:url\(assets/[^)]+\)\}', '', html)
    app = (package/'app.js').read_text()
    if app.count("['events',B.cases.length]")!=1:
        raise ValueError('Unknown statistics layout')
    app = app.replace("['events',B.cases.length]","['candidateCount',B.summary.candidates]")
    scripts = {'app.js':app,
               'online_sampler_v001.js':(run/'source/core/jev_online_sampler_v001.js').read_text(),
               'online_filter.js':(ROOT/'core/jev_online_filter_v001.js').read_text()}
    for name in ['node_deduplication_results.js','node_elimination_results.js',*scripts]:
        code = '<script>\n'+scripts[name]+'\n</script>' if name in scripts else ''
        html = html.replace('<script src="'+name+'"></script>',code)
    # Keep the original map, waveform and sampling behavior. The run controls
    # only the scored dataset and which review stages have recorded evidence.
    html = html.replace('</head>','<style>#dedupControls,#eliminationControls,#nodeDeduplicationTop,'
                        '#nodeEliminationTop,html[lang="zh-CN"] #promptEnglish,html[lang="zh-CN"] [data-i18n="promptEnglish"],'
                        'html[lang="en"] #promptChinese,html[lang="en"] [data-i18n="promptChinese"]'
                        '{display:none!important}</style></head>')
    presentation = """
Object.assign(L.zh,{title:'JEV 候选回退点',source:'53 条轨迹 · 原生前视',candidateCount:'去重前候选',
  rulesNote:'本次使用固定参数 N=7、D=5。',samplingHint:'勾选后在地图和概率波形上显示该轨迹的原始候选节点。'});
Object.assign(L.en,{title:'JEV fallback candidates',source:'53 trajectories · native front view',
  candidateCount:'Candidates before deduplication',rulesNote:'This run uses fixed parameters N=7 and D=5.',
  samplingHint:'Show the original candidate nodes on the map and probability waveform.'});
for(const id of ['filterWindow','streamDelay','nodeElimination','nodeDeduplication']) $(id).disabled=true;
$('nodeElimination').checked=false; $('nodeDeduplication').checked=false;
$('sample_v001').checked=true; updateLanguage();
"""
    html = html.replace('</body>','<script>'+presentation+'</script></body>')
    dest.mkdir(parents=True,exist_ok=False)
    page = dest/'index.html'
    page.write_text(html)
    add_font(page)
    page.write_text(page.read_text().replace('font-family:OracleSans','font-family:CrossingSans'))
    return page


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ['run','replay','output']:
        parser.add_argument('--'+arg,required=True,type=Path)
    args=parser.parse_args()
    print(export(args.run.resolve(),args.replay.resolve(),args.output.resolve()))
