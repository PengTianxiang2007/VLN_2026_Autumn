"""Self-contained JEV request execution for live navigation processes."""
import hashlib
import os
import time
from pathlib import Path

from core.agent_route_choice import write
from core.jev_node import (
    build_compact_fallback_noul_request,
    build_near_fallback_noul_request,
    build_noul_request,
    call_api,
    request_digest,
    request_without_images,
    validate_noul_response,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_jev_task(task):
    """Run one isolated JEV request and return an auditable result record."""
    key = os.environ.get('JEV_API_KEY', '')
    if not key:
        return dict(**task, phase='failed', error='JEV_API_KEY is missing')
    folder = (
        Path(task['output']) / 'cases' / task['episode_id']
        / ('F%06d' % task['frame'])
    )
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        version = task.get('question_version', 'v002')
        builder = {
            'v002': build_noul_request,
            'v003': build_near_fallback_noul_request,
            'v004': build_compact_fallback_noul_request,
        }[version]
        request, image_audit = builder(
            task['images'], task['dataset'], model=task['model']
        )
        write(folder / 'request.json', {
            **request_without_images(request),
            'request_sha256': request_digest(request),
            'question_version': version,
        })
        write(folder / 'images.json', image_audit)
        raw, latency, transport = call_api(
            task['endpoint'],
            key,
            request,
            task['timeout'],
            folder / 'request_full.json',
            attempts=task['attempts'],
        )
        probability = validate_noul_response(raw)
        record = {
            'phase': 'complete',
            'episode_id': task['episode_id'],
            'scene': task['scene'],
            'group': task['group'],
            'frame': task['frame'],
            'image_frames': [row['frame'] for row in task['images']],
            'answer': probability,
            'request_sha256': request_digest(request),
            'question_version': version,
            'latency_seconds': latency,
            'transport': transport,
        }
        write(folder / 'response.json', raw)
        write(folder / 'result.json', record)
        return record
    except Exception as error:
        record = {
            'phase': 'failed',
            'episode_id': task['episode_id'],
            'scene': task['scene'],
            'group': task['group'],
            'frame': task['frame'],
            'image_frames': [row['frame'] for row in task['images']],
            'latency_seconds': time.monotonic() - started,
            'error': str(error).replace(key, '[REDACTED]'),
        }
        write(folder / 'error.json', record)
        return record
