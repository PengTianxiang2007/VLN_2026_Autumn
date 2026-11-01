#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
python_bin="${STREAMVLN_VENV:-$root/.venv}/bin/python"
export PYTHONPATH="$root/streamvln:$root${PYTHONPATH:+:$PYTHONPATH}"

"$python_bin" streamvln/streamvln_eval.py --help >/dev/null
"$python_bin" - <<'PY'
import habitat
import habitat_sim
import torch
from transformers import AutoConfig, AutoTokenizer
from habitat_baselines.config.default import get_config
from model.stream_video_vln import StreamVLNForCausalLM

config = get_config('config/vln_r2r.yaml')
expected = {'val_seen': 778, 'val_unseen': 1839}
for split, count in expected.items():
    with habitat.config.read_write(config):
        config.habitat.dataset.split = split
    dataset = habitat.make_dataset(config.habitat.dataset.type, config=config.habitat.dataset)
    assert len(dataset.episodes) == count, (split, len(dataset.episodes), count)
    print(f'{split}: {count} episodes')
print(f'torch={torch.__version__}, cuda={torch.version.cuda}, gpu_available={torch.cuda.is_available()}')
print(f'habitat_sim={habitat_sim.__version__}, habitat={habitat.__version__}')
model_path = '/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/StreamVLN_R2R_v1_3'
model_config = AutoConfig.from_pretrained(model_path, local_files_only=True)
tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
assert model_config.num_history == 8
print(f'checkpoint_config={model_config.model_type}, tokenizer_size={len(tokenizer)} (metadata only)')
print('R2R smoke test passed (no MP3D simulation run)')
PY
