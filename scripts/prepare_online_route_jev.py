"""Package a front-only JEV sampling-lab replay for the static publisher."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from PIL import Image


def digest(content):
    return hashlib.sha256(content).hexdigest()


def prepare(source, destination):
    subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('prepare_online_visualization.py')),
                    '--html', str(source), '--destination', str(destination)], check=True)
    manifest_file = destination / 'online_manifest.json'
    manifest = json.loads(manifest_file.read_text())
    page = destination / manifest['html']
    html = page.read_text()
    match = re.search(r'(<script id="payload" type="application/json">)(.*?)(</script>)', html, re.S)
    if not match:
        raise ValueError('Missing sampling-lab payload')
    payload = json.loads(match.group(2))
    maps = {scene: info['image'] for scene, info in payload['maps'].items()}
    used = {frame['image'] for case in payload['cases'] for frame in case['frames']}
    if used | set(maps.values()) != set(payload['images']):
        raise ValueError('Unexpected image references')
    for name in ['front', 'maps']:
        (destination / name).mkdir()

    def encode_front(key):
        path = source.parent / payload['images'][key]
        if path.name != 'policy_front.png':
            raise ValueError('Expected native front image')
        content = path.read_bytes()
        if digest(content) != key:
            raise ValueError('Original front hash mismatch')
        name = 'front/' + key + '.webp'
        with Image.open(BytesIO(content)) as image:
            encoded = BytesIO()
            image.convert('RGB').save(encoded, format='WEBP', quality=85, method=3)
        display = encoded.getvalue()
        (destination / name).write_bytes(display)
        return key, name, digest(display)

    with ThreadPoolExecutor(8) as workers:
        for key, name, checksum in workers.map(encode_front, sorted(used)):
            payload['images'][key] = name
            manifest['assets'][name] = checksum
    for scene, key in maps.items():
        path = source.parent / payload['images'][key]
        if not re.fullmatch(r'[A-Za-z0-9_-]+', scene) or path.name != scene + '.png':
            raise ValueError('Unexpected map filename')
        name = 'maps/' + path.name
        shutil.copyfile(path, destination / name)
        payload['images'][key] = name
        manifest['assets'][name] = digest((destination / name).read_bytes())
    license_name = 'font_license.zip'
    with zipfile.ZipFile(destination / license_name, 'x', zipfile.ZIP_DEFLATED) as archive:
        archive.write(source.with_name('FONT_LICENSE.txt'), 'FONT_LICENSE.txt')
    manifest['assets'][license_name] = digest((destination / license_name).read_bytes())
    data = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = html[:match.start(2)] + data + html[match.end(2):]
    # Mirror the published template's map checkbox and keep the branch's sampler.
    quick_toggle = """
<script>
Object.assign(L.zh,{showPoints:'显示回退点',subtitle:'原生前视 · 逐帧回放',footer:'JEV v001 · 前视采样结果'});
Object.assign(L.en,{showPoints:'Show checkpoints',subtitle:'Native front view · frame-by-frame replay',footer:'JEV v001 · front-view sampling results'});
const checkpointToggle=document.createElement('label');
checkpointToggle.className='eliminationOption';
checkpointToggle.innerHTML='<input id="showCheckpoints" type="checkbox"><span data-i18n="showPoints"></span>';
document.querySelector('.trajectoryActions').prepend(checkpointToggle);
const quick=document.getElementById('showCheckpoints'), original=document.getElementById('sample_v001');
quick.checked=original.checked;
quick.onchange=()=>{original.checked=quick.checked;original.dispatchEvent(new Event('change'));};
original.addEventListener('change',()=>{quick.checked=original.checked;});
document.getElementById('reference').checked=true;
updateLanguage();
</script>
"""
    page.write_text(html.replace('</body>', quick_toggle + '</body>'))
    manifest.update(release=destination.name, html_sha256=digest(page.read_bytes()),
                    front_images=len(used), maps=len(maps), display_encoding='WebP quality 85, native dimensions')
    manifest_file.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f"Ready: {len(used)} front images, {len(maps)} maps, {len(manifest['assets'])} assets.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    options = parser.parse_args()
    prepare(options.html.resolve(), options.destination.resolve())
