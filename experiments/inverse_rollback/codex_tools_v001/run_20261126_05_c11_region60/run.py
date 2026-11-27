"""Run one clean fork on the capped H1 endpoint and capture its actual stopping reason."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
LIVE = OUT / "live"
DISCOVERY = ROOT / "outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/live/endpoint.json"
PARENT = "01a21418-31a2-7261-aeff-69b81c8aa1f2"
LAST = "01a21428-71e2-7e02-ad6d-8efb607f16fb"
EPISODE = "kujiale_0128_fix_20_0"
ROLLOUT = Path("/mnt/nas/gezuhao/PengTianxiang/.codex/sessions/2026/11/26") / (
    "rollout-2026-11-26T03-04-19-" + PARENT + ".jsonl")


def read(path):
    return json.loads(path.read_bytes())


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def utc():
    return datetime.now(timezone.utc).isoformat()


def run(*, out=OUT, prompt_file=HERE / "prompt.txt", episode=EPISODE, start_frame=57,
        target_frame=45, target_node="S05", parent=PARENT, last_turn=LAST,
        rollout=ROLLOUT, turns=12, extra_sources=(), move_limit=60, objective="checkpoint_return",
        simulator_pid=3122551, discovery=DISCOVERY):
    live = out / "live"
    endpoint_file = live / "endpoint.json"
    while not endpoint_file.exists():
        if not Path(f"/proc/{simulator_pid}").is_dir():
            raise RuntimeError("Target simulator exited during setup")
        time.sleep(1)
    endpoint = read(endpoint_file)
    placement = read(out / "placement.json")
    if (endpoint["status"], endpoint["episode_id"], endpoint["start_frame"], endpoint["move_limit"], endpoint["pid"]) != (
            "ready", episode, start_frame, move_limit, simulator_pid) or not placement["verified"] or not Path(endpoint["socket"]).is_socket():
        raise ValueError(f"Expected a verified recorded placement with a {move_limit}-movement endpoint")
    if (live / "calls.jsonl").exists():
        raise RuntimeError("Endpoint already used")
    with rollout.open() as stream:
        completed = [e["payload"]["turn_id"] for e in map(json.loads, stream) if
                     e.get("type") == "event_msg" and e["payload"].get("type") == "task_complete"]
    if len(completed) != turns or completed[-1] != last_turn:
        raise RuntimeError("Parent no longer ends on the selected deviation decision")
    if not Path(f"/proc/{simulator_pid}/cwd").resolve().samefile(ROOT):
        raise RuntimeError("Simulator belongs to another workspace")
    if discovery is not None:
        if read(discovery)["status"] != "detached":
            raise RuntimeError("Previous controller is still active")
        link = discovery.with_name(f"endpoint.to-{os.getpid()}")
        link.symlink_to(os.path.relpath(endpoint_file, discovery.parent))
        os.replace(link, discovery)
    prompt = prompt_file.read_text().strip()
    cmd = ["bash", "scripts/codex_vlnverse_robot.sh", "exec", "--sandbox", "read-only", "--disable", "shell_tool",
           "--disable", "unified_exec", "--enable", "code_mode_host", "-c", "project_doc_max_bytes=0",
           "-c", 'model_reasoning_effort="medium"', "fork", "--json", "-o", str(out / "codex-final.txt"), parent, prompt]
    paths = [HERE / "run.py", prompt_file, ROOT / "scripts/vlnverse_robot_bridge.py",
             ROOT / "scripts/vlnverse_robot_mcp.py", ROOT / "scripts/codex_vlnverse_robot.sh",
             ROOT / "experiments/inverse_rollback/pose_hold/run_20261126_03_f57/switch_scene.py", *extra_sources]
    with (out / "launch.json").open("x") as fp:
        json.dump(dict(utc=utc(), parent=parent, last_parent_turn=last_turn, episode_id=episode, seed=2, cap=move_limit,objective=objective,
                       endpoint=endpoint, command=cmd, git_head=subprocess.check_output(["git","rev-parse","HEAD"],
                       cwd=ROOT,text=True).strip(), source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                                 for p in paths}),fp,indent=2)
    events_file = out / "codex-events.jsonl"
    controller_start = time.monotonic()
    controller_utc = utc()
    with events_file.open("xb") as events, (out / "codex.log").open("xb") as log:
        proc = subprocess.Popen(cmd, cwd=ROOT, env={**os.environ, "VLNVERSE_CODEX_MODEL":"gpt-6-astra",
                                "VLNVERSE_ROBOT_ENDPOINT":str(endpoint_file)},stdin=subprocess.DEVNULL,stdout=events,stderr=log)
        print(episode,"capped fork launched",proc.pid,flush=True)
        try:
            while proc.poll() is None and not (live / "movement_limit.json").exists():
                time.sleep(.15)
            if proc.poll() is None:
                proc.terminate()
            try:
                code = proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                code = proc.wait()
        finally:
            if proc.poll() is None:
                proc.terminate()
            Path(endpoint["detach_marker"]).touch(exist_ok=True)
    controller_seconds = time.monotonic() - controller_start
    for _ in range(50):
        if read(endpoint_file)["status"] == "detached":
            break
        time.sleep(.1)
    receipts = live / "calls.jsonl"
    rows = [json.loads(l) for l in receipts.read_text().splitlines()] if receipts.exists() else []
    moves = [r for r in rows if r["action"] in ("turn_left","turn_right","forward") and r["after"]["task_ticks"]>r["before"]["task_ticks"]]
    if len(moves)>move_limit:
        raise RuntimeError("Movement budget exceeded")
    branch_id = None
    with events_file.open() as stream:
        for line in stream:
            if line.startswith('{"type":"thread.started"'):
                branch_id=json.loads(line)["thread_id"]
                break
    declared = any(r.get("result",{}).get("status")=="return_declared" for r in rows)
    native_terminal = next((r["result"]["terminal_reason"] for r in rows if r.get("result",{}).get("status")=="physical_terminal"),None)
    cutoff = live / "movement_limit.json"
    reason = ("finish_return" if declared else "movement_limit" if cutoff.exists() or len(moves)==move_limit else
              "physical_terminal" if native_terminal else "technical_error" if code or (not moves and not rows) else "model_ended")
    first=rows[0]["before"] if rows else None
    last=rows[-1]["after"] if rows else None
    target=read((ROOT / placement["source"]).parents[1] / f"{target_frame:06d}/metadata.json")["robot_pose"]["position_world_m"]
    distance=lambda s: math.dist(s["position"][:2],target[:2])
    states = [first]+[r["after"] for r in moves] if first else []
    nearest = min(enumerate(states), key=lambda i:distance(i[1])) if states else None
    save(out / "result.json",dict(episode_id=episode,seed=2,parent_thread=parent,branch_thread=branch_id,
         start_frame=start_frame,target_frame=target_frame,target_node=target_node,cap=move_limit,objective=objective,movements=len(moves),actions=dict(Counter(r["action"] for r in moves)),
         independent_observations=sum(r["method"]=="observe" for r in rows),endpoint_declared=declared,stop_reason=reason,
         limit_request=read(cutoff) if cutoff.exists() else None,native_terminal=native_terminal,
         start=first,end=last,start_m=distance(first) if first else None,final_m=distance(last) if last else None,
         nearest_m=distance(nearest[1]) if nearest else None,nearest_move=nearest[0] if nearest else None,
         final_image=(str((live/"frames"/f"{rows[-1]['sequence']:05d}.png").relative_to(ROOT)) if rows else None),
         client_returncode=code,controller_started_utc=controller_utc,controller_elapsed_s=controller_seconds,completed_utc=utc()))
    print(reason,len(moves),branch_id,flush=True)
    if code and not cutoff.exists():
        raise SystemExit(code)

if __name__=="__main__":
    run()
