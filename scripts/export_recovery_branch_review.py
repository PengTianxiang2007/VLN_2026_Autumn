"""Reuse the archived v006 map/RGB template for first-call branch results."""
import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

from export_oracle_distance_replay import add_font

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/visualization_publishing/v006_node_multiview70_web_20261121_01'
SPEC = ROOT / 'experiments/agent_recovery/branch_review_v001'
PATTERN = r'<script id="payload" type="application/json">(.*?)</script>'


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def translated_answer(answer, texts):
    result = deepcopy(answer)
    assert len(texts['branches']) == len(result['branches'])
    for branch, (description, basis) in zip(result['branches'], texts['branches']):
        branch.update(entrance_description=description, current_choice_basis=basis)
    assert len(texts['uncertainties']) == len(result['uncertainties'])
    result['uncertainties'] = texts['uncertainties']
    result['previous_attempt']['reason'] = texts['reason']
    return result


def recovery_playback(html, *, instruction=False):
    """Adapt the archived sampler UI to the fixed node list used by v006."""
    def replace_section(start, end, replacement=''):
        nonlocal html
        a = html.index(start)
        b = html.index(end, a)
        html = html[:a] + replacement + html[b:]

    if instruction:
        map_start, map_end = '<div class="mapGrid">', '<section id="nodeMultiview"'
        map_playback = html[html.index(map_start):html.index(map_end, html.index(map_start))]
        replace_section(map_start, map_end)
        after_rgb_slider = html.index('<div class="values">', html.index('id="imageStep"'))
        html = html[:after_rgb_slider] + map_playback + html[after_rgb_slider:]
        replace_section('<h2 data-i18n="current">', '<div id="currentNodeStatus"',
                        '<div class="brHeader"><h2 data-i18n="current"></h2>'
                        '<button type="button" id="observationRollback"></button></div>')
        replace_section('<p class="muted" id="inputInfo">', '<h3 data-i18n="review">')
        replace_section("  $('inputInfo').textContent=", "  $('caseStats').textContent=")

    replace_section('<button type="button" id="nodeEliminationTop"', '</div></div><p id="caseStats">',
                    '<label class="eliminationShortcut"><input id="showCheckpoints" type="checkbox" checked>'
                    '<span data-i18n="showPoints"></span></label>')
    replace_section('<fieldset class="filterBox" id="samplingControls">', '<p class="muted" id="timeline">')
    replace_section('<details><summary data-i18n="rules">', '<details><summary data-i18n="prompt">')
    replace_section('/* Online candidate sampling', '</script>')
    replace_section('const E=window.JEV_NODE_ELIMINATION_DATA', 'const L={')
    replace_section("Object.assign(L.zh,{\n  elimination:", "let lang='zh'")
    replace_section('function fullSampling(', 'function stop()', (ROOT / 'core/recovery_playback_nodes.js').read_text() + '\n')
    replace_section('function nodeLabel(', 'const deviationOverlay')
    html = html.replace('sampleSessions=new Map(),', '')
    html = html.replace('for(const {version,nodes} of state.versions)for(const node of nodes)', 'for(const node of state.nodes)')
    html = html.replace('for(const {version,nodes}of state.versions){', '{')
    html = html.replace('for(const node of nodes){const px=', 'for(const node of state.nodes){const px=')
    html = html.replace('nodeLabel(node,version,state.versions.length)', 'node.id')
    html = html.replace('version.color', 'nodeColor').replace('y(node.value)', 'y(state.values[node.index] ?? 0)')
    html = html.replace('node,version,label}', 'node,label}')
    replace_section("  $('nodeEliminationTop').setAttribute", '  renderCurrentNode(state)')
    replace_section("+(state.versions.length?' '+t('sampleDelay'", 'const noteKey=',
                    ";\n  $('pendingHint').textContent=$('showFiltered').checked?t('curvePending'):'';\n}\n")
    replace_section('    const reviewed=E?.cases.find', '    const button=document.createElement')
    html = html.replace("C${String(D.cases[i].case_number).padStart(2,'0')}", "${B.branchReview.cases[item.episode_id].input.case_id}")
    replace_section("+(reviewed?` · ${t('eliminationReviewed')}", ';button.onclick')
    replace_section('function resetParameters()', "for(const id of ['frame','imageFrame'])$(id).oninput")
    replace_section("$('nodeDeduplication').onchange", "$('language').onchange",
                    "$('showCheckpoints').onchange=draw;\n")
    replace_section("  $('scorePlot').title=hit?", "$('scorePlot').onclick",
                    "  $('scorePlot').title=hit?hit.node.id+' · F'+hit.node.index:'';};\n")
    replace_section('window.JEV_LAB={', '/* Archived review versions;', """window.JEV_LAB = {
  bundle:B, select:selectCase, seek, draw, displayState, state:()=>({caseIndex:ci,frame:index})
};
for(const id of ['filterWindow','streamDelay']) $(id).disabled=true;
$('reference').checked=true;
const query=new URLSearchParams(location.search), requestedCase=Number(query.get('case'));
selectCase(Number.isInteger(requestedCase)&&requestedCase>=1&&requestedCase<=B.cases.length?requestedCase-1:0);
if(query.get('frame')==='last')seek(c().frames.length-1);
</script><script>""")
    return html


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--translations', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--comparison-run', type=Path)
    parser.add_argument('--comparison-translations', type=Path)
    parser.add_argument('--deepseek-run', type=Path)
    parser.add_argument('--deepseek-translations', type=Path)
    parser.add_argument('--instruction-run', type=Path)
    parser.add_argument('--instruction-translations', type=Path)
    parser.add_argument('--qwen-instruction-run', type=Path)
    parser.add_argument('--qwen-instruction-translations', type=Path)
    args = parser.parse_args()
    if bool(args.comparison_run) != bool(args.comparison_translations):
        parser.error('Provide both comparison arguments together')
    if bool(args.deepseek_run) != bool(args.deepseek_translations):
        parser.error('Provide the DeepSeek run and its translations together')
    if bool(args.instruction_run) != bool(args.instruction_translations) or (args.instruction_run and not args.deepseek_run):
        parser.error('Provide the instruction run, its translations, and the matching first-call DeepSeek results')
    if bool(args.qwen_instruction_run) != bool(args.qwen_instruction_translations) or (args.qwen_instruction_run and not args.instruction_run):
        parser.error('Provide both Qwen instruction arguments alongside DeepSeek for paired playback')
    run, out = args.run, args.output
    manifest, results, translations = read(run / 'manifest.json'), read(run / 'results.json'), read(args.translations)
    assert read(run / 'status.json')['phase'] == 'complete'
    assert len(results) == len(manifest['cases']) > 0
    total_images = sum(len(c['images']) for c in manifest['cases'])
    inputs = {c['episode_id']: c for c in manifest['cases']}
    eids = list(inputs)
    html = (SOURCE / 'index.html').read_text()
    bundle = json.loads(re.search(PATTERN, html, re.S)[1])
    original_images = bundle.pop('images')
    original_cases = {c['episode_id']: c for c in bundle['cases']}
    bundle['cases'] = [original_cases[eid] for eid in eids]
    for c in bundle['cases']:
        c['initial_index'] = inputs[c['episode_id']]['checkpoint_step']
    bundle['tag'] = manifest['version'] + '_' + run.name
    scenes = {c['scene'] for c in bundle['cases']}
    bundle['maps'] = {k: v for k, v in bundle['maps'].items() if k in scenes}
    # v006 already committed its effective nodes. Raw sampling candidates are not playback nodes.
    del bundle['dedup']
    upstream = bundle['reviewVersions']['qwen_v006']
    upstream['cases'] = {eid: upstream['cases'][eid] for eid in eids}
    upstream['intervals'] = {eid: upstream['intervals'][eid] for eid in eids}
    bundle['reviewNodes'] = {eid: upstream['cases'][eid]['nodes'] for eid in eids}
    bundle['deviationReviews'] = deepcopy(upstream['intervals'])
    upstream['totals'] = dict(cases=len(eids), calls=sum(len(c['rounds']) for c in upstream['cases'].values()),
                              flagged=sum(bool(v) for v in upstream['intervals'].values()),
                              invalid=sum(r['outcome'] == 'format_error' for c in upstream['cases'].values() for r in c['rounds']))
    upstream['answersFile'] = 'v006_upstream_answers.json'
    archive = 'recovery_branch_review_v001_ten_offline.zip' if len(eids) == 10 else f'recovery_branch_review_v001_{len(eids)}_offline.zip'
    if args.deepseek_run:
        archive = f'recovery_qwen_deepseek_v006_{len(eids)}_offline.zip'
    if args.instruction_run:
        archive = f'recovery_instruction_v001_deepseek_{len(eids)}_offline.zip'
    if args.qwen_instruction_run:
        archive = f'recovery_instruction_v001_qwen_deepseek_{len(eids)}_offline.zip'
    upstream['archiveFile'] = archive
    bundle['reviewVersions'] = {'qwen_v006': upstream}
    bundle['defaultLayers'] = ['qwen_v006']
    bundle['defaultReview'] = 'qwen_v006'
    bundle['v4'] = dict(totals=upstream['totals'])
    # The exact seven inputs are shown by the new panel. Do not package all-node panoramic imagery.
    bundle.pop('nodeMultiview')
    records = {}
    for result in results:
        case = deepcopy(inputs[result['episode_id']])
        trans = translations[case['case_id']]
        answer = translated_answer(result['answer'], trans)
        for i, im in enumerate(case['images']):
            im['display'] = ('assets/mv70_' + im['sha256'] + '.webp') if i < 3 else original_images[im['sha256']]
            assert (SOURCE / im['display']).is_file()
        records[case['episode_id']] = dict(input=case, result=result, translation=answer)
    review = dict(cases=records, prompt_zh=manifest['prompt'], prompt_en=(SPEC / 'prompt_en.txt').read_text(),
                  schema=manifest['schema'], archive=archive, answers='branch_review_answers.json',
                  valid=sum(r['status'] == 'ok' for r in results),
                  identified=sum(r['answer']['previous_attempt']['status'] == 'identified' for r in results),
                  uncertain=sum(r['answer']['previous_attempt']['status'] == 'uncertain' for r in results))
    if args.deepseek_run:
        ds = read(args.deepseek_run / 'results.json')
        texts = read(args.deepseek_translations)
        assert {c['case_id'] for c in inputs.values()} <= set(ds).intersection(texts)
        for eid, case in inputs.items():
            cid = case['case_id']
            source = args.deepseek_run / cid
            assert read(source / 'input.json') == case
            meta = ds[cid]
            original = read(source / 'response.json')['choices'][0]['message']['content']
            assert meta['phase'] == 'complete' and json.loads(original) == meta['answer']
            records[eid]['deepseek'] = dict(result=dict(status='ok', answer=meta['answer'], raw_answer=original),
                                            translation=translated_answer(meta['answer'], texts[cid]))
    instruction_runs = [('instruction', args.instruction_run, args.instruction_translations),
                        ('qwenInstruction', args.qwen_instruction_run, args.qwen_instruction_translations)]
    for field, stage, translation_path in instruction_runs:
        if not stage:
            continue
        is_qwen = field == 'qwenInstruction'
        im = read(stage / 'manifest.json')
        assert im['settings']['model'] == (manifest['model'] if is_qwen else 'deepseek-flash')
        answers = {r['case_id']: r for r in read(stage / 'results.json')}
        lines_zh = read(translation_path)
        assert set(answers) == set(lines_zh) == {c['case_id'] for c in inputs.values()}
        review[field] = dict(model=im['settings']['model'], prompt_zh=im['prompt'],
            prompt_en=(stage / 'source/experiments/agent_recovery/branch_instruction_v001/prompt_en.txt').read_text())
        for item in im['cases']:
            cid, eid = item['case_id'], item['episode_id']
            first = inputs[eid]
            result = answers[cid]
            assert item['images'] == first['images'][:3] and item['node_id'] == first['node_id']
            first_dir = (run / 'cases' if is_qwen else args.deepseek_run) / cid
            assert item['first_response_sha256'] == sha(first_dir / 'response.json')
            inventory = (records[eid] if is_qwen else records[eid]['deepseek'])['result']['answer']
            assert item['context']['branches'] == [{k:b[k] for k in ('id','direction','entrance_description')} for b in inventory['branches']]
            assert item['context']['previous_attempt'] == {k:inventory['previous_attempt'][k] for k in ('status','branch_id')}
            if is_qwen:
                ds_ctx = records[eid]['instruction']['input']['context']
                assert all(item['context'][k] == ds_ctx[k] for k in ('instruction_en','Completed','Current'))
                assert im['prompt'] == review['instruction']['prompt_zh']
            assert result['status'] == 'ok'
            assert bool(lines_zh[cid]) == bool(result['answer']['recovery_instruction_en'])
            node_round = next(r for r in upstream['cases'][eid]['rounds'] if r['current_id'] == item['node_id'])
            assert node_round['instruction_en'] == item['context']['instruction_en']
            records[eid][field] = dict(input=item, result=result, instruction_zh=lines_zh[cid],
                                               task_zh=node_round['instruction_zh'])
    if args.comparison_run:
        comparison = args.comparison_run
        cm = read(comparison / 'manifest.json')
        translated = read(args.comparison_translations)
        by_episode = {c['episode_id']: c for c in cm['cases']}
        review['comparison'] = dict(prompt_zh=cm['prompt'], schema=cm['schema'],
            prompt_en=(comparison / 'source/experiments/agent_recovery/branch_review_v001.1/prompt_en.txt').read_text())
        for row in read(comparison / 'results.json'):
            eid = row['episode_id']
            assert inputs[eid] == by_episode[eid]
            localized = deepcopy(row['answer'])
            texts = translated[row['case_id']]
            def translate_fields(value):
                if isinstance(value, list):
                    for item in value:
                        translate_fields(item)
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key in {'description', 'reason', 'entrance_description', 'current_choice_basis'}:
                            value[key] = texts[item]
                        elif key == 'uncertainties':
                            value[key] = [texts[u] for u in item]
                        else:
                            translate_fields(item)
            translate_fields(localized)
            records[eid]['comparison'] = dict(result=row, translation=localized)
    bundle['branchReview'] = review
    wanted = set(strings(bundle))
    bundle['images'] = {key: value for key, value in original_images.items() if key in wanted}
    match = re.search(PATTERN, html, re.S)
    shell = recovery_playback(html[:match.start(1)] + html[match.end(1):], instruction=bool(args.instruction_run))
    match = re.search(PATTERN, shell, re.S)
    html = shell[:match.start(1)] + encoded(bundle).replace('</', '<\\/') + shell[match.end(1):]
    html, n = re.subn(r'<script id="node-multiview-ui">.*?</script>', '', html, flags=re.S)
    assert n == 1
    html = re.sub(r'<style id="node-multiview-style">.*?</style>', '', html, flags=re.S)
    html = html.replace('<section id="comparisonControls">', '<section id="branchReview"></section><section id="comparisonControls">', 1)
    html = html.replace('<section id="nodeMultiview" aria-label="节点多视角"></section><section id="v4Review"></section>',
                        '<section id="branchInputs"></section><details id="upstreamContext"><summary id="upstreamSummary"></summary><section id="v4Review"></section></details>', 1)
    html = html.replace('</head>', '<style id="branch-review-style">' + (ROOT / 'core/recovery_branch_review.css').read_text() + '</style></head>', 1)
    html = html.replace('</body>', '<script id="branch-review-ui">' + (ROOT / 'core/recovery_branch_review.js').read_text() + '</script></body>', 1)
    html, n = re.subn(r'<style id="embedded-font">.*?</style>', '', html, flags=re.S)
    assert n == 1
    out.mkdir(parents=True, exist_ok=False)
    (out / 'assets').mkdir()
    (out / 'index.html').write_text(html)
    font_provenance = add_font(out / 'index.html')
    html = (out / 'index.html').read_text().replace('font-family:OracleSans', 'font-family:CrossingSans')
    font = re.search(r'data:font/ttf;base64,([A-Za-z0-9+/=]+)', html)
    font_data = base64.b64decode(font[1])
    font_name = 'assets/' + hashlib.sha256(font_data).hexdigest() + '.ttf'
    (out / font_name).write_bytes(font_data)
    html = html[:font.start()] + font_name + html[font.end():]
    (out / 'index.html').write_text(html)
    (out / 'branch_review_answers.json').write_text(encoded(dict(manifest={k:v for k,v in manifest.items() if k!='service'}, display=review))+'\n')
    (out / upstream['answersFile']).write_text(encoded(upstream)+'\n')
    # Copy only assets actually referenced by this ten-case page.
    assets = {}
    referenced = set(re.findall(r'assets/[A-Za-z0-9_.-]+', html))
    for name in sorted(referenced):
        if not (out / name).exists():
            source = SOURCE / name
            assert source.is_file(), name
            os.link(source, out / name)
        assets[name] = sha(out / name)
    for name in ['branch_review_answers.json', upstream['answersFile']]:
        assets[name] = sha(out / name)
    provenance = dict(created_at=datetime.now(timezone.utc).isoformat(), source_html=str(SOURCE / 'index.html'),
                      source_html_sha256=sha(SOURCE / 'index.html'), run=str(run), manifest_sha256=sha(run / 'manifest.json'),
                      results_sha256=sha(run / 'results.json'), display_translations_sha256=sha(args.translations),
                      cases=[c['case_id'] for c in manifest['cases']], input_images=total_images,
                      display_images='same-frame WebP copies; original input PNG paths and SHA256 retained',
                      font=font_provenance, source_sha256={})
    translation_paths = [p for p in (args.translations, args.comparison_translations, args.deepseek_translations, args.instruction_translations, args.qwen_instruction_translations) if p]
    for path in [Path(__file__), ROOT / 'core/recovery_playback_nodes.js', ROOT / 'core/recovery_branch_review.js', ROOT / 'core/recovery_branch_review.css', *translation_paths]:
        dest = out / 'source_snapshot' / (path.resolve().relative_to(ROOT) if ROOT in path.resolve().parents else Path(path.name))
        dest.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy2(path, dest)
        provenance['source_sha256'][str(path)] = sha(path)
    if args.comparison_run:
        provenance['comparison_results_sha256'] = sha(args.comparison_run / 'results.json')
    if args.deepseek_run:
        provenance['deepseek_results_sha256'] = sha(args.deepseek_run / 'results.json')
    if args.instruction_run:
        provenance['instruction_results_sha256'] = sha(args.instruction_run / 'results.json')
        provenance['instruction_image_slots'] = 3 * len(eids)
        provenance['instruction_run'] = str(args.instruction_run)
    if args.qwen_instruction_run:
        provenance['qwen_instruction_run'] = str(args.qwen_instruction_run)
        provenance['qwen_instruction_results_sha256'] = sha(args.qwen_instruction_run / 'results.json')
    provenance['html_sha256'] = sha(out / 'index.html')
    (out / 'export.json').write_text(encoded(provenance)+'\n')
    with zipfile.ZipFile(out / archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=4) as package:
        package.write(out / 'index.html', 'index.html')
        for name in assets:
            package.write(out / name, name)
        package.write(out / 'export.json', 'provenance/export.json')
        public_keys = ('version','upstream_version','model','seed','generation','prompt','schema','git_head','cases','reused_case_ids','without_v006_rollback')
        package.writestr('provenance/manifest.json', encoded({k: manifest[k] for k in public_keys if k in manifest}))
        for case in manifest['cases']:
            package.write(run / 'cases' / case['case_id'] / 'response.json', 'raw/' + case['case_id'] + '.response.json')
            if args.deepseek_run:
                cid = case['case_id']
                package.write(args.deepseek_run / cid / 'response.json', 'raw/deepseek/' + cid + '.response.json')
            if args.instruction_run:
                prefix = 'raw/instruction/deepseek/' if args.qwen_instruction_run else 'raw/instruction/'
                package.write(args.instruction_run / 'cases' / cid / 'response.json', prefix + cid + '.response.json')
            if args.qwen_instruction_run:
                package.write(args.qwen_instruction_run / 'cases' / cid / 'response.json', 'raw/instruction/qwen/' + cid + '.response.json')
        if args.comparison_run:
            for case in cm['cases']:
                cid = case['case_id']
                package.write(args.comparison_run / 'cases' / cid / 'response.json', 'raw/v1.1/' + cid + '.response.json')
        package.write(out / 'FONT_LICENSE.txt', 'FONT_LICENSE.txt')
        description = ('第二次调用的三图、任务进度、替代支路与局部指令，以及第一次调用的七图和原答。\n'
                       'Three views, task progress, alternative branch and local instruction for call two; seven views and original answers for call one.\n'
                       if args.instruction_run else '第一次支路识别的七图和完整原答。\nSeven inputs and original first-call answers.\n')
        package.writestr('README.txt', '解压后打开 index.html / Extract and open index.html.\n' + description)
    assets[archive] = sha(out / archive)
    (out / 'online_manifest.json').write_text(encoded(dict(html='index.html', assets=assets))+'\n')
    print(encoded(dict(html=str(out / 'index.html'), assets=len(assets), cases=len(eids), images=total_images,
                       archive_bytes=(out / archive).stat().st_size)))


if __name__ == '__main__':
    main()
