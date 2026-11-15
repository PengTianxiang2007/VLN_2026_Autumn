"""Publish an HTML and explicitly selected assets; verify remote and public SHA256."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import tarfile
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
SAFE_PART = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*\Z')
STATIC_SUFFIXES = {'.html', '.htm', '.css', '.js', '.json', '.png', '.jpg', '.jpeg',
                   '.webp', '.gif', '.svg', '.ico', '.mp4', '.webm', '.woff',
                   '.woff2', '.ttf', '.otf', '.ttc', '.vtt', '.zip'}


def digest(stream):
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(chunk)
    return value.hexdigest()


def prepare_files(html, assets):
    html = html.absolute()
    if html.suffix.lower() not in {'.html', '.htm'}:
        raise ValueError('Expected an HTML entry file')
    base = html.parent.resolve()
    files = {}
    for relative in [Path(html.name), *assets]:
        if relative.is_absolute() or not all(SAFE_PART.fullmatch(p) for p in relative.parts):
            raise ValueError('Use relative asset paths with plain letters, digits, _, - or .')
        path = base / relative
        if path.suffix.lower() not in STATIC_SUFFIXES or not path.is_file():
            raise ValueError('Not a supported static file: ' + str(relative))
        if any((base / Path(*relative.parts[:i])).is_symlink()
               for i in range(1, len(relative.parts) + 1)):
            raise ValueError('Symlink assets are not allowed: ' + str(relative))
        with path.open('rb') as stream:
            sha = digest(stream)
        files[relative.as_posix()] = {'path': relative.as_posix(), 'sha256': sha,
                                      'bytes': path.stat().st_size}
    return base, list(files.values())


RESERVE = """
import json, pathlib, sys
p = json.load(sys.stdin)
root = pathlib.Path(p['remote_root'])
if not root.is_dir() or root.is_symlink():
    raise RuntimeError('Provision and verify the project root first')
destination = root / p['name']
destination.mkdir(mode=0o700, exist_ok=False)
for row in p['files']:
    (destination / row['path']).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
"""

FINALIZE = """
import hashlib, json, os, pathlib, sys
p = json.load(sys.stdin)
destination = pathlib.Path(p['remote_root']) / p['name']
for row in p['files']:
    source = destination / (row['path'] + '.uploading')
    h = hashlib.sha256()
    with source.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    if source.stat().st_size != row['bytes'] or h.hexdigest() != row['sha256']:
        raise RuntimeError('Upload integrity mismatch: ' + row['path'])
for row in p['files']:
    target = destination / row['path']
    source = destination / (row['path'] + '.uploading')
    os.link(source, target)  # Atomic, refuses to overwrite an existing file.
    source.unlink()
    target.chmod(0o644)
for parent, dirs, files in os.walk(destination, topdown=False):
    pathlib.Path(parent).chmod(0o755)
