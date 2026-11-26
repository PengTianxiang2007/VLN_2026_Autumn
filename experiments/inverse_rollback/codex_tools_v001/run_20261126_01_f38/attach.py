"""Run inside the retained F38 Isaac console, on its main thread."""
from copy import deepcopy
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38"
sys.path.insert(0, str(ROOT / "scripts"))
from run_inverse_rollback import save
from vlnverse_robot_bridge import serve
from core.step_multiview import state_snapshot


def attach(env, task, world, art):
    if task.data["episode_id"] != "kujiale_0036_0_0" or task.step_count != 1901:
        raise RuntimeError("This smoke run requires the retained F38 action boundary.")
    before = state_snapshot(task, world)
    velocity = art.get_world_velocity().copy()
    drives = deepcopy(art.get_applied_action())
    discrete = task.robot.controllers["move_by_discrete"]
    gait = discrete.sub_controllers[0]
    # Stand-still and gait controllers can be distinct. Save initially absent
    # lazy fields as well as the arrays the first physical move will mutate.
    fields = [
        (task, ("step_count", "_done", "warm_up_step")),
        (task.robot, ("current_action",)),
        (discrete, ("current_steps", "current_action")),
        (gait, ("_old_joint_positions", "_old_policy_obs", "_apply_times_left",
                "applied_joint_positions", "update_height_samples_trigger", "dynamic_height_samples")),
        (task.done_checker.stuck_checker, ("last_iter", "agent_last_position", "agent_last_rotation")),
    ]
    snapshots = [(obj, names, {k: deepcopy(getattr(obj, k)) for k in names if hasattr(obj, k)})
                 for obj, names in fields]
    sensor = gait.point_cloud_sensor
    save(OUT / "start.json", dict(pid=os.getpid(), state=before, root_velocity=velocity.tolist()))
    try:
        serve(env, OUT / "smoke", 38, move_limit=1)
    finally:
        # Operator restoration for this smoke test only. This operation is not
        # registered in the agent tool catalog.
        for obj, names, state in snapshots:
            for k in names:
                if k in state:
                    setattr(obj, k, state[k])
                elif hasattr(obj, k):
                    delattr(obj, k)
        gait.point_cloud_sensor = sensor
        art.set_world_pose(position=np.asarray(before["position"]), orientation=np.asarray(before["rotation"]))
        art.set_world_velocity(velocity)
        art.set_joint_positions(np.asarray(before["joints"]))
        art.set_joint_velocities(np.asarray(before["joint_velocities"]))
        if drives is not None:
            art.apply_action(drives)
        from omni.physx import get_physx_interface
        ticks = int(world.current_time_step_index)
        if world.physics_sim_view is not None:
            world.physics_sim_view.update_articulations_kinematic()
        get_physx_interface().update_transformations(False, True, False, False)
        world.render()
        after = state_snapshot(task, world)
        diff = {}
        for k in ("position", "rotation", "joints", "joint_velocities", "camera_position", "camera_rotation"):
            a, b = np.array(after[k]), np.array(before[k])
            diff[k] = float(np.max(np.abs(a-b)))
            if k in ("rotation", "camera_rotation"):
                diff[k] = min(diff[k], float(np.max(np.abs(a+b))))
        read_velocity = art.get_world_velocity()
        diff["root_velocity"] = float(np.max(np.abs(read_velocity - velocity)))
        restored = max(diff.values()) <= 1e-4 and task.step_count == 1901 and after["world_step"] == ticks
        save(OUT / "restored.json", dict(verified=restored, pid=os.getpid(), state=after,
                                         max_abs_errors=diff, root_velocity=read_velocity.tolist()))
        if not restored:
            raise RuntimeError(f"F38 restoration readback failed: {diff}")
    serve(env, OUT / "live", 38)
