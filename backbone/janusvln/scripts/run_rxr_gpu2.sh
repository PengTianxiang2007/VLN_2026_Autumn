#!/usr/bin/env bash
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
output="$root/results/val_unseen/rxr_extra"
mkdir -p "$output"
# A second wrapper must not replace PID/log metadata of an existing run.
exec 7>"$output/supervisor.lock"
flock -n 7 || exit 1
echo "$$" > "$output/run.pid"
date -u '+%Y-%m-%d %H:%M:%S UTC' > "$output/run.started_at"
export PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false NCCL_DEBUG=WARN
bash scripts/janusvln_eval.sh rxr 2 extra >> "$output/run.log" 2>&1
run_code=$?
echo "$run_code" > "$output/run.exit_code"
date -u '+%Y-%m-%d %H:%M:%S UTC' > "$output/run.finished_at"
exit "$run_code"
