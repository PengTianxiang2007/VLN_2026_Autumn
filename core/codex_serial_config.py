"""Frozen defaults shared by the Isaac hook and its CPU reviewer."""
from pathlib import Path
import json
import shutil
import subprocess

from core.codex_client import save, sha256

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "experiments/serial_recovery/codex_v001/prompt_en.txt"
DEFAULTS = dict(version="codex_serial_v001_guard1", movement_budget=180, model="gpt-6-astra",
                reasoning_effort="high", proxy_url="http://127.0.0.1:7892",
                timeout_seconds=300, jev_endpoint="https://api.easyjev.online/v1/systemone",
                request_attempts=10, jev_timeout_seconds=120, jev_total_seconds=420,
                codex_total_seconds=600, boundary_timeout_seconds=1800,
                recovery_idle_seconds=300, recovery_no_move_seconds=600,
                recovery_total_seconds=2700)


def snapshot_source(output):
    paths = [*ROOT.glob("core/codex_*.py"), ROOT / "core/jev_request_runner.py", ROOT / "core/jev_node.py",
             ROOT / "core/jev_online_sampler_v001.js", ROOT / "core/jev_online_sampler_v002.js",
             ROOT / "scripts/jev_sampler_stdio.cjs", ROOT / "scripts/run_codex_shadow.py",
             ROOT / "scripts/run_codex_serial_worker.py", ROOT / "scripts/run_deviation_progress_review.py",
             ROOT / "scripts/vlnverse_robot_bridge.py", ROOT / "scripts/vlnverse_robot_mcp.py",
             ROOT / "scripts/codex_vlnverse_robot.sh", ROOT / "scripts/run_inverse_rollback.py",
             ROOT / "benchmarks/vlnverse/runner/run_full.py",
             ROOT / "core/vlnverse_runtime.py",
             ROOT / "benchmarks/vlnverse/upstream/vlnverse/evaluator/vln_pe_evaluator.py", PROMPT]
    # Freeze the inherited prompts and dedup protocol as well as the adapter.
    paths.extend(ROOT.glob("core/codex_checkpoint_*_en.txt"))
    paths.extend(ROOT.glob("experiments/deviation_progress/codex_memory_v*/prompt_en.txt"))
    paths.append(ROOT / "experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/"
                 "node_deduplication/v001_run02_all/run_dedup.py")
    paths = sorted(set(Path(p) for p in paths))
    hashes = {str(p.relative_to(ROOT)): sha256(p) for p in paths}
    manifest = output / "source_manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text())["sha256"] != hashes:
            raise ValueError("Source changed; prepare a new serial output directory")
        return
    target = output / "source"
    target.mkdir()
    for path in paths:
        copy = target / path.relative_to(ROOT)
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copy)
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    diff = subprocess.check_output(["git", "-C", str(ROOT), "diff", "HEAD", "--", *hashes])
    (output / "source.diff").write_bytes(diff)
    save(manifest, dict(git_head=head, sha256=hashes, source_snapshot=str(target)))
