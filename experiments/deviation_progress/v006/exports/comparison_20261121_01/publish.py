"""Publish the five-version comparison at the user-designated entry."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[5]
RELEASE = 'deviation_five_versions_web_20261121_01'
ENTRY = 'deepseek_v004_six_web_20261120_02'
PREVIOUS = '6302e7d0b2336b99aed951641c6dbd1fea210f5686eaba2953613d49ef03daf1'
BACKUP = 'index_before_v006_comparison_20261121.html'

# Only link verified static assets. Keep the old downloads and switch the entry last.
ATTACH = """
import hashlib, json, os, pathlib, sys, tempfile
p = json.load(sys.stdin)
root = pathlib.Path(p['root'])
source, target = root / p['release'], root / p['entry']
def digest(path):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError('Expected a regular file: '+str(path))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()
if source.is_symlink() or target.is_symlink() or not (target/'assets').is_dir() or (target/'assets').is_symlink():
    raise RuntimeError('Unexpected release directory')
index = target/'index.html'
old = digest(index)
if old not in (p['previous'], p['current']) or digest(source/'index.html') != p['current']:
    raise RuntimeError('Entry changed since preflight')
missing = []
for key, expected in p['assets'].items():
    a, b = source/key, target/key
    if digest(a) != expected:
        raise RuntimeError('Source asset changed: '+key)
    if b.exists() or b.is_symlink():
        if digest(b) != expected:
            raise RuntimeError('Existing asset differs: '+key)
    else:
        missing.append(key)
backup = target / p['backup']
if backup.exists() or old == p['current']:
    if digest(backup) != p['previous']:
        raise RuntimeError('Original entry backup differs')
else:
    os.link(index, backup)
    if digest(backup) != p['previous']:
        raise RuntimeError('Original entry changed during backup')
for key in missing:
    try:
        os.link(source/key, target/key)
    except FileExistsError:
        if digest(target/key) != p['assets'][key]:
            raise
if old != p['current']:
    with tempfile.TemporaryDirectory(dir=target) as staging:
        staged = pathlib.Path(staging)/'index.html'
        os.link(source/'index.html', staged)
        if digest(index) != p['previous']:
            raise RuntimeError('Entry changed during staging')
        os.replace(staged, index)
if digest(index) != p['current']:
    raise RuntimeError('Entry verification failed')
print(json.dumps(dict(assets_verified=len(p['assets']), assets_added=len(missing))))
"""


def main(reuse_release, local_stage=None):
    public = Path(local_stage) if local_stage else ROOT/'outputs/visualization_publishing'/RELEASE
    manifest = json.loads((public/'online_manifest.json').read_text())
    cfg = json.loads((ROOT/'core/visualization_publish.json').read_text())
    host = cfg['ssh_user']+'@'+cfg['ssh_host']
    sha = hashlib.sha256((public/'index.html').read_bytes()).hexdigest()
    payload = dict(root=cfg['remote_root'], release=RELEASE, entry=ENTRY, previous=PREVIOUS,
                   current=sha, assets=manifest['assets'], backup=BACKUP)
    with tempfile.TemporaryDirectory(prefix='vln-paired-') as work:
        socket = str(Path(work)/'control')
        known = Path(work)/'known_hosts'
        known.write_text(cfg['ssh_host']+' '+cfg['host_key']+'\n')
        ssh = ['ssh','-S',socket,'-o','StrictHostKeyChecking=yes','-o','BatchMode=yes',
               '-o','UserKnownHostsFile='+str(known),'-o','HostKeyAlgorithms=ssh-ed25519']
        command = [sys.executable,'-B',str(ROOT/'scripts/publish_visualization.py'),
                   '--html',str(public/'index.html'),'--name',RELEASE,'--ssh-control-path',socket]
        if reuse_release:
            command.append('--verify-only')
        for relative in manifest['assets']:
            command.extend(['--asset',relative])
        try:
            subprocess.run(command, check=True)
            attached = subprocess.run([*ssh,host,'python3 -c '+shlex.quote(ATTACH)],check=True,
                                      input=json.dumps(payload),text=True,stdout=subprocess.PIPE,timeout=180)
        finally:
            subprocess.run([*ssh,'-O','exit',host],capture_output=True,timeout=15)
    base = cfg['public_base_url'].rstrip('/')+'/'+ENTRY+'/'
    http = build_opener(ProxyHandler({}))
    checks = {}
    for name in ('index.html', 'compare5_qwen_v006_model_returns.json', 'vln_v003_v005_v006_five_versions_offline.zip'):
        archive = name.endswith('.zip')
        request = Request(base+name,method='HEAD' if archive else 'GET',headers={'Accept-Encoding':'identity'})
        with http.open(request,timeout=30) as response:
            assert response.status == 200 and response.geturl() == base+name
            source = (public if (public/name).is_file() else public.parent/ENTRY)/name
            size = int(response.headers['Content-Length'])
            assert size == source.stat().st_size
            check = dict(status=response.status, bytes=size, mime=response.headers.get_content_type())
            if not archive:
                assert check['mime'] == ('text/html' if name == 'index.html' else 'application/json')
                check['sha256'] = hashlib.sha256(response.read()).hexdigest()
                assert check['sha256'] == (sha if name=='index.html' else manifest['assets'][name])
            checks[name] = check
    record = dict(url=base+'index.html', updated_at=datetime.now(timezone.utc).isoformat(),
                  immutable_release=RELEASE, old_sha256=PREVIOUS, entry_sha256=sha,
                  backup=BACKUP, http=checks, **json.loads(attached.stdout))
    output = Path(__file__).with_name('publication.json')
    with output.open('x') as stream:
        json.dump(record,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    print(record['url'],sha,flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-release',action='store_true',help='Reverify the immutable release on retry')
    parser.add_argument('--local-stage', help='Optional identical local staging copy to avoid repeated NAS reads')
    args = parser.parse_args()
    main(args.reuse_release, args.local_stage)
