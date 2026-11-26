"""Serve one live VLNVerse H1 on the Isaac main thread. Imported by the owner
of the environment; detaching the tool service leaves the simulator alive.
"""
import json
import os
import socket
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from run_inverse_rollback import save, save_native_rgb, tick_action


class RobotTools:
    def __init__(self, env, directory, start_frame, move_limit):
        self.env = env
        self.task, = env.env.runner.current_tasks.values()
        self.world = env.env.runner._world
        self.controller = self.task.robot.controllers["move_by_discrete"]
        self.directory = directory
        self.start_frame = start_frame
        self.move_limit = move_limit
        self.moves = 0
        self.phase = "active"
        self.sequence = 0

    def state(self):
        position, quaternion = self.task.robot.articulation.get_world_pose()
        return dict(position=position.tolist(), quaternion_wxyz=quaternion.tolist(),
                    task_ticks=int(self.task.step_count), world_ticks=int(self.world.current_time_step_index))

    def call(self, method, action, request_id):
        moves = {"forward": 1, "turn_left": 2, "turn_right": 3}
        if not ((method == "observe" and action is None) or
                (method == "step" and action in (*moves, "finish_return"))):
            raise ValueError("Expected observe() or step(forward | turn_left | turn_right | finish_return)")
        if method == "step" and self.phase != "active":
            raise ValueError(f"Local return is {self.phase}; movement is closed.")
        if action in moves and self.move_limit is not None and self.moves >= self.move_limit:
            raise ValueError("This session has used its movement allowance.")
        if self.task not in self.env.env.runner.current_tasks.values():
            self.phase = "episode_changed"
            raise RuntimeError("The attached H1 episode is no longer current.")

        self.sequence += 1
        image_path = self.directory / "frames" / f"{self.sequence:05d}.png"
        before = self.state()
        audit = dict(request_id=request_id, sequence=self.sequence, method=method, action=action, before=before,
                     started_utc=datetime.now(timezone.utc).isoformat())
        observation = None
        terminal_reason = None
        ticks = 0
        try:
            if action in moves:
                # An interrupted native action may already have moved the robot.
                self.phase = "action_incomplete"
                observation, ended, ticks = tick_action(
                    self.env, {"move_by_discrete": [moves[action]]}, self.controller.steps_per_action)
                self.moves += 1
                self.phase = "physical_terminal" if ended else "active"
                terminal_reason = observation.get("fail_reason") if ended else None
            elif action == "finish_return":
                self.phase = "return_declared"

            frame = save_native_rgb(image_path, self.task, self.world, observation)
            after = self.state()
            if after["world_ticks"] - before["world_ticks"] != ticks:
                raise RuntimeError("World tick count does not match the requested operation.")
            result = dict(episode_id=self.task.data["episode_id"], live_frame=self.start_frame + self.moves,
                          sequence=self.sequence, tool=method, action=action, status=self.phase,
                          physics_ticks_advanced=ticks, terminal_reason=terminal_reason)
            audit.update(result=result, after=after, rgb=frame)
            return result
        except Exception as exc:
            audit.update(error=repr(exc), after=self.state())
            if action in moves and self.phase != "physical_terminal":
                self.phase = "action_incomplete"
            raise
        finally:
            audit["finished_utc"] = datetime.now(timezone.utc).isoformat()
            with (self.directory / "calls.jsonl").open("a") as log:
                log.write(json.dumps(audit, allow_nan=False) + "\n")


def serve(env, directory, start_frame, *, move_limit=None):
    """Attach to a single episode. Each new attachment uses a fresh trace directory."""
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "frames").mkdir()
    robot = RobotTools(env, directory, start_frame, move_limit)
    # Keep sockets on the local host rather than on the project NAS.
    with tempfile.TemporaryDirectory(prefix="vlnverse-h1-") as private, socket.socket(socket.AF_UNIX) as listener:
        address = Path(private) / "robot.sock"
        detach = Path(private) / "detach"
        listener.bind(str(address))
        listener.listen(4)
        listener.settimeout(1)
        endpoint = dict(socket=str(address), detach_marker=str(detach), pid=os.getpid(),
                        episode_id=robot.task.data["episode_id"], start_frame=start_frame)
        receipts = {}
        save(directory / "endpoint.json", dict(endpoint, status="ready"))
        try:
            while not detach.exists():
                try:
                    conn, _ = listener.accept()
                except socket.timeout:
                    continue
                with conn, conn.makefile("rb") as stream:
                    conn.settimeout(10)
                    try:
                        request = json.loads(stream.readline(2048))
                        key = str(uuid.UUID(request["id"]))
                        args = (request["method"], request.get("action"))
                        if key in receipts:
                            previous, reply = receipts[key]
                            if previous != args:
                                raise ValueError("A request ID cannot select two actions.")
                        else:
                            try:
                                reply = {"result": robot.call(*args, request_id=key)}
                            except Exception as exc:
                                reply = {"error": str(exc)}
                            receipts[key] = (args, reply)
                    except (ValueError, KeyError, TypeError, OSError) as exc:
                        reply = {"error": str(exc)}
                    try:
                        conn.sendall(json.dumps(reply).encode() + b"\n")
                    except OSError:
                        pass  # The action receipt survives a client disconnect.
        finally:
            save(directory / "endpoint.json", dict(endpoint, status="detached", moves=robot.moves))
