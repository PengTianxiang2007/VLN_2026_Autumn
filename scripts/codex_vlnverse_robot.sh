#!/usr/bin/env bash
# Launch Codex with the two tools bound to this H1 attachment.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
endpoint=${VLNVERSE_ROBOT_ENDPOINT:?Set VLNVERSE_ROBOT_ENDPOINT to the live endpoint.json}
python="$root/.runtime/crossing_vllm27/bin/python"
server="$root/scripts/vlnverse_robot_mcp.py"
export CODEX_HOME="/mnt/nas/gezuhao/PengTianxiang/.codex"
export HTTP_PROXY=http://127.0.0.1:7892 HTTPS_PROXY=http://127.0.0.1:7892 ALL_PROXY=http://127.0.0.1:7892
export http_proxy="$HTTP_PROXY" https_proxy="$HTTPS_PROXY" all_proxy="$ALL_PROXY"
export NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
# JSON string literals and string arrays are valid TOML values for the CLI.
settings=$(python3 -c 'import json,sys; print("{command=" + json.dumps(sys.argv[1]) + ",args=" + json.dumps(["-B", sys.argv[2], "--endpoint", sys.argv[3]]) + ",startup_timeout_sec=120,tool_timeout_sec=150}")' "$python" "$server" "$(realpath "$endpoint")")
exec /mnt/nas/gezuhao/PengTianxiang/codex-bin/codex -C "$PWD" \
  -m "${VLNVERSE_CODEX_MODEL:-gpt-6-astra}" -c "mcp_servers.vlnverse=$settings" "$@"
