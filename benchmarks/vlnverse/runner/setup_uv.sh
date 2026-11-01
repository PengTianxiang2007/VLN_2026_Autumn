#!/usr/bin/env bash
set -euo pipefail
runner="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project="$(cd "$runner/../../.." && pwd)"
source "$project/scripts/uv_common.sh"
ensure_uv
software="${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}/software/VLNVerse"
venv="${VLNVERSE_VENV:-$project/benchmarks/vlnverse/.venv}"
python3 "$project/scripts/restore_isaac.py"
if [[ ! -x "$venv/bin/python" ]]; then
  uv venv --python "$project/.runtime/isaac45/kit/python/bin/python3" --no-python-downloads "$venv"
fi
uv pip install --python "$venv/bin/python" --index-url "${VLN_PYPI_INDEX:-https://pypi.org/simple}" --prerelease=allow \
  "$software/torch-2.5.1+cu118-cp310-cp310-linux_x86_64.whl" \
  'https://download.pytorch.org/whl/cu118/torchvision-0.20.1%2Bcu118-cp310-cp310-linux_x86_64.whl' \
  -r "$runner/requirements.txt"
