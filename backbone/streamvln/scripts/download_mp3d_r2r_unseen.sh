#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
assets=/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN
archive="$assets/mp3d_habitat.zip"
partial="$archive.partial"
expected=470948ee78ff4d6dc4c4870395d1e790a0f15c72065d1f62cdd229b2bcbe0d36
repo=Believe0029/MP3D_hab
proxy=http://127.0.0.1:7892
scenes=(2azQ1b91cZZ 8194nk5LbLH EU6Fwq7SyZv QUCTc6BB5sX TbHJrupSAjP X7HyMhZNoso Z6MFQCViBuw oLBMNvg9in8 pLe4wQe7qrG x8F5xyUWy9e zsNo4HB9uLZ)

log() { printf '%s %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$*"; }
verified() { [[ -f "$1" ]] && printf '%s  %s\n' "$expected" "$1" | sha256sum -c - >/dev/null; }

mkdir -p "$assets"
if verified "$archive"; then
  log 'Existing MP3D archive verified'
else
  if [[ -e "$archive" ]]; then
    log "Existing archive checksum mismatch; refusing to overwrite $archive"
    exit 1
  fi
  log 'Downloading MP3D Habitat archive from hf-mirror.com'
  if ! env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY aria2c \
    --console-log-level=warn --max-concurrent-downloads=1 --split=4 \
    --max-connection-per-server=4 --min-split-size=64M --file-allocation=none \
    --continue=true --auto-file-renaming=false --max-tries=5 --retry-wait=10 \
    --connect-timeout=30 --timeout=60 --summary-interval=300 \
    --dir="$assets" --out=mp3d_habitat.zip.partial \
    "https://hf-mirror.com/datasets/$repo/resolve/main/mp3d_habitat.zip"; then
    log 'Mirror failed; retrying official Hugging Face through port 7892'
    aria2c --all-proxy="$proxy" --console-log-level=warn \
      --max-concurrent-downloads=1 --split=4 --max-connection-per-server=4 \
      --min-split-size=64M --file-allocation=none --continue=true \
      --auto-file-renaming=false --max-tries=5 --retry-wait=10 \
      --connect-timeout=30 --timeout=60 --summary-interval=300 \
      --dir="$assets" --out=mp3d_habitat.zip.partial \
      "https://huggingface.co/datasets/$repo/resolve/main/mp3d_habitat.zip"
  fi
  printf '%s  %s\n' "$expected" "$partial" | sha256sum -c -
  mv "$partial" "$archive"
  log 'MP3D archive SHA256 verified'
fi

for sid in "${scenes[@]}"; do
  if [[ -s "$assets/mp3d/$sid/$sid.glb" && -s "$assets/mp3d/$sid/$sid.navmesh" ]]; then
    log "Existing scene $sid retained"
    continue
  fi
  unzip -nq "$archive" "mp3d/$sid/*" -d "$assets"
  test -s "$assets/mp3d/$sid/$sid.glb"
  test -s "$assets/mp3d/$sid/$sid.navmesh"
  log "Extracted scene $sid"
done

mkdir -p "$root/data/scene_datasets"
if [[ ! -e "$root/data/scene_datasets/mp3d" ]]; then
  ln -s "$assets/mp3d" "$root/data/scene_datasets/mp3d"
fi
log 'All 11 R2R val_unseen scenes are ready'
