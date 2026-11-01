#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
export PYTHONPATH="$root/streamvln:$root${PYTHONPATH:+:$PYTHONPATH}"
python_bin="${STREAMVLN_VENV:-$root/.venv}/bin/python"

"$python_bin" streamvln/streamvln_eval_rxr.py --help >/dev/null
"$python_bin" - <<'PY'
import collections
import gzip
import json
import math
import os

import habitat
from habitat_baselines.config.default import get_config
import rxr_dataset
from rxr_metrics import normalized_dtw

config = get_config('config/vln_rxr.yaml')
dataset = habitat.make_dataset(config.habitat.dataset.type, config=config.habitat.dataset)
assert len(dataset.episodes) == 3669, len(dataset.episodes)
assert collections.Counter(ep.info['language'] for ep in dataset.episodes) == {
    'en-US': 1223, 'en-IN': 2446
}
assert all(os.path.isfile(ep.scene_id) for ep in dataset.episodes)
ids = [str(ep.episode_id) for ep in dataset.episodes]
assert len(ids) == len(set(ids))
gt_path = config.habitat.dataset.data_path.format(split='val_unseen').replace(
    '_guide.json.gz', '_guide_gt.json.gz'
)
with gzip.open(gt_path, 'rt') as stream:
    gt = json.load(stream)
assert all(ep_id in gt and gt[ep_id]['locations'] for ep_id in ids)
same = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
assert normalized_dtw(same, same) == 1.0
assert math.isclose(
    normalized_dtw([[0.0, 0.0, 0.0]], [[3.0, 0.0, 0.0]]),
    math.exp(-1.0),
)
print('RxR CPU smoke passed: 3669 English Guide episodes, 11 scenes, complete GT')
PY
