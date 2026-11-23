#!/usr/bin/env bash
set -u
record=$(dirname "$0")
export VLN_ROLLBACK_RUN_ID=run_20261123_08_restore_c21
export VLN_ROLLBACK_PROTOCOL=seven_action_judge
export VLN_ROLLBACK_PROMPT_DIR="$record"
.runtime/crossing_vllm27/bin/python -Bu scripts/run_vlm_rollback.py start
code=$?
if [[ -f "outputs/inverse_rollback/vlm_action_v001/$VLN_ROLLBACK_RUN_ID/status.json" ]]; then
    python3 -B "$record/../run_20261123_07_restore_c21/record_result.py" "$record"
fi
exit "$code"
