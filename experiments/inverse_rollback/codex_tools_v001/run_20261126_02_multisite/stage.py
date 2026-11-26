"""Position the existing H1 on its Isaac main thread. Codex only sees observe and step."""
from copy import deepcopy
import json
import os
from pathlib import Path
import traceback

import numpy as np

from core.step_multiview import state_snapshot
from omni.physx import get_physx_interface
from run_inverse_rollback import save
from vlnverse_robot_bridge import serve

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001/run_20261126_02_multisite"
EPISODE = "kujiale_0036_0_0"
STEPS = (ROOT / "outputs/multiview_capture/v001/run_20261117_03/capture/episodes"
         / EPISODE / "attempt_1794972488070620490/steps")


def stage(env, task, world, art):
    original = state_snapshot(task, world)
    if task.data["episode_id"] != EPISODE or original["physics_ticks"] != 1901:
        raise RuntimeError("Expected the retained F38 boundary")
    root_velocity = art.get_world_velocity().copy()
    drives = deepcopy(art.get_applied_action())
    discrete = task.robot.controllers["move_by_discrete"]
    gait = discrete.sub_controllers[0]
    stuck = task.done_checker.stuck_checker
    fields = [
        (task, ("step_count", "_done", "warm_up_step")),
        (task.robot, ("current_action",)),
        (discrete, ("current_steps", "current_action")),
        (gait, ("_old_joint_positions", "_old_policy_obs", "_apply_times_left",
                "applied_joint_positions", "update_height_samples_trigger", "dynamic_height_samples")),
        (stuck, ("last_iter", "agent_last_position", "agent_last_rotation", "position_diff", "rotation_diff")),
    ]
    snapshots = [(obj, names, {k: deepcopy(getattr(obj, k)) for k in names if hasattr(obj, k)})
                 for obj, names in fields]
    sensor = gait.point_cloud_sensor

    def place(state, velocity):
        for obj, names, values in snapshots:
            for key in names:
                if key in values:
                    setattr(obj, key, deepcopy(values[key]))
                elif hasattr(obj, key):
                    delattr(obj, key)
        gait.point_cloud_sensor = sensor
        tick = int(world.current_time_step_index)
        art.set_world_pose(position=np.asarray(state["position"]), orientation=np.asarray(state["rotation"]))
        art.set_world_velocity(velocity)
        art.set_joint_positions(np.asarray(state["joints"]))
        art.set_joint_velocities(np.asarray(state["joint_velocities"]))
        if drives is not None:
            art.apply_action(drives)
        task.step_count = state["physics_ticks"]
        if world.physics_sim_view is not None:
            world.physics_sim_view.update_articulations_kinematic()
        get_physx_interface().update_transformations(False, True, False, False)
        world.render()
        actual = state_snapshot(task, world)
        errors = {"root_velocity": float(np.max(np.abs(art.get_world_velocity() - velocity)))}
        for key in ("position", "rotation", "joints", "joint_velocities", "camera_position", "camera_rotation"):
            a, b = np.asarray(actual[key]), np.asarray(state[key])
            errors[key] = float(np.max(np.abs(a - b)))
            if key in ("rotation", "camera_rotation"):
                errors[key] = min(errors[key], float(np.max(np.abs(a + b))))
        if max(errors.values()) > 1e-4 or actual["world_step"] != tick or task.step_count != state["physics_ticks"]:
            raise RuntimeError(f"Placement readback failed: {errors}, {tick}, {actual}")
        return dict(pid=os.getpid(), state=actual, root_velocity=art.get_world_velocity().tolist(),
                    max_abs_errors=errors, verified=True)

    save(OUT / "start.json", dict(pid=os.getpid(), state=original, root_velocity=root_velocity.tolist()))
    try:
        for frame, limit in ((26, 5), (42, 5), (54, 4)):
            if (OUT / "end-tests").exists():
                break
            record = json.loads((STEPS / f"{frame:06d}" / "metadata.json").read_bytes())
            if ((record["episode_id"], record["seed"], record["step"]) != (EPISODE, 2, frame)
                    or not np.array_equal(record["environment_offset"], task.env_offset)):
                raise ValueError(f"Unexpected source frame {frame}")
            save(OUT / f"placement-{frame}.json", place(record["physical_state_before"], np.zeros(6)))
            serve(env, OUT / f"f{frame}", frame, move_limit=limit)
    except Exception:
        save(OUT / "stage-error.json", {"traceback": traceback.format_exc()})
    finally:
        save(OUT / "restored.json", place(original, root_velocity))
    serve(env, OUT / "live", 38)
