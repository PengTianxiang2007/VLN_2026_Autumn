"""Finish the already generated media package after correcting relative image paths."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[5]
SNAPSHOT=ROOT/'outputs/deviation_progress/v006/all53_20261121_01'
OUT=SNAPSHOT/'exports/web_all53_20261121_01'
ONLINE=ROOT/'outputs/visualization_publishing/qwen_v006_all53_web_20261121_01'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    html=(ONLINE/'index.html').read_text()
    match=re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)
    bundle=json.loads(match[1]);review=bundle['v4']
    rows=[r for group in review['cases'].values() for r in group['rounds']]
    replacements={}
    for row in rows:
        for im in row['images']:
            new='assets/'+im['display_sha256']+'.webp'
            replacements[im['file']]=new
            replacements['front/'+im['sha256']+'.webp']=new
            im['file']=new
    # Only path metadata changes; raw model responses and rendering remain identical.
    for folder in (ONLINE,OUT):
        page=(folder/'index.html').read_text()
        page=re.sub(r'"file":"([^"]+)"',lambda m:'"file":'+json.dumps(replacements.get(m[1],m[1])),page)
        (folder/'index.html').write_text(page)
    manifest=json.loads((ONLINE/'online_manifest.json').read_text());assets=manifest['assets']
    for row in rows:
        for im in row['images']:
            assert assets[im['file']]==im['display_sha256']
    answers=review['answersFile'];name=review['archiveFile']
    (ONLINE/answers).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    assets[answers]=digest(ONLINE/answers)
    with zipfile.ZipFile(ONLINE/name,'x',zipfile.ZIP_DEFLATED,compresslevel=4) as archive:
        for relative in [manifest['html'],*sorted(assets)]:
            archive.write(ONLINE/relative,relative)
        archive.write(OUT/'FONT_LICENSE.txt','FONT_LICENSE.txt')
        archive.writestr('all_rounds.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
        for row in rows:
            assert hashlib.sha256(row['raw_answer'].encode()).hexdigest()==row['raw_answer_sha256']
            archive.writestr(f"raw_answers/{row['case_id']}/{row['current_id']}.txt",row['raw_answer'].encode())
        for lang in ('zh','en'):
            archive.writestr(f'prompts/prompt_{lang}.txt',review['prompt_'+lang])
    assets[name]=digest(ONLINE/name)
    manifest['source_sha256']=digest(OUT/'index.html')
    (ONLINE/'online_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    record=dict(totals=review['totals'],source_snapshot=str(SNAPSHOT),online_sha256=digest(ONLINE/'index.html'),
                offline_sha256=digest(OUT/'index.html'),archive_sha256=assets[name],archive_bytes=(ONLINE/name).stat().st_size,
                online_files=len(assets)+1,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in
                  (Path(__file__),ROOT/'scripts/export_deviation_progress_v004_replay.py',ROOT/'core/deviation_progress_v004_review.js')})
    (OUT/'export.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(record,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
