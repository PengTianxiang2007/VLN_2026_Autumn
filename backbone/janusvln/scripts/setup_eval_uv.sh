#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace="$(cd "$root/../.." && pwd)/benchmarks/habitat_ce"
venv="${JANUSVLN_VENV:-$root/.venv}"
resource="${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}"
archive="$resource/software/StreamVLN/habitat-sim-0.2.4-py3.9-headless-bullet.tar.bz2"
wheel="${JANUSVLN_FLASH_WHEEL:-$resource/software/JanusVLN/flash_attn-2.7.1.post4+cu12torch2.5cxx11abiFALSE-cp39-cp39-linux_x86_64.whl}"
source "$(cd "$root/../.." && pwd)/scripts/uv_common.sh"
ensure_uv
if [[ ! -x "$venv/bin/python" ]]; then
  ensure_python
  uv venv "$venv" --python 3.9.25 --no-python-downloads
fi
if ! "$venv/bin/python" -c 'import torch,torchvision,torchaudio; assert torch.__version__ == "2.5.1+cu124"' 2>/dev/null; then
  install_torch "$venv/bin/python" cu124 2.5.1 0.20.1 2.5.1
fi
uv_install --python "$venv/bin/python" -r "$root/requirements-eval.txt"
if ! "$venv/bin/python" -c 'import flash_attn; assert flash_attn.__version__ == "2.7.1.post4"' 2>/dev/null; then
  if [[ ! -s "$wheel" ]]; then
    mkdir -p "$(dirname "$wheel")"
    if ! curl -fL --retry 2 --max-time 600 \
      'https://ghfast.top/https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.1.post4/flash_attn-2.7.1.post4%2Bcu12torch2.5cxx11abiFALSE-cp39-cp39-linux_x86_64.whl' -o "$wheel.part"; then
      curl -fL --retry 2 --max-time 600 \
        'https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.1.post4/flash_attn-2.7.1.post4%2Bcu12torch2.5cxx11abiFALSE-cp39-cp39-linux_x86_64.whl' -o "$wheel.part"
    fi
    mv "$wheel.part" "$wheel"
  fi
  uv pip install --python "$venv/bin/python" --no-deps "$wheel"
fi
uv_install --python "$venv/bin/python" --no-deps \
  -e "$workspace/habitat-lab-v0.2.4/habitat-lab" \
  -e "$workspace/habitat-lab-v0.2.4/habitat-baselines" -e "$root"
if ! "$venv/bin/python" -c 'import habitat_sim; assert habitat_sim.__version__ == "0.2.4"' 2>/dev/null; then
  echo 'f9938403f7fb2913296f4496bc06d046  '"$archive" | md5sum -c -
  stage="$(mktemp -d /tmp/janusvln-habitat.XXXXXX)"
  trap 'rm -rf "$stage"' EXIT
  tar -xjf "$archive" -C "$stage" lib/python3.9/site-packages
  src="$stage/lib/python3.9/site-packages"
  dst="$venv/lib/python3.9/site-packages"
  cp -a "$src/habitat_sim-0.2.4-py3.9-linux-x86_64.egg" "$src/habitat_sim.pth" \
    "$src/magnum" "$src/magnum-0.0.0.dist-info" "$src/_magnum.cpython-39-x86_64-linux-gnu.so" \
    "$src/corrade" "$src/_corrade.cpython-39-x86_64-linux-gnu.so" "$dst/"
fi
if [[ ! -e "$root/.venv" && ! -L "$root/.venv" ]]; then ln -s "$venv" "$root/.venv"; fi
mkdir -p "$root/data/datasets" "$root/data/scene_datasets"
for name in r2r rxr; do
  target="$root/data/datasets/$name"
  if [[ ! -e "$target" && ! -L "$target" ]]; then ln -s "$resource/assets/StreamVLN/$name" "$target"; fi
done
target="$root/data/scene_datasets/mp3d"
if [[ ! -e "$target" && ! -L "$target" ]]; then ln -s "$resource/assets/StreamVLN/mp3d" "$target"; fi
echo "JanusVLN evaluation environment: $venv"
