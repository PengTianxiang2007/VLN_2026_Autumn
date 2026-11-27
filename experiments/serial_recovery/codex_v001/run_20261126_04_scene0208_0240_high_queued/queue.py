"""Queue two complete scenes after the corresponding scene0036 workers."""
import csv
import fcntl
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core.codex_client import now, process_start_ticks, save, sha256
from core.codex_serial_config import DEFAULTS, snapshot_source
from core.paths import resource_root
from core.seeding import episode_seed

OUT = ROOT / "outputs/serial_recovery/codex_v001" / HERE.name
PREVIOUS = ROOT / "outputs/serial_recovery/codex_v001/run_20261126_03_scene0036_high_dual"
HELPER = HERE.parent / "run_20261126_03_scene0036_high_dual/run.py"
SCENES = ("kujiale_0208", "kujiale_0240")


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def alive(entry):
    pid = entry["launcher_pid"]
    try:
        return (str(process_start_ticks(pid)) == str(entry["launcher_start_ticks"])
                and Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z")
    except (OSError, ProcessLookupError):
        return False


def completion(entry):
    """Require native completion and exact formally scored episode membership."""
    native, serial = Path(entry["native_output"]), Path(entry["serial_output"])
    if (native / "failure.json").exists() or (serial / "halt.json").exists():
        return "failed"
    result = read(native / "result.json")
    if result.get("status") != "complete":
        return "incomplete"
    ids = set()
    for path in serial.glob("episodes/*/attempt_*/result.json"):
        item = read(path)
        metrics = item.get("metrics", {})
        if "success" in metrics and "spl" in metrics:
            ids.add(item.get("episode_id", path.parent.parent.name))
    return "complete" if ids == set(entry["episode_ids"]) else "incomplete"


def prepare():
    if DEFAULTS["reasoning_effort"] != "high" or DEFAULTS["movement_budget"] != 180:
        raise ValueError("Expected approved high / 180 movement protocol")
    previous = read(PREVIOUS / "launch.json")["workers"]
    source = resource_root() / "assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz"
    with gzip.open(source, "rt") as stream:
        episodes = json.load(stream)["episodes"]
    baseline_source = ROOT / "experiments/serial_recovery/v002/run_20261121_06_scene203/baseline203.csv"
    with baseline_source.open() as stream:
        baseline = [r for r in csv.DictReader(stream) if int(r["run_seed"]) == 2 and r["scene"] in SCENES]
    lanes = []
    for gpu, (scene, count) in enumerate(zip(SCENES, (25, 23))):
        ids = [e["episode_id"] for e in episodes if e["scan"] == scene]
        if len(ids) != count or len(set(ids)) != count or any("0128" in e for e in ids):
            raise ValueError("Unexpected scene membership or excluded 0128 scene")
        rows = [r for r in baseline if r["episode_id"] in ids]
        if len(rows) != count or {r["episode_id"] for r in rows} != set(ids):
            raise ValueError("Incomplete paired original results")
        if any(int(r["episode_seed"]) != episode_seed(2, r["episode_id"]) for r in rows):
            raise ValueError("Original seed mismatch")
        predecessor, = [w for w in previous if w["gpu"] == gpu]
        run_id = f"peng_fine_codex_serial_{scene.removeprefix('kujiale_')}_high_20261126_g{gpu}"
        lanes.append(dict(gpu=gpu, scene=scene, episode_ids=ids, predecessor=predecessor,
                          run_id=run_id, native_output=str(ROOT / "outputs/vlnverse/streamvln/results" / run_id),
                          serial_output=str(OUT / f"gpu{gpu}" / "serial")))
    OUT.mkdir(parents=True, exist_ok=False)
    with (HERE / "baseline48.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(baseline[0]))
        writer.writeheader()
        writer.writerows(baseline)
    manifest = dict(prepared_at=now(), seed=2, scenes=list(SCENES), excluded_scene="0128 including fix variants",
                    selection="User selected 0208 in place of 0234; 0240 has complete seed-2 baseline; no episode outcome filtering",
                    workers=lanes, protocol=DEFAULTS, dataset_sha256=sha256(source),
                    baseline_source=str(baseline_source), baseline_sha256=sha256(HERE / "baseline48.csv"),
                    helper_sha256=sha256(HELPER), queue_sha256=sha256(Path(__file__)))
    save(HERE / "manifest.json", manifest)
    save(OUT / "manifest.json", manifest)
    snapshot_source(OUT)
    shutil.copy2(__file__, OUT / "source/queue.py")
    shutil.copy2(HELPER, OUT / "source/previous_run.py")
    return manifest


def launch(lane, manifest, helper):
    snapshot_source(OUT)  # Refuse silent changes while this queue was waiting.
    if sha256(HELPER) != manifest["helper_sha256"]:
        raise RuntimeError("Launch helper changed; prepare a new run")
    destination = OUT / f"gpu{lane['gpu']}"
    destination.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VLN_", "PENG_", "STREAMVLN_", "JANUSVLN_"))
           and k not in ("LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "VIRTUAL_ENV")}
    env.update(JEV_API_KEY=helper.credentials(), VLN_OUTPUT_ROOT=str(ROOT / "outputs"),
               VLN_MODEL_READY_TIMEOUT="3600", VLN_SIM_CACHE_ROOT=str(destination / "runtime_cache"),
               VLN_CODE_COMMIT=read(OUT / "source_manifest.json")["git_head"],
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
    cmd = [sys.executable, "-Bu", str(ROOT / "benchmarks/vlnverse/runner/run_full.py"),
           "--method", "StreamVLN", "--mode", "physical", "--seed", "2",
           "--gpu", str(lane["gpu"]), "--sim-gpu", str(lane["gpu"]), "--allow-shared-gpu",
           "--run-id", lane["run_id"], "--codex-serial-output", lane["serial_output"],
           "--episode-ids", *lane["episode_ids"]]
    with (destination / "launcher.log").open("x") as log:
        child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    save(destination / "launch.json", dict(lane, launcher_pid=child.pid,
         launcher_start_ticks=process_start_ticks(child.pid), command=cmd, started_at=now()))
    return child


def worker():
    lock = (OUT / "queue.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    manifest = read(OUT / "manifest.json")
    if sha256(Path(__file__)) != manifest["queue_sha256"] or sha256(HELPER) != manifest["helper_sha256"]:
        raise RuntimeError("Queue source changed")
    spec = importlib.util.spec_from_file_location("previous_launch", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    state = dict(queued_at=now(), queue_pid=os.getpid(), queue_start_ticks=process_start_ticks(os.getpid()),
                 workers=[dict(gpu=w["gpu"], scene=w["scene"], tasks=len(w["episode_ids"]),
                               phase="waiting_predecessor") for w in manifest["workers"]])
    children = {}

    def persist():
        state["updated_at"] = now()
        save(OUT / "queue_status.json", state)

    persist()
    try:
        while True:
            for lane, status in zip(manifest["workers"], state["workers"]):
                gpu = lane["gpu"]
                if status["phase"] in ("complete", "failed", "blocked_predecessor"):
                    continue
                if gpu in children:
                    rc = children[gpu].poll()
                    if rc is not None:
                        status.update(phase="complete" if rc == 0 and completion(lane) == "complete" else "failed",
                                      returncode=rc, finished_at=now())
                    continue
                predecessor = lane["predecessor"]
                outcome = completion(predecessor)
                if outcome == "failed":
                    status.update(phase="blocked_predecessor", reason="Predecessor technical failure; no automatic continuation")
                    continue
                if alive(predecessor):
                    continue
                if outcome != "complete":
                    status.update(phase="blocked_predecessor", reason="Predecessor exited without complete formal scores")
                    continue
                owned = read(Path(predecessor["native_output"]) / "owned_processes.json")
                if owned.get("status") != "stopped":
                    status.update(phase="blocked_predecessor", reason="Predecessor cleanup not confirmed")
                    continue
                try:
                    status["admission"] = helper.admit(gpu, 1)
                    # Two low-load readings, separated by the normal queue poll.
                    if status["phase"] != "admission_confirming":
                        status.update(phase="admission_confirming")
                        continue
                except RuntimeError as error:
                    status.update(phase="waiting_resources", reason=str(error))
                    continue
                try:
                    children[gpu] = launch(lane, manifest, helper)
                    status.pop("reason", None)
                    status.update(phase="running", launcher_pid=children[gpu].pid, started_at=now())
                except Exception as error:
                    status.update(phase="failed", error_type=type(error).__name__, reason=str(error), finished_at=now())
            persist()
            if all(s["phase"] in ("complete", "failed", "blocked_predecessor") for s in state["workers"]):
                break
            time.sleep(30)
    finally:
        # Signal only this queue's direct children; their native finally blocks own GPU cleanup.
        for gpu, child in children.items():
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    state["workers"][gpu]["cleanup_pending"] = True
                state["workers"][gpu].update(phase="cancelled", finished_at=now())
        state["queue_exited_at"] = now()
        persist()


if __name__ == "__main__":
    if sys.argv[1:] == ["--worker"]:
        def stop(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        worker()
    elif not sys.argv[1:]:
        prepare()
        with (OUT / "queue.log").open("x") as log:
            child = subprocess.Popen([sys.executable, "-Bu", str(Path(__file__)), "--worker"],
                                     cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
        save(OUT / "queue_launch.json", dict(pid=child.pid, start_ticks=process_start_ticks(child.pid), time=now()))
        print(json.dumps(dict(queue_pid=child.pid, output=str(OUT), additional_tasks=48)))
    else:
        raise SystemExit("Use no args to prepare/enqueue; --worker is internal")
