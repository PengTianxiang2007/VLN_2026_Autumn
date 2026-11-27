"""Bounded, fail-closed requests for online navigation only."""
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import signal
import time

from core.codex_client import CodexCallError, CodexSession, now, process_start_ticks


class PipelineGuardError(RuntimeError):
    def __init__(self, stage, code, attempts=0):
        self.stage, self.code, self.attempts = stage, code, attempts
        super().__init__(f"{stage}: {code} (attempts={attempts})")

    def record(self):
        return dict(stage=self.stage, code=self.code, attempts=self.attempts)


class RequestFailure(Exception):
    def __init__(self, kind):
        self.kind = kind
        super().__init__(kind)


def failure_kind(message):
    """Classify provider errors; never turn transport errors into semantic verdicts."""
    value = str(message).lower()
    if (re.search(r"\b(?:http|status(?: code)?)\D{0,8}(?:400|401|402|403|404|405|422)\b", value)
            or any(word in value for word in (
                "unauthorized", "authentication", "forbidden", "invalid api key", "api_key is missing",
                "insufficient_quota", "quota exceeded", "billing", "permission denied",
                "not logged in", "model not found", "unsupported model", "invalid model",
                "session changed", "session is unavailable", "thread not found"))):
        return "permanent_error"
    return "request_error"


def bounded_request(operation, *, stage, attempts, total_seconds, call_seconds, log,
                    clock=time.monotonic, sleep=time.sleep):
    start = clock()
    deadline = start + total_seconds
    for attempt in range(1, attempts + 1):
        remaining = deadline - clock()
        if remaining <= 0:
            raise PipelineGuardError(stage, "total_timeout", attempt - 1)
        try:
            result = operation(min(call_seconds, remaining))
            if clock() >= deadline:
                raise PipelineGuardError(stage, "total_timeout", attempt)
        except RequestFailure as error:
            kind = error.kind
            with log.open("a") as stream:
                stream.write(json.dumps(dict(time=now(), stage=stage, attempt=attempt,
                    error=kind, elapsed_seconds=clock() - start)) + "\n")
            if kind == "permanent_error":
                raise PipelineGuardError(stage, kind, attempt) from error
            if attempt == attempts:
                raise PipelineGuardError(stage, "retry_exhausted", attempt) from error
            remaining = deadline - clock()
            if remaining <= 0:
                raise PipelineGuardError(stage, "total_timeout", attempt) from error
            sleep(min(2 ** attempt, 60, remaining))
        else:
            with log.open("a") as stream:
                stream.write(json.dumps(dict(time=now(), stage=stage, attempt=attempt,
                    status="complete", elapsed_seconds=clock() - start)) + "\n")
            return result
    raise ValueError("At least one request attempt is required")


def score_frame(request, policy):
    from core.jev_request_runner import run_jev_task
    folder = Path(request["output"]) / "cases" / request["episode_id"] / f'F{request["frame"]:06d}'
    folder.mkdir(parents=True, exist_ok=True)

    def call(timeout):
        # curl's Python wrapper allows 15 seconds for process cleanup.
        if timeout <= 15:
            raise PipelineGuardError("jev", "total_timeout")
        answer = run_jev_task(dict(request, timeout=min(request["timeout"], timeout - 15), attempts=1))
        if answer["phase"] != "complete":
            raise RequestFailure(failure_kind(answer.get("error", "")))
        return answer

    return bounded_request(call, stage="jev", attempts=policy["request_attempts"],
        total_seconds=policy["jev_total_seconds"], call_seconds=policy["jev_timeout_seconds"] + 15,
        log=folder / "guard_requests.jsonl")


class BoundedSession(CodexSession):
    def __init__(self, directory, config, *, policy):
        super().__init__(directory, config)
        self.policy = policy

    def ask_checked(self, validate, *args, **kwargs):
        original = self.config

        def call(timeout):
            self.config = replace(original, timeout_seconds=timeout)
            self.failed = False
            try:
                response = super(BoundedSession, self).ask(*args, **kwargs)
            except CodexCallError as error:
                # CLI errors often carry the useful provider status only in stderr/events.
                detail = str(error)
                for path in self.directory.glob(f"turns/turn_{self.turn_count:04d}_*/*"):
                    if path.name in ("stderr.log", "events.jsonl"):
                        with path.open("rb") as stream:
                            stream.seek(max(0, path.stat().st_size - 65536))
                            detail += stream.read().decode(errors="replace")
                raise RequestFailure(failure_kind(detail)) from error
            finally:
                self.config = original
            try:
                answer = validate(json.loads(response["text"]))
            except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
                (Path(response["directory"]) / "invalid_answer.json").write_text(json.dumps(type(error).__name__))
                raise RequestFailure("invalid_answer") from error
            return response, answer

        return bounded_request(call, stage="codex_review", attempts=self.policy["request_attempts"],
            total_seconds=self.policy["codex_total_seconds"], call_seconds=original.timeout_seconds,
            log=self.directory / "guard_requests.jsonl")


class RecoveryWatchdog:
    """Only successful tool calls/movements advance progress; stdout and heartbeats do not."""
    def __init__(self, policy, clock=time.monotonic):
        self.policy, self.clock = policy, clock
        self.started = self.last_call = self.last_move = clock()
        self.sequence = self.moves = 0

    def check(self, robot):
        current = self.clock()
        # Test deadlines before accepting a newly arrived call as progress.
        if current - self.started >= self.policy["recovery_total_seconds"]:
            raise PipelineGuardError("codex_recovery", "total_timeout")
        if current - self.last_call >= self.policy["recovery_idle_seconds"]:
            raise PipelineGuardError("codex_recovery", "tool_idle_timeout")
        if current - self.last_move >= self.policy["recovery_no_move_seconds"]:
            raise PipelineGuardError("codex_recovery", "no_movement_timeout")
        # Audit only successfully completed observations/actions, never failed requests.
        sequence = getattr(robot, "completed_calls", getattr(robot, "sequence", 0))
        if sequence != self.sequence:
            self.sequence, self.last_call = sequence, current
        if robot.moves != self.moves:
            self.moves, self.last_move = robot.moves, current


def cleanup_review_children(folder):
    """Fallback after worker termination, for CLI groups that use separate sessions.

    Only kill recorded leaders whose PID, birth tick, PGID and SID still match.
    Do not guess ownership from executable names or stale PIDs.
    """
    alive = []
    for path in (folder / "review/codex/turns").glob("*/process.json"):
        record = json.loads(path.read_text())
        pid, birth = record["pid"], record.get("start_ticks")
        try:
            if (birth is not None and process_start_ticks(pid) == birth
                    and os.getpgid(pid) == pid and os.getsid(pid) == pid):
                os.killpg(pid, signal.SIGTERM)
                alive.append((pid, birth))
        except (OSError, ValueError):
            continue
    if alive:
        time.sleep(0.2)
    for pid, birth in alive:
        try:
            if process_start_ticks(pid) == birth and os.getpgid(pid) == pid and os.getsid(pid) == pid:
                os.killpg(pid, signal.SIGKILL)
        except (OSError, ValueError):
            pass
