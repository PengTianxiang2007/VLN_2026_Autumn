"""Run one original-review fork using its own simulator endpoint."""
import json
from pathlib import Path
import runpy
import sys
import time
import traceback

from state import HERE, OUT, update

case_id, simulator_pid = sys.argv[1:3]
experiment = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE
move_limit = int(sys.argv[4]) if len(sys.argv) > 4 else 120
out = OUT.parent / experiment.name
case, = [row for row in json.loads((experiment / "cases.json").read_bytes()) if row["case"] == case_id]
dest = out / case_id
endpoint = dest / "live/endpoint.json"
runner = runpy.run_path(str(HERE.parent / "run_20261126_05_c11_region60/run.py"))
try:
    update(case_id, experiment=experiment, phase="awaiting_placement", controller_pid=__import__("os").getpid())
    while not endpoint.exists():
        if (dest / "simulator_error.json").exists() or not Path(f"/proc/{simulator_pid}").exists():
            raise RuntimeError("Simulator did not create its endpoint")
        time.sleep(.25)
    while (out / "controller.pause").exists():
        time.sleep(.5)
    update(case_id, experiment=experiment, phase="running")
    runner["run"](out=dest, prompt_file=dest / "prompt.txt", episode=case["episode"],
                  start_frame=case["start_frame"], target_frame=case["target_frame"],
                  target_node=case["target_node"], parent=case["parent"], last_turn=case["last_turn"],
                  rollout=Path(case["rollout"]), turns=case["turns"], move_limit=move_limit,
                  objective="navigation_goal", simulator_pid=int(simulator_pid), discovery=None,
                  extra_sources=tuple(HERE.glob("*.py")) + tuple(experiment.glob("*.py")) + (experiment / "cases.json", experiment / "prompt.txt",
                  HERE.parent / "run_20261126_06_four_region60/simulator.py"))
except BaseException:
    (dest / "controller_error.txt").write_text(traceback.format_exc())
    raise
finally:
    if endpoint.exists():
        data = json.loads(endpoint.read_bytes())
        if data["status"] == "ready":
            Path(data["detach_marker"]).touch(exist_ok=True)
