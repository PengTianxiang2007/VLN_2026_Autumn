"""Attach archived multiview observations to the frozen five-version review page."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from PIL import Image
from export_oracle_distance_replay import add_font

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'outputs/visualization_publishing/deviation_five_versions_web_20261121_01'
DATA = ROOT/'outputs/offline_route_dataset/v001/run_20261118_01/dataset'
OUT = ROOT/'outputs/visualization_publishing/v006_node_multiview_web_20261121_01'
RECORD = ROOT/'experiments/deviation_progress/v006/exports/node_multiview_20261121_01'
ARCHIVE = 'v006_node_multiview_offline.zip'
PATTERN = r'<script id="payload" type="application/json">(.*?)</script>'


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(encoded(value)+'\n')


def source():
    html = (SOURCE/'index.html').read_text()
    return html, json.loads(re.search(PATTERN, html, re.S)[1])


def media():
    html, bundle = source()
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT/'assets').mkdir()
    groups, jobs, origins = {}, {}, {}
    observation_hashes = {}
    totals = dict(cases=0, retained=0, terminal=0, rollback_targets=0, images=0)
    for case in bundle['cases']:
        eid = case['episode_id']
        path = DATA/'inputs'/eid/'observations.jsonl'
        raw = path.read_bytes()
        observation_hashes[eid] = sha(raw)
        observations = {r['step']:r for r in map(json.loads, raw.splitlines())}
        review = bundle['reviewVersions']['qwen_v006']['cases'][eid]
        targets = [r for r in review['rounds'] if r.get('rollback_target')]
        assert len(targets) <= 1
        target = None
        if targets:
            r = targets[0]
            target = dict(node_id=r['rollback_target']['node_id'], frame=r['rollback_target']['frame'],
                          alarm_frame=r['to_frame'])
            totals['rollback_targets'] += 1
        nodes = []
        for n in review['nodes']:
            obs = observations[n['index']]
            frame = case['frames'][n['index']]
            assert frame['frame'] == obs['step'] == n['index']
            assert frame['image'] == obs['native_front']['sha256']
            assert frame['position'] == obs['robot_pose']['position_world_m']
            assert [v['view_id'] for v in obs['views_360']] == list(range(8))
            assert [v['relative_yaw_deg'] for v in obs['views_360']] == [0,45,90,135,-180,-135,-90,-45]
            assert [v['view_id'] for v in obs['views_180']] == [1,0,7]
            for v in obs['views_180']:
                assert v['sha256'] == obs['views_360'][v['view_id']]['sha256']
            views = []
            for v in obs['views_360']:
                name = 'assets/mv_'+v['sha256']+'.webp'
                entry = dict(image=name, yaw=v['relative_yaw_deg'], source_sha256=v['sha256'])
                views.append(entry)
                jobs[name] = (DATA/v['image'], v['sha256'])
                origins[name] = dict(source=v['image'], sha256=v['sha256'])
            nodes.append(dict(n, position=frame['position'], heading_deg=obs['robot_pose']['heading_deg'],
                              views=views, front_sha256=obs['native_front']['sha256']))
            totals['terminal' if n['terminal_node'] else 'retained'] += 1
        if target:
            assert any(n['id']==target['node_id'] and n['index']==target['frame'] for n in nodes)
        groups[eid] = dict(case_id=review['case_id'], nodes=nodes, rollback=target)
        totals['cases'] += 1
    assert totals == dict(cases=53, retained=376, terminal=53, rollback_targets=47, images=0)

    def convert(item):
        name, (path, expected) = item
        data = path.read_bytes()
        assert sha(data) == expected, str(path)
        with Image.open(io.BytesIO(data)) as im:
            assert im.size == (640,480)
            buf = io.BytesIO()
            im.convert('RGB').save(buf, format='WEBP', quality=85, method=4)
        content = buf.getvalue()
        (OUT/name).write_bytes(content)
        return name, sha(content)

    assets = {}
    with ThreadPoolExecutor(max_workers=6) as workers:
        for i, (name, digest) in enumerate(workers.map(convert, jobs.items()), 1):
            assets[name] = digest
            if i % 256 == 0:
                print('Multiview images:', i, '/', len(jobs), flush=True)
    totals['images'] = len(jobs)
    write(OUT/'multiview_data.json', dict(cases=groups, totals=totals))
    write(OUT/'multiview_media.json', dict(assets=assets, source_images=origins,
        observation_indices_sha256=observation_hashes, source_html_sha256=sha(html.encode()),
        dataset_manifest_sha256=sha((DATA/'manifest.json').read_bytes())))
    print(encoded(totals), flush=True)


def page():
    html, bundle = source()
    media_info = read(OUT/'multiview_media.json')
    assert sha(html.encode()) == media_info['source_html_sha256']
    bundle['nodeMultiview'] = read(OUT/'multiview_data.json')
    for review in bundle['reviewVersions'].values():
        review['archiveFile'] = ARCHIVE
    match = re.search(PATTERN, html, re.S)
    html = html[:match.start(1)]+encoded(bundle).replace('</','<\\/')+html[match.end(1):]
    html = html.replace('<section id="v4Review">', '<section id="nodeMultiview" aria-label="节点多视角"></section><section id="v4Review">', 1)
    css = (ROOT/'core/deviation_node_multiview.css').read_text()
    ui = (ROOT/'core/deviation_node_multiview.js').read_text()
    html = html.replace('</head>', '<style id="node-multiview-style">'+css+'</style></head>', 1)
    html = html.replace('</body>', '<script id="node-multiview-ui">'+ui+'</script></body>', 1)
    html, count = re.subn(r'<style id="embedded-font">.*?</style>', '', html, flags=re.S)
    assert count == 1
    (OUT/'index.html').write_text(html)
    add_font(OUT/'index.html')
    html = (OUT/'index.html').read_text().replace('font-family:OracleSans', 'font-family:CrossingSans')
    match = re.search(r'data:font/ttf;base64,([A-Za-z0-9+/=]+)', html)
    font = base64.b64decode(match[1])
    font_name = 'assets/'+sha(font)+'.ttf'
    html = html[:match.start()]+font_name+html[match.end():]
    (OUT/'index.html').write_text(html)
    (OUT/font_name).write_bytes(font)
    assets = dict(media_info['assets'])
    assets[font_name] = sha(font)
    source_assets = read(SOURCE/'online_manifest.json')['assets']
    for name in sorted(set(bundle['images'].values()) | {v['answersFile'] for v in bundle['reviewVersions'].values()}):
        if not (OUT/name).exists():
            os.link(SOURCE/name, OUT/name)
        assets[name] = source_assets[name]
    # The license is included in the offline ZIP; the static publisher disallows .txt assets.
    write(OUT/'online_manifest.json', dict(html='index.html', assets=assets))
    provenance = dict(created_at=datetime.now(timezone.utc).isoformat(),
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        worktree_status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
        source_html_sha256=media_info['source_html_sha256'],
        dataset_manifest_sha256=media_info['dataset_manifest_sha256'],
        totals=bundle['nodeMultiview']['totals'], model_calls=0,
        html_sha256=sha(html.encode()), source_sha256={})
    snapshot = OUT/'source_snapshot'
    snapshot.mkdir(exist_ok=True)
    for path in [Path(__file__), ROOT/'core/deviation_node_multiview.js', ROOT/'core/deviation_node_multiview.css']:
        provenance['source_sha256'][str(path.relative_to(ROOT))] = sha(path.read_bytes())
        shutil.copy2(path, snapshot/path.name)
    write(OUT/'export.json', provenance)
    print(encoded(dict(html=str(OUT/'index.html'), totals=provenance['totals'])), flush=True)


def package():
    manifest = read(OUT/'online_manifest.json')
    # Reuse the archived front-view media and historical answers without regenerating them.
    old_zip = SOURCE/'vln_v003_v005_v006_five_versions_offline.zip'
    with zipfile.ZipFile(old_zip) as old, zipfile.ZipFile(OUT/ARCHIVE, 'x', zipfile.ZIP_DEFLATED, compresslevel=4) as new:
        names = set(old.namelist())
        for info in old.infolist():
            if info.filename not in ('index.html','README.txt','FONT_LICENSE.txt') and not info.filename.endswith('.ttf'):
                new.writestr(info, old.read(info))
        new.write(OUT/'index.html', 'index.html')
        new.write(OUT/'FONT_LICENSE.txt', 'FONT_LICENSE.txt')
        for name in manifest['assets']:
            if name not in names or name.endswith('.ttf'):
                new.write(OUT/name, name)
        new.writestr('README.txt', '解压后打开 index.html。包含全部历史回答、376 个存档节点和53个终止节点的180°/360°多视角，以及47个v006回退目标。辅助图为640×480 WebP展示副本，原始PNG哈希保留；未改变模型输入和原答。\nExtract and open index.html. Includes all archived answers, 180/360-degree views at 376 retained checkpoints and 53 terminal nodes, and 47 v006 rollback targets. Auxiliary images are 640x480 WebP display copies with original PNG hashes preserved; model inputs and answers are unchanged.\n')
        new.write(OUT/'multiview_media.json', 'provenance/multiview_media.json')
        new.write(OUT/'export.json', 'provenance/export.json')
    manifest['assets'][ARCHIVE] = sha((OUT/ARCHIVE).read_bytes())
    write(OUT/'online_manifest.json', manifest)
    record = read(OUT/'export.json')
    record.update(archive=ARCHIVE, archive_bytes=(OUT/ARCHIVE).stat().st_size,
                  archive_sha256=manifest['assets'][ARCHIVE])
    write(OUT/'export.json', record)
    print(encoded({key:record[key] for key in ('archive','archive_bytes','archive_sha256')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['media','page','package'])
    globals()[parser.parse_args().stage]()
