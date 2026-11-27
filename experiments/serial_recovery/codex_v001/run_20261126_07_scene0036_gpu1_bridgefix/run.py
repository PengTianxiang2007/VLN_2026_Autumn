"""Restart only the unscored GPU1 subset after fixing scripts package shadowing."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core.codex_client import now, process_start_ticks, save, sha256
from core.codex_serial_config import DEFAULTS, snapshot_source

OUT = ROOT / "outputs/serial_recovery/codex_v001" / HERE.name
PREVIOUS = ROOT / "outputs/serial_recovery/codex_v001/run_20261126_05_scene0036_high_dual_nodefix"
HELPER = HERE.parent / "run_20261126_05_scene0036_high_dual_nodefix/run.py"
BRIDGE = ROOT / "benchmarks/vlnverse/upstream/scripts/vlnverse_robot_bridge.py"


def main():
    spec = importlib.util.spec_from_file_location("verified_launcher", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    previous, = [w for w in json.loads((PREVIOUS / "launch.json").read_text())["workers"] if w["gpu"] == 1]
    owned = json.loads((Path(previous["native_output"]) / "owned_processes.json").read_text())
    if owned.get("status") != "stopped" or list(Path(previous["serial_output"]).glob("episodes/*/attempt_*/result.json")):
        raise RuntimeError("Expected stopped predecessor with zero formal scores")
    admission = helper.admit(1, 1)
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Missing Node runtime")
    # Exercise the exact package search order without loading Isaac or the GPU.
    probe_env = dict(os.environ, PYTHONPATH=str(ROOT / "benchmarks/vlnverse/upstream") + os.pathsep + str(ROOT))
    subprocess.run([str(ROOT / "benchmarks/vlnverse/.venv/bin/python"), "-B", "-c",
                    "from scripts.vlnverse_robot_bridge import serve; assert serve.__module__ == 'vlnverse_robot_bridge'"],
                   cwd=ROOT / "benchmarks/vlnverse/upstream", env=probe_env, check=True, timeout=30)
    OUT.mkdir(parents=True, exist_ok=False)
    run_id = "peng_fine_codex_serial_0036_high_20261126_retry2_g1"
    worker = dict(gpu=1, episode_ids=previous["episode_ids"], run_id=run_id,
                  serial_output=str(OUT / "gpu1/serial"),
                  native_output=str(ROOT / "outputs/vlnverse/streamvln/results" / run_id))
    with (HERE.parent / "run_20261126_05_scene0036_high_dual_nodefix/baseline25.csv").open() as stream:
        baseline = [r for r in csv.DictReader(stream) if r["episode_id"] in worker["episode_ids"]]
    if len(baseline) != 12 or {r["episode_id"] for r in baseline} != set(worker["episode_ids"]):
        raise RuntimeError("Paired baseline mismatch")
    with (HERE / "baseline12.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(baseline[0]))
        writer.writeheader()
        writer.writerows(baseline)
    manifest = dict(prepared_at=now(), seed=2, workers=[worker], predecessor=previous,
                    protocol=DEFAULTS, bridge_sha256=sha256(BRIDGE), baseline_sha256=sha256(HERE / "baseline12.csv"))
    save(HERE / "manifest.json", manifest)
    save(OUT / "manifest.json", manifest)
    snapshot_source(OUT)
    shutil.copy2(__file__, OUT / "source/run_gpu1.py")
    shutil.copy2(BRIDGE, OUT / "source/vlnverse_robot_bridge_compat.py")
    destination = OUT / "gpu1"
    destination.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VLN_", "PENG_", "STREAMVLN_", "JANUSVLN_"))
           and k not in ("LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "VIRTUAL_ENV")}
    env.update(JEV_API_KEY=helper.credentials(), VLN_OUTPUT_ROOT=str(ROOT / "outputs"),
               VLN_MODEL_READY_TIMEOUT="3600", VLN_NODE_BINARY=node,
               VLN_SIM_CACHE_ROOT=str(destination / "runtime_cache"),
               VLN_CODE_COMMIT=json.loads((OUT / "source_manifest.json").read_text())["git_head"],
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
    command = [sys.executable, "-Bu", str(ROOT / "benchmarks/vlnverse/runner/run_full.py"),
               "--method", "StreamVLN", "--mode", "physical", "--seed", "2", "--gpu", "1", "--sim-gpu", "1",
               "--allow-shared-gpu", "--run-id", run_id, "--codex-serial-output", worker["serial_output"],
               "--episode-ids", *worker["episode_ids"]]
    with (destination / "launcher.log").open("x") as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    entry = dict(worker, launcher_pid=child.pid, launcher_start_ticks=process_start_ticks(child.pid),
                 started_at=now(), command=command, admission=admission)
    save(OUT / "launch.json", dict(started_at=now(), workers=[entry], retained_simulators_unchanged=True))
    print(json.dumps(dict(gpu=1, launcher_pid=child.pid, tasks=12)), flush=True)


if __name__ == "__main__":
    main()
