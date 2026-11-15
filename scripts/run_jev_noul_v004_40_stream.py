"""Run 40 new episodes through v004 with two causal streaming workers.

Each worker processes one episode at a time. A JEV request is submitted as soon
as its exact t-2,t-1,t observation window arrives, and each worker keeps at most
five requests unresolved before advancing to another stream step.
"""
import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from core.agent_route_choice import now, read, write
from core.crossing_lite import windows
from core.jev_node import (
    COMPACT_FALLBACK_CONTEXT_EN,
    COMPACT_FALLBACK_CONTEXT_ZH,
    COMPACT_FALLBACK_CRITERIA_EN,
    COMPACT_FALLBACK_CRITERIA_ZH,
    COMPACT_FALLBACK_INSTRUCTIONS_EN,
    COMPACT_FALLBACK_INSTRUCTIONS_ZH,
)
from run_jev_noul_five_concurrent import DATASET, run_task, sha


QWEN_RUN = ROOT / 'outputs/crossing_checkpoint/lite_full_v001/run_20261108_01'
EXISTING_V004_SELECTIONS = (
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v004/'
    / 'run_20261108_01_two_cases/selection.json',
    ROOT
    / 'outputs/crossing_checkpoint/jev_noul_v004/'
    / 'run_20261108_03_ten_final/selection.json',
)
EXPECTED_EPISODES = 40
SHARD_COUNT = 2
WINDOW_N = 11
MAX_DELAY_STEPS = 5
MAX_IN_FLIGHT = 5


def prompt_text(language):
    if language == 'en':
        context = COMPACT_FALLBACK_CONTEXT_EN
        instructions = COMPACT_FALLBACK_INSTRUCTIONS_EN
        criteria = COMPACT_FALLBACK_CRITERIA_EN
        labels = ('State context', 'Question type', 'Question', 'true', 'false')
        colon = ':'
    else:
        context = COMPACT_FALLBACK_CONTEXT_ZH
        instructions = COMPACT_FALLBACK_INSTRUCTIONS_ZH
        criteria = COMPACT_FALLBACK_CRITERIA_ZH
        labels = ('状态上下文', '问题类型', '问题', 'true', 'false')
        colon = '：'
    return '\n'.join([
        labels[0] + colon + ' ' + context,
        '',
        labels[1] + colon + ' noul',
        labels[2] + colon + ' ' + instructions,
        '',
        labels[3] + colon + ' ' + criteria['true'],
        labels[4] + colon + ' ' + criteria['false'],
    ])


def source_snapshot(output):
    files = (
        'scripts/run_jev_noul_v004_40_stream.py',
        'scripts/run_jev_noul_five_concurrent.py',
        'core/agent_route_choice.py',
        'core/crossing_lite.py',
        'core/jev_node.py',
    )
    result = {}
    for relative in files:
        source = ROOT / relative
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        result[relative] = sha(source)
    return result


def used_v004_episodes():
    used = set()
    sources = []
    for path in EXISTING_V004_SELECTIONS:
        if not path.exists():
            raise FileNotFoundError(path)
        data = read(path)
        cases = data.get('cases', data.get('episodes', []))
        used.update(row['episode_id'] for row in cases)
        sources.append({'path': str(path), 'sha256': sha(path)})
    return used, sources


