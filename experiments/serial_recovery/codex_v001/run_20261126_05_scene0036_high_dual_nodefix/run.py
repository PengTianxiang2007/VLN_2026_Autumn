"""Start two disjoint native same-GPU workers for the complete scene0036 cohort."""
import csv
import gzip
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core.codex_client import now, process_start_ticks, save, sha256
from core.codex_serial_config import DEFAULTS, snapshot_source
from core.codex_serial_runtime import ReviewWorker
from core.paths import resource_root
from core.seeding import episode_seed

OUT = ROOT / "outputs/serial_recovery/codex_v001" / HERE.name
SCENE = "kujiale_0036"
RETAINED = {1548476, 1548482}


def credentials():
    values = {}
    for line in (ROOT / ".env.easyjev.local").read_text().splitlines():
        line = line.strip().removeprefix("export ")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parts = shlex.split(value, comments=True)
        values[key.strip()] = parts[0] if parts else ""
    if not values.get("JEV_API_KEY"):
        raise RuntimeError("Missing private JEV credential")
    if values.get("JEV_BASE_URL", "").rstrip("/") != "https://api.easyjev.online":
        raise RuntimeError("Private JEV base URL differs from the selected service")
    return values["JEV_API_KEY"]


def admit(gpu, active):
    raw = subprocess.check_output(["nvidia-smi", "--query-gpu=index,uuid,memory.free,utilization.gpu",
                                   "--format=csv,noheader,nounits"], text=True)
    rows = [line.split(", ") for line in raw.strip().splitlines()]
    row, = [r for r in rows if int(r[0]) == gpu]
    memory, utilization = int(row[2]), int(row[3])
    processes = subprocess.check_output(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid",
                                        "--format=csv,noheader"], text=True)
    pids = {int(line.split(",")[1]) for line in processes.splitlines()
            if line.split(",")[0].strip() == row[1]}
    if pids - RETAINED:
        raise RuntimeError(f"GPU {gpu} has an unregistered process; preserving it")
    for pid in pids:
        if Path(f"/proc/{pid}/cwd").resolve() != ROOT or b"run_20261126_08_five_goal120/simulate.py" not in Path(f"/proc/{pid}/cmdline").read_bytes():
            raise RuntimeError("Retained simulator ownership mismatch")
    available = int(next(s.split()[1] for s in Path("/proc/meminfo").read_text().splitlines()
                         if s.startswith("MemAvailable:")))
    if memory < 32000 or utilization > 15 or available < 64 * 1024**2 * (active + 1):
        raise RuntimeError(f"GPU {gpu} or host RAM does not meet admission limits")
    return dict(gpu=gpu, free_mib=memory, utilization=utilization, retained_pids=sorted(pids),
                host_available_kib=available, time=now())


