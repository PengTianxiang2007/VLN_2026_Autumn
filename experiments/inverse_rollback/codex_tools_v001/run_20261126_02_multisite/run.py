"""Run three Codex clients in order against the owned, already-running F38 scene."""
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
PREVIOUS = RUNS / "run_20261126_01_f38/live/endpoint.json"
PID = 3122551
STAGING_COMMAND = f"import runpy; runpy.run_path('{(HERE / 'stage.py').relative_to(ROOT)}')['stage'](env, task, world, art)"


def ready(path, timeout=90):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if path.exists():
            info = json.loads(path.read_bytes())
            if info["pid"] == PID and info["status"] == "ready" and Path(info["socket"]).is_socket():
                return info
        if path.parent.name != "live" and (OUT / "stage-error.json").exists():
            raise RuntimeError((OUT / "stage-error.json").read_text())
        time.sleep(0.5)
    raise TimeoutError(path)


def run_client(frame, turn):
    trial = OUT / f"f{frame}"
    endpoint = trial / "endpoint.json"
    info = ready(endpoint)
    extra = f'随后执行一次 step(action="{turn}")。' if turn else ""
    prompt = ('对当前 VLNVerse H1 做一次动作与相机测试。仅调用 vlnverse 工具，按顺序执行。'
              '先 observe()，再连续四次 step(action="forward")，每次等待上一动作返回。'
              + extra + '最后再 observe()。无需调用 finish_return。每次读取 text 并把返回的 image 内容块'
              '用 image(...) 显示给自己。若返回 physical_terminal 或报错就结束。'
              '回答起止帧和前后图中实际可见的一个变化。')
    (trial / "prompt.txt").write_text(prompt + "\n")
    command = ["bash", "scripts/codex_vlnverse_robot.sh", "exec", "--json", "--ephemeral",
               "--sandbox", "read-only", "--disable", "shell_tool", "--disable", "unified_exec",
               "--enable", "code_mode_host", "-c", "project_doc_max_bytes=0", "-c",
               'model_reasoning_effort="medium"', "-o", str(trial / "codex-final.txt"), "-"]
    print(f"F{frame}: client started", flush=True)
    try:
        with (trial / "codex-events.jsonl").open("x") as events, (trial / "codex.log").open("x") as log:
            subprocess.run(command, input=prompt, text=True, cwd=ROOT, stdout=events, stderr=log,
                           env={**os.environ, "VLNVERSE_ROBOT_ENDPOINT": str(endpoint)}, check=True, timeout=420)
    finally:
        Path(info["detach_marker"]).touch()
    print(f"F{frame}: client finished", flush=True)


def main():
    current = ready(PREVIOUS)
    if current["start_frame"] != 38 or "pose_hold/run_20261126_01/hold.py" not in Path(f"/proc/{PID}/cmdline").read_text():
        raise RuntimeError("Unexpected simulator owner or frame")
    OUT.mkdir(exist_ok=True)
    source = OUT / "source"
    source.mkdir(exist_ok=False)
    for path in (HERE / "stage.py", HERE / "run.py", ROOT / "scripts/codex_vlnverse_robot.sh",
                 ROOT / "scripts/vlnverse_robot_bridge.py", ROOT / "scripts/vlnverse_robot_mcp.py",
                 ROOT / "scripts/run_inverse_rollback.py", ROOT / "core/step_multiview.py"):
        shutil.copyfile(path, source / path.name)
    (source / "git-status.txt").write_bytes(subprocess.check_output(["git", "status", "--short"], cwd=ROOT))
    shutil.copyfile(PREVIOUS, OUT / "previous-endpoint-ready.json")
    Path(current["detach_marker"]).touch()
    subprocess.run(["tmux", "-L", "peng_vln_pose_20261126", "send-keys", "-t", "f38", STAGING_COMMAND, "Enter"], check=True)
    try:
        for frame, turn in ((26, "turn_left"), (42, "turn_right"), (54, None)):
            run_client(frame, turn)
    finally:
        # Let the simulator restore even if a client exits early.
        (OUT / "end-tests").touch()
        for name in ("f26", "f42", "f54"):
            path = OUT / name / "endpoint.json"
            if path.exists():
                info = json.loads(path.read_bytes())
                if info["status"] == "ready" and Path(info["detach_marker"]).parent.exists():
                    Path(info["detach_marker"]).touch(exist_ok=True)
        live = OUT / "live/endpoint.json"
        ready(live)
        shutil.copyfile(PREVIOUS, OUT / "previous-endpoint-detached.json")
        # The normal launcher resolves this discovery path before starting MCP.
        # Save previous receipts and frames in place; future calls use the new trace.
        link = PREVIOUS.with_name("endpoint.multisite-link")
        link.symlink_to(os.path.relpath(live, PREVIOUS.parent))
        link.replace(PREVIOUS)
        print(f"F38 restored; original launcher endpoint resolves to {PREVIOUS.resolve()}", flush=True)


if __name__ == "__main__":
    main()
