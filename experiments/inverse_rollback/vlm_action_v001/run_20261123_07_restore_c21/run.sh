#!/usr/bin/env bash
set -eu
record=$(dirname "$0")
export VLN_ROLLBACK_RUN_ID=run_20261123_07_restore_c21
export VLN_ROLLBACK_PROTOCOL=seven_action_judge
export VLN_ROLLBACK_PROMPT_DIR="$record"
exec .runtime/crossing_vllm27/bin/python -Bu scripts/run_vlm_rollback.py start
