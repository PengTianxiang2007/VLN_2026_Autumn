"""Publish the verified 43-case bundle and update the previous public entry in place."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile

old = 'codex_deviation_v002_terminal4_map_layers_web_20261125_01'
new = 'codex_deviation_v002_combined43_gap6_web_20261125_01'
published = Path('outputs/visualization_publishing')
folder = published / new
manifest = json.loads((folder / 'online_manifest.json').read_text())
files = sorted(manifest['assets'])
config = json.loads(Path('core/visualization_publish.json').read_text())
host = config['ssh_user'] + '@' + config['ssh_host']
html = (folder / 'index.html').read_text()
import re
payload = json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)[1])
ids = [case['case_id'] for case in payload['cases']]
assert len(ids) == 43 and ids == sorted(set(ids))
assert any(review['added'] for case in payload['cases'] for review in case['rounds'])
remote = """
import hashlib,json,os,pathlib,shutil,sys
p=json.load(sys.stdin)
root=pathlib.Path(p['root'])
old,new,archive=[root / p[k] for k in ('old','new','archive')]
def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
for name,sha in p['old_sha'].items():
    if hash_file(old / name)!=sha:
        raise RuntimeError('Previous entry changed: '+name)
if archive.exists():
    raise RuntimeError('Archive path already exists')
shutil.copytree(old,archive,copy_function=os.link)
for asset in p['assets']:
    src,dst=new / asset,old / asset
    if dst.exists():
        if hash_file(dst)!=p['assets'][asset]:
            raise RuntimeError('Asset hash mismatch: '+asset)
    else:
        os.link(src,dst)
for name in ('replay.zip','index.html'):
    staging=old / ('.'+name+'.combined43')
    os.link(new/name,staging)
    os.replace(staging,old/name)
print('Archived original and activated 43-case entry.')
"""
with tempfile.TemporaryDirectory(prefix='vln-43-publish-') as stage:
    sock=str(Path(stage)/'ctl')
    base=['python3','-B','scripts/publish_visualization.py','--html',str(folder/'index.html'),'--ssh-control-path',sock]
    assets=[v for a in files+['replay.zip'] for v in ('--asset',a)]
    try:
        subprocess.run([*base,'--name',new,*assets],check=True)
        old_hash={name:hashlib.sha256((published/'codex_deviation_v002_combined9_map_layers_web_20261125_01'/name).read_bytes()).hexdigest() for name in ('index.html','replay.zip')}
        params=dict(root=config['remote_root'],old=old,new=new,archive=old+'_archive9',old_sha=old_hash,assets=manifest['assets'])
        subprocess.run(['ssh','-S',sock,'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',host,'python3 -c '+shlex.quote(remote)],input=json.dumps(params),text=True,check=True,timeout=90)
        subprocess.run([*base,'--name',old,'--verify-only',*assets],check=True)
    finally:
        subprocess.run(['ssh','-S',sock,'-O','exit',host],stderr=subprocess.DEVNULL)
