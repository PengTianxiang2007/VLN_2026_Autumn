#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace="$(cd "$root/../.." && pwd)/benchmarks/habitat_ce"
venv_path="${STREAMVLN_VENV:-$root/.venv}"
resource_root="${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}"
sim_archive="$resource_root/software/StreamVLN/habitat-sim-0.2.4-py3.9-headless-bullet.tar.bz2"
flash_wheel="$resource_root/software/StreamVLN/flash_attn-2.7.0.post2+cu12torch2.1cxx11abiFALSE-cp39-cp39-linux_x86_64.whl"
lab_dir="$workspace/habitat-lab-v0.2.4"
source "$(cd "$root/../.." && pwd)/scripts/uv_common.sh"
ensure_uv

cd "$root"
if [[ ! -x "$venv_path/bin/python" ]]; then
  ensure_python
  uv venv "$venv_path" --python 3.9.25 --no-python-downloads
fi
if ! "$venv_path/bin/python" -c 'import torch, torchvision; assert torch.__version__ == "2.1.2+cu121"' 2>/dev/null; then
  install_torch "$venv_path/bin/python" cu121 2.1.2 0.16.2
fi
uv_install --python "$venv_path/bin/python" -r requirements-r2r-eval.txt
if ! "$venv_path/bin/python" -c 'import flash_attn; assert flash_attn.__version__ == "2.7.0.post2"' 2>/dev/null; then
  echo 'a0d7a126d77885cd49de710f9bc7f008565ddef27f63b9fe2c1f1d05396e43bc  '"$flash_wheel" | sha256sum -c -
  uv pip install --python "$venv_path/bin/python" --no-deps "$flash_wheel"
fi

if [[ ! -f "$lab_dir/habitat-lab/setup.py" ]]; then
  git clone --depth 1 --branch v0.2.4 https://github.com/facebookresearch/habitat-lab.git "$lab_dir"
fi
if ! "$venv_path/bin/python" -c 'from importlib.metadata import version; assert version("habitat-lab") == "0.2.4"; assert version("habitat-baselines") == "0.2.4"' 2>/dev/null; then
  uv_install --python "$venv_path/bin/python" --no-deps \
    -e "$lab_dir/habitat-lab" -e "$lab_dir/habitat-baselines"
fi
uv_install --python "$venv_path/bin/python" \
  'gym>=0.22,<0.23.1' 'attrs>=19.1' 'tensorboard==2.8.0' 'protobuf==3.20.1' \
  'lmdb>=0.98' ifcfg 'webdataset==0.1.40' 'moviepy>=1.0.1' \
  'faster_fifo>=1.4.2' 'threadpoolctl>=3.1.0'

if ! "$venv_path/bin/python" -c 'import habitat_sim; assert habitat_sim.__version__ == "0.2.4"' 2>/dev/null; then
  if [[ ! -s "$sim_archive" ]]; then
    echo "Missing verified Habitat-Sim archive: $sim_archive" >&2
    exit 1
  fi
  echo 'f9938403f7fb2913296f4496bc06d046  '"$sim_archive" | md5sum -c -
  stage="$(mktemp -d /tmp/streamvln-habitat.XXXXXX)"
  trap 'rm -rf "$stage"' EXIT
  tar -xjf "$sim_archive" -C "$stage" lib/python3.9/site-packages
  src="$stage/lib/python3.9/site-packages"
  dst="$venv_path/lib/python3.9/site-packages"
  cp -a "$src/habitat_sim-0.2.4-py3.9-linux-x86_64.egg" "$src/habitat_sim.pth" \
    "$src/magnum" "$src/magnum-0.0.0.dist-info" "$src/_magnum.cpython-39-x86_64-linux-gnu.so" \
    "$src/corrade" "$src/_corrade.cpython-39-x86_64-linux-gnu.so" "$dst/"
fi

if [[ -d .venv && ! -L .venv ]]; then
  echo 'Existing .venv directory found; leaving it untouched. Use STREAMVLN_VENV directly.' >&2
elif [[ "$venv_path" != "$root/.venv" ]]; then
  ln -sfn "$venv_path" .venv
fi
echo "StreamVLN uv environment ready: $venv_path"
