"""Combine archived v003/v005 reviews without rerunning or revalidating models."""
from collections import Counter
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'outputs/visualization_publishing/qwen_v005_all53_web_20261120_01'
OUT = ROOT/'outputs/visualization_publishing/deviation_four_versions_web_20261120_01'
Q3 = ROOT/'outputs/deviation_progress/v003/run_20261118_01_qwen27b'
D3 = ROOT/'outputs/deviation_progress/v003/run_20261118_03_deepseek29'
Q5 = ROOT/'outputs/deviation_progress/v005/all53_20261120_01'
D5 = ROOT/'outputs/deviation_progress/v005/run_20261120_06_deepseek_official33'
ARCHIVE = 'vln_v003_v005_four_versions_offline.zip'
UI = ROOT/'core/deviation_four_versions.js'


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def error_text(error):
    if not error:
        return None
    messages = {
        'ValueError: Instruction quote is not an exact supplied excerpt': '英文引文不是原始指令中的连续逐字片段。',
        'ValueError: Invalid uncertainties': 'uncertainties 字段的结构不符合输出要求。',
        "ValueError: Unexpected/missing answer fields: ['mode']": '原答多返回了顶层字段 mode。',
        "ValueError: Unexpected/missing answer fields: ['current_id', 'previous_id']": '原答缺少 current_id 和 previous_id 顶层字段。',
        'ValueError: Missing or unordered zh progress headings': '中文累计进度的标题缺失或顺序不符合要求。',
    }
    if error.startswith('JSONDecodeError:'):
        zh = '原答不是合法 JSON，无法解析；具体解析错误：缺少逗号分隔符。'
    else:
        zh = messages[error]
    return dict(zh=zh, en=error)


def collect(key, label, color, run, folders, anchors, replay):
    groups, rows, digests = {}, [], {}
    v3 = key.endswith('v003')
    prompt_dir = (run/'source/experiments/deviation_progress/v003/run_20261112_05/snapshot/run'
                  if v3 else run/'source/experiments/deviation_progress/v005')
    zh = (prompt_dir/'prompt_zh.txt').read_text()
    en_path = prompt_dir/'prompt_en.txt'
    if not en_path.exists():
        en_path = ROOT/'experiments/deviation_progress/v003/run_20261112_05/snapshot/run/prompt_en.txt'
    prompts = dict(prompt_zh=zh, prompt_en=en_path.read_text())
    model = 'deepseek-flash' if key.startswith('deepseek') else 'route53-qwen27b'
    for number, folder in sorted(folders.items()):
        result = read(folder/'result.json')
        eid = result['episode_id']
        assert result['case_number'] == number and eid in replay
        assert result['stop_reason'] in ('first_deviation', 'all_nodes_reviewed')
        case = replay[eid]
        rounds = []
        for item in result['reviews']:
            node = item['node_id']; stem = folder/node
            request_file, response_file = stem.with_suffix('.request.json'), stem.with_suffix('.response.json')
            req, resp = read(request_file), read(response_file)
            assert req['instruction_en'] == case['instruction_en'] and req['prompt_sha256'] == sha(zh.encode())
            raw = resp['response']['choices'][0]['message']['content']
            answer = resp.get('parsed_original')
            assert resp['status'] == item['status']
            outcome = item['answer']['verdict'] if item['status'] == 'ok' else 'format_error'
            imgs = []
            for im in req['images']:
                original = im['sha256']
                assert original == im['image_id'] == case['frames'][im['frame']]['image']
                display = IMAGE_FILES[original]
                imgs.append(dict(frame=im['frame'],role=im['role'],sha256=original,
                                 file=display, display_sha256=Path(display).stem,
                                 original_path=im['path'],representation='same-frame WebP display copy'))
            endpoint = 'local' if key.startswith('qwen') else 'https://api.deepseek.com'
            if key == 'deepseek_v005':
                provenance = stem.with_suffix('.provenance.json')
                endpoint = read(provenance)['endpoint'] if provenance.exists() else 'https://ai.dijinlong.com/v1'
            row = dict(model=model, version=key.split('_')[-1], case_id=f'C{number:02d}',episode_id=eid,
                       current_id=node,previous_id=req['previous_id'],from_frame=req['previous_frame'],
                       to_frame=req['current_frame'],mode=req['mode'],available_at_frame=item['available_at_frame'],
                       terminal_node=item['terminal_node'],instruction_zh=case['instruction_zh'],instruction_en=req['instruction_en'],
                       images=imgs,prior_progress=item['prior_progress'],outcome=outcome,validation_status=item['status'],
                       validation_error=error_text(resp.get('error')),answer=answer,raw_answer=raw,
                       raw_answer_sha256=sha(raw.encode()),committed_progress=item['committed_progress'],
                       progress_anchor=item['progress_anchor'],rollback_target=item.get('rollback_target'),endpoint=endpoint)
            assert req['prior_semantic_progress'] == row['prior_progress']['zh']
            rows.append(row); rounds.append(row)
            digests[f'C{number:02d}/{node}'] = dict(request=sha(request_file.read_bytes()), response=sha(response_file.read_bytes()))
        groups[eid] = dict(case_id=f'C{number:02d}',nodes=anchors[eid],rounds=rounds)
    counts = Counter(r['outcome'] for r in rows)
    intervals = {eid:[dict(from_frame=r['from_frame'],to_frame=r['to_frame']) for r in group['rounds'] if r['outcome']=='deviated']
                 for eid,group in groups.items()}
    review = dict(modelId=key,modelName=label.split()[0],version=key.split('_')[-1],label=label,color=color,
                  cases=groups,intervals=intervals,totals=dict(cases=len(groups),calls=len(rows),flagged=counts['deviated'],
                    invalid=counts['format_error'],nodes=sum(len(g['nodes']) for g in groups.values())),
                  archiveFile=ARCHIVE,answersFile=f'compare4_{key}_model_returns.json',**prompts)
    return review, rows, digests


