"""Cache a public wheel with resumable HTTP Range downloads (stdlib only)."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
import zipfile


def download(url, target, use_proxy=False):
    opener = urllib.request.build_opener() if use_proxy else urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(urllib.request.Request(url, method="HEAD"), timeout=30) as response:
        total = int(response.headers["Content-Length"])
    partial, state_path = Path(str(target) + ".part"), Path(str(target) + ".progress.json")
    block_size = 16 * 1024 * 1024
    state = {"bytes": total, "block_size": block_size, "completed": []}
    if partial.exists() and state_path.exists():
        saved = json.loads(state_path.read_text())
        if saved["bytes"] != total or saved["block_size"] != block_size:
            raise RuntimeError("Partial download has a different size; preserving it for inspection")
        state = saved
    fd = os.open(partial, os.O_RDWR | os.O_CREAT, 0o644)
    os.ftruncate(fd, total)
    completed = set(state["completed"])
    blocks = (total + block_size - 1) // block_size

    def fetch(index):
        start, end = index * block_size, min((index + 1) * block_size, total) - 1
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
                with opener.open(request, timeout=60) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{total}":
                        raise RuntimeError("Server did not honor the requested byte range")
                    offset = start
                    while offset <= end:
                        data = response.read(min(1024 * 1024, end + 1 - offset))
                        if not data:
                            raise RuntimeError("Truncated byte range")
                        written = os.pwrite(fd, data, offset)
                        if written != len(data):
                            raise RuntimeError("Short disk write")
                        offset += written
                return index
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)

    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(fetch, i) for i in range(blocks) if i not in completed]
            last_print = 0.0
            for future in as_completed(futures):
                try:
                    completed.add(future.result())
                except Exception:
                    for pending in futures:
                        pending.cancel()
                    raise
                state["completed"] = sorted(completed)
                temporary = Path(str(state_path) + ".tmp")
                temporary.write_text(json.dumps(state))
                temporary.replace(state_path)
                if time.monotonic() - last_print > 20 or len(completed) == blocks:
                    print(f"{target.name}: {len(completed)}/{blocks} blocks ({total / 1024**2:.1f} MiB)", flush=True)
                    last_print = time.monotonic()
    finally:
        os.close(fd)
    with zipfile.ZipFile(partial) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"Wheel CRC mismatch: {bad}")
    digest = hashlib.sha256()
    with partial.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    partial.replace(target)
    Path(str(target) + ".verified.json").write_text(json.dumps({
        "source": url, "bytes": total, "sha256": digest.hexdigest(), "zip_crc_verified": True}, indent=2) + "\n")
    print(f"Cached and verified {target}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--fallback-url")
    parser.add_argument("--mirror-fallback-url")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--use-proxy", action="store_true", help="Use the inherited proxy for the initial URL")
    args = parser.parse_args()
    if args.target.is_file():
        with zipfile.ZipFile(args.target) as archive:
            if archive.testzip():
                raise RuntimeError("Existing wheel failed CRC; preserving it for inspection")
        print(f"Reusing {args.target}", flush=True)
        return
    args.target.parent.mkdir(parents=True, exist_ok=True)
    sources = [(args.url, args.use_proxy)]
    if args.mirror_fallback_url:
        sources.append((args.mirror_fallback_url, False))
    if args.fallback_url:
        sources.append((args.fallback_url, True))
    last_error = None
    for url, use_proxy in sources:
        try:
            download(url, args.target, use_proxy=use_proxy)
            return
        except Exception as error:
            last_error = error
            print(f"Source failed: {error}; retaining completed blocks", flush=True)
    raise RuntimeError("All configured wheel sources failed") from last_error


if __name__ == "__main__":
    main()
