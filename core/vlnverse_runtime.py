"""Resource placement and bounded recovery; never changes navigation policy."""
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
    if 'needs' in message and 'MiB' in message or 'MiB free; require' in message:
        return 'gpu_admission'
    return 'unclassified'

def retry_delay(kind, failures):
    if kind in ('gpu_oom', 'model_startup_timeout', 'gpu_admission') and failures <= 3:
        return 60 * 2 ** (failures - 1)
    return None
