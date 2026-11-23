"""Add newly captured ±70-degree views to the archived node viewer."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from PIL import Image
from export_deviation_node_multiview import encoded, read, sha
from export_oracle_distance_replay import add_font

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'outputs/visualization_publishing/v006_node_multiview_web_20261121_01'
CAPTURE = ROOT/'outputs/multiview_capture/v006_pose70/run_20261121_01'
OUT = ROOT/'outputs/visualization_publishing/v006_node_multiview70_web_20261121_01'
ARCHIVE = 'v006_node_multiview70_offline.zip'
PATTERN = r'<script id="payload" type="application/json">(.*?)</script>'


def main():
    assert read(CAPTURE/'status.json')['phase'] == 'complete'
    html = (SOURCE/'index.html').read_text()
    source_hash = sha(html.encode())
    match = re.search(PATTERN, html, re.S)
    bundle = json.loads(match[1])
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT/'assets').mkdir()
    assets = {name:digest for name,digest in read(SOURCE/'online_manifest.json')['assets'].items()
              if not name.endswith('.zip')}
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda name:os.link(SOURCE/name,OUT/name),assets))
    jobs, records = [], {}
    count = 0
    for eid, group in bundle['nodeMultiview']['cases'].items():
        for node in group['nodes']:
            if node['terminal_node']:
                continue
            key = f"{group['case_id']}_{node['id']}_F{node['index']:04d}"
            folder = CAPTURE/'points'/key
            raw = (folder/'metadata.json').read_bytes()
            record = json.loads(raw)
            assert (record['episode_id'],record['node_id'],record['frame']) == (eid,node['id'],node['index'])
            assert record['reference_front']['sha256'] == node['front_sha256']
            assert record['robot']['position_world_m'] == node['position']
            assert [v['offset_deg'] for v in record['views']] == [70,0,-70]
            node['views70'] = {}
            for direction, view in zip((1,0,7),record['views']):
                name = 'assets/mv70_'+view['sha256']+'.webp'
                node['views70'][str(direction)] = dict(image=name,yaw=view['offset_deg'],source_sha256=view['sha256'])
                jobs.append((folder/view['file'],view['sha256'],name))
            records[key] = sha(raw)
            count += 1
    assert count == 376 and len(jobs) == 1128

    def convert(job):
        source, expected, name = job
        raw = source.read_bytes()
        assert sha(raw) == expected
        with Image.open(io.BytesIO(raw)) as im:
            assert im.size == (640,480)
            buf = io.BytesIO()
            im.convert('RGB').save(buf,format='WEBP',quality=85,method=4)
        data = buf.getvalue()
        (OUT/name).write_bytes(data)
        return name,sha(data)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for number,(name,digest) in enumerate(pool.map(convert,jobs),1):
            assets[name] = digest
            if number % 256 == 0:
                print('New views',number,'/ 1128',flush=True)
    for version in bundle['reviewVersions'].values():
        version['archiveFile'] = ARCHIVE
    html = html[:match.start(1)]+encoded(bundle).replace('</','<\\/')+html[match.end(1):]
    for tag, identifier, file in [('script','node-multiview-ui','deviation_node_multiview.js'),
                                   ('style','node-multiview-style','deviation_node_multiview.css')]:
        replacement = f'<{tag} id="{identifier}">'+(ROOT/'core'/file).read_text()+f'</{tag}>'
        html, n = re.subn(f'<{tag} id="{identifier}">.*?</{tag}>',lambda _:replacement,html,flags=re.S)
        assert n == 1
    html,n = re.subn(r'<style id="embedded-font">.*?</style>','',html,flags=re.S)
    assert n == 1
    (OUT/'index.html').write_text(html)
    add_font(OUT/'index.html')
    html = (OUT/'index.html').read_text().replace('font-family:OracleSans','font-family:CrossingSans')
    font = re.search(r'data:font/ttf;base64,([A-Za-z0-9+/=]+)',html)
    data = base64.b64decode(font[1])
    name = 'assets/'+sha(data)+'.ttf'
    html = html[:font.start()]+name+html[font.end():]
    (OUT/'index.html').write_text(html)
    (OUT/name).write_bytes(data)
    assets[name] = sha(data)
    record = dict(created_at=datetime.now(timezone.utc).isoformat(),nodes=count,images=len(jobs),
        source_html_sha256=source_hash,html_sha256=sha(html.encode()),capture=str(CAPTURE.relative_to(ROOT)),
        capture_metadata_sha256=records,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        worktree=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),source_sha256={})
    snapshot = OUT/'source_snapshot'
    snapshot.mkdir()
    for path in [Path(__file__),ROOT/'core/deviation_node_multiview.js',ROOT/'core/deviation_node_multiview.css']:
        record['source_sha256'][str(path.relative_to(ROOT))] = sha(path.read_bytes())
        shutil.copy2(path,snapshot/path.name)
    (OUT/'export.json').write_text(encoded(record)+'\n')
    with zipfile.ZipFile(SOURCE/'v006_node_multiview_offline.zip') as old, zipfile.ZipFile(OUT/ARCHIVE,'x',zipfile.ZIP_DEFLATED,compresslevel=4) as new:
        names = set(old.namelist())
        for item in old.infolist():
            if item.filename not in ('index.html','README.txt'):
                new.writestr(item,old.read(item))
        new.write(OUT/'index.html','index.html')
        for name in assets:
            if name not in names:
                new.write(OUT/name,name)
        new.write(OUT/'export.json','provenance/pose70_export.json')
        new.writestr('README.txt','解压后打开 index.html，在视角菜单选择 ±70°，查看376个存档节点的左70°、正前、右70°图片。终止节点显示未采集提示。\nExtract and open index.html. Choose ±70° in the view menu to inspect left 70°, front and right 70° at 376 checkpoints. Terminal nodes show an unavailable message.\n')
    assets[ARCHIVE] = sha((OUT/ARCHIVE).read_bytes())
    (OUT/'online_manifest.json').write_text(encoded(dict(html='index.html',assets=assets))+'\n')
    record.update(archive=ARCHIVE,archive_sha256=assets[ARCHIVE],archive_bytes=(OUT/ARCHIVE).stat().st_size)
    (OUT/'export.json').write_text(encoded(record)+'\n')
    print(encoded(dict(nodes=count,images=len(jobs),archive_bytes=record['archive_bytes'])),flush=True)


if __name__ == '__main__':
    main()
