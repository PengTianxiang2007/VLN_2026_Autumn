"""Publish the new capture option and atomically update the existing viewer entry."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.request import ProxyHandler, Request, build_opener
import zipfile

ROOT = Path(__file__).resolve().parents[5]
RELEASE = 'v006_node_multiview70_web_20261121_01'
ENTRY = 'v006_node_multiview_web_20261121_01'
PUBLIC = ROOT/'outputs/visualization_publishing'/RELEASE
manifest = json.loads((PUBLIC/'online_manifest.json').read_text())
export = json.loads((PUBLIC/'export.json').read_text())
config = json.loads((ROOT/'core/visualization_publish.json').read_text())
assert json.loads((PUBLIC/'browser_check.json').read_text())['passed']
spec = importlib.util.spec_from_file_location('existing_publisher',ROOT/'experiments/deviation_progress/v006/exports/comparison_20261121_01/publish.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
sys.path.insert(0,str(ROOT/'scripts'))
import publish_visualization

with tempfile.TemporaryDirectory(prefix='vln-pose70-publish-',dir='/tmp') as temp:
    stage = Path(temp)
    archive = export['archive']
    shutil.copyfile(PUBLIC/archive,stage/archive)
    with zipfile.ZipFile(stage/archive) as package:
        for name in ['index.html',*(n for n in manifest['assets'] if n != archive)]:
            destination = stage/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(package.read(name))
    socket = str(stage/'ssh-control')
    host = config['ssh_user']+'@'+config['ssh_host']
    known = stage/'known_hosts'
    known.write_text(config['ssh_host']+' '+config['host_key']+'\n')
    ssh = ['ssh','-S',socket,'-o','StrictHostKeyChecking=yes','-o','BatchMode=yes',
           '-o','UserKnownHostsFile='+str(known),'-o','HostKeyAlgorithms=ssh-ed25519']
    sys.argv = ['publish_visualization','--html',str(stage/'index.html'),'--name',RELEASE,'--ssh-control-path',socket]
    for name in manifest['assets']:
        sys.argv.extend(['--asset',name])
    print('Publishing new views and updating the existing entry',flush=True)
    try:
        publish_visualization.main()
        payload = dict(root=config['remote_root'],release=RELEASE,entry=ENTRY,previous=export['source_html_sha256'],
                       current=export['html_sha256'],assets=manifest['assets'],backup='index_before_pose70_20261121.html')
        attached = subprocess.run([*ssh,host,'python3 -c '+shlex.quote(previous.ATTACH)],input=json.dumps(payload),
                                  text=True,capture_output=True,check=True,timeout=180)
    finally:
        subprocess.run([*ssh,'-O','exit',host],capture_output=True,timeout=15)
    url = config['public_base_url'].rstrip('/')+'/'+ENTRY+'/index.html'
    opener = build_opener(ProxyHandler({}))
    with opener.open(Request(url,method='HEAD'),timeout=20) as response:
        assert response.status == 200 and int(response.headers['Content-Length'])==(PUBLIC/'index.html').stat().st_size
    record = dict(url=url,snapshot=RELEASE,entry_sha256=export['html_sha256'],http_status=200,**json.loads(attached.stdout))
    Path(__file__).with_name('publication.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
