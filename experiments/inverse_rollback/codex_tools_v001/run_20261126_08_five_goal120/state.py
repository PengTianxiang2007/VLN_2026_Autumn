"""Serialize progress updates from the two independent simulation workers."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import time

from score import report, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
ASSIGNMENTS = {0: ["C11", "C43", "C23"], 1: ["C17", "C20"]}


def utc():
    return datetime.now(timezone.utc).isoformat()


def update(case_id=None, *, experiment=HERE, **fields):
    out = OUT.parent / experiment.name
    with (out / "status.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        status = json.loads((out / "status.json").read_bytes())
        if case_id is not None:
            status["cases"][case_id].update(fields)
        else:
            status.update(fields)
        terminal = {"finish_return", "movement_limit", "physical_terminal", "model_ended", "technical_error"}
        if all(row["phase"] in terminal for row in status["cases"].values()):
            status["phase"] = "finished"
        else:
            status["phase"] = "running"
        status["elapsed_s"] = time.time() - status["started_unix"]
        status["updated_utc"] = utc()
        write(out / "status.json", status)
        report(out, json.loads((experiment / "cases.json").read_bytes()), status)
