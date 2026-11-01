#!/usr/bin/env bash
set -euo pipefail
runner="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project="$(cd "$runner/../../.." && pwd)"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-600}"
export UV_CONCURRENT_DOWNLOADS="${UV_CONCURRENT_DOWNLOADS:-2}"
source "$project/scripts/uv_common.sh"
ensure_uv
venv="${VLNVERSE_VENV:-$project/benchmarks/vlnverse/.venv}"
python3 "$project/scripts/restore_isaac.py"
if [[ ! -x "$venv/bin/python" ]]; then
  uv venv --python "$project/.runtime/isaac45/kit/python/bin/python3" --no-python-downloads "$venv"
fi
export VLNVERSE_VENV="$venv"
python3 "$project/scripts/bootstrap_isaac_ml.py"
constraints=()
if [[ -f "$project/migration/vlnverse_requirements.lock.txt" ]]; then
  constraints=(--constraint "$project/migration/vlnverse_requirements.lock.txt")
fi
uv pip install --python "$venv/bin/python" --index-url "${VLN_PYPI_INDEX:-https://pypi.org/simple}" --prerelease=allow \
  "${constraints[@]}" \
  'torch==2.5.1+cu118' 'torchvision==0.20.1+cu118' 'rsl-rl-lib==2.2.1' \
  -r "$runner/requirements.txt"
