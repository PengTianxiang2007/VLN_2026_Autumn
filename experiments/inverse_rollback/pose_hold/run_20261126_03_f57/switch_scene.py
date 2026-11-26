"""Load the selected captured episode in the existing single-H1 environment and hold it at F57."""
import json
import os
from pathlib import Path
import runpy

import numpy as np
from omni.physx import get_physx_interface

from core.step_multiview import pose_record, state_snapshot
from run_inverse_rollback import save, save_native_rgb, tick_action
from vlnverse.configs.evaluator.default_config import get_config
from vlnverse.evaluator.utils.eval import generate_episode
from vlnverse.projects.dataloader.base import BasePathKeyDataloader
from vlnverse_robot_bridge import serve

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "outputs/inverse_rollback/pose_hold/run_20261126_03_f57"
EPISODE = "kujiale_0128_fix_20_0"
CAPTURE = ROOT / "outputs/multiview_capture/v001/run_20261117_03"
SOURCE = CAPTURE / "capture/episodes" / EPISODE / "attempt_1794964326806582757/steps/000057/metadata.json"
CONFIG = CAPTURE / ("runs/vlnverse/streamvln/results/peng_fine_multiview104_20261117_03/"
                    "chunk_1794961469812783985/eval_config.py")


def switch_and_place(env, previous_episode="kujiale_0036_0_0", destination=OUT, *,
                     source=SOURCE, episode=EPISODE, scene="kujiale_0128_fix", frame=57,
                     phase="terminal", config=CONFIG):
    record = json.loads(source.read_bytes())
    if (record["episode_id"], record["scene"], record["seed"], record["step"], record["phase"]) != (
            episode, scene, 2, frame, phase):
        raise ValueError("Unexpected recording")

    cfg = get_config(runpy.run_path(str(config))["eval_cfg"])
    settings = cfg.dataset.dataset_settings
    loader = BasePathKeyDataloader(dataset_type=cfg.dataset.dataset_type, **{
        k: settings[k] for k in ("base_data_dir", "split_data_types", "robot_offset",
                                  "filter_same_trajectory", "filter_stairs")})
    loader.task_name = "retained_f57"
    key, = [k for k, value in loader.path_key_data.items() if value["episode_id"] == episode]
    loader.resumed_path_key_list = [key]
    next_cfg, = generate_episode(loader, cfg)
    if loader.path_key_scan[key] != record["scene"] or not Path(next_cfg.scene_asset_path).is_file():
        raise ValueError(f"Unexpected or missing scene asset: {next_cfg.scene_asset_path}, {loader.path_key_scan[key]}")

    runner = env.env.runner
    manager = runner.task_config_manager
    current, = runner.current_tasks.values()
    if (current.data["episode_id"] != previous_episode or manager.env_num != 1
            or manager.current_task_config_idx != len(manager.task_configs)):
        raise RuntimeError("The retained simulator no longer has the expected single episode")
    manager.task_configs.append(next_cfg)
    manager.len_tasks = manager.validate_task_configs()
    env.reset([0])
    task, = runner.current_tasks.values()
    if task.data["episode_id"] != episode or not np.array_equal(task.env_offset, record["environment_offset"]):
        raise RuntimeError("Unexpected episode or world origin after scene reset")
    world = runner._world
    art = task.robot.articulation._articulation
    _, ended, warmup = tick_action(env, {"stand_still": []}, 500)
    if ended:
        raise RuntimeError("H1 ended during initialization")

    target = record["physical_state_before"]
    at_tick = int(world.current_time_step_index)
    art.set_world_pose(position=np.asarray(target["position"]), orientation=np.asarray(target["rotation"]))
    art.set_world_velocity(np.zeros(6))
    art.set_joint_positions(np.asarray(target["joints"]))
    art.set_joint_velocities(np.asarray(target["joint_velocities"]))
    task.step_count = target["physics_ticks"]
    if world.physics_sim_view is not None:
        world.physics_sim_view.update_articulations_kinematic()
    get_physx_interface().update_transformations(False, True, False, False)
    world.render()
    state = state_snapshot(task, world)
    errors = {}
    for k in ("position", "rotation", "joints", "joint_velocities", "camera_position", "camera_rotation"):
        a, b = np.asarray(state[k]), np.asarray(target[k])
        delta = np.max(np.abs(a - b))
        if k in ("rotation", "camera_rotation"):
            delta = min(delta, np.max(np.abs(a + b)))
        errors[k] = float(delta)
    advanced = state["world_step"] - at_tick
    passed = max(errors.values()) < 1e-4 and advanced == 0 and state["physics_ticks"] == target["physics_ticks"]
    save(destination / "placement.json", dict(verified=passed, pid=os.getpid(), episode_id=episode,
         scene=record["scene"], scene_asset=str(next_cfg.scene_asset_path), frame=frame, seed=2,
         source=str(source.relative_to(ROOT)), state=state, robot_pose=pose_record(state["position"], state["rotation"]),
         max_abs_errors=errors, root_velocity=art.get_world_velocity().tolist(), warmup_ticks=warmup,
         placement_ticks=advanced))
    if not passed:
        raise RuntimeError(f"F{frame} readback differs from the recording: {errors}")
    save_native_rgb(destination / "front.png", task, world, None)
    return task, world, art
