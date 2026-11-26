import json
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
root = Path.cwd()
sys.path[:0] = [str(root), str(root/'scripts')]
from core.codex_client import CodexConfig, CodexSession
from export_terra_v006_selected9 import build_model
from export_codex_dedup_comparison import read, save, sha256, payload, package_replay, answer_texts
import publish_visualization

name = 'run_20261124_02_terra_fast_selected9'
run = root/'outputs/codex_tasks/checkpoint_dedup/v006_1'/name
record = root/'experiments/crossing_checkpoint/codex_dedup_v006_1'/name/'exports/comparison_01'
record.mkdir(parents=True,exist_ok=True)
prev = root/'outputs/codex_tasks/checkpoint_dedup/v006/run_20261124_04_astra_remaining7/selected9/exports/astra_terra_selected9'
old_trans = root/'experiments/crossing_checkpoint/codex_dedup_v006_1/run_20261124_01_astra_c01_c11/exports/comparison_01/translations.json'
transfile = record/'translations.json'
translations = read(transfile) if transfile.exists() else read(old_trans)
template = (run/'source/core/codex_checkpoint_candidate_v006_1_en.txt').read_text()
direction = next(p for p in template.split('\n\n') if p.startswith('Examine the left'))
translations[direction] = '以机器人在 B0 时的朝向为准，依次检查左侧、前方和右侧。针对每个方向，在 eligibility_reason 中说明机器人从当前位置或接下来几步内能走向哪里，以及哪些可见证据支持或限制这种判断。将继续向前也作为一个可能的选项。然后判断哪些方向构成通往不同空间区域的独立路线。如果可见地面和墙体布局支持转弯，可以推断被转角遮挡的路线。只计算在选择并沿另一条支路前进之前就能做出的选择。如果多个方向只是绕过同一个障碍物并通向同一区域，将其计为一个选项。如果某个可见开口因依赖更早的一次支路选择而被排除，请说明这种依赖关系。'
def translate(words):
    values={str(i):s for i,s in enumerate(words)}
    schema={'type':'object','properties':{k:{'type':'string'} for k in values},'required':list(values),'additionalProperties':False}
    folder=run/'display_translations'/str(time.time_ns())
    session=CodexSession(folder,CodexConfig(model='gpt-6.1-terra',service_tier='priority',proxy_url='http://127.0.0.1:17982',timeout_seconds=950))
    msg='Translate each English string faithfully into Simplified Chinese for a visual navigation replay. Retain image labels, left/forward/right, uncertainty and negatives. Return the same keys. No tools.\n'+json.dumps(values)
    result=json.loads(session.ask(msg,[],schema,label='translation')['text'])
    assert set(result)==set(values) and all(any('\u4e00'<=c<='\u9fff' for c in v) for v in result.values())
    return {v:result[k] for k,v in values.items()}
pending=set(); futures=[]
with ThreadPoolExecutor(2) as pool:
    while True:
        status=read(run/'status.json')['status']
        if status not in ('running','complete'): raise RuntimeError(read(run/'status.json')['failed_cases'])
        words=dict.fromkeys(s for f in run.glob('cases/*/decisions.jsonl') for l in f.read_text().splitlines() if l for s in answer_texts(json.loads(l)['answer']))
        missing=[s for s in words if s not in pending and s not in translations]
        for i in range(0,len(missing),26):
            rows=missing[i:i+26]
            if len(rows)>=22 or status=='complete':
                futures.append(pool.submit(translate,rows));pending.update(rows)
        for future in futures.copy():
            if future.done():translations.update(future.result());save(transfile,translations);futures.remove(future)
        if status=='complete' and not futures:break
        time.sleep(8)
save(transfile,translations)
offline=run/'exports/terra_fast_v006_1_selected9'
online=root/'outputs/visualization_publishing/terra_fast_v006_1_selected9_web_20261124_01'
html=(prev/'index.html').read_text()
match,b=payload(html)
model=build_model('GPT-6.1 Terra Fast v006.1','gpt-6.1-terra',run,run/'source/core',b,translations,'local_route_choice_v006_1','codex_checkpoint_candidate_v006_1_en.txt')
astra_source=run.parent/'run_20261124_01_astra_c01_c11/exports/astra_v006_1_c01_c11/index.html'
_,astra_bundle=payload(astra_source.read_text())
models={'terra61':model,'astra61':astra_bundle['modelReviews']['astra61'],**b['modelReviews']}
ids=[c['episode_id'] for c in model['cases']]
assert [c['case_number'] for c in model['cases']]==[1,3,4,5,11,17,19,32,34]
for m in models.values():
    m['cases']=[c for c in m['cases'] if c['episode_id'] in ids];m['coverage']=len(m['cases'])
    for c in m['cases']:c['case_index']=ids.index(c['episode_id'])
    m['source_tag']=online.name
    m['summary']={k:sum(c['summary'][k] for c in m['cases']) for k in ('candidates','retained','removed','model_calls','uncertain')}
model.update(sampler_version=b['dedup']['sampler_version'],sampler_config=b['dedup']['sampler_config'],phase_note_zh='九例已完成',phase_note_en='Nine trajectories completed')
cases=[c for c in b['cases'] if c['episode_id'] in ids]
maps={c['scene']:b['maps'][c['scene']] for c in cases}
images={f['image'] for c in cases for f in c['frames']}|{m['image'] for m in maps.values()}
b.update(tag=online.name,cases=cases,maps=maps,images={k:b['images'][k] for k in images},dedup=model,modelReviews=models,primaryModel='terra61',summary=dict(valid_calls=sum(len(c['frames']) for c in cases),candidates=model['summary']['candidates'],retained=model['summary']['retained'],comparisons=model['summary']['model_calls']))
content=json.dumps(b,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
html=html[:match.start(1)]+content+html[match.end(1):]
start=html.index('// Display-only filters over frozen model results.');end=html.index('</script>',start)
html=html[:start]+(root/'core/codex_dedup_comparison.js').read_text()+'\n'+html[end:]
archive=package_replay(html,b['images'],prev,offline,online)
save(record/'snapshot.json',dict(offline=str(offline.relative_to(root)),html_sha256=sha256(offline/'index.html'),zip=archive.name,zip_sha256=sha256(archive),results_sha256=sha256(run/'results.json'),template_sha256=sha256(prev/'index.html')))
subprocess.run(['node','scripts/check_codex_dedup_comparison.cjs',str(online/'index.html'),str(record/'browser_check.json'),str(offline.parent/'page.png')],check=True)
man=read(online/'online_manifest.json')
sys.argv=['publish_visualization','--html',str(online/man['html']),'--name',online.name]
for asset in man['assets']:sys.argv.extend(['--asset',asset])
publish_visualization.main()
