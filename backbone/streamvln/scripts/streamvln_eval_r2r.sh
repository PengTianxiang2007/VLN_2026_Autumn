#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project="$(cd "$root/../.." && pwd)"
python3 "$project/core/paths.py"
if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/streamvln_eval_r2r.sh GPU_IDS" >&2
  echo "Example: bash scripts/streamvln_eval_r2r.sh 1" >&2
  exit 2
fi

gpu_ids="$1"
split=val_unseen
if [[ ! "$gpu_ids" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
  echo "GPU_IDS must be a comma-separated list of GPU indices" >&2
  exit 2
fi
checkpoint="${STREAMVLN_MODEL_PATH:-${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}/models/StreamVLN_R2R_v1_3}"
output="${STREAMVLN_OUTPUT_PATH:-${VLN_OUTPUT_ROOT:-$project/outputs}/streamvln/r2r_ce/no_tta/$(date -u +%Y%m%d_%H%M%S)}"
venv="${STREAMVLN_VENV:-$root/.venv}"
num_procs=$(awk -F, '{print NF}' <<< "$gpu_ids")

export CUDA_VISIBLE_DEVICES="$gpu_ids"
export PYTHONPATH="$root/streamvln:$root${PYTHONPATH:+:$PYTHONPATH}"
export MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet
mkdir -p "$output"
cd "$root"
exec "$venv/bin/torchrun" --standalone --nproc_per_node="$num_procs" \
  streamvln/streamvln_eval.py \
  --model_path "$checkpoint" --eval_split "$split" --output_path "$output"
