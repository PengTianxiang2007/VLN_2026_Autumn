"""Run the four approved review forks serially on the retained H1."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import runpy
import subprocess
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
PRIOR = HERE.parent / "run_20261126_05_c11_region60"
shared = runpy.run_path(str(PRIOR / "run.py"))
discover = shared["DISCOVERY"]
utc = shared["utc"]
read = shared["read"]


def save(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def main(*, experiment=HERE, initial_episode="kujiale_0128_fix_20_0", move_limit=60,
         prompt_template=None, objective="checkpoint_return"):
    out = OUT.parent / experiment.name
    cases = read(experiment / "cases.json")
    prompt_text = (prompt_template or PRIOR / "prompt.txt").read_text()
    placeholder = "{checkpoint}" if prompt_template else "S05 (F45)"
    if prompt_text.count(placeholder) != 1:
        raise ValueError("Expected a single checkpoint placeholder in the prompt")
    old = read(discover)
    if old["status"] != "detached" or old["pid"] != 3122551 or old["episode_id"] != initial_episode:
        raise RuntimeError("Expected the retained simulator at the previous batch endpoint with its controller detached")
    if not Path("/proc/3122551/cwd").resolve().samefile(ROOT):
        raise RuntimeError("Unexpected simulator owner")
    previous = old["episode_id"]
    batch_start = time.monotonic()
    status = dict(started_utc=utc(), simulator_pid=old["pid"], queue_pid=os.getpid(),
                  phase="running", cap=move_limit, objective=objective, cases={c["case"]: {"phase":"queued"} for c in cases})
    status_path = out / "status.json"
    with status_path.open("x") as stream:
        json.dump(status,stream)
    for case in cases:
        case_id = case["case"]
        dest = out / case_id
        dest.mkdir()
        stats = status["cases"][case_id]
        case_clock = time.monotonic()
        stats.update(phase="placing", started_utc=utc())
        status["active_case"] = case_id
        save(status_path,status)
        endpoint = dest / "live/endpoint.json"
        error = dest / "simulator_error.json"
        prompt = dest / "prompt.txt"
        label = f'{case["target_node"]} (F{case["target_frame"]})'
        prompt.write_text(prompt_text.replace(placeholder, label))
        cmd = f"task, world, art = __import__('runpy').run_path({str(HERE/'simulator.py')!r})['attach'](env, {case_id!r}, {previous!r}, experiment={str(experiment)!r}, move_limit={move_limit!r})"
        try:
            tmux = ["tmux","-L","peng_vln_pose_20261126","send-keys","-t","f38:0.0"]
            subprocess.run([*tmux,"-l",cmd],check=True)
            subprocess.run([*tmux,"Enter"],check=True)
            while not endpoint.exists():
                if error.exists():
                    raise RuntimeError(read(error)["traceback"])
                if not Path("/proc/3122551").exists():
                    raise RuntimeError("Retained simulator exited")
                time.sleep(.4)
            previous = case["episode"]
            stats.update(phase="running",placement_elapsed_s=read(dest/"placement_time.json")["elapsed_s"])
            save(status_path,status)
            shared["run"](out=dest, prompt_file=prompt, episode=case["episode"], start_frame=case["start_frame"],
                          target_node=case["target_node"], target_frame=case["target_frame"], parent=case["parent"],
                          last_turn=case["last_turn"], rollout=Path(case["rollout"]), turns=case["turns"],
                          move_limit=move_limit, objective=objective,
                          extra_sources=(experiment/"cases.json", HERE/"queue.py", HERE/"simulator.py",
                                         *((experiment/"run.py", prompt_template) if prompt_template else ())))
            result=read(dest/"result.json")
            stats.update(phase=result["stop_reason"], movements=result["movements"], branch_thread=result["branch_thread"])
        except (Exception,SystemExit):
            stats.update(phase="technical_error",error=traceback.format_exc())
            if error.exists():
                current=read(error)["current_episodes"]
                if len(current)==1:
                    previous=current[0]
            if endpoint.is_file() and read(endpoint)["status"]=="ready":
                Path(read(endpoint)["detach_marker"]).touch(exist_ok=True)
        finally:
            if endpoint.is_file():
                while read(endpoint)["status"]!="detached" and Path("/proc/3122551").exists() and not error.exists():
                    time.sleep(.25)
            calls=dest/"live/calls.jsonl"
            rows=[json.loads(line) for line in calls.open()] if calls.is_file() else []
            stats["first_person_rgb_frames"]=sum("rgb" in r for r in rows)
            if (dest/"result.json").exists():
                stats["controller_elapsed_s"]=read(dest/"result.json")["controller_elapsed_s"]
            if rows:
                stats["first_to_last_tool_s"]=(datetime.fromisoformat(rows[-1]["finished_utc"])-datetime.fromisoformat(rows[0]["started_utc"])).total_seconds()
                stats["tool_execution_s"]=sum((datetime.fromisoformat(r["finished_utc"])-datetime.fromisoformat(r["started_utc"])).total_seconds() for r in rows)
            stats.update(finished_utc=utc(),case_elapsed_s=time.monotonic()-case_clock)
            save(dest/"timing.json",stats)
            status["elapsed_s"]=time.monotonic()-batch_start
            save(status_path,status)
        if not Path("/proc/3122551").exists():
            break
    status.update(phase="finished" if all(c["phase"]!="queued" for c in status["cases"].values()) else "interrupted",
                  active_case=None,finished_utc=utc(),elapsed_s=time.monotonic()-batch_start)
    save(status_path,status)


if __name__=="__main__":
    main()
