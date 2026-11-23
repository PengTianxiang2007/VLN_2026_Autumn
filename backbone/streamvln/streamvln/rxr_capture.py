"""Lossless Habitat observations at the initial state and after each native action."""
import json
from pathlib import Path
import tempfile

from PIL import Image
from scripts.run_rxr_roundtrip import pose


class EpisodeCapture:
    def __init__(self, output, scene, episode, reference):
        parent = Path(output) / "capture" / scene / str(episode.episode_id)
        parent.mkdir(parents=True, exist_ok=True)
        # A retry keeps the incomplete attempt. The native score points to its own attempt.
        self.directory = Path(tempfile.mkdtemp(prefix="attempt_", dir=parent))
        self.relative_path = str(self.directory.relative_to(output))
        metadata = dict(scene_id=scene, episode_id=episode.episode_id,
                        trajectory_id=episode.trajectory_id, language=episode.info.get("language", "en"),
                        instruction=episode.instruction.instruction_text,
                        reference_locations=reference, goals=[goal.position for goal in episode.goals])
        (self.directory / "episode.json").write_text(json.dumps(metadata, ensure_ascii=False))

    def frame(self, step, action, observations, env):
        name = f"{step:04d}.png"
        Image.fromarray(observations["rgb"]).save(self.directory / name, compress_level=2)
        state = env.sim.get_agent_state()
        actions = ("STOP", "MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT")
        row = dict(step=step, action_id=action, action=None if action is None else actions[action],
                   rgb=name, pose=pose(state), camera=pose(state.sensor_states["rgb"]),
                   terminal=bool(env.episode_over),
                   collided=bool(action == 1 and env.sim.previous_step_collided))
        with (self.directory / "trace.jsonl").open("a") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
