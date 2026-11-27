"""Launch exactly two detached native simulation workers for the five cases."""
import hashlib
import json
import shutil
import socket
import subprocess
import time

from score import write
from state import ASSIGNMENTS, HERE, ROOT, OUT, update, utc

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    cases = json.loads((HERE / "cases.json").read_bytes())
    manifest = dict(started_utc=utc(), started_unix=time.time(), host=socket.gethostname(),
                    phase="running", cap=120, objective="navigation_goal", seed=2,
                    cases={c["case"]: dict(phase="queued", gpu=next(g for g, ids in ASSIGNMENTS.items()
                          if c["case"] in ids)) for c in cases})
    write(OUT / "status.json", manifest)
    sources = list(HERE.glob("*"))
    sources += [ROOT / name for name in (
        "experiments/inverse_rollback/codex_tools_v001/run_20261126_05_c11_region60/run.py",
        "experiments/inverse_rollback/codex_tools_v001/run_20261126_06_four_region60/simulator.py",
        "experiments/inverse_rollback/pose_hold/run_20261126_03_f57/switch_scene.py",
        "scripts/vlnverse_robot_bridge.py", "scripts/vlnverse_robot_mcp.py",
        "scripts/codex_vlnverse_robot.sh", "scripts/run_crossing_panorama_isaac.sh")]
    hashes = {}
    for source in sources:
        if source.is_file():
            relative = source.relative_to(ROOT)
            dest = OUT / "source" / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            hashes[str(relative)] = hashlib.sha256(source.read_bytes()).hexdigest()
    write(OUT / "launch.json", dict(host=socket.gethostname(), utc=utc(), assignments=ASSIGNMENTS,
          git_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
          source_sha256=hashes, tmux_socket="peng_vln_goal120_20261126"))
    (OUT / "git_diff.patch").write_bytes(subprocess.check_output(["git","diff"],cwd=ROOT))
    (OUT / "git_status.txt").write_bytes(subprocess.check_output(["git","status","--short"],cwd=ROOT))
    for gpu in ASSIGNMENTS:
        (OUT / f"gpu{gpu}").mkdir()
        subprocess.run(["tmux", "-L", "peng_vln_goal120_20261126", "-f", "/dev/null", "new-session",
                        "-d", "-s", f"gpu{gpu}", "bash", str(HERE / "start.sh"), str(gpu)],check=True,cwd=ROOT)
    update()
    print(str(OUT), flush=True)
