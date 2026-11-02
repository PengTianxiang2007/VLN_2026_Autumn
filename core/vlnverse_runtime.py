"""Resource placement and bounded recovery; never changes navigation policy."""
import json
from pathlib import Path
import time

OOM_MARKERS = ('ERROR_OUT_OF_DEVICE_MEMORY', 'Out of GPU memory', 'CUDA out of memory')

def placement(rows, allowed, busy, separate=False):
    order = allowed if allowed is not None else [r['index'] for r in rows]
    free = {r['index']: r['free_mib'] for r in rows
            if r['index'] in order and r['index'] not in busy and r['utilization'] <= 15}
    if separate:
        # Give the simulator the most headroom, reserving a different model GPU.
        for sim in sorted(free, key=lambda i: -free[i]):
            if free[sim] < 40000:
                continue
            for model in order:
                if model != sim and free.get(model, 0) >= 25000:
                    return model, sim
        return None
    for gpu in order:
        if free.get(gpu, 0) >= 34000:
            return gpu, gpu
    return None

def failure_kind(message):
    if any(marker in message for marker in OOM_MARKERS):
        return 'gpu_oom'
    if 'Model loading timeout' in message:
        return 'model_startup_timeout'
    if ('needs' in message and 'MiB' in message) or 'MiB free; require' in message:
        return 'gpu_admission'
    return 'unclassified'


def log_tail(path, limit=65536):
    """Read only a bounded tail, including for multi-GB simulator logs."""
    try:
        with Path(path).open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - limit))
            return stream.read(limit).decode('utf-8', errors='replace')
    except FileNotFoundError:
        return ''


class RuntimeFailure(RuntimeError):
    def __init__(self, message, phase, log_path=None, returncode=None):
        tail = log_tail(log_path) if log_path is not None else ''
        self.record = dict(kind=failure_kind(message + '\n' + tail), error=message,
                           phase=phase, returncode=returncode)
        if log_path is not None:
            self.record.update(log_path=str(log_path), log_tail=tail)
        super().__init__(f'{message} [{self.record["kind"]}, {phase}]; see {log_path}')


def failure_record(error):
    if isinstance(error, RuntimeFailure):
        return dict(error.record)
    return dict(kind=failure_kind(str(error)), error=str(error), phase='runner')


def worker_failure(path, launch_log, returncode):
    """Early admission/launcher errors can occur before run.json is created."""
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text())
    return RuntimeFailure('Worker exited before recording failure', 'launcher',
                          launch_log, returncode).record


def needs_separate_gpus(failure):
    # Loading/inference OOM on the model card is not evidence of a large scene.
    return failure['kind'] == 'gpu_oom' and failure.get('phase') == 'simulator'


def wait_for_model_ready(process, chunk, timeout=900, interval=2):
    chunk = Path(chunk)
    deadline = time.monotonic() + timeout
    while True:
        rc = process.poll()
        if rc is not None:
            raise RuntimeFailure('Model service failed', 'model_startup', chunk/'agent.log', rc)
        if (chunk/'ready.json').exists():
            return json.loads((chunk/'ready.json').read_text())
        if time.monotonic() >= deadline:
            raise RuntimeFailure('Model loading timeout', 'model_startup', chunk/'agent.log')
        time.sleep(interval)


class OOMLogMonitor:
    """Incremental scan, including markers split across reads and final exit logs."""
    def __init__(self, path, phase):
        self.path, self.phase = Path(path), phase
        self.offset, self.tail = 0, ''

    def check(self):
        if not self.path.exists():
            return
        with self.path.open('r', errors='replace') as stream:
            stream.seek(self.offset)
            while True:
                block = stream.read(65536)
                if not block:
                    break
                self.tail += block
                if any(marker in self.tail for marker in OOM_MARKERS):
                    raise RuntimeFailure('Out of GPU memory in ' + self.phase,
                                         self.phase, self.path)
                self.tail = self.tail[-128:]
            self.offset = stream.tell()

def retry_delay(kind, failures):
    if kind in ('gpu_oom', 'model_startup_timeout', 'gpu_admission') and failures <= 3:
        return 60 * 2 ** (failures - 1)
    return None
