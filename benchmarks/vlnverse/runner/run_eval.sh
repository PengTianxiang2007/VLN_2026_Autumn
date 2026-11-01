#!/usr/bin/env bash
set -euo pipefail
runner="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
benchmark="$runner/../upstream"
project="$(cd "$runner/../../.." && pwd)"
isaac_root=${PENG_ISAAC_ROOT:-$project/.runtime/isaac45}
export VIRTUAL_ENV="${VLNVERSE_VENV:-$project/benchmarks/vlnverse/.venv}"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export OMNI_KIT_ALLOW_ROOT=1
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
# Simulator writes caches/logs only to this task's directories.
cache_root=${VLN_SIM_CACHE_ROOT:-$runner}
export XDG_CACHE_HOME="$cache_root/cache"
export XDG_CONFIG_HOME="$cache_root/config"
export XDG_DATA_HOME="$cache_root/share"
mkdir -p "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
export PYTHONPATH="$benchmark:$project"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
export CARB_APP_PATH="$isaac_root/kit"
export ISAAC_PATH="$isaac_root"
export EXP_PATH="$isaac_root/apps"
export LD_PRELOAD="$isaac_root/kit/libcarb.so"
source "$isaac_root/setup_python_env.sh"
cd "$benchmark"
if [ "${PENG_SMOKE_BACKEND:-physical}" = "camera" ]; then
    exec "$VIRTUAL_ENV/bin/python" -u "$runner/camera_eval.py" "$@"
fi
exec "$VIRTUAL_ENV/bin/python" -u scripts/eval/eval.py --config "$1"