"""

VERIFY = """
import hashlib, json, pathlib, sys
p = json.load(sys.stdin)
destination = pathlib.Path(p['remote_root']) / p['name']
for row in p['files']:
    target = destination / row['path']
    h = hashlib.sha256()
    with target.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    if target.stat().st_size != row['bytes'] or h.hexdigest() != row['sha256']:
        raise RuntimeError('Existing remote file mismatch: ' + row['path'])
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--name', required=True, help='New unique release name; existing names fail')
    parser.add_argument('--asset', type=Path, action='append', default=[],
                        help='Explicit static file, relative to the HTML directory; repeat as needed')
    parser.add_argument('--ssh-control-path', type=Path, help='Reuse an authenticated SSH session')
    parser.add_argument('--identity-file', type=Path, help='Existing SSH key, never copied or logged')
    parser.add_argument('--verify-only', action='store_true', help='Recheck an existing release without uploading or changing it')
    parser.add_argument('--user-proxy', action='store_true', help='Try HTTP via 127.0.0.1:7892; fall back to direct if unavailable')
    parser.add_argument('--full-http-check', action='store_true', help='Optional full HTTP download and hash check; default is a quick HEAD check')
    parser.add_argument('--dry-run', action='store_true', help='Validate local files, without network or writes')
    args = parser.parse_args()
    if not SAFE_PART.fullmatch(args.name):
        parser.error('--name must contain only plain letters, digits, _, - or .')
    config_path = ROOT / 'core/visualization_publish.json'
    config = json.loads(config_path.read_text())
    base, files = prepare_files(args.html, args.asset)
    url_base = config['public_base_url'].rstrip('/') + '/' + quote(args.name) + '/'
    record = {'name': args.name, 'source_directory': str(base), 'files': files,
              'url': url_base + quote(args.html.name), 'phase': 'prepared',
              'verify_only': args.verify_only,
              'http_check': 'full_download' if args.full_http_check else 'head',
              'http_route': 'user_proxy_127.0.0.1_7892' if args.user_proxy else 'direct',
              'created_at': datetime.now(timezone.utc).isoformat(),
              'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest()}
    if args.dry_run:
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    record_dir = ROOT / 'outputs/visualization_publishing' / ('publish_' + stamp)
    record_dir.mkdir(parents=True, exist_ok=False)
    record_path = record_dir / 'publication.json'

    def save():
        record['updated_at'] = datetime.now(timezone.utc).isoformat()
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')

    save()
    print('Publication record: ' + str(record_path), flush=True)
    host = config['ssh_user'] + '@' + config['ssh_host']
    payload = dict(remote_root=config['remote_root'], name=args.name, files=files)
    with tempfile.TemporaryDirectory(prefix='vln-publish-') as temp:
        known_hosts = Path(temp) / 'known_hosts'
        known_hosts.write_text(config['ssh_host'] + ' ' + config['host_key'] + '\n')
        control = str(args.ssh_control_path or Path(temp) / 'control')
        options = ['-o', 'ConnectTimeout=15', '-o', 'StrictHostKeyChecking=yes',
                   '-o', 'UserKnownHostsFile=' + str(known_hosts), '-o', 'HostKeyAlgorithms=ssh-ed25519',
                   '-o', 'ControlMaster=auto', '-o', 'ControlPersist=120',
                   '-o', 'ControlPath=' + control]
        if args.identity_file:
            options += ['-i', str(args.identity_file)]
        ssh_env = os.environ.copy()
        credentials = ROOT / config['credentials_file']
        if not args.identity_file and credentials.is_file():
            helper = Path(temp) / 'askpass.py'
            helper.write_text('#!/usr/bin/env python3\nimport json, os\n'
                              "with open(os.environ['VLN_PUBLISH_CREDENTIALS']) as f:\n"
                              "    print(json.load(f)['password'])\n")
            helper.chmod(0o700)
            ssh_env.update(SSH_ASKPASS=str(helper), SSH_ASKPASS_REQUIRE='force',
                           DISPLAY=ssh_env.get('DISPLAY') or ':0',
                           VLN_PUBLISH_CREDENTIALS=str(credentials))

        def remote(code):
            subprocess.run(['ssh', *options, host, 'python3 -c ' + shlex.quote(code)],
                           input=json.dumps(payload), text=True, check=True, timeout=180, env=ssh_env)

        try:
            if args.verify_only:
                remote(VERIFY)
            else:
                remote(RESERVE)
                record['phase'] = 'uploading'
                save()
                if len(files) > 1:
                    archive = Path(temp) / 'assets.tar'
                    with tarfile.open(archive, 'w') as tar:
                        for row in files:
                            tar.add(base / row['path'], arcname=row['path'] + '.uploading', recursive=False)
                    target = config['remote_root'] + '/' + args.name + '/.transfer.tar'
                    subprocess.run(['scp', *options, str(archive), host + ':' + target],
                                   check=True, timeout=1800, env=ssh_env)
                    remote("import json,pathlib,subprocess,sys\np=json.load(sys.stdin)\nd=pathlib.Path(p['remote_root'])/p['name']\na=d/'.transfer.tar'\nsubprocess.run(['tar','-xf',str(a),'-C',str(d)],check=True)\na.unlink()")
                else:
                    for row in files:
                        target = config['remote_root'] + '/' + args.name + '/' + row['path'] + '.uploading'
                        subprocess.run(['scp', *options, str(base / row['path']), host + ':' + target],
                                       check=True, timeout=1800, env=ssh_env)
                remote(FINALIZE)
            record['phase'] = 'public_unverified'
            record['remote_sha256_verified'] = True
            save()
            proxy = {'http': 'http://127.0.0.1:7892', 'https': 'http://127.0.0.1:7892'} if args.user_proxy else {}
            for row in files:
                if row['path'] != args.html.name and not args.full_http_check:
                    row['http_check'] = 'not_requested; remote_sha256_verified'
                    continue
                url = url_base + quote(row['path'])
                routes = [proxy, {}] if args.user_proxy else [{}]
                for attempt, route in enumerate(routes):
                    try:
                        opener = build_opener(ProxyHandler(route))
                        request = Request(url, method='GET' if args.full_http_check else 'HEAD',
                                          headers={'Accept-Encoding': 'gzip' if args.full_http_check else 'identity'})
                        with opener.open(request, timeout=60 if args.full_http_check else 10) as response:
                            if response.status != 200 or response.geturl() != url:
                                raise RuntimeError('Unexpected HTTP response for ' + row['path'])
                            if row['path'] == args.html.name and response.headers.get_content_type() != 'text/html':
                                raise RuntimeError('HTML served with an incorrect content type')
                            if args.full_http_check:
                                encoding = response.headers.get('Content-Encoding', 'identity')
                                if encoding not in {'identity', 'gzip'}:
                                    raise RuntimeError('Unsupported content encoding: ' + encoding)
                                stream = gzip.GzipFile(fileobj=response) if encoding == 'gzip' else response
                                if digest(stream) != row['sha256']:
                                    raise RuntimeError('Public HTTP integrity mismatch for ' + row['path'])
                            elif response.headers.get('Content-Length') is not None:
                                if int(response.headers['Content-Length']) != row['bytes']:
                                    raise RuntimeError('Public HTTP size mismatch for ' + row['path'])
                        row['http_route'] = 'user_proxy_127.0.0.1_7892' if route else 'direct'
                        if args.user_proxy and not route:
                            record['proxy_fallback_to_direct'] = True
                            record['http_route'] = 'direct'
                        break
                    except Exception:
                        if attempt == len(routes) - 1:
                            raise
                row['http_status'] = 200
                row['http_sha256_verified'] = args.full_http_check
            record['phase'] = 'published'
            record['browser_check'] = 'optional; not run by the publishing tool'
            save()
            print(record['url'])
        except BaseException as error:
            record['failed_during'] = record['phase']
            record['phase'] = 'failed'
            record['error'] = type(error).__name__ + ': ' + str(error)
            save()
            raise
        finally:
            if not args.ssh_control_path:
                subprocess.run(['ssh', '-S', control, '-O', 'exit', host],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)


if __name__ == '__main__':
    main()
