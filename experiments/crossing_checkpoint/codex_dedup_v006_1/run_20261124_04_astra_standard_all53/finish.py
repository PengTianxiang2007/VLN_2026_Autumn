"""Finish the 53-case standard-tier campaign and publish its frozen comparison."""
import json
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

RECORD = Path(__file__).resolve().parent
ROOT = RECORD.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from core.codex_client import CodexConfig, CodexSession, now, save, sha256
from export_codex_dedup_comparison import answer_texts, package_replay, payload, read
from export_terra_v006_selected9 import build_model
import publish_visualization

RUN = ROOT / 'outputs/codex_tasks/checkpoint_dedup/v006_1' / RECORD.name
AGG = RUN / 'all53'
EXPORT = RECORD / 'exports/all53_01'
RELEASE = 'astra_standard_v006_1_all53_web_20261124_01'
ONLINE = ROOT / 'outputs/visualization_publishing' / RELEASE
OLD = ROOT / 'outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_03_all53/exports/all53_20261123_01/index.html'
NINE = RUN.parent / 'run_20261124_02_terra_fast_selected9/exports/terra_fast_v006_1_selected9/index.html'
TAG = 'local_route_choice_v006_1'
PROMPT = 'codex_checkpoint_candidate_v006_1_en.txt'
def report(phase, **data):
    save(RUN / 'delivery_status.json', dict(phase=phase, updated_at=now(), **data))

def collect():
    original = read(RECORD / 'input.json')
    reuse = read(RECORD / 'reuse.json')
    reused = ROOT / reuse['source']
    assert sha256(reused / 'results.json') == reuse['sha256']
    sources = {c['case_number']: reused for c in read(reused / 'results.json')['cases']}
    attempt = RUN
    for index in range(4):
        while read(attempt / 'status.json')['status'] == 'running':
            time.sleep(20)
        result = read(attempt / 'results.json')
        sources.update({c['case_number']: attempt for c in result['cases']})
        if not result['failures']:
            break
        if index == 3:
            raise RuntimeError(result['failures'])
        bad = {row['case_number'] for row in result['failures']}
        todo = [dict(c) for c in original['cases'] if c['case_number'] in bad]
        for c in todo:
            prev = next(attempt.glob(f"cases/C{c['case_number']:02d}_*"))
            if (prev/'decisions.jsonl').is_file() and read(prev/'state.json')['processed']:
                c['resume_from'] = str(prev)
        attempt = RUN / f'retry_{index+1:02d}'
        if not (attempt/'status.json').is_file():
            manifest = dict(original, cases=todo, case_numbers=sorted(bad))
            manifest['candidate_count'] = manifest['expected_comparisons'] = sum(len(c['nodes']) for c in todo)
            inp = RECORD / (attempt.name+'_input.json')
            save(inp, manifest)
            cmd = read(RECORD / 'launch.json')
            cmd[cmd.index('--input')+1] = str(inp)
            cmd[cmd.index('--output')+1] = str(attempt)
            report('retry', cases=sorted(bad), attempt=index+1)
            with (RUN/(attempt.name+'.log')).open('a') as log:
                subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    assert sorted(sources) == list(range(1,54))
    cases = []
    times = []
    for number, source in sorted(sources.items()):
        config = read(source/'status.json')['config']
        assert config['service_tier'] is None and config['model']=='gpt-6-astra'
        f = next(source.glob(f'cases/C{number:02d}_*/result.json'))
        c = read(f)
        assert c['prompt_revision']==TAG and len(c['nodes'])==len(c['decisions'])
        cases.append(c)
        times.extend(read(Path(d['response_directory'])/'response.json')['elapsed_seconds'] for d in c['decisions'])
    assert len(times)==494
    totals = {k:sum(c['summary'][k] for c in cases) for k in cases[0]['summary']}
    save(AGG/'results.json',dict(cases=cases,summary=totals,failures=[],sources={str(k):str(v.relative_to(ROOT)) for k,v in sources.items()}))
    first = datetime.fromisoformat(read(RUN/'status.json')['started_at'])
    last = max(datetime.fromisoformat(read(p/'status.json')['completed_at']) for p in set(sources.values()))
    save(AGG/'timing.json',dict(mean=statistics.mean(times),median=statistics.median(times),fresh51_wall_seconds=(last-first).total_seconds(),count=len(times)))
    return cases

def translate(batch):
    inputs = {str(i):v for i,v in enumerate(batch)}
    schema = dict(type='object', properties={k:dict(type='string') for k in inputs}, required=list(inputs),additionalProperties=False)
    for attempt in range(3):
        session = CodexSession(RUN/'display_translations'/str(time.time_ns()), CodexConfig(model='gpt-6-luna', reasoning_effort='low', proxy_url='http://127.0.0.1:17982',timeout_seconds=1800))
        try:
            prompt = 'Translate each string faithfully into Simplified Chinese for a VLN replay. Preserve all image identifiers, directions, spatial relations, and uncertainty. Use 回退点 for recovery checkpoint. Return the same keys.\n'+json.dumps(inputs)
            out = json.loads(session.ask(prompt,[],schema,label='translation')['text'])
            assert set(out)==set(inputs) and all(any('\u4e00'<=ch<='\u9fff' for ch in t) for t in out.values())
            return {v:out[k] for k,v in inputs.items()}
        except Exception:
            if attempt==2: raise
            time.sleep(10)

