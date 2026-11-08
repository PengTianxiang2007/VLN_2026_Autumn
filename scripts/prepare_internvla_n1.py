"""Fetch revision-pinned N1 inference assets only, verifying HF LFS SHA256."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RESOURCE = Path('/mnt/nas/gezuhao/shared_dataset/Resource_Peng')
REPO = 'InternRobotics/InternVLA-N1-wo-dagger'
REVISION = '377366bc480b6643b807b6ea8fa642715683cf7b'
DEST = RESOURCE / 'models/InternVLA-N1-wo-dagger'
REPORT = ROOT / 'outputs/reproduction/internvla_n1_fine825_seed0_20261102'


def valid_range(headers, status, start, total, requested_end, received):
    matches = re.findall(r'^content-range:\s*bytes (\d+)-(\d+)/(\d+)\s*$', headers, flags=re.I | re.M)
    if status.strip() != '206' or not matches:
        return False
    first, last, size = map(int, matches[-1])
    return first == start and size == total and first <= last <= requested_end and 0 < received <= last-first+1


def transfer_bounded(path, url, size):
    """Bound each connection in time and bytes, retaining valid short transfers."""
    partial = path.with_name(path.name + '.partial')
    stalls = 0
    while not partial.exists() or partial.stat().st_size < size:
        start = partial.stat().st_size if partial.exists() else 0
        end = min(size - 1, start + 16 * 1024 * 1024 - 1)
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='n1_download_range_') as directory:
            payload = Path(directory) / 'payload'
            headers = Path(directory) / 'headers'
            command = ['curl', '--proxy', os.environ['https_proxy'], '--noproxy', '',
                       '--location', '--fail', '--silent', '--show-error',
                       '--connect-timeout', '15', '--max-time', '120',
                       '--speed-limit', '65536', '--speed-time', '30',
                       '--range', f'{start}-{end}', '--dump-header', str(headers),
                       '--output', str(payload), '--write-out', '%{http_code}', url]
            result = subprocess.run(command, capture_output=True, text=True, timeout=135)
            count = payload.stat().st_size if payload.exists() else 0
            header_text = headers.read_text() if headers.exists() else ''
            accepted = valid_range(header_text, result.stdout, start, size, end, count)
            if accepted:
                with partial.open('ab') as dst, payload.open('rb') as src:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                    dst.flush()
                    os.fsync(dst.fileno())
                stalls = 0
                print(json.dumps({'file': path.name, 'bytes': start+count, 'total': size,
                                  'range_seconds': round(time.monotonic()-started, 2),
                                  'resumable_short_read': result.returncode != 0}), flush=True)
            else:
                stalls += 1
                print(f'RANGE_RETRY {path.name} offset={start} stalls={stalls} curl={result.returncode} {result.stderr[:200]}', flush=True)
                if stalls >= 8:
                    raise RuntimeError(f'No verified download progress for {path.name}')
                time.sleep(min(60, stalls * 5))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def fetch(item):
    path, url, size, sha = item
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        actual = digest(path)
        if path.stat().st_size != size or (sha and actual != sha):
            raise RuntimeError(f'Existing asset conflicts: {path}')
        return {'path': str(path), 'size': size, 'sha256': actual, 'reused': True}
    partial = path.with_name(path.name + '.partial')
    if size >= 64 * 1024 * 1024:
        transfer_bounded(path, url, size)
        if partial.stat().st_size != size:
            raise RuntimeError(f'Incorrect final size: {path.name}')
        actual = digest(partial)
        if sha and actual != sha:
            raise RuntimeError(f'SHA256 mismatch, partial preserved: {path.name}')
        partial.rename(path)
        print('VERIFIED ' + path.name, flush=True)
        return {'path': str(path), 'size': size, 'sha256': actual, 'url': url}
    consecutive_stalls = 0
    while True:
        before = partial.stat().st_size if partial.exists() else 0
        if before > size:
            raise RuntimeError(f'Oversized partial preserved for inspection: {path.name}')
        try:
            start = partial.stat().st_size if partial.exists() else 0
            if start < size:
                request = urllib.request.Request(url, headers={'Range': f'bytes={start}-'} if start else {})
                with urllib.request.urlopen(request, timeout=90) as response:
                    append = start > 0 and response.status == 206
                    if append and not response.headers.get('Content-Range', '').startswith(f'bytes {start}-'):
                        raise RuntimeError('Invalid range response')
                    with partial.open('ab' if append else 'wb') as f:
                        last_report = time.monotonic()
                        while True:
                            chunk = response.read(4 * 1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                            if time.monotonic() - last_report > 30:
                                print(json.dumps({'file': path.name, 'bytes': f.tell(), 'total': size}), flush=True)
                                last_report = time.monotonic()
            if partial.stat().st_size != size:
                raise RuntimeError(f'Wrong size for {path.name}: {partial.stat().st_size}/{size}')
        except Exception as e:
            after = partial.stat().st_size if partial.exists() else 0
            consecutive_stalls = 0 if after > before else consecutive_stalls + 1
            print(f'TRANSFER_INTERRUPTED {path.name} bytes={after}/{size} consecutive_stalls={consecutive_stalls} {e}', flush=True)
            if consecutive_stalls >= 8:
                raise
            time.sleep(5 if after > before else min(60, 10 * consecutive_stalls))
            continue
        actual = digest(partial)
        if sha and actual != sha:
            raise RuntimeError(f'SHA256 mismatch, partial preserved: {path.name}')
        partial.rename(path)
        print('VERIFIED ' + path.name, flush=True)
        return {'path': str(path), 'size': size, 'sha256': actual, 'url': url}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proxy', required=True, help='Explicit user-authorized HTTP proxy or reverse tunnel; no automatic fallback')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.proxy)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or not parsed.port:
        parser.error('Expected an explicit loopback HTTP proxy URL')
    # Never inherit another user's proxy or silently switch routes.
    for key in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'all_proxy'):
        os.environ[key] = args.proxy
    os.environ['NO_PROXY'] = os.environ['no_proxy'] = '127.0.0.1,localhost'
    urllib.request.install_opener(urllib.request.build_opener())
    REPORT.mkdir(parents=True, exist_ok=True)
    def metadata(repo, revision):
        cached = REPORT / ('checkpoint_metadata.json' if repo == REPO else 'depth_checkpoint_metadata.json')
        if cached.exists():
            data = json.loads(cached.read_text())
            if data.get('id') == repo and data.get('sha') == revision:
                return data
        return json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true', timeout=60))
    meta = metadata(REPO, REVISION)
    (REPORT / 'checkpoint_metadata.json').write_text(json.dumps(meta, indent=2))
    jobs = []
    for entry in meta['siblings']:
        name = entry['rfilename']
        if name in ('.gitattributes', 'trainer_state.json'):
            continue
        jobs.append((DEST / name, f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}', entry['size'], entry.get('lfs', {}).get('sha256')))
    depth_repo = 'depth-anything/Depth-Anything-V2-Small'
    depth_meta = metadata(depth_repo, '03876f8651c73a60fe4c2c48294e09fcb6838fcf')
    (REPORT / 'depth_checkpoint_metadata.json').write_text(json.dumps(depth_meta, indent=2))
    for entry in depth_meta['siblings']:
        if entry['rfilename'] == 'depth_anything_v2_vits.pth':
            jobs.append((RESOURCE / 'models/Depth-Anything-V2-Small' / entry['rfilename'], f'https://huggingface.co/{depth_repo}/resolve/{depth_meta["sha"]}/{entry["rfilename"]}', entry['size'], entry.get('lfs', {}).get('sha256')))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(fetch, jobs))
    (REPORT / 'assets_verified.json').write_text(json.dumps({'repo': REPO, 'revision': REVISION, 'files': results}, indent=2))
    print('ALL_ASSETS_VERIFIED', flush=True)


if __name__ == '__main__':
    main()