def select_cases():
    selection = read(QWEN_RUN / 'evaluation_selection.json')
    used, sources = used_v004_episodes()
    selected = []
    for group in ('failure', 'success'):
        candidates = [
            row for row in selection
            if row['group'] == group and row['episode_id'] not in used
        ]
        if len(candidates) < EXPECTED_EPISODES // 2:
            raise ValueError('Insufficient unused %s episodes' % group)
        selected.extend(candidates[:EXPECTED_EPISODES // 2])
    if len(selected) != EXPECTED_EPISODES:
        raise ValueError('Expected 40 selected episodes')
    ids = [row['episode_id'] for row in selected]
    if len(ids) != len(set(ids)) or used.intersection(ids):
        raise ValueError('Selection overlaps previous v004 work')
    shards = [
        selected[:10] + selected[20:30],
        selected[10:20] + selected[30:40],
    ]
    if sorted(row['episode_id'] for shard in shards for row in shard) != sorted(ids):
        raise ValueError('Shard partition changed selected episodes')
    return selected, shards, sources


def episode_index():
    rows = map(
        json.loads,
        (DATASET / 'inputs/episodes.jsonl').read_text().splitlines(),
    )
    return {row['episode_id']: row for row in rows}


def build_episode_plan(shards, episodes):
    plan = []
    for shard_index, shard in enumerate(shards):
        shard_rows = []
        for case in shard:
            episode = episodes[case['episode_id']]
            observations = read(DATASET / episode['observations'])
            shard_rows.append({
                **case,
                'observations': len(observations),
                'eligible': sum(1 for _ in windows(observations)),
            })
        plan.append(shard_rows)
    return plan


def offline_streaming_prominence(values, window_size, max_delay):
    """Reference implementation matching the current browser visualization."""
    count = len(values)
    sigma = max(0.5, window_size / 6.0)
    past_radius = max(1, int(math.ceil(3 * sigma)))
    smoothed = [None] * count
    for index in range(count):
        total, weight = 0.0, 0.0
        end = min(count - 1, index + max_delay)
        for other in range(max(0, index - past_radius), end + 1):
            value = values[other]
            if value is None:
                continue
            distance = other - index
            current_weight = math.exp(
                -(distance * distance) / (2 * sigma * sigma)
            )
            total += value * current_weight
            weight += current_weight
        if weight > 0:
            smoothed[index] = total / weight
    positive = [None] * count
    baseline_window = 2 * window_size + 1
    for index in range(count):
        if smoothed[index] is None:
            continue
        samples = [
            value for value in smoothed[
                max(0, index - baseline_window + 1):index + 1
            ]
            if value is not None
        ]
        if samples:
            positive[index] = max(
                0.0, smoothed[index] - sum(samples) / len(samples)
            )
    out = [None] * count
    history = []
    for index, value in enumerate(positive):
        if value is None:
            continue
        history.append(value)
        history.sort()
        p95 = history[min(len(history) - 1, int(math.floor(0.95 * len(history))))]
        out[index] = min(1.0, value / p95) if p95 > 0 else 0.0
    return out


def offline_nodes(series, window_size):
    """Exact batch sampler used by the current visualization."""
    high_threshold = 0.6
    low_threshold = 0.18
    plateau_threshold = 0.45
    min_distance = 3
    plateau_interval = 5
    plateau_minimum = 3
    warmup = max(7, window_size)
    peaks = []
    for index in range(warmup, len(series) - 2):
        value = series[index]
        if value is None or value < low_threshold:
            continue
        look = 1 if value >= high_threshold else 2
        neighbours = [
            series[other]
            for other in range(
                max(0, index - look),
                min(len(series), index + look + 1),
            )
            if other != index and series[other] is not None
        ]
        if any(value < other for other in neighbours):
            continue
        left = [
            item for item in series[
                max(0, index - min_distance):index + 1
            ]
            if item is not None
        ]
        right = [
            item for item in series[
                index:min(len(series), index + min_distance + 1)
            ]
            if item is not None
        ]
        if not left or not right:
            continue
        if min(value - min(left), value - min(right)) >= 0.03:
            peaks.append({'index': index, 'value': value, 'kind': 'peak'})
    regions = []
    current = []
    for index, value in enumerate(series):
        if value is not None and value >= plateau_threshold:
            current.append(index)
        elif current:
            regions.append(current)
            current = []
    if current:
        regions.append(current)
    plateau = []
    for region in regions:
        if len(region) < plateau_minimum:
            continue
        for offset in range(plateau_interval // 2, len(region), plateau_interval):
            index = region[offset]
            plateau.append({
                'index': index,
                'value': series[index],
                'kind': 'plateau',
            })
    candidates = sorted(
        peaks + plateau,
        key=lambda item: (-item['value'], item['index']),
    )
    nodes = []
    for candidate in candidates:
        if all(
            abs(node['index'] - candidate['index']) >= min_distance
            for node in nodes
        ):
            nodes.append(candidate)
    return sorted(nodes, key=lambda item: item['index'])


class OnlineProminence:
    """Prefix-invariant prominence and causal event sampling.

    Streaming prominence at index i freezes when raw JEV values through i+D
    have resolved. Event detection then uses only values that are already
    available, so an emitted node is never changed or removed by future frames.
    """

    def __init__(self, window_size=WINDOW_N, max_delay=MAX_DELAY_STEPS):
        if window_size < 3 or window_size % 2 == 0:
            raise ValueError('Window must be an odd integer >= 3')
        if max_delay < 0 or max_delay > 5:
            raise ValueError('Maximum delay must be between 0 and 5')
        self.window_size = window_size
        self.max_delay = max_delay
        self.raw = []
        self.final = []
        self.smoothed = []
        self.positive = []
        self.out = []
        self.history = []
        self.next_freeze = 0
        self.stream_finished = False
        self.nodes = []
        self.plateau_start = None
        self.max_node_lag = 0

    def add_pending(self):
        self.raw.append(None)
        self.final.append(False)
        self.smoothed.append(None)
        self.positive.append(None)
        self.out.append(None)

    def resolve(self, index, value):
        if not 0 <= index < len(self.raw):
            raise IndexError(index)
        if self.final[index]:
            raise ValueError('JEV stream value resolved twice')
        self.raw[index] = value
        self.final[index] = True
        self._freeze_ready()

    def finish(self):
        if not all(self.final):
            raise ValueError('Cannot finish with unresolved JEV stream values')
        self.stream_finished = True
        self._freeze_ready()
        if self.next_freeze != len(self.raw):
            raise ValueError('Online prominence did not freeze every frame')
        return self.nodes

    def _freeze_ready(self):
        count = len(self.raw)
        while self.next_freeze < count:
            index = self.next_freeze
            needed_end = min(count - 1, index + self.max_delay)
            if not self.stream_finished and not all(
                self.final[position]
                for position in range(needed_end + 1)
            ):
                break
            sigma = max(0.5, self.window_size / 6.0)
            past_radius = max(1, int(math.ceil(3 * sigma)))
            total, weight = 0.0, 0.0
            for other in range(max(0, index - past_radius), needed_end + 1):
                value = self.raw[other]
                if value is None:
                    continue
                distance = other - index
                current_weight = math.exp(
                    -(distance * distance) / (2 * sigma * sigma)
                )
                total += value * current_weight
                weight += current_weight
            if weight <= 0:
                raise ValueError('No resolved values in prominence window')
            smoothed = total / weight
            self.smoothed[index] = smoothed
            baseline_window = 2 * self.window_size + 1
            samples = [
                value for value in self.smoothed[
                    max(0, index - baseline_window + 1):index + 1
                ]
                if value is not None
            ]
            positive = max(0.0, smoothed - sum(samples) / len(samples))
            self.positive[index] = positive
            self.history.append(positive)
            self.history.sort()
            p95 = self.history[
                min(
                    len(self.history) - 1,
                    int(math.floor(0.95 * len(self.history))),
                )
            ]
            value = min(1.0, positive / p95) if p95 > 0 else 0.0
            self.out[index] = value
            self._emit_available_candidates(index)
            self.next_freeze += 1

    def _raw_neighbours(self, index, look):
        result = []
        for other in range(max(0, index - look), min(len(self.raw), index + look + 1)):
            if other != index:
                result.append((other, self.raw[other]))
        return result

    def _add_node(self, index, kind, available_at):
        if any(abs(node['index'] - index) < 3 for node in self.nodes):
            return
        self.nodes.append({
            'index': index,
            'value': self.out[index],
            'kind': kind,
            'available_at_stream_index': available_at,
            'lag_steps': available_at - index,
        })
        self.max_node_lag = max(self.max_node_lag, available_at - index)

    def _emit_available_candidates(self, available_at):
        index = available_at
        value = self.out[index]
        if value is None:
            return
        warmup = max(7, self.window_size)
        if index >= warmup and value >= 0.18:
            look = 1 if value >= 0.6 else 2
            neighbours = self._raw_neighbours(index, look)
            if neighbours and all(item is not None for _, item in neighbours):
                if all(value >= item for _, item in neighbours):
                    radius_values = [
                        self.raw[other]
                        for other in range(
                            max(0, index - 3),
                            min(len(self.raw), index + 4),
                        )
                        if other != index and self.raw[other] is not None
                    ]
                    if radius_values:
                        left = [
                            self.raw[other]
                            for other in range(max(0, index - 3), index + 1)
                            if self.raw[other] is not None
                        ]
                        right = [
                            self.raw[other]
                            for other in range(index, min(len(self.raw), index + 4))
                            if self.raw[other] is not None
                        ]
                        if (
                            left
                            and right
                            and min(value - min(left), value - min(right)) >= 0.03
                        ):
                            self._add_node(index, 'peak', available_at)
        if value >= 0.45:
            if self.plateau_start is None:
                self.plateau_start = index
            offset = index - self.plateau_start
            if offset >= 2 and (offset - 2) % 5 == 0:
                self._add_node(index, 'plateau', available_at)
        else:
            self.plateau_start = None


def acquire_key():
    key = os.environ.get('JEV_API_KEY')
    if key:
        return key
    if sys.stdin.isatty():
        import getpass
        key = getpass.getpass('JEV API key: ')
    else:
        key = sys.stdin.readline()
    key = key.strip()
    if not key:
        raise RuntimeError('JEV_API_KEY is required')
    return key


def prepare(output):
    if output.exists():
        raise ValueError('Use a new output directory')
    selected, shards, selection_sources = select_cases()
    episodes = episode_index()
    plan = build_episode_plan(shards, episodes)
    expected_calls = sum(row['eligible'] for shard in plan for row in shard)
    if expected_calls != 3369:
        raise ValueError('Unexpected call count: %d' % expected_calls)
    output.mkdir(parents=True)
    hashes = source_snapshot(output)
    write(output / 'selection.json', {
        'cases': selected,
        'rule': (
            'First 20 unused failures and first 20 unused successes in the '
            'frozen 61-case order. Previous v004 cases are excluded.'
        ),
        'source': str(QWEN_RUN / 'evaluation_selection.json'),
        'source_sha256': sha(QWEN_RUN / 'evaluation_selection.json'),
        'previous_v004_selections': selection_sources,
    })
    write(output / 'plan.json', {
        'shard_count': SHARD_COUNT,
        'workers': 2,
        'streaming': True,
        'window_n': WINDOW_N,
        'max_delay_steps': MAX_DELAY_STEPS,
        'max_in_flight_per_worker': MAX_IN_FLIGHT,
        'episodes': EXPECTED_EPISODES,
        'expected_calls': expected_calls,
        'shards': plan,
    })
    write(output / 'prompt_en.json', {
        'context': COMPACT_FALLBACK_CONTEXT_EN,
        'question': {
            'type': 'noul',
            'instructions': COMPACT_FALLBACK_INSTRUCTIONS_EN,
            'criteria': dict(COMPACT_FALLBACK_CRITERIA_EN),
        },
    })
    write(output / 'prompt_zh.json', {
        'context': COMPACT_FALLBACK_CONTEXT_ZH,
        'question': {
            'type': 'noul',
            'instructions': COMPACT_FALLBACK_INSTRUCTIONS_ZH,
            'criteria': dict(COMPACT_FALLBACK_CRITERIA_ZH),
        },
    })
    write(output / 'prompt_v004_en.txt', prompt_text('en'))
    write(output / 'prompt_v004_zh.txt', prompt_text('zh'))
    workspace = subprocess.check_output(
        ['git', 'status', '--short'], cwd=ROOT, text=True
    )
    (output / 'workspace_status.txt').write_text(workspace)
    write(output / 'manifest.json', {
        'created_at': now(),
        'git_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'dataset': str(DATASET),
        'qwen_run': str(QWEN_RUN),
        'model': 'jev-1.14.0',
        'endpoint': 'https://api.site/v1/systemone',
        'response_type': 'noul',
        'question_version': 'v004',
        'protocol': (
            'Two parallel episode workers. Exact t-2,t-1,t RGB is submitted as '
            'each stream step arrives; at most five requests per worker may be '
            'unresolved. No task, action, map, label, outcome, or prior answer '
            'is sent. Streaming Prominence uses N=11,D=5.'
        ),
        'source_sha256': hashes,
        'credential_on_disk': False,
    })
    write(output / 'status.json', {
        'phase': 'prepared_waiting_for_key',
        'created_at': now(),
        'episodes': EXPECTED_EPISODES,
        'expected_calls': expected_calls,
        'workers': 2,
        'window_n': WINDOW_N,
        'max_delay_steps': MAX_DELAY_STEPS,
    })
    print(json.dumps({
        'output': str(output),
        'episodes': EXPECTED_EPISODES,
        'expected_calls': expected_calls,
        'shards': [len(shard) for shard in plan],
    }, ensure_ascii=False, indent=2))


def refresh_prepare(output):
    """Refresh snapshots before a prepared run starts."""
    if (output / 'shard_0').exists() or (output / 'shard_1').exists():
        raise ValueError('Cannot refresh a run after workers started')
    manifest = read(output / 'manifest.json')
    hashes = source_snapshot(output)
    write(output / 'prompt_v004_en.txt', prompt_text('en'))
    write(output / 'prompt_v004_zh.txt', prompt_text('zh'))
    manifest['source_sha256'] = hashes
    manifest['artifacts_refreshed_at'] = now()
    write(output / 'manifest.json', manifest)
    print(json.dumps({
        'output': str(output),
        'refreshed_at': manifest['artifacts_refreshed_at'],
        'source_sha256': hashes,
    }, ensure_ascii=False, indent=2))


def run_episode(shard_root, case, key, args, counters):
    episode = episode_index()[case['episode_id']]
    observations = read(DATASET / episode['observations'])
    stream = list(windows(observations))
    if len(stream) != case['eligible']:
        raise ValueError('Eligible frame count changed')
    sampler = OnlineProminence(WINDOW_N, MAX_DELAY_STEPS)
    futures = {}
    rows_by_index = {}
    episode_root = shard_root / 'episodes' / case['episode_id']
    if episode_root.exists():
        raise ValueError('Episode output already exists')
    episode_root.mkdir(parents=True)
    started_at = now()
    started = time.monotonic()
    pending = deque()

    def resolve_call(item, resolved_at, after_stream_end=False):
        meta = item[0]
        future = item[1]
        task = meta['task']
        try:
            row = future.result()
        except BaseException as error:
            row = {
                **{key_name: task[key_name] for key_name in (
                    'episode_id', 'scene', 'group', 'frame', 'images',
                    'question_version'
                )},
                'phase': 'failed',
                'error': type(error).__name__ + ': ' + str(error),
            }
        lag_steps = resolved_at - meta['submitted_at']
        row.update({
            'stream_index': meta['index'],
            'submitted_at_stream_index': meta['submitted_at'],
            'resolved_at_stream_index': resolved_at,
            'unresolved_step_lag': lag_steps,
        })
        if after_stream_end:
            row['resolved_after_stream_end'] = True
        rows_by_index[meta['index']] = row
        probability = (
            row['answer']['probability_yes']
            if row.get('phase') == 'complete'
            else None
        )
        sampler.resolve(meta['index'], probability)
        counters['resolved_calls'] += 1
        if not after_stream_end:
            counters['max_unresolved_step_lag'] = max(
                counters['max_unresolved_step_lag'], lag_steps
            )

    def write_status(index, frame):
        write(shard_root / 'status.json', {
            'phase': 'running',
            'updated_at': now(),
            'current_episode': case['episode_id'],
            'current_frame': frame,
            'stream_index': index,
            'in_flight': len(pending),
            'completed_episodes': counters['completed_episodes'],
            'total_episodes': len(counters['cases']),
            'resolved_calls': counters['resolved_calls'],
            'expected_calls': counters['expected_calls'],
            'max_unresolved_step_lag': counters[
                'max_unresolved_step_lag'
            ],
        })

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(MAX_IN_FLIGHT, args.max_in_flight)
    ) as executor:
        for index, (frame, images) in enumerate(stream):
            sampler.add_pending()
            task = {
                'episode_id': case['episode_id'],
                'scene': case['scene'],
                'group': case['group'],
                'frame': frame,
                'images': images,
                'question_version': 'v004',
                'output': str(shard_root),
                'endpoint': 'https://api.site/v1/systemone',
                'model': 'jev-1.14.0',
                'timeout': args.timeout,
                'attempts': args.attempts,
            }
            future = executor.submit(run_task, task)
            metadata = {
                'index': index,
                'frame': frame,
                'submitted_at': index,
                'task': task,
            }
            pending.append((metadata, future))
            while len(pending) >= args.max_in_flight:
                resolve_call(pending.popleft(), index)
                write_status(index, frame)
        final_index = len(stream) - 1
        while pending:
            resolve_call(pending.popleft(), final_index, after_stream_end=True)
            write_status(final_index, stream[-1][0])
    nodes = sampler.finish()
    rows = [rows_by_index[index] for index in range(len(stream))]
    raw = sampler.raw
    reference = offline_streaming_prominence(raw, WINDOW_N, MAX_DELAY_STEPS)
    reference_nodes = offline_nodes(reference, WINDOW_N)
    valid = [row for row in rows if row.get('phase') == 'complete']
    result = {
        'episode_id': case['episode_id'],
        'scene': case['scene'],
        'group': case['group'],
        'observations': case['observations'],
        'eligible': len(stream),
        'valid_calls': len(valid),
        'failed_calls': len(rows) - len(valid),
        'mean_probability_yes': (
            sum(row['answer']['probability_yes'] for row in valid) / len(valid)
            if valid else None
        ),
        'streaming': {
            'window_n': WINDOW_N,
            'max_delay_steps': MAX_DELAY_STEPS,
            'raw': raw,
            'filtered': sampler.out,
            'nodes': nodes,
            'max_node_lag_steps': sampler.max_node_lag,
            'prefix_invariant': True,
        },
        'offline_reference': {
            'filtered': reference,
            'nodes': reference_nodes,
        },
        'calls': rows,
        'started_at': started_at,
        'finished_at': now(),
        'duration_seconds': time.monotonic() - started,
    }
    write(episode_root / 'episode.json', result)
    return result


def run_shard(output, shard_index, args):
    if not 0 <= shard_index < SHARD_COUNT:
        raise ValueError('Invalid shard index')
    plan = read(output / 'plan.json')
    shard_rows = plan['shards'][shard_index]
    if len(shard_rows) != EXPECTED_EPISODES // SHARD_COUNT:
        raise ValueError('Shard must contain 20 episodes')
    if not os.environ.get('JEV_API_KEY'):
        raise RuntimeError('Set JEV_API_KEY in the parent process')
    shard_root = output / ('shard_%d' % shard_index)
    if shard_root.exists():
        raise ValueError('Shard output already exists')
    shard_root.mkdir(parents=True)
    expected_calls = sum(row['eligible'] for row in shard_rows)
    counters = {
        'cases': shard_rows,
        'completed_episodes': 0,
        'resolved_calls': 0,
        'expected_calls': expected_calls,
        'max_unresolved_step_lag': 0,
    }
    write(shard_root / 'status.json', {
        'phase': 'running',
        'started_at': now(),
        'shard': shard_index,
        'episodes': len(shard_rows),
        'expected_calls': expected_calls,
        'max_in_flight': args.max_in_flight,
        'window_n': WINDOW_N,
        'max_delay_steps': MAX_DELAY_STEPS,
    })
    results = []
    for case in shard_rows:
        result = run_episode(shard_root, case, os.environ['JEV_API_KEY'], args, counters)
        results.append(result)
        counters['completed_episodes'] += 1
        rows = [call for episode in results for call in episode['calls']]
        write(shard_root / 'results.json', {
            'episodes': results,
            'call_rows': rows,
        })
        write(shard_root / 'status.json', {
            'phase': 'running',
            'updated_at': now(),
            'shard': shard_index,
            'completed_episodes': counters['completed_episodes'],
            'total_episodes': len(shard_rows),
            'resolved_calls': counters['resolved_calls'],
            'expected_calls': expected_calls,
            'max_unresolved_step_lag': counters['max_unresolved_step_lag'],
        })
    valid_calls = sum(episode['valid_calls'] for episode in results)
    summary = {
        'phase': (
            'complete' if valid_calls == expected_calls
            else 'complete_with_failures'
        ),
        'finished_at': now(),
        'shard': shard_index,
        'episodes': len(results),
        'expected_calls': expected_calls,
        'valid_calls': valid_calls,
        'failed_calls': expected_calls - valid_calls,
        'max_unresolved_step_lag': counters['max_unresolved_step_lag'],
        'window_n': WINDOW_N,
        'max_delay_steps': MAX_DELAY_STEPS,
        'max_in_flight': args.max_in_flight,
    }
    write(shard_root / 'summary.json', summary)
    write(shard_root / 'status.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def finalize(output):
    plan = read(output / 'plan.json')
    shard_summaries = [
        read(output / ('shard_%d' % index) / 'summary.json')
        for index in range(SHARD_COUNT)
    ]
    episodes = []
    calls = []
    for index in range(SHARD_COUNT):
        result = read(output / ('shard_%d' % index) / 'results.json')
        episodes.extend(result['episodes'])
        calls.extend(result['call_rows'])
    unique_episodes = {row['episode_id'] for row in episodes}
    if len(episodes) != EXPECTED_EPISODES or len(unique_episodes) != EXPECTED_EPISODES:
        raise ValueError('Final episode set is incomplete or duplicated')
    if len(calls) != plan['expected_calls']:
        raise ValueError('Final call set is incomplete')
    valid = [row for row in calls if row.get('phase') == 'complete']
    probabilities = [row['answer']['probability_yes'] for row in valid]
    nodes = [
        node for episode in episodes
        for node in episode['streaming']['nodes']
    ]
    summary = {
        'phase': (
            'complete' if len(valid) == len(calls)
            else 'complete_with_failures'
        ),
        'finished_at': now(),
        'episodes': len(episodes),
        'groups': dict(Counter(row['group'] for row in episodes)),
        'expected_calls': len(calls),
        'valid_calls': len(valid),
        'failed_calls': len(calls) - len(valid),
        'workers': 2,
        'max_in_flight_per_worker': MAX_IN_FLIGHT,
        'window_n': WINDOW_N,
        'max_delay_steps': MAX_DELAY_STEPS,
        'max_unresolved_step_lag': max(
            row['max_unresolved_step_lag'] for row in shard_summaries
        ),
        'max_online_node_lag': max(
            episode['streaming']['max_node_lag_steps']
            for episode in episodes
        ),
        'mean_probability_yes': (
            sum(probabilities) / len(probabilities) if probabilities else None
        ),
        'online_nodes': len(nodes),
        'episodes_with_failures': sum(
            episode['failed_calls'] > 0 for episode in episodes
        ),
    }
    write(output / 'results.json', {
        'episodes': episodes,
        'call_rows': calls,
    })
    write(output / 'summary.json', summary)
    write(output / 'status.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def supervise(output, args):
    """Read one key into memory, then start exactly two episode workers."""
    plan = read(output / 'plan.json')
    if plan['workers'] != SHARD_COUNT:
        raise ValueError('Prepared plan does not use two workers')
    key = acquire_key()
    child_env = os.environ.copy()
    child_env['JEV_API_KEY'] = key
    os.environ.pop('JEV_API_KEY', None)
    logs = output / 'logs'
    logs.mkdir(exist_ok=True)
    processes = []
    handles = []
    try:
        for shard_index in range(SHARD_COUNT):
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                'shard',
                '--output',
                str(output),
                '--shard',
                str(shard_index),
                '--max-in-flight',
                str(args.max_in_flight),
                '--attempts',
                str(args.attempts),
                '--timeout',
                str(args.timeout),
            ]
            handle = (logs / ('shard_%d.log' % shard_index)).open('ab', buffering=0)
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=child_env,
                stdin=subprocess.DEVNULL,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            processes.append(process)
            handles.append(handle)
        write(output / 'status.json', {
            'phase': 'running',
            'started_at': now(),
            'workers': 2,
            'worker_pids': [process.pid for process in processes],
            'episodes': EXPECTED_EPISODES,
            'expected_calls': plan['expected_calls'],
            'window_n': WINDOW_N,
            'max_delay_steps': MAX_DELAY_STEPS,
            'max_in_flight_per_worker': args.max_in_flight,
            'credential_on_disk': False,
        })

        def stop_children(signum, frame):
            del signum, frame
            for process in processes:
                if process.poll() is None:
                    process.terminate()

        previous_handlers = {}
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.signal(signum, stop_children)
        try:
            return_codes = [process.wait() for process in processes]
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
        if any(return_codes):
            write(output / 'status.json', {
                'phase': 'failed',
                'failed_at': now(),
                'worker_pids': [process.pid for process in processes],
                'return_codes': return_codes,
                'window_n': WINDOW_N,
                'max_delay_steps': MAX_DELAY_STEPS,
                'credential_on_disk': False,
            })
            raise RuntimeError('At least one streaming worker failed')
        finalize(output)
    finally:
        child_env.pop('JEV_API_KEY', None)
        for handle in handles:
            handle.close()


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    prepare_parser = subparsers.add_parser('prepare')
    prepare_parser.add_argument('--output', required=True, type=Path)
    refresh_parser = subparsers.add_parser('refresh-prepare')
    refresh_parser.add_argument('--output', required=True, type=Path)
    run_parser = subparsers.add_parser('shard')
    run_parser.add_argument('--output', required=True, type=Path)
    run_parser.add_argument('--shard', required=True, type=int, choices=(0, 1))
    run_parser.add_argument('--max-in-flight', type=int, default=MAX_IN_FLIGHT)
    run_parser.add_argument('--attempts', type=int, default=5)
    run_parser.add_argument('--timeout', type=float, default=120)
    supervise_parser = subparsers.add_parser('supervise')
    supervise_parser.add_argument('--output', required=True, type=Path)
    supervise_parser.add_argument('--max-in-flight', type=int, default=MAX_IN_FLIGHT)
    supervise_parser.add_argument('--attempts', type=int, default=5)
    supervise_parser.add_argument('--timeout', type=float, default=120)
    finalize_parser = subparsers.add_parser('finalize')
    finalize_parser.add_argument('--output', required=True, type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    output = args.output.resolve()
    if args.command == 'prepare':
        prepare(output)
    elif args.command == 'refresh-prepare':
        refresh_prepare(output)
    elif args.command == 'shard':
        if not 1 <= args.max_in_flight <= MAX_IN_FLIGHT:
            raise ValueError('max-in-flight must be between 1 and 5')
        if not 1 <= args.attempts <= 5:
            raise ValueError('attempts must be between 1 and 5')
        run_shard(output, args.shard, args)
    elif args.command == 'supervise':
        if not 1 <= args.max_in_flight <= MAX_IN_FLIGHT:
            raise ValueError('max-in-flight must be between 1 and 5')
        if not 1 <= args.attempts <= 5:
            raise ValueError('attempts must be between 1 and 5')
        supervise(output, args)
    else:
        finalize(output)


if __name__ == '__main__':
    main()
