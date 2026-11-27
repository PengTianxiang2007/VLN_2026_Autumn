"""Opt-in native VLNVerse action gate. No teleport, reset, or metric replacement."""
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time

import numpy as np
from PIL import Image

from core.codex_client import now, save, sha256
from core.codex_live_takeover import clean_child_env, takeover
from core.codex_serial_config import DEFAULTS, ROOT, snapshot_source
from core.codex_serial_guard import PipelineGuardError, cleanup_review_children
from core.oracle_crossing import plain


class ReviewWorker:
    def __init__(self, folder):
        self.folder = folder
        self.config = json.loads((folder / "config.json").read_text())
        self.log = (folder / "worker.log").open("x")
        try:
            self.child = subprocess.Popen(
                [str(ROOT / ".runtime/crossing_vllm27/bin/python"), "-Bu",
                 str(ROOT / "scripts/run_codex_serial_worker.py"), str(folder)],
                cwd=ROOT, env=clean_child_env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.log, bufsize=0, start_new_session=True)
        except BaseException:
            self.log.close()
            raise
        save(folder / "worker_process.json", dict(pid=self.child.pid, started_at=now()))

    def request(self, row, heartbeat):
        try:
            self.child.stdin.write((json.dumps(row) + "\n").encode())
            self.child.stdin.flush()
        except BrokenPipeError:
            self.raise_worker_failure()
        deadline = time.monotonic() + self.config["boundary_timeout_seconds"]
        buffer = b""
        while b"\n" not in buffer:
            if time.monotonic() >= deadline:
                self.close()
                raise PipelineGuardError("review_worker", "boundary_timeout")
            heartbeat()
            if not select.select([self.child.stdout], [], [], min(1, max(0, deadline-time.monotonic())))[0]:
                continue
            data = os.read(self.child.stdout.fileno(), 65536)
            if not data:
                self.raise_worker_failure()
            buffer += data
            if len(buffer) > 4 * 1024 * 1024:
                raise PipelineGuardError("review_worker", "oversized_reply")
        if time.monotonic() >= deadline:
            raise PipelineGuardError("review_worker", "boundary_timeout")
        answer = json.loads(buffer)
        if (answer.get("episode_id"), answer.get("frame")) != (row["episode_id"], row["frame"]):
            raise ValueError("Reviewer replied to another episode/action boundary")
        return answer

    def raise_worker_failure(self):
        failure = self.folder / "worker_failure.json"
        if failure.exists():
            cause = json.loads(failure.read_text())
            raise PipelineGuardError(cause["stage"], cause["code"], cause["attempts"])
        raise PipelineGuardError("review_worker", "worker_exited")

    def close(self):
        if self.child.poll() is None:
            # The worker handles TERM and closes its independently owned Codex group.
            self.child.terminate()
            try:
                self.child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(self.child.pid, signal.SIGKILL)
                self.child.wait()
        cleanup_review_children(self.folder)
        self.child.stdin.close()
        self.child.stdout.close()
        self.log.close()


