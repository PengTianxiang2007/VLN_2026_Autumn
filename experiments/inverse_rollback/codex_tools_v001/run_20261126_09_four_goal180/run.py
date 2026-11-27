"""Append four review forks to the two retained simulation consoles."""
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / "run_20261126_08_five_goal120"
sys.path.insert(0, str(PRIOR))
from state import utc, update
from score import write

OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
ASSIGNMENTS = {0: ["C19", "C22"], 1: ["C21", "C30"]}


if __name__ == "__main__":
    previous = json.loads((OUT.parent / PRIOR.name / "status.json").read_bytes())
    pids = {gpu: next(row["simulator_pid"] for row in previous["cases"].values() if row["gpu"] == gpu)
            for gpu in ASSIGNMENTS}
    for gpu, pid in pids.items():
        proc = Path("/proc") / str(pid)
        if not (proc / "cwd").resolve().samefile(ROOT) or str(PRIOR / "simulate.py") not in (
            proc / "cmdline").read_bytes().replace(b"\0", b" ").decode():
            raise RuntimeError(f"Unexpected simulator on GPU {gpu}")
        pane_pid = subprocess.check_output(["tmux", "-L", "peng_vln_goal120_20261126", "display-message",
                    "-p", "-t", f"gpu{gpu}:0.0", "#{pane_pid}"], text=True).strip()
        if int(pane_pid) != pid:
            raise RuntimeError("Simulator console ownership changed")
    OUT.mkdir(parents=True, exist_ok=False)
    cases = json.loads((HERE / "cases.json").read_bytes())
    status = dict(phase="running", started_utc=utc(), started_unix=time.time(),
                  host=socket.gethostname(), cap=180, seed=2, objective="navigation_goal",
                  cases={c["case"]:dict(phase="queued",gpu=next(g for g,ids in ASSIGNMENTS.items()
                         if c["case"] in ids),simulator_pid=pids[next(g for g,ids in ASSIGNMENTS.items()
                         if c["case"] in ids)]) for c in cases})
    write(OUT / "status.json", status)
    sources = [*HERE.glob("*"), *PRIOR.glob("*.py"),
        HERE.parent / "run_20261126_05_c11_region60/run.py",
        HERE.parent / "run_20261126_06_four_region60/simulator.py",
        ROOT / "experiments/inverse_rollback/pose_hold/run_20261126_03_f57/switch_scene.py",
        ROOT / "scripts/vlnverse_robot_bridge.py", ROOT / "scripts/vlnverse_robot_mcp.py",
        ROOT / "scripts/codex_vlnverse_robot.sh"]
    hashes = {}
    for path in sources:
        if path.is_file():
            dest = OUT / "source" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    commands = {}
    for gpu, ids in ASSIGNMENTS.items():
        command = (f"__import__('runpy').run_path({str(PRIOR / 'simulate.py')!r})['run_cases']"
                   f"(env, [c for c in __import__('json').loads(__import__('pathlib').Path("
                   f"{str(HERE / 'cases.json')!r}).read_text()) if c['case'] in {ids!r}],"
                   f" experiment={str(HERE)!r}, move_limit=180)")
        commands[str(gpu)] = command
    write(OUT / "launch.json", dict(host=socket.gethostname(), utc=utc(), assignments=ASSIGNMENTS,
          simulator_pids=pids, source_sha256=hashes, commands=commands,
          git_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()))
    (OUT / "git_diff.patch").write_bytes(subprocess.check_output(["git","diff"],cwd=ROOT))
    for gpu, command in commands.items():
        base = ["tmux","-L","peng_vln_goal120_20261126","send-keys","-t",f"gpu{gpu}:0.0"]
        subprocess.run([*base,"-l",command],check=True)
        subprocess.run([*base,"Enter"],check=True)
    update(experiment=HERE)
    print("Queued", ASSIGNMENTS, "with 180 movements per case", flush=True)
