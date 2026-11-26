"""Place the retained H1 at the captured terminal observation, then accept local actions."""
import json
import os
from pathlib import Path

import numpy as np
from omni.physx import get_physx_interface

from core.step_multiview import pose_record, state_snapshot
from run_inverse_rollback import save, save_native_rgb
from vlnverse_robot_bridge import serve

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "outputs/inverse_rollback/pose_hold/run_20261126_02_f65"
EPISODE = "kujiale_0036_0_0"
SOURCE = (ROOT / "outputs/multiview_capture/v001/run_20261117_03/capture/episodes"
          / EPISODE / "attempt_1794972488070620490/steps/000065/metadata.json")


def place(env, task, world, art):
    record = json.loads(SOURCE.read_bytes())
    if (task.data["episode_id"] != EPISODE or (record["episode_id"], record["step"], record["seed"],
            record["phase"]) != (EPISODE, 65, 2, "terminal")
            or not np.array_equal(task.env_offset, record["environment_offset"])):
        raise ValueError("Unexpected episode, recorded frame, or world origin")

    target = record["physical_state_before"]
    world_step = int(world.current_time_step_index)
    art.set_world_pose(position=np.array(target["position"]), orientation=np.array(target["rotation"]))
    art.set_world_velocity(np.zeros(6))
    art.set_joint_positions(np.array(target["joints"]))
    art.set_joint_velocities(np.array(target["joint_velocities"]))
    task.step_count = target["physics_ticks"]
    if world.physics_sim_view is not None:
        world.physics_sim_view.update_articulations_kinematic()
    get_physx_interface().update_transformations(False, True, False, False)
    world.render()

    actual = state_snapshot(task, world)
    errors = {}
    for key in ("position", "rotation", "joints", "joint_velocities", "camera_position", "camera_rotation"):
        a, b = np.asarray(actual[key]), np.asarray(target[key])
        err = np.max(np.abs(a - b))
        if key in ("rotation", "camera_rotation"):
            err = min(err, np.max(np.abs(a + b)))
        errors[key] = float(err)
    advanced = actual["world_step"] - world_step
    verified = max(errors.values()) < 1e-4 and advanced == 0 and actual["physics_ticks"] == target["physics_ticks"]
    save(OUT / "placement.json", dict(pid=os.getpid(), episode_id=EPISODE, frame=65, phase=record["phase"],
         source=str(SOURCE.relative_to(ROOT)), state=actual, max_abs_errors=errors,
         robot_pose=pose_record(actual["position"], actual["rotation"]), verified=verified,
         physics_ticks_advanced=advanced, root_velocity=art.get_world_velocity().tolist()))
    if not verified:
        raise RuntimeError(f"F65 placement differs from capture: {errors}")
    save_native_rgb(OUT / "front.png", task, world, None)
    serve(env, OUT / "live", 65)
