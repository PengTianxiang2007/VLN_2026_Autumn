#!/usr/bin/env bash
# Source from the model setup scripts. All changes are local to this process/repo.
project="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime="${VLN_RUNTIME_ROOT:-$project/.runtime}"
export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$runtime/python}"
export UV_PYTHON_BIN_DIR="${UV_PYTHON_BIN_DIR:-$runtime/bin}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$runtime/cache}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-120}"
export UV_CONCURRENT_DOWNLOADS="${UV_CONCURRENT_DOWNLOADS:-4}"
export UV_CONCURRENT_BUILDS="${UV_CONCURRENT_BUILDS:-2}"
export UV_CONCURRENT_INSTALLS="${UV_CONCURRENT_INSTALLS:-4}"
export UV_HTTP_RETRIES="${UV_HTTP_RETRIES:-1}"
export MAX_JOBS="${MAX_JOBS:-2}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
export OPENBLAS_NUM_THREADS=2
# Domestic mirrors are accessed directly; upstream GitHub uses the inherited proxy.
mirror_hosts="mirror.sjtu.edu.cn,s3.jcloud.sjtu.edu.cn,pypi.tuna.tsinghua.edu.cn,mirrors.nju.edu.cn,ghfast.top"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$mirror_hosts"
export no_proxy="$NO_PROXY"
export PATH="$runtime/tools/bin:$runtime/bin:$PATH"

ensure_uv() {
  if command -v uv >/dev/null; then return; fi
  mkdir -p "$runtime/tools"
  local index
  for index in https://pypi.tuna.tsinghua.edu.cn/simple https://mirror.sjtu.edu.cn/pypi/web/simple https://pypi.org/simple; do
    if python3 -m pip install --target "$runtime/tools" --no-cache-dir --only-binary=:all: --index-url "$index" 'uv==0.12.24'; then return; fi
  done
  return 1
}

ensure_python() {
  uv python install 3.9.25 --no-bin --mirror https://ghfast.top/https://github.com/astral-sh/python-build-standalone/releases/download ||
    uv python install 3.9.25 --no-bin --mirror https://github.com/astral-sh/python-build-standalone/releases/download
}

uv_install() {
  local index
  local cached_wheels="${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}/software/pytorch/pip_cache_reused"
  local -a cache_args=()
  if [[ -d "$cached_wheels" ]]; then cache_args=(--find-links "$cached_wheels"); fi
  for index in https://pypi.tuna.tsinghua.edu.cn/simple https://mirror.sjtu.edu.cn/pypi/web/simple https://pypi.org/simple; do
    if uv pip install --index-url "$index" "${cache_args[@]}" "$@"; then return; fi
    echo "Installation from $index failed; trying the next source." >&2
  done
  return 1
}

install_torch() {
  local python_bin="$1" cuda="$2" torch_version="$3" vision_version="$4" audio_version="${5:-}"
  local package version filename target
  local -a wheels
  wheels=()
  # Cache first: uv's streaming metadata fetch can stall on this mirror's redirect.
  for package in torch torchvision torchaudio; do
    case "$package" in torch) version="$torch_version" ;; torchvision) version="$vision_version" ;; torchaudio) version="$audio_version" ;; esac
    [[ -n "$version" ]] || continue
    filename="$package-$version+$cuda-cp39-cp39-linux_x86_64.whl"
    target="${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}/software/pytorch/$filename"
    if [[ "${VLN_TORCH_SOURCE:-mirror}" == upstream ]]; then
      python3 "$project/scripts/download_wheel.py" \
        --url "https://download.pytorch.org/whl/$cuda/${filename/+/%2B}" --use-proxy --target "$target" || return 1
    elif [[ "${VLN_TORCH_SOURCE:-mirror}" == nju ]]; then
      python3 "$project/scripts/download_wheel.py" \
        --url "https://mirrors.nju.edu.cn/pytorch/whl/$cuda/${filename/+/%2B}" \
        --fallback-url "https://download.pytorch.org/whl/$cuda/${filename/+/%2B}" --target "$target" || return 1
    else
      python3 "$project/scripts/download_wheel.py" \
        --url "https://mirror.sjtu.edu.cn/pytorch-wheels/$cuda/${filename/+/%2B}" \
        --mirror-fallback-url "https://mirrors.nju.edu.cn/pytorch/whl/$cuda/${filename/+/%2B}" \
        --fallback-url "https://download.pytorch.org/whl/$cuda/${filename/+/%2B}" --target "$target" || return 1
    fi
    wheels+=("$target")
  done
  uv_install --python "$python_bin" "${wheels[@]}"
}
