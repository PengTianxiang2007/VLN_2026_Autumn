"""Keep this already-running Isaac worker resident at its final result commit."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


record = Path(__file__).resolve().parent
root = record.parents[3]
run = root / "outputs/inverse_rollback/vlm_action_v001" / record.name
cases = json.loads((record / "cases.json").read_text())
final = run / "cases" / cases[-1]
marker = run / "simulator_retained.json"


def save(path, data):
    temp = path.with_suffix(".hold.tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n")
    temp.replace(path)


def retain():
    save(marker, dict(phase="waiting_for_final_case", case=final.name, guard_pid=os.getpid()))
    while not (final / "start_B.json").exists():
        status = json.loads((run / "status.json").read_text())
        if status["phase"] in ("error", "complete"):
            raise RuntimeError(f"Run ended before hold: {status}")
        time.sleep(0.5)

    # start_B.json is the last rename in this directory before result.json.
    # Requests and images use subdirectories. The action trace is append-only.
    while True:
        status = json.loads((run / "status.json").read_text())
        if status.get("case") == final.name and status["phase"] in ("turnaround", "return_request"):
            break
        if status["phase"] in ("error", "complete") or (final / "result.json").exists():
            raise RuntimeError("Missed the final worker")
        time.sleep(0.05)
    pid = status["pid"]
    proc = Path(f"/proc/{pid}")
    argv = (proc / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    if (proc / "cwd").resolve() != root or argv[-3:-1] != [os.fsencode(run / "source/run_vlm_rollback.py"), b"worker"]:
        raise RuntimeError("Final worker identity mismatch")
    start = (proc / "stat").read_text().split()[21]
    identity = dict(case=final.name, pid=pid, gpu=argv[-1].decode(), start_ticks=start, guard_pid=os.getpid())
    handle = os.open(final, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.fcntl(handle, fcntl.F_SETOWN, pid)
        fcntl.fcntl(handle, fcntl.F_SETSIG, signal.SIGSTOP)
        fcntl.fcntl(handle, fcntl.F_NOTIFY, fcntl.DN_RENAME)
        save(marker, dict(phase="armed", **identity))
        while True:
            stat = (proc / "stat").read_text().split()
            if stat[21] != start:
                raise RuntimeError("Worker PID changed")
            if stat[2] == "T" and (final / "result.json").exists():
                break
            time.sleep(0.25)
    finally:
        os.close(handle)
    held = dict(phase="held", **identity, time=time.time())
    save(marker, held)
    results = [json.loads((run / "cases" / cid / "result.json").read_text()) for cid in cases]
    passed = sum(r["passed"] for r in results)
    save(run / "summary.json", dict(results=results, passed=passed))
    subprocess.run([sys.executable, "-B", str(record / "compare.py")], cwd=root, check=True)
    save(run / "status.json", dict(phase="complete_simulator_retained", cases=len(results), passed=passed, **identity, time=time.time()))


if __name__ == "__main__":
    try:
        retain()
    except Exception as exc:
        save(run / "retention_error.json", dict(error=repr(exc), time=time.time()))
        raise
