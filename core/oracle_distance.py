"""Distance-only Oracle geometry and dataset preparation; no model or simulator imports."""
import hashlib
import json
import math
from pathlib import Path


DEFAULT_THRESHOLDS = {'early': 0.75, 'short': 1.5, 'medium': 3.0, 'long': 4.0}


def positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be finite and positive')
    return value


def xy(value):
    result = [float(value[0]), float(value[1])]
    if not all(math.isfinite(v) for v in result):
        raise ValueError('Nonfinite position')
    return result


def route_segments(reference):
    points = [xy(p) for p in reference]
    if not points:
        raise ValueError('Empty reference route')
    arc = 0.0
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        if length > 1e-9:
            yield a, b, arc, length
            arc += length


def project_reference(position, reference):
    """Project onto line segments, not sampled vertices; z never enters the distance."""
    p = xy(position)
    best = None
    for a, b, arc, length in route_segments(reference):
        delta = [b[k] - a[k] for k in (0, 1)]
        fraction = max(0.0, min(1.0, sum((p[k] - a[k]) * delta[k] for k in (0, 1)) / length**2))
        point = [a[k] + fraction * delta[k] for k in (0, 1)]
        candidate = {'distance_m': math.dist(p, point), 'point': point,
                     'arc_m': arc + fraction * length}
        # Equal-distance overlaps prefer the first reference occurrence, explicitly.
        if best is None or candidate['distance_m'] < best['distance_m']:
            best = candidate
    if best is None:
        point = xy(reference[0])
        return {'distance_m': math.dist(p, point), 'point': point, 'arc_m': 0.0}
    return best


def landing_target(event, reference, offset_m=0.75):
    offset_m = positive(offset_m, 'landing offset')
    projection = project_reference(event['position'], reference)
    segments = list(route_segments(reference))
    if not segments:
        raise ValueError('Cannot derive heading from a zero-length reference route')
    total = segments[-1][2] + segments[-1][3]
    target_arc = min(total, projection['arc_m'] + offset_m)
    for index, (a, b, arc, length) in enumerate(segments):
        # At a corner, face along the outgoing reference segment.
        if target_arc < arc + length - 1e-9 or index == len(segments) - 1:
            fraction = min(1.0, max(0.0, (target_arc - arc) / length))
            point = [a[k] + fraction * (b[k] - a[k]) for k in (0, 1)]
            return {'id': event['id'], 'annotation_frame': event['frame'],
                    'crossing_position': xy(event['position']),
                    'crossing_reference_distance_m': projection['distance_m'],
                    'crossing_reference_arc_m': projection['arc_m'],
                    'target_xy': point, 'target_yaw_rad': math.atan2(b[1] - a[1], b[0] - a[0]),
                    'reference_arc_m': target_arc, 'requested_offset_m': offset_m,
                    'actual_offset_m': target_arc - projection['arc_m'],
                    'target_crossing_distance_m': math.dist(point, xy(event['position'])),
                    'planned_goal_distance_m': math.dist(point, xy(reference[-1])),
                    'near_goal_3m': math.dist(point, xy(reference[-1])) < 3.0}
    raise RuntimeError('Reference interpolation failed')


class DistanceTrigger:
    """Latch the nearest annotated crossing at first onset; threshold alone triggers.

    A larger arm threshold never chooses a new landing while the same excursion
    continues. Returning below onset clears that excursion. No frame/time triggers.
    """
    def __init__(self, case, threshold_m, onset_m):
        self.case = case
        self.threshold = positive(threshold_m, 'threshold')
        self.onset = positive(onset_m, 'onset')
        if self.threshold < self.onset or not case['targets']:
            raise ValueError('Invalid distance trigger configuration')
        self.event = None
        self.last_near_route_position = None
        self.serial = 0

    def update(self, position, action_index):
        distance = project_reference(position, self.case['reference_path'])['distance_m']
        if distance < self.onset:
            self.last_near_route_position = xy(position)
            self.event = None
        elif self.event is None:
            anchor = self.last_near_route_position or xy(position)
            target = min(self.case['targets'], key=lambda t: (math.dist(anchor, t['crossing_position']), t['id']))
            self.serial += 1
            self.event = {'excursion': self.serial, 'target_id': target['id'],
                          'onset_action_index': action_index, 'onset_distance_m': distance,
                          'association_position': list(anchor)}
        return {'distance_m': distance, 'threshold_reached': distance >= self.threshold,
                'event': dict(self.event) if self.event else None}


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def build_cohort(dataset, offset_m=0.75, thresholds=None):
    """Select every wrong-choice annotation; preserve duplicate-trajectory events."""
    root = Path(dataset).resolve()
    thresholds = thresholds or DEFAULT_THRESHOLDS
    inputs = {r['episode_id']: r for r in read_jsonl(root / 'inputs/episodes.jsonl')}
    metadata = {r['episode_id']: r for r in read_jsonl(root / 'evaluation/episodes.jsonl')}
    events = [r for r in read_jsonl(root / 'evaluation/events.jsonl') if r['type'] == 'wrong_choice']
    if len({e['id'] for e in events}) != len(events):
        raise ValueError('Duplicate annotation IDs')
    cases, diagnostics, files = [], [], set()
    for eid in sorted({e['episode_id'] for e in events}):
        path = root / metadata[eid]['trajectory']
        trajectory = json.loads(path.read_text(encoding='utf-8'))
        reference = trajectory['reference_path']
        selected = sorted([e for e in events if e['episode_id'] == eid], key=lambda e: (e['frame'], e['id']))
        distances = [project_reference(f['position'], reference)['distance_m'] for f in trajectory['frames']]
        for event in selected:
            before = [d for f, d in zip(trajectory['frames'], distances) if f['frame'] < event['frame']]
            after = [d for f, d in zip(trajectory['frames'], distances) if f['frame'] >= event['frame']]
            diagnostics.append({'event_id': event['id'], 'episode_id': eid,
                                'maximum_before_m': max(before, default=0.0),
                                'maximum_after_m': max(after, default=0.0)})
        cases.append({'episode_id': eid, 'scene': metadata[eid]['scene'],
                      'instruction': inputs[eid]['instruction'], 'seed': inputs[eid]['seed'],
                      'reference_path': reference,
                      'targets': [landing_target(e, reference, offset_m) for e in selected]})
        files.add(path)
    files.update(root / f for f in ('inputs/episodes.jsonl', 'evaluation/episodes.jsonl', 'evaluation/events.jsonl'))
    return {'schema': 1, 'dataset': str(root), 'episodes': len(cases), 'events': len(events),
            'cases': cases, 'source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
            'historical_diagnostics': {'events': diagnostics, 'thresholds_m': thresholds,
                'reached_after_annotation': {k: sum(d['maximum_after_m'] >= v for d in diagnostics) for k, v in thresholds.items()},
                'reached_before_annotation': {k: sum(d['maximum_before_m'] >= v for d in diagnostics) for k, v in thresholds.items()},
                'interpretation': 'Protocol design on historical trajectories, not simulation results or accuracy.'}}
