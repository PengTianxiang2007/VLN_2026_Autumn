#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project="$(cd "$root/../.." && pwd)"
python3 "$project/core/paths.py"
if [[ $# -ne 1 || ! "$1" =~ ^[0-9]+$ ]]; then
  echo "Usage: bash scripts/streamvln_eval_rxr.sh PHYSICAL_GPU_ID" >&2
  exit 2
fi

checkpoint="${STREAMVLN_MODEL_PATH:-${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}/models/StreamVLN_R2R_v1_3}"
output="${STREAMVLN_OUTPUT_PATH:-${VLN_OUTPUT_ROOT:-$project/outputs}/streamvln/rxr_ce/no_tta/$(date -u +%Y%m%d_%H%M%S)}"
venv="${STREAMVLN_VENV:-$root/.venv}"

export CUDA_VISIBLE_DEVICES="$1"
export PYTHONPATH="$root/streamvln:$root${PYTHONPATH:+:$PYTHONPATH}"
export MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet
mkdir -p "$output"
cd "$root"
exec "$venv/bin/torchrun" --standalone --nproc_per_node=1 \
  streamvln/streamvln_eval_rxr.py \
  --model_path "$checkpoint" \
  --habitat_config_path config/vln_rxr.yaml \
  --eval_split val_unseen \
  --output_path "$output"
