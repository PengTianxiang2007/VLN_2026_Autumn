"""Three-image local choice scoring; model requests never read evaluation labels."""
import base64
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

SCHEMA = {'type': 'object', 'additionalProperties': False,
          'properties': {'score': {'type': 'integer', 'enum': [1, 2, 3, 4, 5]},
                         'reason': {'type': 'string', 'minLength': 1, 'maxLength': 200}},
          'required': ['score', 'reason']}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def select_cases(rows, counts, seed):
    """Round-robin scenes within each outcome, before viewing any predictions."""
    rng = random.Random(seed)
    selected = []
    for group, count in counts.items():
        scenes = defaultdict(list)
        for row in sorted(rows, key=lambda r: r['episode_id']):
            if row['group'] == group:
                scenes[row['scene']].append(row)
        order = sorted(scenes)
        rng.shuffle(order)
        for scene in order:
            rng.shuffle(scenes[scene])
        if sum(map(len, scenes.values())) < count:
            raise ValueError('Insufficient cases for ' + group)
        group_selected = []
        while len(group_selected) < count:
            for scene in order:
                if scenes[scene] and len(group_selected) < count:
                    group_selected.append(scenes[scene].pop())
        selected.extend(group_selected)
    return selected


def windows(observations):
    """Exact t-2,t-1,t; never substitute a stale or terminal reused image."""
    frames = {r['frame']: r for r in observations}
    if len(frames) != len(observations):
        raise ValueError('Duplicate observation frame')
    for t in sorted(frames):
        row = frames[t]
        if not row['eligible_for_inference']:
            continue
        history = []
        for f in range(max(0, t - 2), t + 1):
            im = frames.get(f)
            if not im or not im['eligible_for_inference'] or im['terminal'] or im['rgb_reused']:
                raise ValueError('Missing or reused image inside three-frame window')
            history.append({k: im[k] for k in ('frame', 'rgb', 'rgb_sha256')})
        yield t, history


def request(prompt, images, dataset, model, seed, embed=True):
    ids = [r['frame'] for r in images]
    if not ids or ids != list(range(max(0, ids[-1] - 2), ids[-1] + 1)):
        raise ValueError('Expected consecutive current and previous two images')
    content = []
    for im in images:
        delta = ids[-1] - im['frame']
        label = 'Current observation t:' if delta == 0 else 'Previous observation t-%d:' % delta
        content.append({'type': 'text', 'text': label})
        if embed:
            path = Path(dataset) / im['rgb']
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != im['rgb_sha256']:
                raise ValueError('Source RGB hash changed')
            mime = 'image/' + ('jpeg' if path.suffix in ('.jpg', '.jpeg') else path.suffix[1:])
            url = 'data:' + mime + ';base64,' + base64.b64encode(raw).decode()
        else:
            url = 'sha256:' + im['rgb_sha256']
        content.append({'type': 'image_url', 'image_url': {'url': url}})
    content.append({'type': 'text', 'text': 'Score the CURRENT local route-choice situation.'})
    return dict(model=model, messages=[{'role': 'system', 'content': prompt},
                {'role': 'user', 'content': content}], temperature=0, seed=seed,
                max_tokens=256, stream=False, chat_template_kwargs={'enable_thinking': False},
                response_format={'type': 'json_schema', 'json_schema': {
                    'name': 'crossing_score', 'strict': True, 'schema': SCHEMA}})


def request_seed(episode, frame, seed):
    return int(digest([episode, frame, seed])[:8], 16) % 2147483647


def validate(answer):
    if not isinstance(answer, dict) or set(answer) != {'score', 'reason'}:
        raise ValueError('Unexpected score response fields')
    if type(answer['score']) is not int or answer['score'] not in range(1, 6):
        raise ValueError('Expected integer score 1..5')
    if not isinstance(answer['reason'], str) or not 1 <= len(answer['reason'].strip()) <= 200:
        raise ValueError('Expected short visual reason')
    return answer
