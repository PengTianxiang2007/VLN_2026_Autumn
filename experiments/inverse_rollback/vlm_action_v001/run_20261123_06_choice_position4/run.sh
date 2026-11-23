#!/usr/bin/env bash
set -eu
record=$(dirname "$0")
export VLN_ROLLBACK_RUN_ID=run_20261123_06_choice_position4
export VLN_ROLLBACK_PROMPT_DIR="$record"
export VLN_ROLLBACK_REUSE="$record/outbound_sources.json"
.runtime/crossing_vllm27/bin/python -Bu scripts/run_vlm_rollback.py start
python3 -B "$record/compare.py"
