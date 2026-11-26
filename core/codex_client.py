"""Logged-in Codex CLI transport: one explicitly named session per task.

No direct API client, shell=True, implicit retries, or resume --last. Native
sessions stay in the user's CODEX_HOME; task-local evidence is archived here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_ready(answer):
    if answer != {"ready": True}:
        raise ValueError("Missing ready acknowledgement")
    return answer


@dataclass(frozen=True)
class CodexConfig:
    binary: str = "/mnt/nas/gezuhao/PengTianxiang/codex-bin/codex"
    home: str = "/mnt/nas/gezuhao/PengTianxiang/.codex"
    model: str = "gpt-6-astra"
    reasoning_effort: str = "medium"
    timeout_seconds: float = 600
    proxy_url: str | None = None
    service_tier: str | None = None


class CodexCallError(RuntimeError):
    """Transport/incomplete-turn failure; must not become a dedup verdict."""


class CodexSession:
    def ask_checked(self, validate, *args, **kwargs):
        response = self.ask(*args, **kwargs)
        return response, validate(json.loads(response["text"]))

    def __init__(self, directory: Path, config: CodexConfig, *, thread_id=None, turn_count=0):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=False)
        self.config = config
        self.thread_id = thread_id
        self.turn_count = turn_count
        self.failed = False
        self._save_session("created")

    def _save_session(self, status):
        save(self.directory / "session.json", dict(
            thread_id=self.thread_id, turns=self.turn_count, status=status,
            updated_at=now(), config=asdict(self.config),
        ))

    def _command(self, folder, images):
        command = [self.config.binary, "exec"]
        if self.thread_id:
            command += ["resume", self.thread_id]
        command += ["--ignore-user-config", "--skip-git-repo-check", "--json",
                    "--model", self.config.model,
                    "--output-schema", str(folder / "schema.json"),
                    "--output-last-message", str(folder / "final.txt")]
        if self.config.service_tier:
            command += ["-c", "service_tier=" + json.dumps(self.config.service_tier)]
        for key, value in {
            "model_reasoning_effort": self.config.reasoning_effort,
            "sandbox_mode": "read-only", "approval_policy": "never",
            "web_search": "disabled", "project_doc_max_bytes": 0,
        }.items():
            command += ["-c", key + "=" + json.dumps(value)]
        # This interface consumes attached observations and returns JSON only.
        for feature in ("shell_tool", "unified_exec", "shell_snapshot", "apps",
                        "plugins", "hooks", "multi_agent", "image_generation",
                        "view_image", "sleep_tool", "skill_search", "code_mode_host"):
            command += ["--disable", feature]
        for path in images:
            command += ["--image", str(path)]
        return command + ["-"]

    @staticmethod
    def _stop(child):
        if child.poll() is not None:
            return
        # start_new_session gives this invocation its own process group.
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()

    def ask(self, prompt: str, images: list[Path], schema: dict, *, label: str,
            metadata: dict | None = None):
        if self.failed:
            raise CodexCallError("Session has a failed turn; create a new run instead of silently retrying")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
            raise ValueError("Invalid turn label")
        self.turn_count += 1
        folder = self.directory / "turns" / f"turn_{self.turn_count:04d}_{label}"
        folder.mkdir(parents=True, exist_ok=False)
        attachments = folder / "images"
        attachments.mkdir()
        image_records = []
        for number, source in enumerate(images, 1):
            data = source.read_bytes()
            target = attachments / f"{number:02d}{source.suffix.lower()}"
            target.write_bytes(data)
            image_records.append(dict(number=number, source=str(source), path=str(target),
                                      sha256=hashlib.sha256(data).hexdigest()))
        (folder / "prompt.txt").write_text(prompt, encoding="utf-8")
        save(folder / "schema.json", schema)
        expected_thread = self.thread_id
        command = self._command(folder, [Path(x["path"]) for x in image_records])
        request = dict(started_at=now(), resumed_thread_id=expected_thread,
                       command=command, cwd=str(self.directory), images=image_records,
                       metadata=metadata or {}, prompt_sha256=sha256(folder / "prompt.txt"))
        save(folder / "request.json", request)
        self._save_session("running")
        env = os.environ.copy()
        env["CODEX_HOME"] = self.config.home
        if self.config.proxy_url:
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
                env[key] = self.config.proxy_url
        # Authentication comes from the supplied home, not an inherited API key.
        for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY"):
            env.pop(key, None)
        start = time.monotonic()
        child = None
        failure = None
        try:
            with (folder / "events.jsonl").open("w") as stdout, (folder / "stderr.log").open("w") as stderr:
                child = subprocess.Popen(command, cwd=self.directory, env=env,
                                         stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                         text=True, encoding="utf-8", start_new_session=True)
                save(folder / "process.json", dict(pid=child.pid, started_at=now()))
                child.communicate(prompt, timeout=self.config.timeout_seconds)
        except BaseException as error:
            failure = error
        finally:
            if child is not None:
                self._stop(child)

        events = []
        for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
                if isinstance(event, dict):
                    events.append(event)
            except ValueError:
                pass  # Keep the original line in events.jsonl for diagnosis.
        threads = [e["thread_id"] for e in events if e.get("type") == "thread.started"]
        if threads and not expected_thread:
            self.thread_id = threads[0]
        completed = [e for e in events if e.get("type") == "turn.completed"]
        errors = [e for e in events if e.get("type") == "turn.failed" or
                  (e.get("type") == "error" and not e.get("message", "").startswith("Reconnecting..."))]
        final_path = folder / "final.txt"
        raw = final_path.read_text(encoding="utf-8") if final_path.exists() else ""
        if failure is None:
            if child.returncode != 0:
                failure = CodexCallError(f"Codex exited with code {child.returncode}")
            elif not self.thread_id or any(t != self.thread_id for t in threads):
                failure = CodexCallError("Missing or mismatched Codex thread ID")
            elif errors or not completed or not raw.strip():
                failure = CodexCallError("Codex did not complete a valid response turn")
        result = dict(thread_id=self.thread_id, resumed_thread_id=expected_thread,
                      turn=self.turn_count, directory=str(folder), completed_at=now(),
                      elapsed_seconds=round(time.monotonic() - start, 3),
                      returncode=child.returncode if child else None,
                      usage=completed[-1].get("usage", {}) if completed else {},
                      status="error" if failure else "ok")
        if failure:
            result["error"] = f"{type(failure).__name__}: {failure}"
        save(folder / "response.json", result)
        self.failed = failure is not None
        self._save_session(result["status"])
        if failure:
            if isinstance(failure, (KeyboardInterrupt, SystemExit)):
                raise failure
            raise CodexCallError(f"{result['error']}; logs: {folder}") from failure
        return dict(result, text=raw)
