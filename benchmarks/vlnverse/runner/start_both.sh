#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 2 ]; then
  echo "Usage: bash $0 MODEL_GPU SIM_GPU [--mode physical|flash]" >&2
  exit 2
fi
peng_model_gpu="$1"
peng_sim_gpu="$2"
shift 2
script="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_both.sh"
bash "$script" "$peng_model_gpu" --sim-gpu "$peng_sim_gpu" --preflight-only "$@"
launch_dir=/mnt/nas/gezuhao/shared_dataset/Resource_Peng/evaluations/VLNVerse/launches
mkdir -p "$launch_dir"
launch_log="$launch_dir/full_$(date -u +%Y%m%d_%H%M%S)_$$.log"
nohup setsid bash "$script" "$peng_model_gpu" --sim-gpu "$peng_sim_gpu" "$@" > "$launch_log" 2>&1 < /dev/null &
peng_launcher_pid=$!
printf 'LAUNCHER_PID=%s\nLOG=%s\n' "$peng_launcher_pid" "$launch_log"
