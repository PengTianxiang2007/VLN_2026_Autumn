#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
gpu=${1:?Pass GPU 0 or 1}
out="$root/outputs/inverse_rollback/codex_tools_v001/run_20261126_08_five_goal120"
cd "$root"
export CUDA_VISIBLE_DEVICES="$gpu" VLN_SIM_RENDER_GPU="$gpu" VLN_EVAL_SEED=2 PYTHONHASHSEED=2
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
export VLN_SIM_CACHE_ROOT="$out/gpu$gpu/isaac" TMPDIR=/tmp
exec bash scripts/run_crossing_panorama_isaac.sh "$here/simulate.py" >> "$out/gpu$gpu/isaac.log" 2>&1
