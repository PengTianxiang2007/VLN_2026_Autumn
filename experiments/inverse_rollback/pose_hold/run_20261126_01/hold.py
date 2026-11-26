"""Keep the restored H1 available in the original Python process via tmux."""
import code
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import traceback

ROOT = Path(__file__).resolve().parents[4]
CAPTURE = ROOT / "outputs/multiview_capture/v001/run_20261117_03"
OUT = ROOT / "outputs/inverse_rollback/pose_hold/run_20261126_01"
EPISODE = "kujiale_0036_0_0"
FRAME = CAPTURE / "capture/episodes" / EPISODE / "attempt_1794972488070620490/steps/000038/metadata.json"
CONFIG = CAPTURE / "runs/vlnverse/streamvln/results/peng_fine_multiview104_20261117_03/chunk_1794961469812783985/eval_config.py"
sys.path[:0] = [str(CAPTURE / "code"), str(CAPTURE / "code/benchmarks/vlnverse/upstream"), str(ROOT)]
gpu = int(os.environ["VLN_SIM_RENDER_GPU"])
sys.argv[1:] = [f"--/renderer/activeGpu={gpu}", "--/renderer/multiGpu/enabled=False"]


def status(phase, **data):
    record = dict(phase=phase, pid=os.getpid(), gpu=gpu, episode=EPISODE, step=38, **data)
    tmp = OUT / "status.tmp"
    tmp.write_text(json.dumps(record, indent=2) + "\n")
    tmp.replace(OUT / "status.json")


def prepare():
    import numpy as np
    from PIL import Image
    from vlnverse.configs.evaluator.default_config import get_config
    from vlnverse.evaluator.utils.common import set_seed_model
    from vlnverse.evaluator.utils.eval import generate_episode
    from vlnverse.projects.dataloader.base import BasePathKeyDataloader
    from vlnverse.env import Env
    tick_action = runpy.run_path(str(ROOT / "scripts/run_inverse_rollback.py"))["tick_action"]
    from core.step_multiview import state_snapshot, pose_record

    record = json.loads(FRAME.read_bytes())
    assert (record["episode_id"], record["step"], record["seed"]) == (EPISODE, 38, 2)
    set_seed_model(2)
    cfg = get_config(runpy.run_path(str(CONFIG))["eval_cfg"])
    settings = cfg.dataset.dataset_settings
    loader = BasePathKeyDataloader(dataset_type=cfg.dataset.dataset_type, **{
        k: settings[k] for k in ("base_data_dir", "split_data_types", "robot_offset",
                                 "filter_same_trajectory", "filter_stairs")})
    loader.task_name = "retained_f38"
    key, = [k for k, v in loader.path_key_data.items() if v["episode_id"] == EPISODE]
    loader.resumed_path_key_list = [key]
    cfg.task.task_settings["episodes"] = generate_episode(loader, cfg)
    env = Env.init(cfg.env, cfg.task)
    try:
        env.reset()
        task, = env.env.runner.current_tasks.values()
        assert task.data["episode_id"] == EPISODE
        world = env.env.runner._world
        art = task.robot.articulation._articulation
        _, ended, _ = tick_action(env, {"stand_still": []}, 500)
        if ended:
            raise RuntimeError("Episode ended during initialization")
        s = record["physical_state_before"]
        offset = np.asarray(task.env_offset) - np.asarray(record["environment_offset"])
        if np.any(offset):
            raise ValueError(f"Historical single-environment origin differs: {offset}")
        art.set_world_pose(position=np.asarray(s["position"]), orientation=np.asarray(s["rotation"]))
        art.set_world_velocity(np.zeros(6))
        art.set_joint_positions(np.asarray(s["joints"]))
        art.set_joint_velocities(np.asarray(s["joint_velocities"]))
        task.step_count = s["physics_ticks"]
        from omni.physx import get_physx_interface
        start_tick = int(world.current_time_step_index)
        if world.physics_sim_view is not None:
            world.physics_sim_view.update_articulations_kinematic()
        get_physx_interface().update_transformations(False, True, False, False)
        world.render()
        rgb = task.get_rgb_depth()["rgb"]
        current = state_snapshot(task, world)
        delta = {key: float(np.max(np.abs(np.subtract(current[key], s[key]))))
                 for key in ("position", "joints", "joint_velocities", "camera_position")}
        for key in ("rotation", "camera_rotation"):
            p, q = np.asarray(current[key]), np.asarray(s[key])
            delta[key] = float(min(np.max(np.abs(p-q)), np.max(np.abs(p+q))))
        if (int(world.current_time_step_index) != start_tick or task.step_count != s["physics_ticks"]
                or max(delta.values()) > 0.001):
            raise RuntimeError(f"Pose or frozen tick readback mismatch: {delta}, tick {world.current_time_step_index}, expected {start_tick}")
        Image.fromarray(rgb).save(OUT / "front.png")
        status("held", source=str(FRAME.relative_to(ROOT)), sha256=hashlib.sha256(FRAME.read_bytes()).hexdigest(),
               config=str(CONFIG.relative_to(ROOT)), readback=current, maximum_absolute_errors=delta,
               robot_pose=pose_record(current["position"], current["rotation"]),
               post_placement_physics_ticks=int(world.current_time_step_index)-start_tick,
               root_velocity="initialized to zero; absent from capture",
               tmux_socket="peng_vln_pose_20261126", tmux_session="f38")
        print("F38 HELD. env, task, world and art are live. Waiting for input.", flush=True)
        code.interact(banner="", local=dict(env=env, task=task, world=world, art=art))
    finally:
        env.close()


if __name__ == "__main__":
    status("loading")
    try:
        prepare()
    except BaseException as exc:
        status("error", error=repr(exc), traceback=traceback.format_exc())
        raise
