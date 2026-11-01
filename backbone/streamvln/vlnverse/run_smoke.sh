#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "Usage: bash $0 GPU_ID [physical|camera]" >&2
  exit 2
fi
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/benchmarks/vlnverse/runner/run_smoke.py" \
  --method StreamVLN --gpu "$1" --backend "${2:-physical}" --steps 5
