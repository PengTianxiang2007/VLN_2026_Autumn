"""Add the already exported v006 answers to the frozen v003/v005 comparison."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
from export_oracle_distance_replay import add_font

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'outputs/visualization_publishing/deviation_four_versions_web_20261120_02'
V6=ROOT/'outputs/visualization_publishing/qwen_v006_all53_web_20261121_01'
OUT=ROOT/'outputs/visualization_publishing/deviation_five_versions_web_20261121_01'
UI=ROOT/'core/deviation_four_versions.js'
ARCHIVE='vln_v003_v005_v006_five_versions_offline.zip'
PATTERN=r'<script id="payload" type="application/json">(.*?)</script>'


def read(path):return json.loads(path.read_text())
def encoded(data):return json.dumps(data,ensure_ascii=False,separators=(',',':'))
def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    html=(SOURCE/'index.html').read_text();match=re.search(PATTERN,html,re.S)
    bundle=json.loads(match[1]);v6=json.loads(re.search(PATTERN,(V6/'index.html').read_text(),re.S)[1])
    assert bundle['cases']==v6['cases'] and bundle['images']==v6['images']
    versions=bundle['reviewVersions'];review=v6['v4']
    review.pop('originals',None)
    review.update(modelId='qwen_v006',label='Qwen v006',color='#c02b59',intervals=v6['deviationReviews'])
    for eid,g in review['cases'].items():
        assert g['nodes']==bundle['reviewNodes'][eid]
        for row in g['rounds']:
            row['endpoint']='local';row['version']='v006'
    versions['qwen_v006']=review
    bundle['defaultLayers']=['qwen_v005','deepseek_v005','qwen_v006']
    bundle['defaultReview']='qwen_v006'
    bundle['tag']=bundle['dedup']['source_tag']='deviation_five_versions_20261121_01'
    bundle['v4']=dict(totals=review['totals'])
    all_rows={}
    for key,version in versions.items():
        version['archiveFile']=ARCHIVE;version['answersFile']=f'compare5_{key}_model_returns.json'
        all_rows[key]=[r for g in version['cases'].values() for r in g['rounds']]
    assert sum(len(rows) for rows in all_rows.values())==1131
    html=html[:match.start(1)]+encoded(bundle).replace('</','<\\/')+html[match.end(1):]
    start=html.index('<script>/* Four archived review versions;')
    end=html.index('</script>',start)+len('</script>')
    html=html[:start]+'<script>'+UI.read_text()+'</script>'+html[end:]
    html,n=re.subn(r'<style id="embedded-font">.*?</style>','',html,flags=re.S);assert n==1
    OUT.mkdir(parents=True,exist_ok=False);(OUT/'assets').mkdir()
    (OUT/'index.html').write_text(html);add_font(OUT/'index.html')
    html=(OUT/'index.html').read_text().replace('font-family:OracleSans','font-family:CrossingSans')
    font=re.search(r'data:font/ttf;base64,([A-Za-z0-9+/=]+)',html)
    font_data=base64.b64decode(font[1]);font_name='assets/'+sha(font_data)+'.ttf'
    html=html[:font.start()]+font_name+html[font.end():]
    (OUT/'index.html').write_text(html);(OUT/font_name).write_bytes(font_data)
    source_assets=read(SOURCE/'online_manifest.json')['assets']
    required=set(bundle['images'].values())|{font_name};assets={}
    for name in sorted(required):
        if name==font_name:assets[name]=sha(font_data)
        else:os.link(SOURCE/name,OUT/name);assets[name]=source_assets[name]
    for key,rows in all_rows.items():
        name=versions[key]['answersFile'];data=encoded(rows).encode()
        (OUT/name).write_bytes(data);assets[name]=sha(data)
    # Read existing media from a single archive, avoiding thousands of NAS reads.
    old_archive=SOURCE/'vln_v003_v005_four_versions_offline_02.zip'
    with tempfile.TemporaryDirectory(prefix='vln-five-versions-',dir='/tmp') as scratch:
        archive=Path(scratch)/ARCHIVE
        with zipfile.ZipFile(old_archive) as old,zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=4) as new:
            new.writestr('index.html',html)
            for name in sorted(required):new.writestr(name,font_data if name==font_name else old.read(name))
            new.writestr('FONT_LICENSE.txt',old.read('FONT_LICENSE.txt'))
            for key,rows in all_rows.items():
                new.writestr(versions[key]['answersFile'],encoded(rows))
                new.writestr(key+'/all_rounds.jsonl',''.join(encoded(r)+'\n' for r in rows))
                for row in rows:
                    assert sha(row['raw_answer'].encode())==row['raw_answer_sha256']
                    new.writestr(f"{key}/raw_answers/{row['case_id']}/{row['current_id']}.txt",row['raw_answer'])
                for lang in ('zh','en'):new.writestr(f'{key}/prompts/prompt_{lang}.txt',versions[key]['prompt_'+lang])
            new.writestr('README.txt','解压后打开 index.html。五组选零至三组偏航区间。DeepSeek v003 仅覆盖 C01–C29。原答与格式失败完整保留。图片为同帧同分辨率 WebP 展示副本，原始输入 PNG 哈希保留。\nExtract and open index.html. Select zero to three of five deviation layers. DeepSeek v003 covers C01–C29 only. All raw answers and validation failures are retained. Images are same-frame, same-resolution WebP display copies; original input PNG hashes are preserved.\n')
        assets[ARCHIVE]=sha(archive.read_bytes());shutil.copy2(archive,OUT/ARCHIVE)
    (OUT/'online_manifest.json').write_text(encoded(dict(html='index.html',assets=assets)))
    record=dict(versions={k:v['totals'] for k,v in versions.items()},rounds=sum(map(len,all_rows.values())),
                html_sha256=sha(html.encode()),archive_bytes=(OUT/ARCHIVE).stat().st_size,archive_sha256=assets[ARCHIVE],
                source_html_sha256=sha((SOURCE/'index.html').read_bytes()),v6_html_sha256=sha((V6/'index.html').read_bytes()),
                git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                exporter_sha256=sha(Path(__file__).read_bytes()),ui_sha256=sha(UI.read_bytes()))
    (OUT/'export.json').write_text(encoded(record));print(encoded(record),flush=True)


if __name__=='__main__':main()
