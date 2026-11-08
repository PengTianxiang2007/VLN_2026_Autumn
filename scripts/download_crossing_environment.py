"""Resume the frozen missing vLLM wheels from the domestic mirror, then verify all hashes."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/crossing_checkpoint/seed2_v1_20261103/environment_qwen27'
WHEELS = ROOT / '.runtime/crossing_wheelhouse'


def write(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def valid(entry):
    path = WHEELS / entry['filename']
    if not path.is_file() or Path(str(path) + '.aria2').exists():
        return False
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest() == entry['sha256']


def main():
    lock = (OUT / 'download.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    manifest = json.loads((WHEELS / 'manifest.json').read_text())
    assert manifest and all(e['url'].startswith('https://mirrors.aliyun.com/pypi/') for e in manifest)
    env = {k: v for k, v in os.environ.items() if 'proxy' not in k.lower()}
    state = dict(pid=os.getpid(), transport='direct_no_proxy', total_files=len(manifest))
    child = None

    def publish(phase, **kwargs):
        state.update(phase=phase, updated_at=time.time(), **kwargs)
        write(OUT / 'download_status.json', state)

    def stop(signum, frame):
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGINT)
        publish('stopped', signal=signum)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for attempt in range(1, 7):
        pending = [e for e in manifest if not valid(e)]
        if not pending:
            write(WHEELS / 'verified.json', dict(passed=True, verified_at=time.time(), files=manifest))
            publish('verified', verified_files=len(manifest))
            return
        inputs = WHEELS / 'download.txt'
        inputs.write_text(''.join(
            f"{e['url']}\n  dir={WHEELS}\n  out={e['filename']}\n  checksum=sha-256={e['sha256']}\n"
            for e in pending))
        command = ['aria2c', '--no-conf=true', '--all-proxy=', '--user-agent=curl/8.5.0',
                   '--max-connection-per-server=8', '--split=8', '--max-concurrent-downloads=4',
                   '--min-split-size=4M', '--file-allocation=none', '--continue=true',
                   '--auto-file-renaming=false', '--check-integrity=true', '--max-tries=8',
                   '--retry-wait=3', '--timeout=120', '--connect-timeout=15',
                   '--summary-interval=30', '--show-console-readout=false',
                   '--console-log-level=notice', '--download-result=full',
                   '--input-file=' + str(inputs)]
        with (OUT / 'prefetch.log').open('a') as log:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
        publish('downloading', attempt=attempt, downloader_pid=child.pid,
                verified_files=len(manifest)-len(pending), remaining_files=len(pending))
        code = child.wait()
        publish('checking_downloads', exit_code=code)
        if code:
            time.sleep(10)
    pending = [e['filename'] for e in manifest if not valid(e)]
    if pending:
        publish('failed', missing=pending)
        raise SystemExit(1)
    write(WHEELS / 'verified.json', dict(passed=True, verified_at=time.time(), files=manifest))
    publish('verified', verified_files=len(manifest))


if __name__ == '__main__':
    main()
