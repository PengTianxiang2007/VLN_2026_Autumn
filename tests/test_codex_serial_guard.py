"""Failure injection for online request budgets, watchdogs and queue halt propagation."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
import uuid

from core.codex_client import CodexCallError, CodexConfig, CodexSession, save
from core.codex_serial_config import DEFAULTS
from core.codex_serial_guard import (BoundedSession, PipelineGuardError, RequestFailure,
                                    RecoveryWatchdog, bounded_request, cleanup_review_children,
                                    failure_kind, score_frame)
from core.codex_serial_runtime import ReviewWorker
from scripts import vlnverse_robot_bridge as bridge
from benchmarks.vlnverse.runner.run_full import check_serial_chunk


class FakeClock:
    def __init__(self):
        self.value = 0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class GuardTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)

    def test_transient_retry_is_bounded_and_permanent_error_stops_immediately(self):
        clock = FakeClock()
        call = Mock(side_effect=[RequestFailure("request_error"), RequestFailure("request_error"), "ok"])
        opts = dict(stage="jev", attempts=3, total_seconds=420, call_seconds=135,
                    log=self.folder / "retry.jsonl", clock=clock, sleep=clock.sleep)
        self.assertEqual(bounded_request(call, **opts), "ok")
        self.assertEqual((call.call_count, clock()), (3, 6))
        for kind, count in (("request_error", 3), ("permanent_error", 1)):
            call = Mock(side_effect=RequestFailure(kind))
            with self.assertRaises(PipelineGuardError) as caught:
                bounded_request(call, **opts)
            self.assertEqual(call.call_count, count)
            self.assertEqual(caught.exception.code, "retry_exhausted" if count == 3 else "permanent_error")

    def test_total_deadline_shortens_calls_and_rejects_late_results(self):
        clock = FakeClock()
        budgets = []

        def call(timeout):
            budgets.append(timeout)
            clock.sleep(timeout)
            raise RequestFailure("request_error")

        with self.assertRaises(PipelineGuardError) as caught:
            bounded_request(call, stage="codex", attempts=3, total_seconds=600, call_seconds=300,
                            log=self.folder / "retry.jsonl", clock=clock, sleep=clock.sleep)
        self.assertEqual(budgets, [300, 298])
        self.assertEqual(caught.exception.code, "total_timeout")

    def test_configured_ten_attempts_have_capped_backoff(self):
        self.assertEqual(DEFAULTS["request_attempts"], 10)
        clock = FakeClock()
        waits = []

        def sleep(seconds):
            waits.append(seconds)
            clock.sleep(seconds)

        operation = Mock(side_effect=RequestFailure("request_error"))
        with self.assertRaises(PipelineGuardError) as caught:
            bounded_request(operation, stage="jev", attempts=DEFAULTS["request_attempts"],
                total_seconds=DEFAULTS["jev_total_seconds"], call_seconds=135,
                log=self.folder / "ten.jsonl", clock=clock, sleep=sleep)
        self.assertEqual(operation.call_count, 10)
        self.assertEqual(caught.exception.code, "retry_exhausted")
        self.assertEqual(waits, [2, 4, 8, 16, 32, 60, 60, 60, 60])

    def test_jev_auth_error_is_not_retried_and_120_second_timeout_is_preserved(self):
        request = dict(output=str(self.folder), episode_id="live", frame=0, timeout=120)
        with patch("core.jev_request_runner.run_jev_task", return_value=dict(phase="failed", error="HTTP 401")) as api:
            with self.assertRaises(PipelineGuardError) as caught:
                score_frame(request, DEFAULTS)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(api.call_args.args[0]["timeout"], 120)
        self.assertEqual(caught.exception.code, "permanent_error")
        for message in ("HTTP 403", "401 Unauthorized", "insufficient_quota", "invalid api key"):
            self.assertEqual(failure_kind(message), "permanent_error")
        for message in ("HTTP 429", "HTTP 503", "transport timeout"):
            self.assertEqual(failure_kind(message), "request_error")

    def test_codex_auth_failure_stops_and_timeout_kills_its_actual_cli(self):
        session = BoundedSession(self.folder / "auth", CodexConfig(), policy=DEFAULTS)
        with patch.object(CodexSession, "ask", side_effect=CodexCallError("HTTP 401")) as call:
            with self.assertRaises(PipelineGuardError):
                session.ask_checked(lambda value: value, "p", [], {}, label="test")
        self.assertEqual(call.call_count, 1)

        cli = self.folder / "fake-codex"
        cli.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
        cli.chmod(0o700)
        session = BoundedSession(self.folder / "timeout", CodexConfig(binary=str(cli), timeout_seconds=0.1),
                                 policy=dict(DEFAULTS, request_attempts=1, codex_total_seconds=1))
        with self.assertRaises(PipelineGuardError):
            session.ask_checked(lambda value: value, "p", [], {}, label="test")
        process = json.loads(next((session.directory / "turns").glob("*/process.json")).read_text())
        self.assertFalse(Path(f'/proc/{process["pid"]}').exists())

    def test_partial_stdout_cannot_bypass_boundary_timeout(self):
        save(self.folder / "config.json", dict(boundary_timeout_seconds=0.15))
        real_popen = subprocess.Popen

        def launch(*args, **kwargs):
            return real_popen([sys.executable, "-u", "-c",
                              "import sys,time; sys.stdout.write('partial'); sys.stdout.flush(); time.sleep(30)"], **kwargs)

        with patch("core.codex_serial_runtime.subprocess.Popen", side_effect=launch):
            worker = ReviewWorker(self.folder)
        self.addCleanup(worker.close)
        with self.assertRaises(PipelineGuardError) as caught:
            worker.request(dict(episode_id="live", frame=0), lambda: None)
        self.assertEqual(caught.exception.code, "boundary_timeout")
        self.assertIsNotNone(worker.child.poll())

    def test_watchdog_ignores_heartbeat_and_repeated_observe(self):
        clock = FakeClock()
        robot = NS(completed_calls=0, moves=0)
        guard = RecoveryWatchdog(DEFAULTS, clock)
        clock.value = 300
        with self.assertRaises(PipelineGuardError) as caught:
            guard.check(robot)
        self.assertEqual(caught.exception.code, "tool_idle_timeout")

        clock.value = 0
        guard = RecoveryWatchdog(DEFAULTS, clock)
        for t in (100, 200, 300, 400, 500):
            clock.value = t
            robot.completed_calls += 1
            guard.check(robot)
        clock.value = 600
        with self.assertRaises(PipelineGuardError) as caught:
            guard.check(robot)
        self.assertEqual(caught.exception.code, "no_movement_timeout")

        clock.value = 0
        guard = RecoveryWatchdog(dict(DEFAULTS, recovery_total_seconds=30), clock)
        for t in (9, 18, 27):
            clock.value = t
            robot.moves += 1
            robot.completed_calls += 1
            guard.check(robot)
        clock.value = 30
        with self.assertRaises(PipelineGuardError) as caught:
            guard.check(robot)
        self.assertEqual(caught.exception.code, "total_timeout")

    def test_late_socket_request_is_rejected_before_any_movement(self):
        robot = NS(task=NS(data=dict(episode_id="live")), moves=0, call=Mock())
        client_thread = None

        def ready(endpoint):
            nonlocal client_thread
            address = json.loads(endpoint.read_text())["socket"]

            def client():
                with socket.socket(socket.AF_UNIX) as sock:
                    sock.settimeout(2)
                    sock.connect(address)
                    sock.sendall(json.dumps(dict(id=str(uuid.uuid4()), method="step", action="forward")).encode()+b"\n")
                    try:
                        sock.recv(1024)
                    except (ConnectionResetError, socket.timeout):
                        pass

            client_thread = threading.Thread(target=client)
            client_thread.start()

        guard = Mock(side_effect=[False, PipelineGuardError("codex_recovery", "tool_idle_timeout")])
        with patch.object(bridge, "RobotTools", return_value=robot):
            with self.assertRaises(PipelineGuardError):
                bridge.serve(None, self.folder / "live", 0, on_ready=ready, should_detach=guard)
        client_thread.join(timeout=3)
        self.assertFalse(client_thread.is_alive())
        robot.call.assert_not_called()
        self.assertEqual(json.loads((self.folder / "live/endpoint.json").read_text())["status"], "detached")

    def test_halted_queue_cannot_silently_retry_even_after_some_completed_episodes(self):
        settings = dict(output_dir=str(self.folder))
        check_serial_chunk(settings, 0, 1, 0)
        with self.assertRaises(RuntimeError):
            check_serial_chunk(settings, 0, 0, 0)
        with self.assertRaises(RuntimeError):
            check_serial_chunk(settings, 1, 1, 0)
        save(self.folder / "halt.json", dict(scored=False))
        with self.assertRaises(RuntimeError):
            check_serial_chunk(settings, 0, 1, 0)
        check_serial_chunk(None, 1, 0, 0)  # Legacy launcher policy unchanged.

    def test_cleanup_never_kills_a_reused_or_unverified_pid(self):
        directory = self.folder / "review/codex/turns/turn_0001"
        directory.mkdir(parents=True)
        save(directory / "process.json", dict(pid=1234, start_ticks=100))
        with patch("core.codex_serial_guard.process_start_ticks", return_value=101), \
             patch("core.codex_serial_guard.os.killpg") as kill:
            cleanup_review_children(self.folder)
        kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
