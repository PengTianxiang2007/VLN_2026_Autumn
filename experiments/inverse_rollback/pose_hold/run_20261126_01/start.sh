#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out="$root/outputs/inverse_rollback/pose_hold/run_20261126_01"
cd "$root"
export CUDA_VISIBLE_DEVICES=3 VLN_SIM_RENDER_GPU=3 VLN_EVAL_SEED=2 PYTHONHASHSEED=2
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
export VLN_SIM_CACHE_ROOT="$out/isaac"
exec bash scripts/run_crossing_panorama_isaac.sh "$here/hold.py"