class SerialHook:
    def __init__(self, evaluator, settings):
        if (evaluator.env_num != 1 or evaluator.proc_num != 1 or evaluator.run_seed is None
                or evaluator.robot_flash or evaluator.robot_name != "h1"):
            raise ValueError("Codex serial v001 requires one physical H1 environment and an explicit seed")
        if evaluator.review or evaluator.jev_live or os.environ.get("VLN_SERIAL_OUTPUT"):
            raise ValueError("Codex serial capture must run without another navigation hook/observer")
        if not os.environ.get("JEV_API_KEY"):
            raise RuntimeError("JEV_API_KEY is required for serial navigation")
        self.e = evaluator
        self.output = Path(settings["output_dir"]).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        if (self.output / "halt.json").exists():
            raise RuntimeError("This serial run was halted; retain its evidence and use a new output directory")
        self.config = dict(DEFAULTS, seed=evaluator.run_seed)
        config_path = self.output / "config.json"
        if config_path.exists() and json.loads(config_path.read_text()) != self.config:
            raise ValueError("Existing serial output uses another protocol; choose a new output directory")
        save(config_path, self.config)
        snapshot_source(self.output)
        self.worker = None
        self.active = False
        self.pending_terminal = None
        self.last_heartbeat = 0
        self.reset = evaluator.reset_seeded_agent
        self.action = evaluator.get_action
        self.step = evaluator.env_step
        self.terminate = evaluator.terminate_ops
        evaluator.reset_seeded_agent = self.after_reset
        evaluator.get_action = self.before_action
        evaluator.env_step = self.step_with_terminal
        evaluator.terminate_ops = self.finish_before_reset
        self.old_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, self.cancel)

    def cancel(self, *_):
        raise KeyboardInterrupt("Serial navigation cancelled")

    def event(self, kind, **fields):
        row = dict(kind=kind, time=now(), episode_id=self.eid, frame=self.frame, **plain(fields))
        with (self.folder / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        save(self.output / "live.json", row)
        print("CODEX_SERIAL " + json.dumps(row, ensure_ascii=False), flush=True)

    def heartbeat(self):
        if time.monotonic() - self.last_heartbeat >= 30:
            self.last_heartbeat = time.monotonic()
            self.event("waiting", stage=self.stage)

    def after_reset(self, infos, indices):
        self.reset(infos, indices)
        if not indices:
            return
        if indices != [0] or len(infos) != 1:
            raise ValueError("Unexpected serial environment reset")
        self.close_worker()
        data = infos[0].data
        self.eid = data["episode_id"]
        self.folder = self.output / "episodes" / self.eid / ("attempt_%d" % time.time_ns())
        self.folder.mkdir(parents=True)
        (self.folder / "frames").mkdir()
        self.frame = 0
        self.active = True
        self.pending_terminal = None
        self.recovery = None
        self.started = time.monotonic()
        self.policy_seconds = self.review_seconds = self.action_seconds = 0.0
        save(self.folder / "config.json", self.config)
        save(self.folder / "start.json", dict(episode_id=self.eid, seed=self.e.run_seed,
             instruction=data["instruction"]["instruction_text"], scene=data.get("scan", ""), started_at=now()))
        self.worker = ReviewWorker(self.folder)
        self.event("episode_started")

    def capture(self, ob, *, terminal=False):
        task, = self.e.env.env.runner.current_tasks.values()
        if task.data["episode_id"] != self.eid:
            raise RuntimeError("Episode changed before observation capture")
        world = self.e.env.env.runner._world
        rgb = ob.get("rgb")
        source = "native_observation"
        if rgb is None and terminal:
            # Native STOP returns metrics without RGB. Read the existing camera
            # before reset; never execute another action just to obtain an image.
            before = (int(world.current_time_step_index), int(task.step_count))
            rgb = task.get_rgb_depth().get("rgb")
            if before != (int(world.current_time_step_index), int(task.step_count)):
                raise RuntimeError("Terminal RGB capture advanced physics")
            source = "terminal_camera_read"
        if rgb is None:
            raise RuntimeError("Missing actual first-person RGB")
        path = self.folder / "frames" / (f"F{self.frame:06d}" + ("_terminal" if terminal else "") + ".png")
        Image.fromarray(np.asarray(rgb, dtype=np.uint8)).save(path)
        position, quaternion = task.robot.articulation.get_world_pose()
        row = dict(episode_id=self.eid, step=self.frame, terminal=terminal,
                   native_front=dict(image=str(path.relative_to(self.folder)), sha256=sha256(path), source=source),
                   robot_position=plain(position), quaternion_wxyz=plain(quaternion),
                   task_ticks=int(task.step_count), world_ticks=int(world.current_time_step_index),
                   simulation_time_s=float(world.current_time), time=now())
        with (self.folder / "observations.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        return row

    def before_action(self, observations, actions):
        if not self.active or self.e.runner_status[0].name != "NORMAL":
            return self.action(observations, actions)
        ob = observations[0]
        captured = self.capture(ob)
        before = time.monotonic()
        result, actions = self.action(observations, actions)
        self.policy_seconds += time.monotonic() - before
        proposed = actions[0][self.e.robot_name]
        stop = "stop" in proposed
        self.stage = "terminal_review" if stop else "jev_and_review"
        self.event("boundary_wait", proposed_action=proposed, stop_requested=stop)
        before = time.monotonic()
        answer = self.worker.request(dict(episode_id=self.eid, frame=self.frame,
                         native_front=captured["native_front"], stop_requested=stop), self.heartbeat)
        self.review_seconds += time.monotonic() - before
        decision = answer["decision"]
        self.event("boundary_reviewed", decision=decision, wait_seconds=time.monotonic() - before)
        if decision == "deviated":
            self.close_worker()  # Parent thread is complete and cannot acquire another turn.
            self.stage = "gpt_takeover"
            self.event("takeover_started", thread_id=answer["thread_id"], review_turn=answer["review_turn"],
                       rollback_target=answer["rollback_target"], original_action_discarded=proposed)
            terminal_ob, ended, self.recovery = takeover(self.e.env, self.folder / "recovery", answer,
                                                       self.config, self.heartbeat)
            self.frame += self.recovery["movements"]
            if not ended:
                # Finalize exactly once through the original native STOP path.
                before_stop = time.monotonic()
                terminal_obs, terminal_flags = self.step(np.array([{self.e.robot_name: {"stop": []}}]))
                self.action_seconds += time.monotonic() - before_stop
                self.event("native_action_executed", action={"stop": []}, terminated=bool(terminal_flags[0]),
                           reason="recovery_finalization")
                self.frame += 1
            else:
                terminal_obs, terminal_flags = [terminal_ob], [True]
            if not terminal_flags[0]:
                raise RuntimeError("Native finalization did not terminate the episode")
            self.pending_terminal = terminal_obs, terminal_flags
        elif decision != ("stop" if stop else "continue"):
            raise ValueError("Reviewer did not authorize the proposed native action")
        elif stop:
            self.close_worker()
        return result, actions

    def step_with_terminal(self, actions):
        if self.pending_terminal is not None:
            result = self.pending_terminal
            self.pending_terminal = None
            return result
        before = time.monotonic()
        result = self.step(actions)
        if self.active:
            self.action_seconds += time.monotonic() - before
            self.event("native_action_executed", action=actions[0][self.e.robot_name], terminated=bool(result[1][0]))
            self.frame += 1
        return result

    def finish_before_reset(self, observations, infos, terminated):
        completed = None
        if self.active and terminated[0]:
            self.capture(observations[0], terminal=True)
            self.close_worker()
            metrics = plain(next(iter(observations[0]["metrics"].values()))[0])
            self.event("episode_finished", metrics=metrics, recovery=self.recovery)
            completed = self.folder / "result.json", dict(episode_id=self.eid, seed=self.e.run_seed, phase="complete",
                 metrics=metrics, recovery=self.recovery, final_frame=self.frame,
                 model_declared_success=bool(self.recovery and self.recovery["model_declared_success"]),
                 elapsed_seconds=time.monotonic() - self.started, policy_seconds=self.policy_seconds,
                 review_seconds=self.review_seconds, native_action_seconds=self.action_seconds,
                 recovery_seconds=self.recovery["elapsed_seconds"] if self.recovery else 0.0)
            self.active = False
        result = self.terminate(observations, infos, terminated)
        if completed:
            save(*completed)  # Commit only after the native scorer/data collector succeeds.
        return result

    def close_worker(self):
        if self.worker is not None:
            self.worker.close()
            self.worker = None

    def failed(self, error):
        record = dict(phase="cancelled" if isinstance(error, (KeyboardInterrupt, SystemExit))
                      else "technical_error", error=type(error).__name__, time=now(), scored=False,
                      automatic_retry_allowed=False)
        if isinstance(error, PipelineGuardError):
            record.update(error.record())
        elif isinstance(error, ModuleNotFoundError):
            record["missing_module"] = error.name
        elif type(error) is RuntimeError:
            record["detail"] = str(error)[:500]
        if self.active:
            # No fabricated STOP/score on transport or infrastructure failure.
            record.update(episode_id=self.eid, frame=self.frame,
                          elapsed_seconds=time.monotonic() - self.started)
            save(self.folder / "failure.json", record)
        # The launcher must not turn exhausted local retries into fresh episode retries.
        save(self.output / "halt.json", record)

    def close(self):
        self.close_worker()
        signal.signal(signal.SIGTERM, self.old_sigterm)
