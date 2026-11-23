"""Queue the remaining cases after the current H1 pilot and aggregate its 22 endpoints."""
import getpass
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

from run_vlm_rollback import read, save, sha


ROOT = Path.cwd()
SERIES = Path("inverse_rollback/vlm_action_v001")
BASE = ROOT / "outputs" / SERIES
NAME = "run_20261123_05_finish22"
OUT = BASE / NAME
RECORD = ROOT / "experiments" / SERIES / NAME
FIRST = BASE / "run_20261123_03_deepseek3"
PREVIOUS = BASE / "run_20261123_04_deepseek10"
DATA = BASE / "run_20261123_02/manifest.json"


def collect(rows, runs):
    expected = {r["case_id"]: r["episode_id"] for r in rows}
    results = {}
    reuse = {}
    for run in runs:
        manifest = run / "manifest.json"
        if not manifest.is_file():
            continue
        for case in read(manifest)["cases"]:
            cid = case["case_id"]
            if case["episode_id"] != expected[cid]:
                raise ValueError(f"Episode mismatch for {cid} in {run}")
            folder = run / "cases" / cid
            desc = folder / "requests/outbound"
            if (desc/"answer.json").is_file():
                reuse[cid] = str(desc.relative_to(ROOT))
            result = folder / "result.json"
            if result.is_file():
                value = read(result)
                if cid in results or value["case"] != cid:
                    raise ValueError(f"Duplicate or mismatched result for {cid}")
                results[cid] = dict(value, episode_id=expected[cid], source=str(result.relative_to(ROOT)))
    return results, reuse


def snapshot(phase, rows, runs, active=None):
    results, reuse = collect(rows, runs)
    ordered = [results[r["case_id"]] for r in rows if r["case_id"] in results]
    pending = [r["case_id"] for r in rows if r["case_id"] not in results]
    data = dict(phase=phase, updated_at=time.time(), supervisor_pid=os.getpid(), total=len(rows),
                completed=len(ordered), passed=sum(r["passed"] for r in ordered), pending=pending,
                mean_exit_xy_m=statistics.mean(r["xy_m"] for r in ordered) if ordered else None, results=ordered)
    if active and (active/"status.json").exists():
        data.update(active_run=str(active.relative_to(ROOT)), active_status=read(active/"status.json"))
    save(OUT/"progress.json", data)
    return data, reuse


def main(key):
    rows = read(DATA)["cases"]
    if len(rows) != 22 or len({r["episode_id"] for r in rows}) != 22:
        raise ValueError("Expected 22 distinct episodes")
    runs = [FIRST, PREVIOUS]
    selected = [c["case_id"] for run in runs for c in read(run/"manifest.json")["cases"]]
    if selected + read(RECORD/"cases.json") != [r["case_id"] for r in rows]:
        raise ValueError("Existing and scheduled batches do not partition the frozen dataset")
    src = OUT / "source"
    src.mkdir(parents=True, exist_ok=False)
    for f in (Path(__file__), ROOT/"scripts/run_vlm_rollback.py", FIRST/"source/outbound_en.txt", FIRST/"source/return_en.txt"):
        shutil.copy2(f, src/f.name)
    save(OUT/"manifest.json", dict(cases=rows, seed=2, preceding_runs=[str(r.relative_to(ROOT)) for r in runs],
        new_cases=read(RECORD/"cases.json"), dataset_sha256=sha(DATA), git_head=subprocess.check_output(
            ["git","rev-parse","HEAD"],text=True).strip(), sources={p.name:sha(p) for p in src.iterdir()}))

    while True:
        previous_status = read(PREVIOUS/"status.json")
        if previous_status["phase"] in ("cancelled","canceled","paused"):
            raise RuntimeError("Preceding run was explicitly cancelled or paused")
        session = subprocess.run(["tmux","-L","peng_h1_ds10_20261123","has-session","-t","rollback10"],
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if session.returncode and previous_status["phase"] in ("complete","error"):
            break
        if session.returncode:
            pid = previous_status.get("pid")
            cmdline = Path(f"/proc/{pid}/cmdline")
            try:
                worker_alive = b"run_vlm_rollback.py" in cmdline.read_bytes()
            except FileNotFoundError:
                worker_alive = False
            if not worker_alive:
                break
        snapshot("waiting_for_previous",rows,runs,PREVIOUS)
        time.sleep(20)

    stalled = 0
    while True:
        progress, reuse = snapshot("selecting_remaining",rows,runs)
        missing = progress["pending"]
        if not missing:
            progress["phase"] = "complete"
            save(OUT/"summary.json",progress)
            save(OUT/"progress.json",progress)
            save(RECORD/"summary.json",progress)
            with (RECORD/"README.md").open("a") as f:
                f.write(f"\n全部 22 例已完成，位置达标 {progress['passed']}/22，"
                        f"平均退出水平误差 {progress['mean_exit_xy_m']:.3f} 米。[逐例结果](summary.json)\n")
            return
        number = len(runs) - 1
        name = f"attempt_{number:02d}"
        attempt = OUT / name
        case_file = OUT / f"{name}_cases.json"
        reuse_file = OUT / f"{name}_descriptions.json"
        save(case_file,missing)
        save(reuse_file,{cid:reuse[cid] for cid in missing if cid in reuse})
        env = dict(os.environ, VLN_ROLLBACK_RUN_ID=f"{NAME}/{name}", VLN_ROLLBACK_CASE_FILE=str(case_file),
                   VLN_ROLLBACK_REUSE=str(reuse_file), VLN_ROLLBACK_PROMPT_DIR=str(src))
        runs.append(attempt)
        with (OUT / f"{name}.log").open("x") as log:
            with subprocess.Popen([sys.executable,"-Bu",str(src/"run_vlm_rollback.py"),"start"],env=env,
                                  stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True) as job:
                job.stdin.write(key+"\n")
                job.stdin.close()
                while job.poll() is None:
                    snapshot("running",rows,runs,attempt)
                    try:
                        job.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        pass
        done, _ = collect(rows,runs)
        stalled = stalled+1 if len(done) == progress["completed"] else 0
        if stalled >= 3:
            raise RuntimeError(f"Three attempts made no progress; see {name}.log")
        if job.returncode:
            time.sleep(20)


if __name__ == "__main__":
    if OUT.exists():
        raise SystemExit("Queue already exists")
    credential = getpass.getpass("DeepSeek key (hidden): ")
    if not credential:
        raise SystemExit("Missing runtime credential")
    OUT.mkdir()
    try:
        main(credential)
    except Exception as exc:
        state = read(OUT/"progress.json") if (OUT/"progress.json").exists() else {}
        save(OUT/"progress.json",dict(state,phase="error",error=str(exc).replace(credential,"[redacted]"),updated_at=time.time()))
        raise
