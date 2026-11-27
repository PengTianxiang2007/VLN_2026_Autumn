"""One native Isaac process per GPU, retaining its last scene after the queue."""
import code
from datetime import datetime
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import traceback

from score import after_case
from state import ASSIGNMENTS, HERE, OUT, ROOT, update, utc

GPU = int(os.environ["VLN_SIM_RENDER_GPU"])
CAPTURE = ROOT / "outputs/multiview_capture/v001/run_20261117_03"
sys.path[:0] = [str(CAPTURE / "code"), str(CAPTURE / "code/benchmarks/vlnverse/upstream"),
                str(ROOT / "scripts"), str(ROOT)]
sys.argv[1:] = [f"--/renderer/activeGpu={GPU}", "--/renderer/multiGpu/enabled=False"]


def run_cases(env, selected, *, experiment=HERE, move_limit=120):
    experiment = Path(experiment)
    out = OUT.parent / experiment.name
    update = runpy.run_path(str(HERE / "state.py"))["update"]
    attach = runpy.run_path(str(HERE.parent / "run_20261126_06_four_region60/simulator.py"))["attach"]
    for case in selected:
        dest = out / case["case"]
        dest.mkdir()
        prompt = (experiment / "prompt.txt").read_text().replace(
            "{checkpoint}", f'{case["target_node"]} (F{case["target_frame"]})')
        (dest / "prompt.txt").write_text(prompt)
        start = time.monotonic()
        stats = dict(phase="placing", gpu=GPU, simulator_pid=os.getpid(), started_utc=utc())
        update(case["case"], experiment=experiment, **stats)
        task, = env.env.runner.current_tasks.values()
        clean_env = dict(os.environ)
        # The CLI and MCP interpreter use their own libraries.
        for key in ("LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "VIRTUAL_ENV"):
            clean_env.pop(key, None)
        with (dest / "controller.log").open("x") as log:
            controller = subprocess.Popen(["/usr/bin/python3", "-Bu", str(HERE / "control.py"),
                                           case["case"], str(os.getpid()), str(experiment), str(move_limit)],
                                          cwd=ROOT, env=clean_env, stdout=log, stderr=subprocess.STDOUT)
            try:
                attach(env, case["case"], task.data["episode_id"], experiment=experiment,
                       move_limit=move_limit, scoring_path=str(HERE / "score.py"))
                controller.wait()
                result = json.loads((dest / "result.json").read_bytes())
                stats.update(phase=result["stop_reason"], movements=result["movements"],
                             branch_thread=result["branch_thread"], controller_elapsed_s=result["controller_elapsed_s"])
            except (Exception, SystemExit):
                stats.update(phase="technical_error", error=traceback.format_exc())
            finally:
                if controller.poll() is None:
                    controller.terminate()
                    try:
                        controller.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        controller.kill()
                        controller.wait()
        calls = dest / "live/calls.jsonl"
        rows = [json.loads(line) for line in calls.open()] if calls.exists() else []
        stats["first_person_rgb_frames"] = sum("rgb" in row for row in rows)
        stats.update(finished_utc=utc(), case_elapsed_s=time.monotonic() - start)
        if (dest / "placement_time.json").exists():
            stats["placement_elapsed_s"] = json.loads((dest / "placement_time.json").read_bytes())["elapsed_s"]
        if rows:
            stats["tool_execution_s"] = sum(
                (datetime.fromisoformat(r["finished_utc"]) - datetime.fromisoformat(r["started_utc"])).total_seconds()
                for r in rows)
        (dest / "timing.json").write_text(json.dumps(stats, indent=2) + "\n")
        after_case(out, case, stats, refresh=False)
        update(case["case"], experiment=experiment, **stats)


def main():
    from vlnverse.configs.evaluator.default_config import get_config
    from vlnverse.evaluator.utils.common import set_seed_model
    from vlnverse.evaluator.utils.eval import generate_episode
    from vlnverse.projects.dataloader.base import BasePathKeyDataloader
    from vlnverse.env import Env

    cases = json.loads((HERE / "cases.json").read_bytes())
    selected = [next(c for c in cases if c["case"] == name) for name in ASSIGNMENTS[GPU]]
    first = selected[0]
    for case in selected:
        update(case["case"], simulator_pid=os.getpid())
    set_seed_model(2)
    cfg = get_config(runpy.run_path(str(ROOT / first["config"]))["eval_cfg"])
    settings = cfg.dataset.dataset_settings
    loader = BasePathKeyDataloader(dataset_type=cfg.dataset.dataset_type, **{
        k: settings[k] for k in ("base_data_dir", "split_data_types", "robot_offset",
                                 "filter_same_trajectory", "filter_stairs")})
    loader.task_name = f"goal120_gpu{GPU}"
    key, = [k for k, row in loader.path_key_data.items() if row["episode_id"] == first["episode"]]
    loader.resumed_path_key_list = [key]
    cfg.task.task_settings["episodes"] = generate_episode(loader, cfg)
    env = Env.init(cfg.env, cfg.task)
    try:
        env.reset()
        run_cases(env, selected)
        task, = env.env.runner.current_tasks.values()
        world = env.env.runner._world
        print(f"GPU {GPU} finished; retained episode {task.data['episode_id']}.", flush=True)
        code.interact(banner="", local=dict(env=env, task=task, world=world))
    finally:
        env.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        error = traceback.format_exc()
        (OUT / f"gpu{GPU}_error.txt").write_text(error)
        for name in ASSIGNMENTS[GPU]:
            status = json.loads((OUT / "status.json").read_bytes())
            if status["cases"][name]["phase"] in ("queued", "placing", "awaiting_placement", "running"):
                update(name, phase="technical_error", error=error)
        raise
