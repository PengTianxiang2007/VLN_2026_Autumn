"""Publish this immutable multiview export with the repository's standard publisher."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[5]
RELEASE = 'v006_node_multiview_web_20261121_01'
PUBLIC = ROOT/'outputs/visualization_publishing'/RELEASE
sys.path.insert(0, str(ROOT/'scripts'))
import publish_visualization

manifest = json.loads((PUBLIC/'online_manifest.json').read_text())
manifest['assets'].pop('FONT_LICENSE.txt', None)
(PUBLIC/'online_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))+'\n')
# Read one archive from NAS and stage only the selected files on local disk.
# The standard publisher still hashes every staged file and verifies remote hashes.
with tempfile.TemporaryDirectory(prefix='vln-v006-multiview-publish-') as temp:
    stage = Path(temp)
    archive = 'v006_node_multiview_offline.zip'
    shutil.copyfile(PUBLIC/archive, stage/archive)
    with zipfile.ZipFile(stage/archive) as package:
        for name in [manifest['html'], *(n for n in manifest['assets'] if n != archive)]:
            destination = stage/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(package.read(name))
    print('Publishing staged static files:',len(manifest['assets'])+1,flush=True)
    sys.argv = ['publish_visualization', '--html', str(stage/manifest['html']), '--name', RELEASE]
    for asset in manifest['assets']:
        sys.argv.extend(['--asset', asset])
    publish_visualization.main()