def main():
    global IMAGE_FILES
    OUT.mkdir(parents=True, exist_ok=False)
    html = (SOURCE/'index.html').read_text()
    match = re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
    bundle = json.loads(match[1]); replay = {c['episode_id']:c for c in bundle['cases']}
    IMAGE_FILES = bundle['images']
    anchors = read(Q3/'retained_nodes_and_terminals.json')
    q5_sources = {int(k[1:]):Path(v) for k,v in read(Q5/'case_sources.json').items()}
    specs = [
        ('qwen_v003','Qwen v003','#2563eb',Q3,{i:Q3/f'deviation/run/cases/C{i:02d}' for i in range(1,54)}),
        ('deepseek_v003','DeepSeek v003','#9333ea',D3,{i:D3/f'deviation/run/cases/C{i:02d}' for i in range(1,30)}),
        ('qwen_v005','Qwen v005','#c87500',Q5,q5_sources),
        ('deepseek_v005','DeepSeek v005','#00866b',D5,{i:D5/f'run/cases/C{i:02d}' for i in range(1,54)}),
    ]
    versions, all_rows, proofs = {}, {}, {}
    for key, label, color, run, folders in specs:
        review, rows, digests = collect(key,label,color,run,folders,anchors,replay)
        versions[key] = review; all_rows[key] = rows; proofs[key] = digests
        print(key, encoded(review['totals']), flush=True)
    bundle['reviewVersions'] = versions
    bundle['reviewNodes'] = {eid:anchors[eid] for eid in replay}
    bundle['v4'] = dict(totals=versions['deepseek_v005']['totals'])
    bundle['deviationReviews'] = {}
    bundle['tag'] = 'deviation_four_versions_20261120_01'
    bundle['dedup']['source_tag'] = bundle['tag']
    html = html[:match.start(1)] + encoded(bundle).replace('</','<\\/') + html[match.end(1):]
    start=html.index('const deviationOverlay = (() => {'); end=html.index('L.zh.effectiveCount',start)
    html=html[:start]+"const deviationOverlay={drawMap:a=>window.MultiDeviation?.drawMap(a),drawBands:a=>window.MultiDeviation?.drawBands(a)};\n"+html[end:]
    html=html.replace('B.v4.cases[c().episode_id].nodes.find','B.reviewNodes[c().episode_id].find')
    html=html.replace('<p id="caseStats"></p>','<p id="caseStats"></p><section id="comparisonControls"></section>')
    html=html.replace('<div class="controls"><button id="restart"','<div id="comparisonTracks"></div><div class="controls"><button id="restart"')
    old_start=html.index('<script>/* Round details for the frozen Route53 replay.')
    old_end=html.index('</script>',old_start)+len('</script>')
    html=html[:old_start]+'<script>'+UI.read_text()+'</script>'+html[old_end:]
    html=html.replace("['effectiveCount',B.v4.totals.nodes]","['v4coverage',B.v4.totals.cases]")
    html,n=re.subn(r'<style id="embedded-font">.*?</style>','',html,flags=re.S)
    assert n==1
    (OUT/'index.html').write_text(html)
    from export_oracle_distance_replay import add_font
    add_font(OUT/'index.html')
    html=(OUT/'index.html').read_text().replace('font-family:OracleSans','font-family:CrossingSans')
    font=re.search(r'data:font/ttf;base64,([A-Za-z0-9+/=]+)',html)
    font_data=base64.b64decode(font[1]); font_name='assets/'+sha(font_data)+'.ttf'
    (OUT/'assets').mkdir(); (OUT/font_name).write_bytes(font_data)
    html=html[:font.start()]+font_name+html[font.end():]
    (OUT/'index.html').write_text(html)
    assets={}; required=set(IMAGE_FILES.values())
    required.update(re.findall(r'assets/[a-f0-9]+\.(?:ttf|woff2?)',html))
    source_manifest=read(SOURCE/'online_manifest.json')
    for name in sorted(required):
        if name==font_name:
            assets[name]=sha(font_data)
        else:
            os.link(SOURCE/name,OUT/name)
            assets[name]=source_manifest['assets'][name]
    for key, rows in all_rows.items():
        name=versions[key]['answersFile']; data=encoded(rows).encode()
        (OUT/name).write_bytes(data); assets[name]=sha(data)
    # Use the already compact archive for media, avoiding thousands of NAS image reads.
    media_zip=ROOT/'outputs/visualization_publishing/qwen_v005_all53_compact_download_20261120_01/qwen_v005_all_53_compact_offline.zip'
    with tempfile.TemporaryDirectory(prefix='vln-four-versions-',dir='/tmp') as scratch:
        archive=Path(scratch)/ARCHIVE
        with zipfile.ZipFile(media_zip) as old, zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as new:
            new.writestr('index.html',html)
            for name in sorted(required): new.writestr(name,font_data if name==font_name else old.read(name))
            new.writestr('FONT_LICENSE.txt',old.read('FONT_LICENSE.txt'))
            for key,rows in all_rows.items():
                new.writestr(versions[key]['answersFile'],encoded(rows))
                new.writestr(key+'/all_rounds.jsonl',''.join(encoded(r)+'\n' for r in rows))
                for r in rows: new.writestr(f"{key}/raw_answers/{r['case_id']}/{r['current_id']}.txt",r['raw_answer'])
                for lang in ('zh','en'): new.writestr(f'{key}/prompts/prompt_{lang}.txt',versions[key]['prompt_'+lang])
            new.writestr('README.txt','解压整个压缩包后打开 index.html。四版本可勾选零至三组偏航区间。DeepSeek v003 仅评审 C01–C29。格式失败原答不计入有效报警。图片为同帧同分辨率 WebP 展示副本，逐轮 JSON 保留原始输入 PNG 哈希。\nExtract the whole archive and open index.html. Select zero to three of four deviation layers. DeepSeek v003 covers C01–C29 only. Invalid answers do not count as accepted alarms. Images are same-frame, same-resolution WebP display copies; round JSON retains original PNG hashes.\n')
        shutil.copy2(archive,OUT/ARCHIVE)
    assets[ARCHIVE]=sha((OUT/ARCHIVE).read_bytes())
    (OUT/'online_manifest.json').write_text(encoded(dict(html='index.html',assets=assets)))
    (OUT/'export.json').write_text(encoded(dict(versions={k:v['totals'] for k,v in versions.items()},
        source_html_sha256=sha((SOURCE/'index.html').read_bytes()),html_sha256=sha(html.encode()),
        archive_bytes=(OUT/ARCHIVE).stat().st_size,archive_sha256=assets[ARCHIVE],media_assets=len(required),
        source_hashes=proofs,exporter_sha256=sha(Path(__file__).read_bytes()),ui_sha256=sha(UI.read_bytes()))))
    print(encoded(dict(output=str(OUT),archive_bytes=(OUT/ARCHIVE).stat().st_size,media_assets=len(required))),flush=True)


if __name__=='__main__':
    main()
