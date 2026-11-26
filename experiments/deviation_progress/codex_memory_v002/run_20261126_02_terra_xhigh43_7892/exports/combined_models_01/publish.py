"""Stage the complete release and atomically switch the existing public replay."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile

root = Path('outputs/visualization_publishing')
previous = root / 'codex_deviation_v002_combined43_gap6_web_20261125_01'
stage = root / 'codex_deviation_v002_astra_terra_web_20261126_01'
stable = 'codex_deviation_v002_terminal4_map_layers_web_20261125_01'
config = json.loads(Path('core/visualization_publish.json').read_text())
host = config['ssh_user'] + '@' + config['ssh_host']
assets = json.loads((stage/'online_manifest.json').read_text())['assets']
old_assets = json.loads((previous/'online_manifest.json').read_text())['assets']
entries = ['replay.zip','index.html']
old_sha = {name:hashlib.sha256((previous/name).read_bytes()).hexdigest() for name in entries}
params = dict(root=config['remote_root'], stable=stable, stage=stage.name, old_sha=old_sha,
              entries=entries, added=[name for name in assets if name not in old_assets],
              reuse={name:sha for name,sha in assets.items() if old_assets.get(name)==sha})
activate = """
import hashlib,json,os,pathlib,shutil,sys
p=json.load(sys.stdin)
root=pathlib.Path(p['root'])
live,staged=root/p['stable'],root/p['stage']
for name,expected in p['old_sha'].items():
    if hashlib.sha256((live/name).read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Previous release changed: '+name)
for name,expected in p['reuse'].items():
    if hashlib.sha256((live/name).read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Shared asset changed: '+name)
    os.link(live/name,staged/name)
shutil.copytree(live,root/(p['stable']+'_archive43'),copy_function=os.link)
for name in p['added']:
    os.link(staged/name,live/name)
for name in p['entries']:
    tmp=live/('.'+name+'.astra_terra')
    os.link(staged/name,tmp)
    os.replace(tmp,live/name)
"""
with tempfile.TemporaryDirectory(prefix='vln-model-replay-') as directory:
    sock = str(Path(directory)/'ctl')
    base = ['python3','-Bu','scripts/publish_visualization.py','--html',str(stage/'index.html'),
            '--ssh-control-path',sock]
    files = [v for name in [*params['added'],'replay.zip'] for v in ('--asset',name)]
    try:
        subprocess.run([*base,'--name',stage.name,*files],check=True)
        subprocess.run(['ssh','-S',sock,'-o','BatchMode=yes',host,'python3 -c '+shlex.quote(activate)],
                       input=json.dumps(params),text=True,check=True,timeout=90)
        subprocess.run([*base,'--name',stable,'--verify-only',*files],check=True)
    finally:
        subprocess.run(['ssh','-S',sock,'-O','exit',host],stderr=subprocess.DEVNULL)
