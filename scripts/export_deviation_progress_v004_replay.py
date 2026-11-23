"""Export completed review versions on the same Route53 replay."""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from export_route53_deepseek_dedup import replace_once
from export_oracle_distance_replay import add_font
from core.agent_route_choice import file_hash, read, write

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT/'core/deviation_progress_v004_review.js'
MODELS = {'deepseek-flash': ('deepseek', 'DeepSeek'), 'route53-qwen27b': ('qwen', 'Qwen27B')}
CSS = '''
#v4ModelChoice{display:inline-flex;align-items:center;gap:8px;margin-top:12px;font-weight:600}
#v4ModelChoice select{float:none;position:static;color:#182b40}
#v4Review{margin:18px 0;padding:16px;border:1px solid #b8c8da;border-radius:8px;background:#fff;color:#182b40}
#v4Review h3{margin:0}#v4Review h4{margin:0 0 5px;font-size:14px;color:#28425c}
#v4Review p{line-height:1.55;white-space:pre-line;margin:4px 0 9px}
.v4block{padding:10px 0;min-width:0}.v4cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;border-top:1px solid #e1e8f0}
.v4rounds,.v4roundhead,.v4links{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:10px 0}
.v4roundhead{justify-content:space-between;padding-top:10px}.v4pill{padding:4px 7px;background:#edf1f5;color:#34475a;border:1px solid #cad4df;border-radius:4px;font-size:12px}
.v4pill.consistent{color:#0c5a46;background:#e5f6ee}.v4pill.uncertain{color:#735000;background:#fff2d2}
.v4pill.deviated,.v4rollback{color:#9e172d;background:#ffeaed}.v4pill.format_error,.v4error{color:#64378a;background:#f5e9ff}
.v4pill[aria-pressed=true],.v4images button[aria-current=true]{outline:2px solid #244b74}
.v4images{display:grid;grid-template-columns:repeat(auto-fit,minmax(78px,1fr));gap:5px}
.v4images button{min-width:0;padding:2px;background:#f6f8fa;color:#234;border:1px solid #cdd6df}
.v4images img{width:100%;display:block;aspect-ratio:4/3;object-fit:contain}.v4images span{font-size:11px}
#v4Review details{border-top:1px solid #e1e8f0;padding:8px 0}#v4Review pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:26rem;overflow:auto}
.v4links{gap:18px;font-size:13px}.v4error,.v4rollback{padding:6px 9px}@media(max-width:800px){.v4cols{grid-template-columns:1fr;gap:0}}
'''


def url(mime, data):
    return 'data:'+mime+';base64,'+base64.b64encode(data).decode('ascii')


