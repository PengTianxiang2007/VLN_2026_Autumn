import json
import os
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUNS = ROOT / "outputs/inverse_rollback/codex_tools_v001"
OUT = RUNS / HERE.name
STABLE = RUNS / "run_20261126_01_f38/live/endpoint.json"
PID = 3122551


def ready(path):
    for _ in range(240):
        if path.exists():
            info = json.loads(path.read_bytes())
            if (info["pid"] == PID and info["episode_id"] == "kujiale_0036_0_0"
                    and info["status"] == "ready" and Path(info["socket"]).is_socket()):
                return info
        time.sleep(0.5)
    raise TimeoutError(path)


def main():
    previous = STABLE.resolve()
    current = ready(previous)
    if current["start_frame"] != 38 or "pose_hold/run_20261126_01/hold.py" not in Path(f"/proc/{PID}/cmdline").read_text():
        raise RuntimeError("Unexpected simulator")
    OUT.mkdir(exist_ok=False)
    source = OUT / "source"
    source.mkdir()
    for file in (HERE / "prompt.txt", HERE / "stage.py", HERE / "run.py", ROOT / "scripts/codex_vlnverse_robot.sh",
                 ROOT / "scripts/vlnverse_robot_bridge.py", ROOT / "scripts/vlnverse_robot_mcp.py",
                 ROOT / "scripts/run_inverse_rollback.py", ROOT / "core/step_multiview.py"):
        shutil.copyfile(file, source / file.name)
    (source / "git-status.txt").write_bytes(subprocess.check_output(["git", "status", "--short"], cwd=ROOT))
    shutil.copyfile(previous, OUT / "previous-endpoint-ready.json")
    command = f"import runpy; runpy.run_path('{(HERE / 'stage.py').relative_to(ROOT)}')['stage'](env, task, world, art)"
    Path(current["detach_marker"]).touch()
    subprocess.run(["tmux", "-L", "peng_vln_pose_20261126", "send-keys", "-t", "f38", command, "Enter"], check=True)
    endpoint = OUT / "agent/endpoint.json"
    info = ready(endpoint)
    args = ["bash", "scripts/codex_vlnverse_robot.sh", "exec", "--json", "--sandbox", "read-only",
            "--disable", "shell_tool", "--disable", "unified_exec", "--enable", "code_mode_host",
            "-c", "project_doc_max_bytes=0", "-c", 'model_reasoning_effort="medium"',
            "-o", str(OUT / "codex-final.txt"), "-"]
    try:
        print("Running autonomous Codex from F38", flush=True)
        with (OUT / "codex-events.jsonl").open("xb") as events, (OUT / "codex.log").open("xb") as log:
            subprocess.run(args, cwd=ROOT, input=(HERE / "prompt.txt").read_bytes(), stdout=events, stderr=log,
                           env={**os.environ, "VLNVERSE_ROBOT_ENDPOINT": str(endpoint)}, check=True)
    finally:
        Path(info["detach_marker"]).touch()
        live = OUT / "live/endpoint.json"
        ready(live)
        shutil.copyfile(previous, OUT / "previous-endpoint-detached.json")
        alias = previous.with_name("endpoint.tv-link")
        alias.symlink_to(os.path.relpath(live, previous.parent))
        alias.replace(previous)
        print("Restored F38 on the original simulator and launcher path", flush=True)


if __name__ == "__main__":
    main()
