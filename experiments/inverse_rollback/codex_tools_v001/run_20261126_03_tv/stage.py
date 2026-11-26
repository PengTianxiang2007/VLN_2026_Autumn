"""Run a single autonomous test on the retained Isaac main thread, then restore F38."""
from copy import deepcopy
import importlib
import os
from pathlib import Path
import traceback

import numpy as np
from omni.physx import get_physx_interface

import vlnverse_robot_bridge
from core.step_multiview import state_snapshot
from run_inverse_rollback import save, save_native_rgb

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv"


def scene_objects():
    import omni.usd
    from pxr import Usd, UsdGeom

    scene = omni.usd.get_context().get_stage()
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    objects = []
    for prim in scene.Traverse():
        path = str(prim.GetPath())
        _, marker, suffix = path.partition("/scene/Meshes/")
        if not marker or len(suffix.split("/")) != 2:
            continue
        box = cache.ComputeWorldBound(prim)
        aligned = box.ComputeAlignedRange()
        if aligned.IsEmpty():
            continue
        objects.append(dict(path=path, minimum=list(aligned.GetMin()), maximum=list(aligned.GetMax()),
                            corners=[list(box.GetMatrix().Transform(box.GetRange().GetCorner(i))) for i in range(8)]))
    return dict(meters_per_unit=UsdGeom.GetStageMetersPerUnit(scene), objects=objects)


def stage(env, task, world, art):
    if task.data["episode_id"] != "kujiale_0036_0_0" or task.step_count != 1901:
        raise RuntimeError("The H1 must already be at the retained F38 boundary")
    bridge = importlib.reload(vlnverse_robot_bridge)
    before = state_snapshot(task, world)
    vel = art.get_world_velocity().copy()
    drives = deepcopy(art.get_applied_action())
    discrete = task.robot.controllers["move_by_discrete"]
    gait = discrete.sub_controllers[0]
    sensor = gait.point_cloud_sensor
    fields = [(task, ("step_count", "_done", "warm_up_step")), (task.robot, ("current_action",)),
              (discrete, ("current_steps", "current_action")),
              (gait, ("_old_joint_positions", "_old_policy_obs", "_apply_times_left", "applied_joint_positions",
                      "update_height_samples_trigger", "dynamic_height_samples")),
              (task.done_checker.stuck_checker, ("last_iter", "agent_last_position", "agent_last_rotation",
                                                 "position_diff", "rotation_diff"))]
    snapshots = [(obj, names, {k: deepcopy(getattr(obj, k)) for k in names if hasattr(obj, k)})
                 for obj, names in fields]
    evidence = OUT / "operator"
    evidence.mkdir()
    try:
        save(OUT / "start.json", dict(pid=os.getpid(), state=before, root_velocity=vel.tolist(),
                                      rgb=save_native_rgb(evidence / "start.png", task, world, None)))
        bridge.serve(env, OUT / "agent", 38)
        end = state_snapshot(task, world)
        save(OUT / "end.json", dict(state=end, root_velocity=art.get_world_velocity().tolist(),
                                    rgb=save_native_rgb(evidence / "end.png", task, world, None)))
        try:
            save(evidence / "objects.json", scene_objects())
        except Exception:
            save(evidence / "geometry-error.json", dict(error=traceback.format_exc()))
    finally:
        for obj, names, stored in snapshots:
            for key in names:
                if key in stored:
                    setattr(obj, key, stored[key])
                elif hasattr(obj, key):
                    delattr(obj, key)
        gait.point_cloud_sensor = sensor
        art.set_world_pose(position=np.asarray(before["position"]), orientation=np.asarray(before["rotation"]))
        art.set_world_velocity(vel)
        art.set_joint_positions(np.asarray(before["joints"]))
        art.set_joint_velocities(np.asarray(before["joint_velocities"]))
        if drives is not None:
            art.apply_action(drives)
        tick = int(world.current_time_step_index)
        if world.physics_sim_view is not None:
            world.physics_sim_view.update_articulations_kinematic()
        get_physx_interface().update_transformations(False, True, False, False)
        world.render()
        restored = state_snapshot(task, world)
        errors = {"root_velocity": float(np.max(np.abs(art.get_world_velocity() - vel)))}
        for key in ("position", "rotation", "joints", "joint_velocities", "camera_position", "camera_rotation"):
            a, b = np.asarray(restored[key]), np.asarray(before[key])
            errors[key] = float(np.max(np.abs(a-b)))
            if key in ("rotation", "camera_rotation"):
                errors[key] = min(errors[key], float(np.max(np.abs(a+b))))
        passed = max(errors.values()) < 1e-4 and restored["world_step"] == tick and task.step_count == 1901
        save(OUT / "restored.json", dict(pid=os.getpid(), verified=passed, state=restored, max_abs_errors=errors))
        if not passed:
            raise RuntimeError(f"F38 restoration failed: {errors}")
        bridge.serve(env, OUT / "live", 38)
