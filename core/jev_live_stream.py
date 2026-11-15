"""Causal JEV scoring hooks for live VLNVerse navigation."""
import concurrent.futures
import fcntl
import json
import os
import re
import time
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

from core.agent_route_choice import now
from core.vlnverse_review import recording_only, write_json
from core.jev_request_runner import run_jev_task, sha
from core.jev_stream import (
    OnlineProminence,
    offline_nodes,
    offline_streaming_prominence,
)


class JevLiveReview:
    """Observe policy RGB online without changing navigation or its score."""

    def __init__(self, settings, run_id, dataset):
        del dataset
        self.root = Path(settings['output_dir']).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.seed = int(settings['seed'])
        self.window_n = int(settings.get('window_n', 11))
        self.max_delay = int(settings.get('max_delay_steps', 5))
        self.max_in_flight = int(settings.get('max_in_flight', 5))
        self.attempts = int(settings.get('attempts', 5))
        self.timeout = float(settings.get('timeout', 120))
        self.endpoint = settings.get(
            'endpoint', 'https://api.site/v1/systemone'
        )
        self.model = settings.get('model', 'jev-1.14.0')
        if self.window_n < 3 or self.window_n % 2 == 0:
            raise ValueError('JEV live window_n must be odd and >= 3')
        if not 0 <= self.max_delay <= 5:
            raise ValueError('JEV live max_delay_steps must be in [0, 5]')
        if not 1 <= self.max_in_flight <= 5:
            raise ValueError('JEV live max_in_flight must be in [1, 5]')
        if not os.environ.get('JEV_API_KEY'):
            raise RuntimeError('JEV_API_KEY is required for live scoring')
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_in_flight
        )
        self.active = None
        self.pending = deque()
        self.sampler = None

    def _safe_name(self, value):
        value = str(value)
        return value if re.fullmatch(r'[A-Za-z0-9_.-]+', value) else 'episode_' + sha_text(value)

    def _status(self):
        if self.active is None:
            return
        payload = {
            key: self.active[key]
            for key in (
                'run_id', 'seed', 'scene', 'episode_id', 'path_key',
                'step', 'resolved_calls', 'expected_calls',
                'max_unresolved_step_lag', 'status',
            )
        }
        payload['pending_calls'] = len(self.pending)
        payload['updated_at'] = now()
        write_json(self.active['directory_path'] / 'status.json', payload)

    def _resolve_call(self, item, resolved_at, after_stream_end=False):
        meta, future = item
        try:
            row = future.result()
        except BaseException as error:
            row = {
                **{key: meta['task'][key] for key in (
                    'episode_id', 'scene', 'group', 'frame', 'images',
                    'question_version'
                )},
                'phase': 'failed',
                'error': type(error).__name__ + ': ' + str(error),
            }
        lag = resolved_at - meta['submitted_at']
        row.update({
            'stream_index': meta['index'],
            'submitted_at_stream_index': meta['submitted_at'],
            'resolved_at_stream_index': resolved_at,
            'unresolved_step_lag': lag,
        })
        if after_stream_end:
            row['resolved_after_stream_end'] = True
        probability = (
            row['answer']['probability_yes']
            if row.get('phase') == 'complete'
            else None
        )
        self.sampler.resolve(meta['index'], probability)
        self.active['resolved_calls'] += 1
        self.active['calls'].append(row)
        if not after_stream_end:
            self.active['max_unresolved_step_lag'] = max(
                self.active['max_unresolved_step_lag'], lag
            )
        with (self.active['directory_path'] / 'calls.jsonl').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        self._status()

    @recording_only
    def start(self, path_key):
        if self.active is not None:
            raise RuntimeError('Previous live JEV episode is still active')
        if self.pending:
            raise RuntimeError('Pending live JEV calls survived episode boundary')
        path_key = str(path_key)
        key_parts = path_key.split('_')
        scene = next(
            (
                '_'.join(key_parts[index:index + 2])
                for index in range(len(key_parts) - 1)
                if key_parts[index] == 'kujiale' and key_parts[index + 1].isdigit()
            ),
            'unknown_scene',
        )
        scene_marker = scene + '_'
        scene_position = path_key.find(scene_marker)
        episode_id = (
            path_key[scene_position + len(scene_marker):]
            if scene_position >= 0 else path_key
        )
        directory = (
            self.root / ('seed_%d' % self.seed) / self._safe_name(scene)
            / self._safe_name(episode_id) / ('attempt_%d' % time.time_ns())
        )
        directory.mkdir(parents=True, exist_ok=False)
        (directory / 'frames').mkdir()
        self.active = {
            'run_id': self.run_id,
            'seed': self.seed,
            'scene': scene,
            'episode_id': episode_id,
            'path_key': path_key,
            'directory': str(directory),
            'directory_path': directory,
            'step': 0,
            'resolved_calls': 0,
            'expected_calls': 0,
            'max_unresolved_step_lag': 0,
            'calls': [],
            'history': deque(maxlen=3),
            'status': 'running',
            'started_at': now(),
            'window_n': self.window_n,
            'max_delay_steps': self.max_delay,
            'max_in_flight': self.max_in_flight,
        }
        self.sampler = OnlineProminence(self.window_n, self.max_delay)
        write_json(directory / 'case.json', {
            key: value for key, value in self.active.items()
            if key not in ('history', 'directory_path')
        })
        self._status()
        print(
            'JEV_LIVE_START %s %s' % (self.seed, episode_id),
            flush=True,
        )

    @recording_only
    def observe(self, path_key, observation, action, terminal=False):
        if self.active is None:
            return
        if str(path_key) != self.active['path_key']:
            raise ValueError('Live JEV episode association changed')
        if terminal:
            self.active['terminal_observation'] = True
            return
        rgb = observation.get('rgb')
        if rgb is None:
            raise ValueError('Live JEV requires RGB observation')
        rgb = np.asarray(rgb)
        if rgb.dtype != np.uint8 or rgb.shape != (480, 640, 3):
            raise ValueError('Unexpected live RGB shape or dtype')
        index = self.active['step']
        episode_dir = self.active['directory_path']
        image_path = episode_dir / 'frames' / ('F%06d.jpg' % index)
        Image.fromarray(rgb).save(image_path, quality=92, subsampling=0)
        image = {
            'frame': index,
            'rgb': str(image_path.relative_to(episode_dir)),
            'rgb_sha256': sha(image_path),
        }
        self.active['history'].append(image)
        self.sampler.add_pending()
        self.active['expected_calls'] += 1
        while self.pending and (
            len(self.pending) >= self.max_in_flight
            or index - self.pending[0][0]['submitted_at'] > self.max_delay
        ):
            self._resolve_call(self.pending.popleft(), index)
        images = list(self.active['history'])
        task = {
            'episode_id': self.active['episode_id'],
            'scene': self.active['scene'],
            'group': 'live_navigation',
            'frame': index,
            'images': images,
            'question_version': 'v004',
            'dataset': str(episode_dir),
            'output': str(episode_dir),
            'endpoint': self.endpoint,
            'model': self.model,
            'timeout': self.timeout,
            'attempts': self.attempts,
        }
        future = self.executor.submit(run_jev_task, task)
        self.pending.append((
            {'index': index, 'submitted_at': index, 'task': task},
            future,
        ))
        position = observation.get('globalgps')
        if position is None:
            position = observation.get('current_pose')
        self.active.setdefault('actions', []).append({
            'step': index,
            'action': action,
            'position': (
                np.asarray(position).astype(float).tolist()
                if position is not None else None
            ),
            'image': image['rgb'],
        })
        self.active['step'] += 1
        self._status()

    @recording_only
    def finish(self, path_key, metrics):
        if self.active is None:
            return
        if str(path_key) != self.active['path_key']:
            raise ValueError('Live JEV finish association changed')
        final_index = max(0, self.active['step'] - 1)
        while self.pending:
            self._resolve_call(
                self.pending.popleft(), final_index, after_stream_end=True
            )
        nodes = self.sampler.finish()
        raw = self.sampler.raw
        reference = offline_streaming_prominence(
            raw, self.window_n, self.max_delay
        )
        reference_nodes = offline_nodes(reference, self.window_n)
        numeric_metrics = {
            key: float(metrics[key])
            for key in ('success', 'spl', 'NE', 'osr', 'TL', 'steps')
            if key in metrics
        }
        result = {
            key: value
            for key, value in self.active.items()
            if key not in ('history', 'calls', 'directory_path')
        }
        result.update({
            'status': 'complete',
            'finished_at': now(),
            'metrics': numeric_metrics,
            'fail_reason': metrics.get('fail_reason'),
            'calls': self.active['calls'],
            'streaming': {
                'window_n': self.window_n,
                'max_delay_steps': self.max_delay,
                'raw': raw,
                'filtered': self.sampler.out,
                'nodes': nodes,
                'max_online_node_lag': self.sampler.max_node_lag,
                'prefix_invariant': True,
            },
            'offline_reference': {
                'filtered': reference,
                'nodes': reference_nodes,
            },
        })
        write_json(self.active['directory_path'] / 'episode.json', result)
        with (self.root / 'index.jsonl').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.write(json.dumps({
                'seed': self.seed,
                'scene': self.active['scene'],
                'episode_id': self.active['episode_id'],
                'directory': self.active['directory'],
                'metrics': numeric_metrics,
                'fail_reason': metrics.get('fail_reason'),
                'steps': self.active['step'],
                'valid_calls': sum(
                    call.get('phase') == 'complete'
                    for call in self.active['calls']
                ),
                'expected_calls': self.active['expected_calls'],
                'max_unresolved_step_lag': self.active[
                    'max_unresolved_step_lag'
                ],
                'online_nodes': len(nodes),
            }, ensure_ascii=False) + '\n')
        print(
            'JEV_LIVE_FINISH %s %s calls=%d/%d nodes=%d lag=%d' % (
                self.seed,
                self.active['episode_id'],
                sum(
                    call.get('phase') == 'complete'
                    for call in self.active['calls']
                ),
                self.active['expected_calls'],
                len(nodes),
                self.active['max_unresolved_step_lag'],
            ),
            flush=True,
        )
        self.active = None
        self.sampler = None

    def close(self):
        if self.active is not None:
            raise RuntimeError('Cannot close live JEV with an active episode')
        self.executor.shutdown(wait=True)


def sha_text(value):
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()[:16]
