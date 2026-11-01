#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
python_bin="${JANUSVLN_VENV:-$root/.venv}/bin/python"
export CUDA_VISIBLE_DEVICES=''
export PYTHONDONTWRITEBYTECODE=1
export NUMBA_CACHE_DIR=/tmp/janusvln-numba-cache
export PYTHONPATH="$root/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
"$python_bin" src/evaluation.py --help >/dev/null
"$python_bin" - <<'PY'
import gzip
import json
from pathlib import Path
from importlib.metadata import version
import torch, flash_attn, habitat, habitat_sim, habitat_baselines
from habitat_baselines.config.default import get_config
from habitat_extensions import rxr_dataset
from habitat_extensions.rxr_metrics import normalized_dtw
from qwen_vl.model.modeling_qwen2_5_vl import Qwen2_5_VLForConditionalGenerationForJanusVLN
for name in ['torch', 'torchvision', 'torchaudio', 'transformers', 'flash-attn', 'JanusVLN']:
    print(name, version(name))
print('Habitat-Sim', habitat_sim.__version__)
cfg = get_config('config/vln_r2r.yaml')
with habitat.config.read_write(cfg):
    cfg.habitat.dataset.split = 'val_unseen'
data = habitat.make_dataset(cfg.habitat.dataset.type, config=cfg.habitat.dataset)
assert len(data.episodes) == 1839
for episode in data.episodes:
    assert Path(episode.scene_id).is_file(), episode.scene_id
print('R2R: 1839 episodes; all scene files present')
p = Path('data/datasets/rxr/val_unseen')
with gzip.open(p / 'val_unseen_guide.json.gz', 'rt') as f:
    episodes = json.load(f)['episodes']
english = [e for e in episodes if e['instruction']['language'] in ('en-US','en-IN')]
assert len(english) == 3669
with gzip.open(p / 'val_unseen_guide_gt.json.gz', 'rt') as f:
    gt = json.load(f)
for episode in english:
    assert str(episode['episode_id']) in gt
    scene = episode['scene_id']
    scene = scene[scene.index('mp3d/'):]
    assert (Path('data/scene_datasets') / scene).is_file(), scene
cfg_rxr = get_config('config/vln_rxr.yaml')
rxr = habitat.make_dataset(cfg_rxr.habitat.dataset.type, config=cfg_rxr.habitat.dataset)
assert len(rxr.episodes) == 3669
assert {e.info['language'] for e in rxr.episodes} == {'en-US', 'en-IN'}
for e in rxr.episodes:
    assert Path(e.scene_id).is_file()
assert normalized_dtw([[0,0,0],[1,0,0]], [[0,0,0],[1,0,0]]) == 1.0
assert abs(normalized_dtw([[0,0,0]], [[3,0,0]]) - __import__('math').exp(-1)) < 1e-12
print('RxR: registered dataset loads 3669 English Guide episodes; scene files and ground truth present; nDTW checks passed')
print('CPU environment smoke check passed; no simulation or model weights loaded')
PY
