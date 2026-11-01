#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "Usage: bash $0 GPU_ID [--limit-episodes N] [--resume RUN_ID] [--mode physical|flash] [--preflight-only]" >&2
  exit 2
fi
peng_gpu="$1"
shift
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/benchmarks/vlnverse/runner/run_full.py" --method JanusVLN --gpu "$peng_gpu" "$@"
