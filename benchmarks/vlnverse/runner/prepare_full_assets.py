"""Fetch one real VLNVerse fine episode and its complete scene; preserve verified files."""
import concurrent.futures, gzip, hashlib, json, os, time, urllib.request, threading, re
import requests
from pathlib import Path
ROOT = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/VLNVerse')
ROOT.mkdir(parents=True, exist_ok=True)
OFFICIAL = 'https://huggingface.co'
MIRROR = 'https://hf-mirror.com'
THREAD_STATE=threading.local()
RATE_LOCK=threading.Lock()
RATE_UNTIL=0.0
def wait_rate_limit():
    while True:
        with RATE_LOCK: delay=RATE_UNTIL-time.monotonic()
        if delay<=0: return
        time.sleep(min(delay,10))
def client():
    if not hasattr(THREAD_STATE,'session'): THREAD_STATE.session=requests.Session()
    return THREAD_STATE.session
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
    global RATE_UNTIL
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
    if part.exists() and expected_size is not None and part.stat().st_size == expected_size:
        if not expected_sha or sha256(part) == expected_sha:
            part.rename(target)
            return relative
        part.rename(part.with_name(part.name + '.conflict.' + str(time.time_ns())))
    if part.exists() and expected_size is not None and part.stat().st_size > expected_size:
        part.rename(part.with_name(part.name + '.conflict.' + str(time.time_ns())))
    last_error = None
    for attempt in range(6):
        for endpoint in (MIRROR, OFFICIAL):
            url = f'{endpoint}/datasets/{repo}/resolve/main/{urllib.parse.quote(relative)}'
            offset = part.stat().st_size if part.exists() else 0
            headers = {'User-Agent': 'peng-vlnverse-smoke/1.0'}
            if offset: headers['Range'] = f'bytes={offset}-'
            try:
                wait_rate_limit()
                with client().get(url,headers=headers,stream=True,timeout=90) as response:
                    if response.status_code==429:
                        retry=response.headers.get('Retry-After','')
                        limits=response.headers.get('RateLimit','')
                        match=re.search(r't=(\d+)',limits)
                        delay=float(retry) if retry.isdigit() else (float(match.group(1)) if match else 120.)
                        with RATE_LOCK:
                            RATE_UNTIL=max(RATE_UNTIL,time.monotonic()+delay+2)
                        print('RATE_LIMIT_PAUSE',endpoint,round(delay+2),flush=True)
                    response.raise_for_status()
                    append = offset and response.status_code == 206
                    with part.open('ab' if append else 'wb') as stream:
                        for chunk in response.iter_content(4*1024*1024):
                            if chunk: stream.write(chunk)
                if expected_size is not None and part.stat().st_size != expected_size:
                    raise RuntimeError(f'Incomplete file {relative}')
                if expected_sha and sha256(part) != expected_sha:
                    raise RuntimeError(f'Hash mismatch {relative}')
                part.rename(target)
                return relative
            except Exception as exc:
                last_error = str(exc)
                if part.exists() and expected_size is not None and part.stat().st_size == expected_size:
                    if not expected_sha or sha256(part)==expected_sha:
                        part.rename(target); return relative
                    part.rename(part.with_name(part.name+'.conflict.'+str(time.time_ns())))
        time.sleep(1 + attempt)
    raise RuntimeError(f'{relative}: {last_error}')

if __name__ == '__main__':
    annotation = ROOT / 'data/raw_data/final_splits/fine_val_unseen.json.gz'
    with gzip.open(annotation, 'rt') as f: episodes = json.load(f)['episodes']
    scenes = sorted({e['scan'] for e in episodes})
    target = ROOT / 'data/eval/fine/val_unseen/val_unseen.json.gz'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with gzip.open(target, 'wt') as f: json.dump({'episodes': episodes}, f)
    else:
        with gzip.open(target, 'rt') as f: assert json.load(f)['episodes'] == episodes
    manifest_path = ROOT / 'fine_val_unseen_scene_manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        assert {x['folder'] for x in manifest} == set(scenes)
    else:
        def get_scene(scene):
            files = [x for x in tree('Eyz/VLNVerse_scene', scene) if '/.thumbs/' not in x['path']]
            print('MANIFEST', scene, len(files), sum(x['size'] for x in files), flush=True)
            return {'repo':'Eyz/VLNVerse_scene','folder':scene,'files':files}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            manifest = list(pool.map(get_scene, scenes))
        manifest_path.write_text(json.dumps(manifest, indent=2))
    count = sum(len(x['files']) for x in manifest)
    total = sum(f['size'] for x in manifest for f in x['files'])
    print('TOTAL', len(episodes), len(scenes), count, total, flush=True)
    for entry in manifest:
        scene = entry['folder']; files = entry['files']
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(download, entry['repo'], f, ROOT/'scenes') for f in files]
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                future.result(); completed += 1
                if completed % 50 == 0 or completed == len(files):
                    print('PROGRESS', scene, completed, len(files), flush=True)
        print('SCENE_VERIFIED', scene, flush=True)
    (ROOT/'fine_val_unseen_assets_ready.json').write_text(json.dumps({'status':'verified','episodes':len(episodes),'scenes':scenes,'files':count,'bytes':total,'manifest':str(manifest_path)},indent=2))
    print('FULL_ASSETS_READY', flush=True)
