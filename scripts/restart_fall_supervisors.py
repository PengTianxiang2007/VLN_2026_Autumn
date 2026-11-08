"""Replace this experiment's schedulers at worker boundaries; leave navigation workers running."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from scripts.test_fall_retries import admission_failure, process_alive, write_json, now


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return dict(state=fields[0], start_ticks=fields[19])
    except FileNotFoundError:
        return None


def same_process(pid, initial):
    current = identity(pid)
    return current and current['start_ticks'] == initial['start_ticks'] and current['state'] not in ('Z', 'X')


def handover(campaign):
    lock = (campaign / 'supervisor_handover.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    source = PROJECT / 'scripts/test_fall_retries.py'
    record = dict(status='draining_existing_workers', started_at=now(), manager_pid=os.getpid(),
                  supervisor_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), arms={})
    old = {}
    try:
        # Validate ownership and reasons for all requested replacements first.
        for arm in ('reset', 'replay'):
            status = json.loads((campaign / f'status_{arm}.json').read_text())
            if any(admission_failure(f)['kind'] != 'gpu_admission' for f in status.get('blocked_units', {}).values()):
                raise RuntimeError('Refusing to automatically clear an unrelated runtime failure')
            pid = status['supervisor_pid']
            initial = identity(pid)
            if initial is None or initial['state'] in ('Z', 'X'):
                raise RuntimeError('Expected the recorded supervisor to be alive')
            args = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
            if (b'scripts/test_fall_retries.py' not in args or b'run' not in args
                    or str(campaign).encode() not in args or arm.encode() not in args):
                raise RuntimeError('Supervisor process identity does not match this campaign')
            old[arm] = dict(pid=pid, identity=initial, paused=False)
            write_json(campaign / f'handover_previous_{arm}.json', status)
        for arm, prior in old.items():
            if not same_process(prior['pid'], prior['identity']):
                raise RuntimeError('Supervisor identity changed before handover')
            # PID only: never signal its process group or navigation children.
            os.kill(prior['pid'], signal.SIGSTOP)
            prior['paused'] = True
            for _ in range(40):
                current = identity(prior['pid'])
                if current and current['state'] in ('T', 't'):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError('Scheduler did not stop admitting work')
            children = Path(f'/proc/{prior["pid"]}/task/{prior["pid"]}/children').read_text().split()
            prior['children'] = {int(pid): identity(int(pid)) for pid in children}
            record['arms'][arm] = dict(old_supervisor_pid=prior['pid'], worker_pids=list(prior['children']),
                                       status='waiting_for_existing_workers')
        while old:
            for arm, prior in list(old.items()):
                active = [pid for pid, initial in prior['children'].items() if initial and same_process(pid, initial)]
                record['arms'][arm]['active_old_children'] = active
                if active:
                    continue
                if same_process(prior['pid'], prior['identity']):
                    # Current workers have all exited. The existing cleanup handler
                    # can now reap them without interrupting a trial.
                    os.kill(prior['pid'], signal.SIGTERM)
                    os.kill(prior['pid'], signal.SIGCONT)
                    prior['paused'] = False
                    deadline = time.monotonic() + 30
                    while same_process(prior['pid'], prior['identity']):
                        if time.monotonic() >= deadline:
                            raise RuntimeError('Old supervisor did not release its campaign lock')
                        time.sleep(0.2)
                env = {k: v for k, v in os.environ.items() if not k.lower().endswith('_proxy')}
                env.update(PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1')
                with (campaign / f'supervisor_{arm}.log').open('a') as log:
                    process = subprocess.Popen([sys.executable, 'scripts/test_fall_retries.py', 'run',
                                                '--campaign', str(campaign), '--arm', arm],
                                               cwd=PROJECT, env=env, stdin=subprocess.DEVNULL,
                                               stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                (campaign / f'supervisor_{arm}.pid').write_text(str(process.pid) + '\n')
                record['arms'][arm].update(status='restarted', new_supervisor_pid=process.pid, restarted_at=now())
                print(json.dumps(dict(event='supervisor_replaced', arm=arm, old_pid=prior['pid'], new_pid=process.pid)), flush=True)
                del old[arm]
            record['updated_at'] = now()
            write_json(campaign / 'supervisor_handover.json', record)
            if old:
                time.sleep(5)
        record.update(status='complete', finished_at=now())
    except BaseException as error:
        record.update(status='failed', error=str(error), updated_at=now())
        raise
    finally:
        for prior in old.values():
            if prior['paused'] and same_process(prior['pid'], prior['identity']):
                os.kill(prior['pid'], signal.SIGCONT)
        write_json(campaign / 'supervisor_handover.json', record)
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    handover(parser.parse_args().campaign.resolve())