def prepare():
    if DEFAULTS["reasoning_effort"] != "high" or DEFAULTS["request_attempts"] != 10:
        raise RuntimeError("Expected Codex high and the approved ten-attempt guard")
    OUT.mkdir(parents=True, exist_ok=False)
    source = resource_root() / "assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz"
    with gzip.open(source, "rt") as stream:
        episodes = [e for e in json.load(stream)["episodes"] if e["scan"] == SCENE]
    ids = [e["episode_id"] for e in episodes]
    if len(ids) != 25 or len(set(ids)) != 25:
        raise ValueError("Complete scene0036 must contain 25 unique episodes")
    baseline_source = ROOT / "experiments/serial_recovery/v002/run_20261121_06_scene203/baseline203.csv"
    with baseline_source.open() as stream:
        baseline = [r for r in csv.DictReader(stream) if r["episode_id"] in ids and int(r["run_seed"]) == 2]
    if {r["episode_id"] for r in baseline} != set(ids) or len(baseline) != 25:
        raise ValueError("Incomplete paired baseline")
    for row in baseline:
        if int(row["episode_seed"]) != episode_seed(2, row["episode_id"]):
            raise ValueError("Paired baseline seed mismatch")
    with (HERE / "baseline25.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(baseline[0]))
        writer.writeheader(); writer.writerows(baseline)
    workers = []
    for gpu in (0, 1):
        run_id = f"peng_fine_codex_serial_0036_high_20261126_retry1_g{gpu}"
        workers.append(dict(gpu=gpu, episode_ids=ids[gpu::2], run_id=run_id,
                            serial_output=str(OUT / f"gpu{gpu}" / "serial"),
                            native_output=str(ROOT / "outputs/vlnverse/streamvln/results" / run_id)))
    manifest = dict(scene=SCENE, seed=2, episode_ids=ids, workers=workers, protocol=DEFAULTS,
                    prepared_at=now(), dataset_sha256=sha256(source),
                    baseline_source=str(baseline_source), baseline_sha256=sha256(HERE / "baseline25.csv"),
                    retained_simulators=sorted(RETAINED), split_rule="Alternating original split order: 13/12")
    save(HERE / "manifest.json", manifest)
    save(OUT / "manifest.json", manifest)
    snapshot_source(OUT)
    shutil.copy2(__file__, OUT / "source/run_dual.py")
    return manifest


def launch():
    node_runtime = shutil.which("node")
    if not node_runtime:
        raise RuntimeError("Node runtime is required before loading GPU services")
    os.environ["VLN_NODE_BINARY"] = node_runtime
    manifest = prepare()
    os.environ["JEV_API_KEY"] = credentials()
    admissions = [admit(gpu, 0) for gpu in (0, 1)]
    probe = OUT / "jev_probe"
    probe.mkdir()
    source = ROOT / "outputs/multiview_capture/v001/run_20261117_03/capture/episodes/kujiale_0036_0_0/attempt_1794972488070620490/steps/000000/policy_front.png"
    shutil.copy2(source, probe / "front.png")
    save(probe / "config.json", DEFAULTS)
    save(probe / "start.json", dict(episode_id="startup_probe", scene=SCENE,
         instruction="Runtime connectivity probe only; no navigation."))
    started = time.monotonic()
    worker = ReviewWorker(probe)
    try:
        reply = worker.request(dict(episode_id="startup_probe", frame=0, stop_requested=False,
             native_front=dict(image="front.png", sha256=sha256(probe / "front.png"))), lambda: None)
        if reply.get("decision") != "continue":
            raise RuntimeError("Actual CPU review worker did not acknowledge the first boundary")
    finally:
        worker.close()
    save(probe / "verification.json", dict(phase="complete", time=now(),
         latency_seconds=time.monotonic() - started, node_binary=node_runtime,
         actual_worker=True, actual_jev=True, actual_sampler=True, included_in_navigation=False))
    print("JEV_CONNECTION_VERIFIED", flush=True)
    launch_record = dict(started_at=now(), workers=[], admissions=admissions,
                         retained_simulators_unchanged=True, reasoning_effort="high", node_binary=node_runtime)
    save(OUT / "launch.json", launch_record)
    for gpu, worker in enumerate(manifest["workers"]):
        admission = admit(gpu, gpu)
        destination = OUT / f"gpu{gpu}"
        destination.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("VLN_", "PENG_", "STREAMVLN_", "JANUSVLN_"))
               and k not in ("LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "VIRTUAL_ENV")}
        env.update(VLN_OUTPUT_ROOT=str(ROOT / "outputs"), VLN_MODEL_READY_TIMEOUT="3600",
                   VLN_NODE_BINARY=node_runtime,
                   VLN_SIM_CACHE_ROOT=str(destination / "runtime_cache"),
                   VLN_CODE_COMMIT=json.loads((OUT / "source_manifest.json").read_text())["git_head"],
                   PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
        command = [sys.executable, "-Bu", str(ROOT / "benchmarks/vlnverse/runner/run_full.py"),
                   "--method", "StreamVLN", "--mode", "physical", "--seed", "2",
                   "--gpu", str(gpu), "--sim-gpu", str(gpu), "--allow-shared-gpu",
                   "--run-id", worker["run_id"], "--codex-serial-output", worker["serial_output"],
                   "--episode-ids", *worker["episode_ids"]]
        with (destination / "launcher.log").open("x") as log:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        entry = dict(worker, launcher_pid=child.pid, launcher_start_ticks=process_start_ticks(child.pid),
                     command=command, admission=admission, started_at=now())
        launch_record["workers"].append(entry)
        save(OUT / "launch.json", launch_record)
        print(json.dumps(dict(gpu=gpu, launcher_pid=child.pid, tasks=len(worker["episode_ids"]))), flush=True)
        time.sleep(2)
        if child.poll() is not None:
            raise RuntimeError(f"GPU {gpu} launcher exited; inspect its launcher.log")


if __name__ == "__main__":
    launch()
