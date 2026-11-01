#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

resource="${VLN_RESOURCE_ROOT:-/mnt/nas/gezuhao/shared_dataset/Resource_Peng}"/models
checkpoint="$resource/StreamVLN_R2R_v1_3"
siglip="$resource/siglip-so400m-patch14-384"
repo=mengwei0427/StreamVLN_Video_qwen_1_5_r2r_rxr_envdrop_scalevln_v1_3
proxy=http://127.0.0.1:7892

log() { printf '%s %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$*"; }
verified() { [[ -f "$1" ]] && printf '%s  %s\n' "$2" "$1" | sha256sum -c - >/dev/null; }
wait_for_previous() {
  local pid="${1:-}"
  [[ -z "$pid" ]] && return
  while kill -0 "$pid" 2>/dev/null; do sleep 60; done
}
fetch_shard() {
  local name="$1" hash="$2" target="$checkpoint/$1"
  if verified "$target" "$hash"; then log "Verified existing $name"; return; fi
  if [[ -f "$target" ]]; then log "Hash mismatch for $target; refusing to overwrite"; return 1; fi
  local partial="$target.partial"
  log "Downloading $name from hf-mirror.com"
  if ! env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY aria2c \
    --console-log-level=warn --max-concurrent-downloads=1 --split=4 \
    --max-connection-per-server=4 --min-split-size=64M --file-allocation=none \
    --continue=true --auto-file-renaming=false --max-tries=4 --retry-wait=10 \
    --dir="$checkpoint" --out="$name.partial" \
    "https://hf-mirror.com/$repo/resolve/main/$name"; then
    log "Mirror failed; retrying $name from Hugging Face through port 7892"
    aria2c --all-proxy="$proxy" --console-log-level=warn \
      --max-concurrent-downloads=1 --split=2 --max-connection-per-server=2 \
      --min-split-size=64M --file-allocation=none --continue=true \
      --auto-file-renaming=false --max-tries=4 --retry-wait=10 \
      --dir="$checkpoint" --out="$name.partial" \
      "https://huggingface.co/$repo/resolve/main/$name"
  fi
  printf '%s  %s\n' "$hash" "$partial" | sha256sum -c -
  mv "$partial" "$target"
  log "Verified $name"
}

mkdir -p "$checkpoint" "$siglip"
wait_for_previous "${WAIT_SHARD3_PID:-}"
fetch_shard model-00001-of-00004.safetensors 6a1a4fc8ba9ab5e8832d2d23dc6d21d18bf1f84daf03b904409721f93927a87a
fetch_shard model-00002-of-00004.safetensors d7b781ef3772d39537f81fb87a31b5db04118fbf9edcd78dbe60ad2d67d77f49
fetch_shard model-00003-of-00004.safetensors 9a79a47a31c62fc2beab869cebf2e7bf956dbf630c14ef6017148fa7e41fe628
fetch_shard model-00004-of-00004.safetensors 5e9eb8f127c0ec37b175c266b0cbae3106a591ec3d93698aee500f7735f041fe

wait_for_previous "${WAIT_SIGLIP_PID:-}"
siglip_hash=ea2abad2b7f8a9c1aa5e49a244d5d57ffa71c56f720c94bc5d240ef4d6e1d94a
if ! verified "$siglip/model.safetensors" "$siglip_hash"; then
  log "SigLIP mirror download did not complete; using Hugging Face via port 7892"
  env HTTPS_PROXY="$proxy" HTTP_PROXY="$proxy" HF_ENDPOINT=https://huggingface.co \
    HF_HOME=/tmp/streamvln-hf-cache HF_XET_NUM_CONCURRENT_RANGE_GETS=4 \
    "${STREAMVLN_VENV:-$root/.venv}/bin/python" - <<'PY'
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='google/siglip-so400m-patch14-384',
    filename='model.safetensors',
    local_dir='/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/siglip-so400m-patch14-384',
)
PY
fi
printf '%s  %s\n' "$siglip_hash" "$siglip/model.safetensors" | sha256sum -c -

python3 - "$checkpoint" "$siglip" <<'PY'
import json, shutil, sys
from pathlib import Path
checkpoint, siglip = map(Path, sys.argv[1:])
config_path = checkpoint / 'config.json'
backup = checkpoint / 'config.upstream.json'
if not backup.exists():
    shutil.copy2(config_path, backup)
config = json.loads(config_path.read_text())
config['mm_vision_tower'] = str(siglip)
config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n')
print('Pointed checkpoint config at local SigLIP weights')
PY
log 'All benchmark weights verified and ready'
