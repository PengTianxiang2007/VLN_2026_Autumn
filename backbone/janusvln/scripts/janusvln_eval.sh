#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo 'Usage: bash scripts/janusvln_eval.sh r2r|rxr PHYSICAL_GPU [extra|base] [additional evaluator arguments]' >&2
  exit 2
fi
benchmark="$1"; gpu="$2"; variant="${3:-extra}"
if [[ $# -ge 3 ]]; then shift 3; else shift 2; fi
[[ "$benchmark" == r2r || "$benchmark" == rxr ]] || { echo 'Invalid benchmark' >&2; exit 2; }
[[ "$gpu" =~ ^[0-9]+$ ]] || { echo 'Specify one physical GPU number' >&2; exit 2; }
case "$variant" in extra) model_name=JanusVLN_Extra ;; base) model_name=JanusVLN_Base ;; *) echo 'Invalid model variant' >&2; exit 2 ;; esac
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project="$(cd "$root/../.." && pwd)"
python3 "$project/core/paths.py"
cd "$root"
model_path="${JANUSVLN_MODEL_PATH:-${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}/models/$model_name}"
output="${JANUSVLN_OUTPUT_PATH:-${VLN_OUTPUT_ROOT:-$project/outputs}/janusvln/${benchmark}_ce/no_tta/$(date -u +%Y%m%d_%H%M%S)}"
[[ -f "$model_path/model.safetensors.index.json" ]] || { echo "Missing checkpoint: $model_path" >&2; exit 1; }
[[ ! -f "$model_path/download_manifest.json" || -f "$model_path/download_verified.json" ]] || { echo 'Checkpoint download has not finished verification' >&2; exit 1; }
free_memory="$(nvidia-smi -i "$gpu" --query-gpu=memory.free --format=csv,noheader,nounits | tr -d ' ')"
[[ "$free_memory" =~ ^[0-9]+$ ]] || { echo 'Cannot read GPU memory' >&2; exit 1; }
[[ "$free_memory" -ge 30000 ]] || { echo "GPU $gpu has only $free_memory MiB free; need at least 30000 MiB" >&2; exit 1; }
exec 8>"/tmp/janusvln-gpu-${gpu}.lock"
flock -n 8 || { echo "Another JanusVLN evaluation holds GPU $gpu" >&2; exit 1; }
mkdir -p "$output"
exec 9>"$output/run.lock"
flock -n 9 || { echo "Another evaluation holds $output/run.lock" >&2; exit 1; }
export CUDA_VISIBLE_DEVICES="$gpu" PYTHONDONTWRITEBYTECODE=1
export NUMBA_CACHE_DIR=/tmp/janusvln-numba-cache
export PYTHONPATH="$root/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
python_bin="${JANUSVLN_VENV:-$root/.venv}/bin/python"
echo "benchmark=$benchmark checkpoint=$model_path gpu=$gpu output=$output"
"$python_bin" -m torch.distributed.run --standalone --nnodes=1 --nproc_per_node=1 src/evaluation.py \
  --model_path "$model_path" --habitat_config_path "config/vln_${benchmark}.yaml" \
  --eval_split val_unseen --output_path "$output" "$@"
