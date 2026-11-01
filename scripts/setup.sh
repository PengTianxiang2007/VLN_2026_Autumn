#!/usr/bin/env bash
set -euo pipefail
project="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
model="${1:-}"
source "$project/scripts/uv_common.sh"
ensure_uv
case "$model" in
  streamvln)
    export STREAMVLN_VENV="${STREAMVLN_VENV:-$project/backbone/streamvln/.venv}"
    bash "$project/backbone/streamvln/scripts/setup_r2r_uv.sh"
    ;;
  janusvln)
    export JANUSVLN_VENV="${JANUSVLN_VENV:-$project/backbone/janusvln/.venv}"
    bash "$project/backbone/janusvln/scripts/setup_eval_uv.sh"
    ;;
  vlnverse)
    bash "$project/benchmarks/vlnverse/runner/setup_uv.sh"
    ;;
  *) echo 'Usage: bash scripts/setup.sh streamvln|janusvln|vlnverse' >&2; exit 2 ;;
esac
python3 "$project/core/paths.py"
