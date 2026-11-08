"""Download an official ModelScope checkpoint directly, with proxies disabled and SHA256 checks."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
from pathlib import Path, PurePosixPath
import threading
import time
import urllib.parse
import urllib.request


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error('workers must be 1..8')
    # Do not inherit a different proxy or NO_PROXY bypass.
    for key in list(os.environ):
        if 'proxy' in key.lower():
            del os.environ[key]
    args.output.mkdir(parents=True, exist_ok=True)
    base = 'https://modelscope.cn/api/v1/models/' + args.model

    def opener():
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))

    manifest_path = args.output / 'download_manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest['model_id'] != args.model:
            raise ValueError('Existing manifest belongs to a different model')
    else:
        with opener().open(base + '/repo/files?Revision=master&Recursive=true', timeout=30) as r:
            listing = json.load(r)
        if listing.get('Code') != 200:
            raise RuntimeError('ModelScope file listing failed')
        files = []
        for entry in listing['Data']['Files']:
            path = PurePosixPath(entry['Path'])
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe model path')
            if entry['Type'] != 'blob' or len(path.parts) != 1:
                continue
            if path.suffix not in ['.json', '.safetensors', '.jinja', '.txt', '.md'] and path.name != 'LICENSE':
                continue
            files.append({k: entry[k] for k in ['Path', 'Size', 'Sha256', 'Revision']})
        if not any(f['Path'].endswith('.safetensors') for f in files):
            raise ValueError('Checkpoint listing has no safetensors')
        manifest = dict(schema=1, source='official ModelScope repository', model_id=args.model,
                        fetched_at=datetime.now(timezone.utc).isoformat(), files=files,
                        total_bytes=sum(f['Size'] for f in files))
        write_json(manifest_path, manifest)
    status = dict(phase='downloading', model_id=args.model, total_files=len(manifest['files']),
                  total_bytes=manifest['total_bytes'], verified_files=[], errors={}, pid=os.getpid())
    lock = threading.Lock()

    def fetch(entry):
        path = args.output / entry['Path']
        partial = path.with_name(path.name + '.part')
        if entry['Size'] == 0:
            if entry['Sha256'] != hashlib.sha256(b'').hexdigest():
                raise ValueError('Invalid empty-file checksum in manifest')
            if path.exists() and path.stat().st_size:
                raise ValueError('Refusing to replace an existing nonempty file')
            path.write_bytes(b'')
            return entry['Path']
        if path.exists():
            if path.stat().st_size == entry['Size'] and digest(path) == entry['Sha256']:
                return entry['Path']
            raise RuntimeError(f'Existing complete file failed validation: {path.name}; preserving it')
        url = base + '/repo?' + urllib.parse.urlencode(
            {'Revision': entry['Revision'], 'FilePath': entry['Path']})
        for attempt in range(4):
            try:
                offset = partial.stat().st_size if partial.exists() else 0
                if offset > entry['Size']:
                    raise ValueError('Partial file exceeds declared size')
                if offset < entry['Size']:
                    headers = {'User-Agent': 'crossing-offline-checkpoint/1.0'}
                    if offset:
                        headers['Range'] = f'bytes={offset}-'
                    command = ['curl','--location','--fail','--silent','--show-error',
                               '--proxy','','--noproxy','*','--connect-timeout','15',
                               '--max-time','900','--speed-time','60','--speed-limit','1024',
                               '--output',str(partial)]
                    if offset:
                        command.extend(['--continue-at','-'])
                    result = subprocess.run(command+[url],capture_output=True,text=True)
                    if result.returncode == 33 and offset:
                        result = subprocess.run(command[:-2]+[url],capture_output=True,text=True)
                    if result.returncode:
                        raise RuntimeError(f'Direct curl transfer failed: {result.returncode}')
                if partial.stat().st_size != entry['Size']:
                    raise ValueError('Downloaded length differs from manifest')
                if digest(partial) != entry['Sha256']:
                    raise ValueError('SHA256 mismatch; partial file preserved')
                partial.replace(path)
                return entry['Path']
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))

    write_json(args.output / 'download_status.json', status)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(fetch, f): f for f in manifest['files']}
        for future in concurrent.futures.as_completed(pending):
            entry = pending[future]
            try:
                filename = future.result()
                status['verified_files'].append(filename)
                print(json.dumps({'verified': filename, 'bytes': entry['Size']}), flush=True)
            except Exception as error:
                status['errors'][entry['Path']] = type(error).__name__ + ': ' + str(error)
                print(json.dumps({'failed': entry['Path'], 'error': type(error).__name__}), flush=True)
            with lock:
                status['updated_at'] = datetime.now(timezone.utc).isoformat()
                write_json(args.output / 'download_status.json', status)
    status['phase'] = 'failed' if status['errors'] else 'verified'
    status['updated_at'] = datetime.now(timezone.utc).isoformat()
    write_json(args.output / 'download_status.json', status)
    if status['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
