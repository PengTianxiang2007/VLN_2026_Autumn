"""Send the approved return instruction to one fork of the completed deviation review."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
LIVE = ROOT / "outputs/inverse_rollback/pose_hold/run_20261126_03_f57/live"
PARENT = "01a21418-31a2-7261-aeff-69b81c8aa1f2"
LAST = "01a21428-71e2-7e02-ad6d-8efb607f16fb"
HOME = Path("/mnt/nas/gezuhao/PengTianxiang/.codex")
ROLLOUT = HOME / "sessions/2026/11/26" / ("rollout-2026-11-26T03-04-19-" + PARENT + ".jsonl")


def main():
    endpoint = json.loads((LIVE / "endpoint.json").read_bytes())
    if (endpoint["episode_id"], endpoint["start_frame"], endpoint["pid"], endpoint["status"]) != (
            "kujiale_0128_fix_20_0", 57, 3122551, "ready") or not Path(endpoint["socket"]).is_socket():
        raise RuntimeError("F57 endpoint is not attached")
    receipts = LIVE / "calls.jsonl"
    if receipts.exists() and receipts.stat().st_size:
        raise RuntimeError("F57 endpoint already used; check its current pose")
    events = [r["payload"] for r in map(json.loads, ROLLOUT.open()) if r.get("type") == "event_msg"]
    completed = [e.get("turn_id") for e in events if e.get("type") == "task_complete"]
    if len(completed) != 12 or completed[-1] != LAST:
        raise RuntimeError("Parent session no longer ends at the approved boundary")
    prompt = (HERE / "prompt.txt").read_text().strip()
    cmd = ["bash", "scripts/codex_vlnverse_robot.sh", "exec", "--sandbox", "read-only",
           "--disable", "shell_tool", "--disable", "unified_exec", "--enable", "code_mode_host",
           "-c", "project_doc_max_bytes=0", "-c", 'model_reasoning_effort="medium"',
           "fork", "--json", "-o", str(OUT / "codex-final.txt"), PARENT, prompt]
    files = [HERE / "run.py", HERE / "prompt.txt", ROOT / "scripts/codex_vlnverse_robot.sh",
             ROOT / "scripts/vlnverse_robot_bridge.py", ROOT / "scripts/vlnverse_robot_mcp.py",
             ROOT / "experiments/inverse_rollback/pose_hold/run_20261126_03_f57/switch_scene.py"]
    manifest = dict(started_utc=datetime.now(timezone.utc).isoformat(), parent=PARENT, last_turn=LAST,
                    copied_turns=12, episode=endpoint["episode_id"], seed=2, start_frame=57, target_frame=45,
                    simulator_pid=endpoint["pid"], endpoint=str(LIVE / "endpoint.json"), command=cmd,
                    git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,text=True).strip(),
                    sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    with (OUT / "launch.json").open("x") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
    with (OUT / "codex-events.jsonl").open("xb") as stdout, (OUT / "codex.log").open("xb") as stderr:
        subprocess.run(cmd, cwd=ROOT, env={**os.environ, "VLNVERSE_ROBOT_ENDPOINT":str(LIVE / "endpoint.json"),
                       "VLNVERSE_CODEX_MODEL":"gpt-6-astra"}, stdin=subprocess.DEVNULL,
                       stdout=stdout, stderr=stderr, check=True)


if __name__ == "__main__":
    main()
