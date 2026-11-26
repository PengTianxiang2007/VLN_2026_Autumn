"""Add the completed Terra reviews and two Astra branches to the 43-case replay."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
RUNS = ROOT / 'outputs/codex_tasks/deviation_progress/codex_memory_v002'
TERRA = RUNS / HERE.parents[1].name
OUT = TERRA / 'exports' / HERE.name
OLD = RUNS / 'run_20261125_09_gap6_remaining34/exports/combined43_01/index.html'
PUBLIC = ROOT / 'outputs/visualization_publishing/codex_deviation_v002_astra_terra_web_20261126_01'
BASE = HERE.parents[2] / 'run_20261125_01_terminal4/exports/map_layers_01/export.py'
spec = importlib.util.spec_from_file_location('map_replay', BASE)
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)
read = replay.read


def terra_cases(cases):
    dataset = ROOT / read(TERRA / 'input.json')['image_root']
    def build(path):
        result = read(path)
        cid = 'C%02d' % result['case_number']
        base = cases[cid]
        item = dict(case_id=cid, frames=base['frames'][:-1], instruction_en=base['instruction_en'],
                    instruction_zh=base['instruction_zh'])
        replay.prepare_case(result, item, dataset, TERRA)
        assert item['frames'][-1] == base['frames'][-1] and result['episode_id'] == base['episode_id']
        for key in ('frames','instruction_en','instruction_zh','referenceErrors','original_success'):
            item.pop(key)
        return item
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(build, sorted(TERRA.glob('cases/*/result.json'))))


def update_astra(cases):
    c = cases['C01']
    branch = RUNS / 'run_20261125_03_c01_s04'
    result = read(branch / 'result.json')
    directory = next(branch.glob('codex/turns/*'))
    answer = result['answer']
    zh = read(next((OUT / 'display_translation').glob('turns/*/final.txt')))
    sample = next(n for n in c['samples'] if n['id'] == 'S04')
    assert sample['index'] == 38 and result['action'] == 'append_current' and c['samples'][-1] == sample
    sample.update(action=result['action'], active=['S04'])
    branches = [zh['branch1'], zh['branch2']]
    translated = dict(answer, b_only=branches, reason=zh['reason'], eligibility_reason=zh['eligibility_reason'])
    c.update(effective=[sample], terminalReviewed=False, alarm=None, group='partial', rounds=[], initial_index=38,
             checkpointReview=dict(frames=sample['imageFrames'],
                en=dict(prompt=(directory/'prompt.txt').read_text(), raw=(directory/'final.txt').read_text(),
                        reason=answer['reason'], eligibility_reason=answer['eligibility_reason'], branches=answer['b_only']),
                zh=dict(prompt=zh['prompt'], raw=json.dumps(translated,ensure_ascii=False,indent=2),
                        reason=zh['reason'], eligibility_reason=zh['eligibility_reason'], branches=branches)))
    c = cases['C27']
    branch = RUNS / 'run_20261125_04_c27_interval7'
    r = c['rounds'][-1]
    directory = next(branch.glob('uniform7/turns/*'))
    en = (directory/'prompt.txt').read_text()
    refs = json.loads(re.search(r'grouped by actual frame: (\{[^\n]*\})',en)[1])
    added = read(branch/'protocol.json')['frames']
    req = read(directory/'request.json')
    assert [im['sha256'] for im in req['images']] == [c['frames'][f]['image'] for f in added]
    raw = (directory/'final.txt').read_text()
    ans = json.loads(raw)
    assert ans['verdict'] == 'deviated' and (r['a'],r['b']) == (7,42)
    zh = re.sub(r'会话中已经提供的图像按实际帧号分组如下：[^\n]*', lambda _:
                '本轮可使用的图像按实际帧号分组如下：' + json.dumps(refs,ensure_ascii=False) + '。',r['prompts'][0])
    zh = zh.replace('使用本会话中已经提供的视觉观测。','使用本会话中已经提供的视觉观测和本轮随附的编号图像。')
    r.update(answer=ans, raw=raw, refs=refs, added=added, prompts=[zh,en], uniform7=True)
    c.update(alarm=ans['previous_id'], group='alarmed')


def stats(cases):
    return dict(candidates=sum(len(c['samples']) for c in cases),
                reviews=sum(len(c['rounds']) for c in cases), alarms=sum(bool(c['alarm']) for c in cases))


def main():
    html = OLD.read_text()
    pattern = re.compile(r'(<script id="payload" type="application/json">)(.*?)(</script>)',re.S)
    match = pattern.search(html)
    bundle = json.loads(match[2])
    cases = {c['case_id']:c for c in bundle['cases']}
    terra = terra_cases(cases)
    assert len(cases)==43 and set(cases)-{c['case_id'] for c in terra}=={'C02','C15','C31','C39'} and len(terra)==39
    update_astra(cases)
    bundle['terra'] = terra
    bundle['summary'] = stats(bundle['cases'])
    bundle['modelStats'] = dict(astra=bundle['summary'], terra=stats(terra))
    html = html[:match.start(2)]+json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+html[match.end(2):]
    html = re.sub(r'<style id="embedded-font">.*?</style>','',html,flags=re.S)
    html = html.replace('<h2 data-i18n="cases">','<label for="reviewModel" data-i18n="modelLabel"></label>'
        '<select id="reviewModel"><option value="astra">GPT-6 Astra · medium (43)</option>'
        '<option value="terra">GPT-6.1 Terra · xhigh (39)</option></select><h2 data-i18n="cases">',1)
    html = html.replace('<option value="initOnly" data-i18n="initOnly"></option>',
        '<option value="initOnly" data-i18n="initOnly"></option><option value="partial" data-i18n="partial"></option>',1)
    html = html.replace('function caseSummary(v){','''function caseSummary(v){
  if(v.checkpointReview)return localText('S04 · F38 已建点，本分支只复判此候选','S04 · F38 retained; this branch reassessed this candidate only');''')
    html = html.replace('  const v=c(), i=selectedRound.get(ci)', '''  if(c().checkpointReview)return checkpointPanel(root,c());
  const v=c(), i=selectedRound.get(ci)''')
    html = html.replace("    const picker=make('div',undefined,'reviewPicks');","""    if(r.uniform7)root.append(make('p',localText('终止段复判 · 均匀补入七张前视图。报警后记录回退目标 S02（F7）。','Reassessed terminal segment · Seven evenly spaced front views were added. The alarm identifies S02 (F7) as the rollback target.')));
    const picker=make('div',undefined,'reviewPicks');""")
    html = html.replace('createVersionControls();\nfor(const id', (HERE/'models.js').read_text()+'\ncreateVersionControls();\nfor(const id',1)
    html = html.replace('setupTerminalReplay();\n</script>',"""setupTerminalReplay();
$('reviewModel').onchange = () => setModel($('reviewModel').value);
setModel('astra');
</script>""",1)
    out = OUT / 'index.html'
    out.write_text(html)
    del html, match
    replay.add_font(out)
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/prepare_online_visualization.py'),
                    '--html',str(out),'--destination',str(PUBLIC)],check=True)
    entry = PUBLIC/'index.html'
    online = entry.read_text()
    assert '<button id="export"' in online
    entry.write_text(online.replace('<button id="export"', '<a href="replay.zip" download data-i18n="download">下载离线回放</a> <button id="export"',1))
    with zipfile.ZipFile(PUBLIC/'replay.zip','w',zipfile.ZIP_DEFLATED,compresslevel=2) as archive:
        for path in (out,OUT/'FONT_LICENSE.txt'):
            archive.write(path,path.name)
    print(bundle['modelStats'],flush=True)


if __name__ == '__main__':
    main()
