"""Fetch one real VLNVerse fine episode and its complete scene; preserve verified files."""
import concurrent.futures, gzip, hashlib, json, os, time, urllib.request
from pathlib import Path
ROOT = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse')
ROOT.mkdir(parents=True, exist_ok=True)
OFFICIAL = 'https://huggingface.co'
MIRROR = 'https://hf-mirror.com'
def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'peng-vlnverse-smoke/1.0'}), timeout=90)
def read_json(url):
    with request(url) as response: return json.load(response)
def tree(repo, folder=''):
    url = f'{OFFICIAL}/api/datasets/{repo}/tree/main/{folder}?recursive=true&limit=1000'
    items = []
    while url:
        with request(url) as response:
            items.extend(json.load(response))
            link = response.headers.get('Link', '')
            url = next((x.split('>')[0].strip(' <') for x in link.split(',') if 'rel="next"' in x), None)
    return [x for x in items if x['type'] == 'file']
def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''): digest.update(block)
    return digest.hexdigest()
def download(repo, item, directory):
    relative = item['path']; target = directory / relative
    expected_size = item.get('size'); expected_sha = item.get('lfs', {}).get('oid')
    if target.exists():
        if expected_size is not None and target.stat().st_size != expected_size:
            raise RuntimeError(f'Existing file size mismatch; preserving {target}')
        if expected_sha and sha256(target) != expected_sha:
            raise RuntimeError(f'Existing file hash mismatch; preserving {target}')
        return relative
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + '.part')
    last_error = None
    for attempt in range(4):
        for endpoint in (MIRROR, OFFICIAL):
            url = f'{endpoint}/datasets/{repo}/resolve/main/{urllib.parse.quote(relative)}'
            offset = part.stat().st_size if part.exists() else 0
            headers = {'User-Agent': 'peng-vlnverse-smoke/1.0'}
            if offset: headers['Range'] = f'bytes={offset}-'
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=90) as response:
                    append = offset and response.status == 206
                    with part.open('ab' if append else 'wb') as stream:
                        while True:
                            chunk = response.read(4 * 1024 * 1024)
                            if not chunk: break
                            stream.write(chunk)
                if expected_size is not None and part.stat().st_size != expected_size:
                    raise RuntimeError(f'Incomplete file {relative}')
                if expected_sha and sha256(part) != expected_sha:
                    raise RuntimeError(f'Hash mismatch {relative}')
                part.rename(target)
                return relative
            except Exception as exc:
                last_error = str(exc)
        time.sleep(1 + attempt)
    raise RuntimeError(f'{relative}: {last_error}')
repo = 'Eyz/VLNVerse_data'
items = tree(repo, 'raw_data/final_splits')
annotation = next(x for x in items if x['path'].endswith('/fine_val_unseen.json.gz'))
download(repo, annotation, ROOT / 'data')
with gzip.open(ROOT / 'data' / annotation['path'], 'rt') as stream: episodes = json.load(stream)['episodes']
episode = episodes[0]
scene = episode['scan']
smoke_data = ROOT / 'data' / 'smoke' / 'fine' / 'val_unseen'
smoke_data.mkdir(parents=True, exist_ok=True)
with gzip.open(smoke_data / 'val_unseen.json.gz', 'wt') as stream: json.dump({'episodes': [episode]}, stream)
(ROOT / 'smoke_episode.json').write_text(json.dumps(episode, indent=2))
resources = [('Eyz/VLNVerse_scene', scene, ROOT / 'scenes')] # H1 dataset is gated: skipped.
manifest = []
for repo, folder, directory in resources:
    items = tree(repo, folder)
    items = [x for x in items if '/.thumbs/' not in x['path']]
    print(f'{repo}: {len(items)} files, {sum(x["size"] for x in items)/1024**2:.1f} MiB', flush=True)
    manifest.append({'repo': repo, 'folder': folder, 'files': items})
    (ROOT / 'download_manifest.json').write_text(json.dumps(manifest, indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(download, repo, item, directory): item['path'] for item in items}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            future.result(); completed += 1
            if completed % 25 == 0 or completed == len(items): print(f'{repo}: {completed}/{len(items)}', flush=True)
(ROOT / 'download_verified.json').write_text(json.dumps({'scene': scene, 'episode_id': episode['episode_id'], 'resources': manifest}, indent=2))
print('ASSETS_READY', flush=True)
