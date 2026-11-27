"""CPU contracts for the live STOP barrier, same-session fork, and native finalization."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from core.codex_client import save, sha256
from core.codex_live_takeover import takeover
from core.codex_serial_config import DEFAULTS
from core.codex_serial_guard import PipelineGuardError
from core.codex_serial_review import review_stream
from core.codex_serial_runtime import SerialHook
from scripts import vlnverse_robot_bridge as bridge


class StreamTests(unittest.TestCase):
    def run_stream(self, alarm=None, stop=8, same=False):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        save(folder / "start.json", dict(episode_id="live", instruction="Turn left.", scene="scene"))
        requests = []
        for f in range(stop + 1):
            image = folder / f"F{f}.png"
            image.write_bytes(b"transport fixture")
            requests.append(dict(episode_id="live", frame=f, stop_requested=f == stop,
                                 native_front=dict(image=image.name, sha256=sha256(image))))
        trace, prompts, scored = [], [], []
        pending = iter(requests)

        class Session:
            thread_id = "same-live-thread"

            def __init__(self, directory, config, **kwargs):
                self.directory, self.turn = directory, 0
                directory.mkdir(parents=True)

            def ask_checked(self, validate, prompt, images, schema, *, label, metadata):
                self.turn += 1
                directory = self.directory / str(self.turn)
                directory.mkdir()
                prompts.append((label, prompt))
                if label == "initialization" or label == "terminal_observation":
                    answer = dict(ready=True)
                elif label.startswith("deviation_"):
                    verdict = "deviated" if label == "deviation_" + str(alarm) else "consistent"
                    answer = dict(previous_id=metadata["previous_id"], current_id=metadata["current_id"],
                        verdict=verdict, segment_summary=dict(en="Hall.", zh="走廊。"), reason=dict(en="Route.", zh="路线。"),
                        instruction_evidence=[dict(quote_en="Turn left.", quote_zh="左转。")],
                        visual_evidence=[dict(frames=[metadata["current_frame"]], description=dict(en="Door.", zh="门。"))],
                        semantic_progress=dict(en="Completed: start. Current: hall. Pending: left.",
                                               zh="已完成：起点。当前：走廊。待执行：左转。") if verdict == "consistent" else None,
                        uncertainties=[])
                else:
                    compare = metadata["previous_id"] is not None
                    answer = dict(previous_id=metadata["previous_id"], current_id=metadata["current_id"],
                        eligibility="eligible", eligibility_reason="Visible branches.", reason="Branches.",
                        relation=("same" if same else "different") if compare else "not_compared",
                        matched_branches=[dict(description="Door.", a_frames=["A0"], b_frames=["B0"])] if same and compare else [],
                        a_only=[], b_only=[] if same and compare else ["Door."])
                checked = validate(answer)
                trace.append(label)
                return dict(thread_id=self.thread_id, turn=self.turn, directory=str(directory),
                            usage={}, text=json.dumps(answer)), checked

        class Sampler:
            def send(self, request):
                f = request["frame"]
                return dict(node=dict(id="S01" if f == 2 else "S02", index=f-2)) if f in (2, 5) else {}

            def close(self):
                trace.append("sampler_closed")

        def score(request):
            scored.append(request["frame"])
            return dict(answer=dict(probability_yes=0.9))

        replies = []

        def reply(row):
            trace.append("reply_" + str(row["frame"]) + "_" + row["decision"])
            replies.append(row)

        with patch("core.codex_serial_review.BoundedSession", Session), redirect_stdout(io.StringIO()):
            result = review_stream(folder, DEFAULTS, lambda: next(pending, None), reply,
                                   scorer=score, sampler_factory=Sampler)
        return result, replies, trace, prompts, scored

    def test_pending_stop_waits_for_final_review_and_uses_current_rgb(self):
        result, replies, trace, prompts, scored = self.run_stream()
        self.assertEqual(replies[-1]["decision"], "stop")
        self.assertTrue(result["terminal_reviewed"])
        self.assertEqual(scored, list(range(8)))
        for f, label in ((2, "deviation_S01"), (5, "deviation_S02"), (8, "deviation_END")):
            decision = "stop" if f == 8 else "continue"
            self.assertLess(trace.index(label), trace.index(f"reply_{f}_{decision}"))
        prompt = dict(prompts)["terminal_observation"]
        self.assertIn("STOP has not been executed", prompt)
        self.assertNotIn("trajectory has ended", prompt)

    def test_terminal_deviation_returns_final_thread_turn_and_retained_target(self):
        result, replies, trace, _, _ = self.run_stream(alarm="END")
        last = replies[-1]
        self.assertEqual((last["frame"], last["decision"], last["thread_id"]), (8, "deviated", "same-live-thread"))
        self.assertEqual(last["rollback_target"], "C01:S02:F3")
        self.assertEqual(last["review_turn"], result["deviation_reviews"][-1]["turn"])
        self.assertNotIn("reply_8_stop", trace)

    def test_midroute_alarm_blocks_next_motion_and_does_not_consume_future_frames(self):
        _, replies, trace, _, scored = self.run_stream(alarm="S02")
        self.assertEqual((replies[-1]["frame"], replies[-1]["rollback_target"]), (5, "C01:S01:F0"))
        self.assertEqual(scored, list(range(6)))
        self.assertNotIn("reply_5_continue", trace)

    def test_no_checkpoint_stop_is_initialization_only(self):
        result, replies, _, _, scored = self.run_stream(stop=0)
        self.assertEqual(scored, [])
        self.assertEqual(result["stop_reason"], "terminal_initialization_only")
        self.assertEqual(replies[-1]["decision"], "stop")

    def test_dedup_removed_node_is_not_a_rollback_target(self):
        result, replies, _, _, _ = self.run_stream(alarm="END", same=True)
        self.assertEqual([n["id"] for n in result["effective_nodes"]], ["S02"])
        self.assertEqual(replies[-1]["rollback_target"], "C01:S02:F3")


class NativeGateTests(unittest.TestCase):
    def test_native_stop_without_rgb_reads_camera_and_commits_metrics(self):
        e, hook = self.make_hook()
        task, = e.env.env.runner.current_tasks.values()
        task.get_rgb_depth = Mock(return_value=dict(rgb=self.ob["rgb"]))
        terminal = dict(self.ob)
        terminal.pop("rgb")  # Actual VlnEvalTask STOP observation has no RGB.
        e.terminate_ops([terminal], [], [True])
        self.assertEqual(task.get_rgb_depth.call_count, 1)
        self.assertEqual(task.step_count, 10)
        self.assertEqual(e.env.env.runner._world.current_time_step_index, 10)
        self.native_end.assert_called_once()
        result = json.loads((hook.folder / "result.json").read_text())
        self.assertEqual(result["metrics"], self.ob["metrics"]["native"][0])
        capture = json.loads((hook.folder / "observations.jsonl").read_text().splitlines()[-1])
        self.assertEqual(capture["native_front"]["source"], "terminal_camera_read")
        self.assertTrue((hook.folder / capture["native_front"]["image"]).is_file())

    def make_hook(self, decision="stop", proposed="stop"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ob = dict(rgb=np.zeros((3, 4, 3), dtype=np.uint8), metrics={"native": [dict(success=1, spl=0.4)]})
        task = NS(data=dict(episode_id="live"), step_count=10,
                  robot=NS(articulation=NS(get_world_pose=lambda: (np.zeros(3), np.array([1, 0, 0, 0])))))
        env = NS(env=NS(runner=NS(current_tasks={"task": task}, _world=NS(current_time_step_index=10, current_time=0.1))))
        actions = np.array([{"h1": {proposed: [] if proposed == "stop" else [1]}}])
        e = NS(env=env, env_num=1, proc_num=1, run_seed=2, robot_flash=False, robot_name="h1",
               review=None, jev_live=None, runner_status=[NS(name="NORMAL")], reset_seeded_agent=Mock(),
               get_action=Mock(return_value=([self.ob], actions)),
               env_step=Mock(return_value=([self.ob], [True])), terminate_ops=Mock(return_value=(True, [])))
        self.native_step, self.native_end = e.env_step, e.terminate_ops
        self.worker = Mock()
        self.worker.request.return_value = dict(decision=decision, thread_id="parent", review_turn=7,
            rollback_target="S01", episode_id="live", frame=0)
        with patch.dict("os.environ", {"JEV_API_KEY": "fixture"}), patch("core.codex_serial_runtime.ReviewWorker", return_value=self.worker):
            hook = SerialHook(e, dict(output_dir=tmp.name))
            self.addCleanup(hook.close)
            e.reset_seeded_agent([NS(data=dict(episode_id="live", instruction=dict(instruction_text="Turn left.")))], [0])
        return e, hook

    def test_stop_is_not_executed_before_review_and_finalizes_once(self):
        e, hook = self.make_hook()
        self.worker.request.side_effect = lambda row, heartbeat: (
            self.assertEqual(self.native_step.call_count, 0) or dict(decision="stop"))
        _, actions = e.get_action([self.ob], [])
        self.native_step.assert_not_called()
        obs, ended = e.env_step(actions)
        e.terminate_ops(obs, [], ended)
        self.assertEqual(self.native_step.call_count, 1)
        self.assertEqual(self.native_end.call_count, 1)
        result = json.loads((hook.folder / "result.json").read_text())
        self.assertEqual(result["metrics"], dict(success=1, spl=0.4))

    def test_stop_alarm_forks_at_current_boundary_and_discards_native_action(self):
        e, hook = self.make_hook("deviated")
        summary = dict(movements=180, model_declared_success=False, elapsed_seconds=2, stop_reason="movement_budget")

        def recover(env, folder, answer, config, heartbeat):
            self.native_step.assert_not_called()
            self.native_end.assert_not_called()
            self.assertIs(env, e.env)
            self.assertEqual((answer["thread_id"], answer["review_turn"], config["movement_budget"]), ("parent", 7, 180))
            return self.ob, False, summary

        with patch("core.codex_serial_runtime.takeover", side_effect=recover):
            _, actions = e.get_action([self.ob], [])
        self.assertEqual(self.native_step.call_count, 1)  # Only the final native STOP.
        obs, ended = e.env_step(actions)
        self.assertEqual(self.native_step.call_count, 1)
        e.terminate_ops(obs, [], ended)
        self.native_end.assert_called_once()
        self.assertEqual(json.loads((hook.folder / "result.json").read_text())["recovery"], summary)

    def test_physical_terminal_during_takeover_never_gets_another_stop(self):
        e, _ = self.make_hook("deviated", proposed="move_by_discrete")
        with patch("core.codex_serial_runtime.takeover", return_value=(self.ob, True,
                   dict(movements=3, model_declared_success=False, elapsed_seconds=1))):
            _, actions = e.get_action([self.ob], [])
        self.assertEqual(e.env_step(actions), ([self.ob], [True]))
        self.native_step.assert_not_called()

    def test_review_transport_failure_cannot_advance_or_score(self):
        e, hook = self.make_hook()
        self.worker.request.side_effect = RuntimeError("worker exited")
        with self.assertRaises(RuntimeError):
            e.get_action([self.ob], [])
        self.native_step.assert_not_called()
        self.native_end.assert_not_called()
        self.assertFalse((hook.folder / "result.json").exists())

    def test_recovery_timeout_halts_without_native_stop_or_score(self):
        e, hook = self.make_hook("deviated")
        error = PipelineGuardError("codex_recovery", "tool_idle_timeout")
        with patch("core.codex_serial_runtime.takeover", side_effect=error):
            with self.assertRaises(PipelineGuardError):
                e.get_action([self.ob], [])
        hook.failed(error)
        self.native_step.assert_not_called()
        self.native_end.assert_not_called()
        failure = json.loads((hook.output / "halt.json").read_text())
        self.assertFalse(failure["scored"])
        self.assertFalse(failure["automatic_retry_allowed"])
        self.assertEqual(failure["code"], "tool_idle_timeout")


class BridgeBudgetTests(unittest.TestCase):
    def test_180_actual_movements_are_a_hard_limit_and_observe_costs_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "frames").mkdir()
            task = NS(data=dict(episode_id="live"), robot=NS(controllers={"move_by_discrete": NS(steps_per_action=50)}))
            env = NS(env=NS(runner=NS(current_tasks={"task": task}, _world=NS())))
            robot = bridge.RobotTools(env, folder, 12, 180)
            state = dict(task_ticks=0, world_ticks=0)
            robot.state = lambda: dict(state)

            def tick(*_):
                state["task_ticks"] += 50
                state["world_ticks"] += 50
                return {"rgb": "actual"}, False, 50

            with patch.object(bridge, "tick_action", side_effect=tick) as move, patch.object(bridge, "save_native_rgb", return_value={}) as capture:
                robot.call("observe", None, "observe")
                for i in range(180):
                    result = robot.call("step", "turn_left" if i % 2 else "forward", str(i))
                self.assertEqual((robot.moves, result["moves_remaining"], result["live_frame"]), (180, 0, 192))
                with self.assertRaises(ValueError):
                    robot.call("step", "forward", "excess")
                robot.call("observe", None, "last_view")
                robot.call("step", "finish_return", "finish")
                self.assertEqual(move.call_count, 180)
                self.assertEqual(capture.call_count, 183)
                self.assertEqual(robot.phase, "return_declared")


class LiveForkTests(unittest.TestCase):
    def test_fork_uses_final_review_session_and_cap_detaches_its_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review = root / "review"
            (review / "codex").mkdir(parents=True)
            last = dict(answer=dict(verdict="deviated"), turn=8)
            save(review / "result.json", dict(deviation_reviews=[last], rollback_target="C01:S01:F0",
                                              effective_nodes=[dict(candidate_id="C01:S01:F0")]))
            save(review / "codex/session.json", dict(turns=8, thread_id="parent"))
            boundary = dict(episode_id="live", frame=20, thread_id="parent", review_turn=8,
                            rollback_target="C01:S01:F0", review_directory=str(review))
            env = NS(env=NS(runner=NS(current_tasks={"task": NS(data=dict(episode_id="live"))})))
            child = Mock(pid=123, poll=Mock(return_value=None))

            def launch(command, **kwargs):
                self.assertEqual(kwargs["cwd"], review / "codex")
                self.assertEqual(command[-2], "parent")
                self.assertIn("fork", command)
                self.assertIn("Return the robot to checkpoint C01:S01:F0.", command[-1])
                kwargs["stdout"].write(json.dumps(dict(type="thread.started", thread_id="branch")) + "\n")
                kwargs["stdout"].flush()
                return child

            def serve(env_arg, directory, frame, *, move_limit, on_ready, should_detach):
                self.assertIs(env_arg, env)
                self.assertEqual((frame, move_limit), (20, 180))
                directory.mkdir()
                on_ready(directory / "endpoint.json")
                robot = NS(phase="active", moves=179, ended=False, last_observation={"rgb": "last"})
                self.assertFalse(should_detach(robot))
                robot.moves = 180
                self.assertTrue(should_detach(robot))
                return robot

            with patch("core.codex_live_takeover.subprocess.Popen", side_effect=launch), \
                 patch("core.codex_live_takeover.CodexSession._stop") as stop, patch.object(bridge, "serve", side_effect=serve):
                _, ended, summary = takeover(env, root / "recovery", boundary, DEFAULTS)
            stop.assert_called_once_with(child)
            self.assertFalse(ended)
            self.assertEqual((summary["stop_reason"], summary["branch_thread"]), ("movement_budget", "branch"))
            self.assertFalse(summary["model_declared_success"])
            save(review / "codex/session.json", dict(turns=9, thread_id="parent"))
            with patch("core.codex_live_takeover.subprocess.Popen") as process:
                with self.assertRaises(ValueError):
                    takeover(env, root / "stale", boundary, DEFAULTS)
                process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
