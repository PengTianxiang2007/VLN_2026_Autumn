"""Called on the retained Isaac console's main thread, once per case."""
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
PLACE = ROOT / "experiments/inverse_rollback/pose_hold/run_20261126_03_f57/switch_scene.py"


def attach(env, case_id, previous_episode, *, experiment=HERE, move_limit=60):
    from run_inverse_rollback import save
    from vlnverse_robot_bridge import serve
    experiment = Path(experiment)
    case, = [c for c in json.loads((experiment / "cases.json").read_bytes()) if c["case"] == case_id]
    directory = OUT.parent / experiment.name / case_id
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    try:
        place = runpy.run_path(str(PLACE))["switch_and_place"]
        place(env, previous_episode=previous_episode, destination=directory,
              source=ROOT/case["source"], episode=case["episode"], scene=case["scene"],
              frame=case["start_frame"], phase=case["phase"], config=ROOT/case["config"])
        save(directory / "placement_time.json", dict(started_utc=started,
             finished_utc=datetime.now(timezone.utc).isoformat(), elapsed_s=time.monotonic()-clock))
        serve(env, directory / "live", case["start_frame"], move_limit=move_limit)
    except Exception:
        current = [t.data.get("episode_id") for t in env.env.runner.current_tasks.values()]
        save(directory / "simulator_error.json", dict(traceback=traceback.format_exc(),
             current_episodes=current, utc=datetime.now(timezone.utc).isoformat()))
        raise
    task, = env.env.runner.current_tasks.values()
    return task, env.env.runner._world, task.robot.articulation._articulation
