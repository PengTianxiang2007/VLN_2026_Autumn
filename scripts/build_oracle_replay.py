"""Export the completed Oracle campaigns as one offline, animated HTML review.

Reads recorded poses/RGB only. Never starts a model or simulator.
"""
import argparse
import base64
import hashlib
import io
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'outputs/oracle_crossing'
GROUPS = [('early', '尽早纠正', 'seed2_10_multi_20261103')] + [
    (f'd{d}', f'偏移 {d} 米', f'seed2_10_delay{d}m_20261103') for d in (3, 5, 8, 12)]


def distance_to_reference(position, reference):
    best = float('inf')
    for a, b in zip(reference, reference[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        den = dx * dx + dy * dy
        t = max(0., min(1., ((position[0] - a[0]) * dx + (position[1] - a[1]) * dy) / den)) if den else 0.
        best = min(best, math.hypot(position[0] - a[0] - t * dx, position[1] - a[1] - t * dy))
    return best


def yaw_wxyz(rotation):
    if rotation is None:
        return None
    w, x, y, z = rotation
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def walk_edges(nodes):
    """A teleport boundary must never become a walking edge."""
    return [(i - 1, i) for i in range(1, len(nodes)) if nodes[i - 1]['segment'] == nodes[i]['segment']]


def review_start(nodes, before_index, previous_after, crossing, reason):
    """Locate a review interval, not a ground-truth semantic error onset."""
    candidates = list(range(previous_after, before_index + 1))
    match = re.search(r'第\s*(\d+)\s*(?:至|到|—|–|-)\s*(\d+)\s*(?:个)?动作', reason)
    if match:
        start, end = map(int, match.groups())
        valid = [i for i in candidates if start <= nodes[i]['a'] <= end]
        if valid and end <= nodes[before_index]['a']:
            return valid[0], '审阅文字中的观察区间；不是精确错误起始时刻'
    # Last closest approach to this recorded crossing, within this uninterrupted leg.
    distances = [math.dist(nodes[i]['p'][:2], crossing[:2]) for i in candidates]
    minimum = min(distances)
    nearest = [i for i, d in zip(candidates, distances) if d <= minimum + .08]
    index = nearest[-1]
    if index == before_index and index > previous_after:
        index -= 1
    return index, '按本段轨迹最后接近关联 crossing 的位置回溯估计'


def geometric_deviation(nodes, threshold=.5):
    """Visual aid only: three consecutive recorded positions off the reference."""
    for i in range(len(nodes) - 2):
        part = nodes[i:i + 3]
        if len({n['segment'] for n in part}) == 1 and all(n['distance'] >= threshold for n in part):
            return i
    return None


class Media:
    def __init__(self):
        self.jobs = []
        self.index = {}

    def add(self, path, width=320):
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        key = (str(path.resolve()), width)
        if key not in self.index:
            self.index[key] = len(self.jobs)
            self.jobs.append(key)
        return self.index[key]

    def encode(self):
        from PIL import Image

        def convert(job):
            path, width = job
            with Image.open(path) as image:
                image = image.convert('RGB')
                image.thumbnail((width, int(width * .75)), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                image.save(buffer, 'WEBP', quality=70 if width == 320 else 82, method=3)
            return 'data:image/webp;base64,' + base64.b64encode(buffer.getvalue()).decode()

        with ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(convert, self.jobs))


def build_trace(c, campaign, media):
    attempts = sorted((campaign / 'oracle_records' / c['episode_id']).glob('attempt_*'))
    complete = [a for a in attempts if (a / 'result.json').exists()]
    assert len(complete) == 1, (campaign.name, c['episode_id'], len(complete))
    attempt = complete[0]
    actions = {a['action_index']: a['action'] for a in map(json.loads, (attempt / 'actions.jsonl').read_text().splitlines())}
    ivs = c['interventions']
    by_action = {iv['action_index']: iv for iv in ivs}
    assert len(by_action) == len(ivs)
    nodes, events = [], []
    reference = c['reference']
    previous_after = 0

    def node(a, position, rotation, frame, segment, phase='walk', event=None, rgb_note='动作前的实际 RGB 观测'):
        action = actions.get(a, {})
        code = 0 if 'stop' in action else (action.get('move_by_discrete') or [-1])[0]
        return dict(a=a, p=[round(x, 6) for x in position], yaw=yaw_wxyz(rotation),
                    image=media.add(frame), segment=segment, phase=phase, event=event,
                    action={0: 'STOP', 1: '前进', 2: '左转', 3: '右转', -1: '结束'}.get(code, '未知'),
                    distance=round(distance_to_reference(position, reference), 5), rgb_note=rgb_note)

    for obs in c['oracle_observations']:
        a = obs['action_index']
        iv = by_action.get(a)
        segment = obs.get('intervention_count', int(obs.get('teleported', False)))
        if iv:
            assert math.dist(obs['position'], iv['before_position']) < .001
            ei = len(events)
            request = Path(iv['request_directory'])
            before = len(nodes)
            nodes.append(node(a, iv['before_position'], iv['before_rotation'], request / 'before.png', ei, 'before', ei, '精确记录：瞬移前观测'))
            after = len(nodes)
            nodes.append(node(a, iv['after_position'], iv['after_rotation'], request / 'after.png', ei + 1, 'after', ei, '精确记录：瞬移并站稳后的观测'))
            target = next(t for t in c['targets'] if t['id'] == iv['target_id'])
            start, basis = review_start(nodes, before, previous_after, target['crossing_position'], iv['response']['reason'])
            events.append(dict(number=iv['number'], crossing=iv['target_id'], crossing_position=target['crossing_position'],
                               before=before, after=after, start=start, start_basis=basis,
                               step=a, reason=iv['response']['reason'], translation=iv['translation_m'],
                               deviation=iv['trigger_reference_distance_m'], before_ne=iv['before_NE'], after_ne=iv['handover_NE'],
                               inside_goal=iv['inside_success_radius_at_handover'], already_near_goal=iv['inside_success_radius_before_intervention'],
                               memory=iv['memory_unchanged'], memory_sha256=iv['memory_sha256'],
                               before_image=media.add(request / 'before.png', 640), after_image=media.add(request / 'after.png', 640)))
            previous_after = after
        else:
            nodes.append(node(a, obs['position'], obs.get('rotation'), attempt / obs['frame'], segment))
    assert nodes
    # Exact final position is recorded, but no separate final orientation/RGB is promised.
    last = dict(nodes[-1])
    last.update(p=[round(v, 6) for v in c['oracle']['path'][-1]], yaw=None, phase='end',
                a=max(actions, default=nodes[-1]['a']), event=None, action='任务结束',
                rgb_note='终止位置；画面复用末次观测，未新增终止 RGB')
    last['distance'] = round(distance_to_reference(last['p'], reference), 5)
    nodes.append(last)
    for ei, event in enumerate(events):
        assert nodes[event['before']]['segment'] + 1 == nodes[event['after']]['segment']
        assert (event['before'], event['after']) not in walk_edges(nodes)
        assert event['start'] <= event['before'] < event['after']
        assert event['memory']
    geometric = geometric_deviation(nodes) if not events else None
    return dict(nodes=nodes, events=events, geometric=geometric, result=c['oracle']['fail_reason'],
                metrics=c['oracle']['metrics'], max_deviation=c['max_reference_distance_m'],
                notes=c['analysis'].get('notes', []), threshold=c['deviation_threshold_m'],
                action_count=len(actions))


def build(output):
    media = Media()
    data = dict(version=2, groups=[], cases=[], scenes={}, images=[])
    case_by_id = {}
    for key, label, folder in GROUPS:
        campaign = BASE / folder
        source = json.loads((campaign / 'report/results.json').read_text())
        assert source['summary']['oracle_complete'] == 10
        data['groups'].append(dict(id=key, label=label, summary=source['summary']))
        for c in source['cases']:
            if c['scene'] not in data['scenes']:
                data['scenes'][c['scene']] = dict(geometry={k: c['geometry'][k] for k in ('width', 'height', 'resolution', 'low', 'high')}, image=c['floorplan'])
            if c['episode_id'] not in case_by_id:
                item = dict(id=c['episode_id'], scene=c['scene'], instruction=c['instruction'], reference=c['reference'],
                            crossings=c['targets'], control=c['control']['path'], control_metrics=c['control']['metrics'], runs={})
                case_by_id[c['episode_id']] = item
                data['cases'].append(item)
            else:
                assert c['reference'] == case_by_id[c['episode_id']]['reference']
                assert c['targets'] == case_by_id[c['episode_id']]['crossings']
            case_by_id[c['episode_id']]['runs'][key] = build_trace(c, campaign, media)
    print(json.dumps(dict(phase='encoding_recorded_images', images=len(media.jobs)), ensure_ascii=False), flush=True)
    data['images'] = media.encode()
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    template = (ROOT / 'core/oracle_replay.html').read_text()
    assert template.count('__PAYLOAD__') == 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace('__PAYLOAD__', payload))
    metadata = dict(html=str(output), bytes=output.stat().st_size, sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                    cases=len(data['cases']), runs=50, correction_events=sum(len(r['events']) for c in data['cases'] for r in c['runs'].values()),
                    nodes=sum(len(r['nodes']) for c in data['cases'] for r in c['runs'].values()), images=len(data['images']),
                    estimated_intervals=sum('估计' in e['start_basis'] for c in data['cases'] for r in c['runs'].values() for e in r['events']),
                    no_model_or_simulator_started=True)
    output.with_suffix('.build.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(metadata, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE / 'oracle_replay_v2_20261104.html')
    parser.add_argument('--refresh-template', action='store_true', help='Reuse the existing embedded data; update only the interface.')
    args = parser.parse_args()
    if args.refresh_template:
        old = args.output.read_text()
        payload = re.search(r'<script id="replay-data" type="application/json">(.*?)</script>', old, re.S).group(1)
        args.output.write_text((ROOT / 'core/oracle_replay.html').read_text().replace('__PAYLOAD__', payload))
        metadata_path = args.output.with_suffix('.build.json')
        metadata = json.loads(metadata_path.read_text())
        metadata.update(bytes=args.output.stat().st_size, sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(template_refreshed=True, bytes=metadata['bytes'])))
    else:
        build(args.output)
