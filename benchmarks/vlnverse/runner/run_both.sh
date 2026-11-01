#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "Usage: bash $0 GPU_ID [--mode physical|flash] [--preflight-only]" >&2
  exit 2
fi
peng_preflight=false
for peng_arg in "$@"; do
  if [ "$peng_arg" = "--preflight-only" ]; then peng_preflight=true; fi
  if [ "$peng_arg" = "--resume" ]; then
    echo "Resume each method with its own VLNVerse/run_eval.sh and run ID." >&2
    exit 2
  fi
done
peng_gpu="$1"
shift
project="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
bash "$project/backbone/streamvln/vlnverse/run_eval.sh" "$peng_gpu" --preflight-only "$@"
bash "$project/backbone/janusvln/vlnverse/run_eval.sh" "$peng_gpu" --preflight-only "$@"
if [ "$peng_preflight" = true ]; then exit 0; fi
bash "$project/backbone/streamvln/vlnverse/run_eval.sh" "$peng_gpu" "$@"
bash "$project/backbone/janusvln/vlnverse/run_eval.sh" "$peng_gpu" "$@"