def export(cases):
    cache = EXPORT/'translations.json'
    known = read(cache) if cache.exists() else read(RECORD.parent/'run_20261124_02_terra_fast_selected9/exports/comparison_01/translations.json')
    words = dict.fromkeys(text for c in cases for d in c['decisions'] for text in answer_texts(d['answer']))
    missing = [w for w in words if w not in known]
    report('translating', model='gpt-6-luna', remaining=len(missing))
    with ThreadPoolExecutor(max_workers=12) as pool:
        jobs = [pool.submit(translate,missing[i:i+26]) for i in range(0,len(missing),26)]
        for job in as_completed(jobs):
            known.update(job.result())
            save(cache,known)
            report('translating', model='gpt-6-luna', remaining=sum(w not in known for w in words))
    html = OLD.read_text()
    html=html.replace("heading.className='muted';heading.textContent=","if(!node)continue;heading.className='muted';heading.textContent=",1)
    match, b = payload(html)
    _, nine = payload(NINE.read_text())
    for key in ('memory','astra6','terra6','terra61'):
        b['modelReviews'][key] = nine['modelReviews'][key]
    model = build_model('GPT-6 Astra v006.1','gpt-6-astra',AGG,RUN/'source/core',b,known,TAG,PROMPT,reference_model='astra3')
    model.update(sampler_version=b['dedup']['sampler_version'],sampler_config=b['dedup']['sampler_config'],phase_note_zh='53 例已完成',phase_note_en='53 trajectories completed')
    b['modelReviews'] = {'astra61':model, **b['modelReviews']}
    ids = [c['episode_id'] for c in b['cases']]
    for m in b['modelReviews'].values():
        m['source_tag']=RELEASE
        for c in m['cases']:
            c['case_index']=ids.index(c['episode_id'])
    b.update(primaryModel='astra61',dedup=model,tag=RELEASE)
    b['summary'].update(retained=model['summary']['retained'],comparisons=494)
    text=json.dumps(b,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html=html[:match.start(1)]+text+html[match.end(1):]
    start=html.index('// Display-only filters over frozen model results.')
    html=html[:start]+(ROOT/'core/codex_dedup_comparison.js').read_text()+'\n'+html[html.index('</script>',start):]
    off=AGG/'exports/astra_standard_v006_1_all53'
    snapshot=EXPORT/'snapshot.json'
    if not snapshot.exists():
        report('packaging')
        archive=package_replay(html,b['images'],OLD.parent,off,ONLINE)
        save(snapshot,dict(offline=str(off.relative_to(ROOT)),html_sha256=sha256(off/'index.html'),zip=archive.name,zip_sha256=sha256(archive),results_sha256=sha256(AGG/'results.json')))
    publish_completed()

def publish_completed(check_browser=True):
    off=AGG/'exports/astra_standard_v006_1_all53'
    snapshot=EXPORT/'snapshot.json'
    if check_browser and not (EXPORT/'browser_check.json').exists():
        report('checking')
        subprocess.run(['node','scripts/check_codex_dedup_comparison.cjs',str(ONLINE/'index.html'),str(EXPORT/'browser_check.json'),str(off.parent/'preview.png')],check=True)
    report('publishing')
    man=read(ONLINE/'online_manifest.json')
    sys.argv=['publish_visualization','--html',str(ONLINE/man['html']),'--name',RELEASE]
    for asset in man['assets']:sys.argv.extend(['--asset',asset])
    publish_visualization.main()
    pub=next(read(p) for p in sorted(ONLINE.parent.glob('publish_*/publication.json'),reverse=True) if read(p)['name']==RELEASE and read(p)['phase']=='published')
    assert pub['remote_sha256_verified'] and next(f for f in pub['files'] if f['path']=='index.html')['http_status']==200
    s=read(AGG/'results.json')['summary']; t=read(AGG/'timing.json'); snap=read(snapshot)
    summary=f"GPT-6 Astra 常规档 v006.1 完成 53 例。494 个原始候选保留 {s['retained']} 个，排除 {s['not_eligible']} 个不合格候选与 {s['duplicates']} 个重复候选。候选调用均值 {t['mean']:.2f} 秒。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[完整回放]({pub['url']})。"
    (EXPORT/'README.md').write_text(f"# 全集双语导出\n\n{summary}\n\n发布 {pub['updated_at']}，本地 {snap['offline']}/index.html，SHA256 {snap['html_sha256']}。离线包 {snap['zip']}，SHA256 {snap['zip_sha256']}。远端哈希与入口 HTTP 200 通过。\n")
    with (RECORD/'README.md').open('a') as file:file.write('\n'+summary+'\n')
    for file in [ROOT/'docs/STATUS.md',ROOT/'experiments/README.md',RECORD.parents[1]/'README.md']:
        head,body=file.read_text().split('\n',1)
        file.write_text(head+'\n\n'+summary+'\n'+body)
    report('published',url=pub['url'],summary=s,timing=t)

if __name__=='__main__':
    AGG.mkdir(exist_ok=True)
    EXPORT.mkdir(parents=True,exist_ok=True)
    try:
        report('reviewing')
        if (EXPORT/'snapshot.json').exists():
            publish_completed()
        else:
            export(read(AGG/'results.json')['cases'] if (AGG/'results.json').exists() else collect())
    except Exception as error:
        report('error',error=repr(error))
        raise
