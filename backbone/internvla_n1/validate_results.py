"""Validate scored episode identities directly from the official LMDB."""
import argparse
import json
import math
from pathlib import Path
import lmdb
import msgpack_numpy
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('run', type=Path)
a = p.parse_args()
expected = json.loads((a.run / 'episodes.json').read_text())
trace = a.run / 'agent_trace.jsonl'
if not trace.exists():
    raise RuntimeError('No real model action trace; refusing to validate an unused policy')
calls = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
if not calls or not any(row.get('llm_output') for row in calls):
    raise RuntimeError('No verified model generation')
if a.run.parent.name == 'smoke' and len({row['reset'] for row in calls}) < len(expected):
    raise RuntimeError('Smoke requires model actions in every test episode, including a reset')
db = lmdb.open(str(a.run / 'data/sample_episodes/evaluation/sample_data.lmdb'), readonly=True, lock=False)
rows = []
with db.begin() as tx:
    for e in expected:
        key = str(e['trajectory_id']) + '_' + str(e['episode_id'])
        raw = tx.get(key.encode())
        if raw is None:
            raise RuntimeError('Unscored episode: ' + key)
        info = msgpack_numpy.unpackb(raw)['info']
        if str(info['episode_id']) != str(e['episode_id']):
            raise RuntimeError('Score identity mismatch')
        for metric in ('success', 'spl', 'NE', 'osr', 'TL'):
            if not math.isfinite(float(info[metric])):
                raise RuntimeError('Invalid metric ' + metric)
        if any(not 0 <= float(info[k]) <= 1 for k in ('success', 'spl', 'osr')):
            raise RuntimeError('Invalid bounded metric')
        rows.append({'episode_id': e['episode_id'], 'scene': e['scan'], 'seed': 0, 'path_key': key, 'info': info})
db.close()
assert len({r['episode_id'] for r in rows}) == len(expected)
def normalize(x):
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    raise TypeError(type(x).__name__)
(a.run / 'validated_rows.json').write_text(json.dumps(rows, default=normalize))
print(json.dumps({'validated': len(rows)}))