def text_values(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for item in obj:
            yield from text_values(item)
    elif isinstance(obj, dict):
        yield from text_values(list(obj.values()))


def collect(run, bundle, display_images=None):
    status, manifest = read(run/'status.json'), read(run/'manifest.json')
    if status['phase'] != 'complete' or status.get('failed_cases') or not manifest.get('cases'):
        raise ValueError('The selected review must be complete: '+str(run))
    model = manifest['settings']['model']
    model_id, model_name = MODELS[model]
    version = manifest.get('version', 'v004')
    if version != 'v004':
        model_id += '_'+version
    cases = {c['episode_id']:c for c in bundle['cases']}
    records = {c['episode_id']:c for c in bundle['dedup']['cases']}
    anchors = read(run/'retained_nodes_and_terminals.json')
    bundle['cases'], bundle['dedup']['cases'] = [], []
    bundle['deviationReviews'] = {}
    groups, originals, flat = {}, {}, []
    hashes = {}
    case_sources = read(run/'case_sources.json') if (run/'case_sources.json').is_file() else {}
    display_overrides = read(run/'display_overrides.json') if (run/'display_overrides.json').is_file() else {}
    error_translations = {
        "ValueError: Unexpected/missing answer fields: ['type']": '原答多返回了顶层字段 type。',
        'ValueError: Invalid uncertainties': 'uncertainties 字段的结构不符合输出要求。',
        'ValueError: Instruction quote is not an exact supplied excerpt': '英文引文不是原始指令中的连续逐字片段。',
        'ValueError: Missing semantic progress': '缺少合法的累计语义进度。',
        'ValueError: Incomplete response: length': '回答达到长度上限，被截断，未通过校验。',
    }
    checked = {row['case_number']:row for row in read(run/f'{version}_results.json')}
    for number in manifest['cases']:
        label = f'C{number:02d}'
        folder = Path(case_sources[label]) if label in case_sources else run/'run/cases'/label
        case_result = read(folder/'result.json')
        eid = case_result['episode_id']
        replay = cases[eid]
        assert case_result['case_number'] == records[eid]['case_number'] == number
        assert replay['terminal_node'] == anchors[eid][-1] and replay['terminal_node']['index'] == len(replay['frames'])-1
        dedup = records[eid]
        dedup['case_index'] = len(bundle['cases'])
        bundle['cases'].append(replay)
        bundle['dedup']['cases'].append(dedup)
        rounds = []
        for item in case_result['reviews']:
            node = item['node_id']
            stem = folder / node
            reqfile, respfile = stem.with_suffix('.request.json'), stem.with_suffix('.response.json')
            req, resp = read(reqfile), read(respfile)
            raw = resp['response']['choices'][0]['message']['content']
            try:
                answer = json.loads(raw)
            except json.JSONDecodeError:
                assert item['status'] != 'ok'
                answer = None
            if 'parsed_original' in resp:
                assert answer == resp['parsed_original']
            assert resp['status'] == item['status']
            assert req['prompt_sha256'] == manifest['prompt_sha256'] and req['instruction_en'] == replay['instruction_en']
            outcome = answer['verdict'] if item['status']=='ok' else 'format_error'
            if outcome=='format_error' and resp['error'] not in error_translations:
                raise ValueError('Translate the validation error for display: '+resp['error'])
            imgs = []
            for im in req['images']:
                key = im['sha256']
                assert key == im['image_id'] == replay['frames'][im['frame']]['image']
                if display_images is not None:
                    display = bundle['images'][key]
                    originals[key] = display
                    display_hash = file_hash(display_images/display)
                    imgs.append(dict(frame=im['frame'],role=im['role'],sha256=key,file=f'assets/{display_hash}.webp',
                        display_sha256=display_hash,
                        representation='same-frame WebP display copy; original input SHA256 retained'))
                    continue
                if key not in originals:
                    data = Path(im['path']).read_bytes()
                    assert hashlib.sha256(data).hexdigest() == key and data[:8] == b'\x89PNG\r\n\x1a\n'
                    originals[key] = url('image/png', data)
                imgs.append(dict(frame=im['frame'],role=im['role'],sha256=key,file=f'assets/{key}.png'))
            row = dict(model=model,case_id=label,episode_id=eid,current_id=node,previous_id=req['previous_id'],
                       from_frame=req['previous_frame'],to_frame=req['current_frame'],mode=req['mode'],
                       available_at_frame=item['available_at_frame'],terminal_node=item['terminal_node'],
                       instruction_zh=replay['instruction_zh'],instruction_en=req['instruction_en'],
                       images=imgs,prior_progress=item['prior_progress'],outcome=outcome,validation_status=item['status'],
                       validation_error=resp.get('error'),answer=answer,raw_answer=raw,
                       raw_answer_sha256=hashlib.sha256(raw.encode()).hexdigest(),committed_progress=item['committed_progress'],
                       progress_anchor=item['progress_anchor'],rollback_target=item.get('rollback_target'))
            if resp.get('error'):
                row['validation_error_text'] = dict(zh=error_translations[resp['error']],en=resp['error'])
            if f'{label}/{node}' in display_overrides:
                assert outcome == 'format_error'
                row['display_partial'] = display_overrides[f'{label}/{node}']
            assert req['prior_semantic_progress'] == row['prior_progress']['zh']
            rounds.append(row); flat.append(row)
            hashes[f'{label}/{node}'] = dict(request=file_hash(reqfile), response=file_hash(respfile))
        assert [v['current_id'] for v in rounds] == [v['node'] for v in checked[number]['rounds']]
        assert [v['outcome'] for v in rounds] == [v['verdict'] for v in checked[number]['rounds']]
        groups[eid] = dict(case_id=label,nodes=anchors[eid],rounds=rounds)
        bundle['deviationReviews'][eid] = [dict(from_frame=v['from_frame'],to_frame=v['to_frame']) for v in rounds if v['outcome']=='deviated']
    selected_translations = set(text_values(bundle['dedup']['cases']))
    d = bundle['dedup']
    d['translations'] = {k:v for k,v in d['translations'].items() if k in selected_translations}
    bundle['tag'] = d['source_tag'] = 'deviation_'+version+'_'+run.name
    d.update(phase_note_zh=f'{len(groups)} 条离线轨迹',phase_note_en=f'{len(groups)} offline trajectories')
    scenes = {c['scene'] for c in bundle['cases']}
    bundle['maps'] = {k:v for k,v in bundle['maps'].items() if k in scenes}
    keys = {f['image'] for c in bundle['cases'] for f in c['frames']} | {m['image'] for m in bundle['maps'].values()}
    bundle['images'] = {k:bundle['images'][k] for k in sorted(keys)}
    counts = Counter(r['outcome'] for r in flat)
    assert dict(counts) == status.get('completed_case_verdicts', status.get('verdicts'))
    totals = dict(calls=len(flat), flagged=counts['deviated'], invalid=counts['format_error'],
                  frames=sum(len(c['frames']) for c in bundle['cases']),nodes=sum(len(g['nodes']) for g in groups.values()),
                  input_png=len(originals), scenes=len(scenes))
    bundle['summary'] = dict(candidates=sum(c['summary']['candidates'] for c in d['cases']),
                             retained=totals['nodes']-len(groups),comparisons=sum(c['summary']['model_calls'] for c in d['cases']),
                             valid_calls=totals['frames']-len(groups))
    prompts = run/'source/experiments/deviation_progress'/version
    bundle['v4'] = dict(cases=groups, totals={**totals, 'cases':len(groups)},
                        originals=originals, modelId=model_id, modelName=model_name,
                        version=version, partial=bool(manifest.get('partial')),
                        compact_inputs=display_images is not None,
                        **{'prompt_'+lang:(prompts/f'prompt_{lang}.txt').read_text() for lang in ('zh','en')})
    if manifest.get('mode') == 'cached_response_revalidation':
        bundle['v4']['originalRounds'] = manifest['original_rounds']
    return flat, hashes, totals


def export(run, template, out, online, compare_run=None, compact_inputs=False):
    out.mkdir(parents=True,exist_ok=False)
    html = template.read_text()
    m = re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
    frozen = m[1]
    bundle = json.loads(frozen)
    flat, hashes, totals = collect(run, bundle, template.parent if compact_inputs else None)
    first = bundle['v4']['modelId']
    model_rows = {first: flat}
    model_records = {first: dict(run=str(run), totals=totals, answers=hashes)}
    reviews = [bundle['v4']]
    comparisons = [compare_run] if isinstance(compare_run, Path) else (compare_run or [])
    if comparisons:
        bundle['v4Originals'] = bundle['v4'].pop('originals')
        bundle['v4Alternatives'] = {}
    for compare_run in comparisons:
        other = json.loads(frozen)
        rows, checks, counts = collect(compare_run, other, template.parent if compact_inputs else None)
        review = other['v4']
        key = review['modelId']
        if key in model_rows:
            raise ValueError('Choose different models or review versions')
        for field in ('cases', 'maps', 'images', 'summary'):
            if bundle[field] != other[field]:
                raise ValueError('Different trajectory data: '+field)
        for eid, group in bundle['v4']['cases'].items():
            assert group['nodes'] == review['cases'][eid]['nodes']
        bundle['v4Originals'].update(review.pop('originals'))
        bundle['v4Alternatives'][key] = dict(review=review, intervals=other['deviationReviews'], tag=other['tag'])
        model_rows[key] = rows
        model_records[key] = dict(run=str(compare_run), totals=counts, answers=checks)
        reviews.append(review)
    name = ('qwen_deepseek' if comparisons else first)+'_v004_six_offline.zip'
    if bundle['v4'].get('partial'):
        count = len(bundle['v4']['cases'])
        name = f'qwen_v005_completed_{count}_offline.zip'
    elif len(bundle['v4']['cases']) != 6 and not comparisons:
        name = first+f"_all_{len(bundle['v4']['cases'])}_offline.zip"
    elif any(review['version'] != 'v004' for review in reviews):
        name = first+'_comparison_six_offline.zip'
    for review in reviews:
        key = review['modelId']
        review['archiveFile'] = name
        if review.get('partial'):
            review['answersFile'] = key+f"_partial_{len(review['cases'])}_model_returns.json"
        elif len(review['cases']) != 6:
            review['answersFile'] = key+f"_all_{len(review['cases'])}_model_returns.json"
        else:
            review['answersFile'] = key+'_model_returns.json' if comparisons or review['version'] != 'v004' else 'model_returns.json'
    for key, relative in bundle['images'].items():
        path = template.parent/relative
        mime = {'.webp':'image/webp','.png':'image/png'}[path.suffix]
        bundle['images'][key] = url(mime,path.read_bytes())
    if compact_inputs:
        originals = bundle.get('v4Originals', bundle['v4'].get('originals'))
        for key in originals:
            originals[key] = bundle['images'][key]
    content = json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html = html[:m.start(1)] + content + html[m.end(1):]
    html,n = re.subn(r'<style id="embedded-font">.*?</style>','',html,flags=re.S)
    assert n==1
    html = replace_once(html,'</head>','<style>'+CSS+'</style></head>')
    html = replace_once(html,'<h3 data-i18n="plot">','<section id="v4Review"></section><h3 data-i18n="plot">')
    html = replace_once(html,'loadNote();draw();','loadNote();draw();window.syncV4Review?.();')
    html = replace_once(html,"return selectedCount>1?version.id+'·'+node.id:node.id;",
        "const n=B.v4.cases[c().episode_id].nodes.find(v=>v.index===node.index);"
        "return $('nodeDeduplication').checked && n ? n.id : (lang==='zh'?'候选 ':'Candidate ')+node.id;")
    html = replace_once(html,"['candidateCount',B.summary.candidates],['trajectories',new Set(B.cases.map(v=>v.real_episode_id)).size],"
        "['retainedCount',B.summary.retained],['effectiveCount',B.summary.retained+B.cases.length],['pairCount',B.summary.comparisons]",
        "['trajectories',B.cases.length],['effectiveCount',B.v4.totals.nodes],['v4calls',B.v4.totals.calls],"
        "['v4alarm',B.v4.totals.flagged],['v4invalid',B.v4.totals.invalid]")
    html = replace_once(html,'</body>','<script>'+PANEL.read_text()+'</script></body>')
    page = out/'index.html'
    page.write_text(html)
    add_font(page)
    page.write_text(page.read_text().replace('font-family:OracleSans','font-family:CrossingSans'))
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/prepare_online_visualization.py'),
                    '--html',str(page),'--destination',str(online)],check=True)
    manifest=read(online/'online_manifest.json')
    assets=manifest['assets']
    for review in reviews:
        rows = model_rows[review['modelId']]
        for row in rows:
            for im in row['images']:
                assert assets[im['file']]==im.get('display_sha256',im['sha256'])
        answers_file = review['answersFile']
        write(online/answers_file,rows)
        assets[answers_file]=file_hash(online/answers_file)
    with zipfile.ZipFile(online/name,'x',zipfile.ZIP_DEFLATED,compresslevel=4) as archive:
        for p in [manifest['html'], *sorted(assets)]:
            archive.write(online/p,p)
        archive.write(out/'FONT_LICENSE.txt','FONT_LICENSE.txt')
        for key, rows in model_rows.items():
            prefix = key+'/' if comparisons else ''
            archive.writestr(prefix+'all_rounds.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
            for row in rows:
                archive.writestr(f"{prefix}raw_answers/{row['case_id']}/{row['current_id']}.txt",row['raw_answer'].encode())
        for review in reviews:
            prefix = review['modelId']+'/' if comparisons else ''
            for lang in ('zh','en'):
                archive.writestr(f'{prefix}prompts/prompt_{lang}.txt',review['prompt_'+lang])
    with zipfile.ZipFile(online/name) as archive:
        assert archive.testzip() is None
        for key, rows in model_rows.items():
            prefix = key+'/' if comparisons else ''
            for row in rows:
                assert hashlib.sha256(archive.read(f"{prefix}raw_answers/{row['case_id']}/{row['current_id']}.txt")).hexdigest()==row['raw_answer_sha256']
    assets[name]=file_hash(online/name)
    write(online/'online_manifest.json',manifest)
    write(out/'export.json',dict(totals=totals,source_html_sha256=file_hash(template),method=file_hash(Path(__file__)),
          ui=file_hash(PANEL),answers=hashes,models=model_records,offline_sha256=file_hash(page),online_sha256=file_hash(online/'index.html'),
          archive_sha256=assets[name],online_files=len(assets)+1))
    print(json.dumps({key:item['totals'] for key,item in model_records.items()},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--compare-run',type=Path,action='append',help='Additional review of the same frozen trajectories')
    p.add_argument('--template',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--online',type=Path,required=True)
    p.add_argument('--compact-inputs',action='store_true',help='Reuse the same-frame WebP display copies, preserving original input SHA256')
    a=p.parse_args()
    export(a.run,a.template,a.output,a.online,a.compare_run,a.compact_inputs)
