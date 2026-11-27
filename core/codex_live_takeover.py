"""Fork the completed live deviation thread; serve H1 actions on the Isaac thread."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from core.codex_client import CodexSession, now, save, sha256
from core.codex_serial_config import PROMPT, ROOT
from core.codex_serial_guard import PipelineGuardError, RecoveryWatchdog


def clean_child_env():
    env = dict(os.environ)
    # Resolve the sampler runtime before removing Isaac's PATH entries. Node may
    # be provided by the server outside /usr/bin (e.g. DSW's export_bin).
    node = env.get("VLN_NODE_BINARY") or shutil.which("node", path=env.get("PATH", ""))
    if node:
        env["VLN_NODE_BINARY"] = str(Path(node).absolute())
    for key in ("LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "VIRTUAL_ENV",
                "OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY"):
        env.pop(key, None)
    # Do not inherit Isaac's environment through PATH either.
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    return env


def takeover(env, folder, boundary, config, heartbeat=lambda: None):
    from scripts.vlnverse_robot_bridge import serve

    folder.mkdir()
    review = Path(boundary["review_directory"])
    result = json.loads((review / "result.json").read_text())
    session = json.loads((review / "codex/session.json").read_text())
    last = result["deviation_reviews"][-1]
    if (last["answer"]["verdict"] != "deviated" or last["turn"] != boundary["review_turn"]
            or session["turns"] != last["turn"] or session["thread_id"] != boundary["thread_id"]
            or result["rollback_target"] != boundary["rollback_target"]
            or boundary["rollback_target"] not in {n["candidate_id"] for n in result["effective_nodes"]}):
        raise ValueError("Takeover must fork the final deviation turn and a retained checkpoint")
    task, = env.env.runner.current_tasks.values()
    if task.data["episode_id"] != boundary["episode_id"]:
        raise RuntimeError("Episode changed before takeover")
    prompt = PROMPT.read_text().replace("{checkpoint}", boundary["rollback_target"])
    (folder / "prompt.txt").write_text(prompt)
    child = None
    reason = None
    started = time.monotonic()
    watchdog = RecoveryWatchdog(config)
    command = ["bash", str(ROOT / "scripts/codex_vlnverse_robot.sh"), "exec",
               "--sandbox", "read-only", "--disable", "shell_tool", "--disable", "unified_exec",
               "--enable", "code_mode_host", "-c", "project_doc_max_bytes=0",
               "-c", "model_reasoning_effort=" + json.dumps(config["reasoning_effort"]),
               "fork", "--json", "-o", str(folder / "final.txt"), boundary["thread_id"], prompt]
    with (folder / "events.jsonl").open("x") as events, (folder / "stderr.log").open("x") as errors:
        def launch(endpoint):
            nonlocal child
            child_env = clean_child_env()
            child_env.update(VLNVERSE_ROBOT_ENDPOINT=str(endpoint), VLNVERSE_CODEX_MODEL=config["model"])
            # Keep the source session's cwd. No worktree/session lookup or replay.
            child = subprocess.Popen(command, cwd=review / "codex", env=child_env,
                                     stdin=subprocess.DEVNULL, stdout=events, stderr=errors,
                                     start_new_session=True)
            save(folder / "launch.json", dict(utc=now(), pid=child.pid, parent_thread=boundary["thread_id"],
                 parent_turn=boundary["review_turn"], source_session_sha256=sha256(review / "codex/session.json"),
                 endpoint=str(endpoint), movement_budget=config["movement_budget"], command=command))

        def done(robot):
            nonlocal reason
            heartbeat()
            if robot.phase == "return_declared":
                reason = "model_declared_complete"
            elif robot.ended:
                reason = "physical_terminal"
            elif robot.phase != "active":
                raise RuntimeError("Live robot action failed: " + robot.phase)
            elif robot.moves >= config["movement_budget"]:
                reason = "movement_budget"
            else:
                watchdog.check(robot)
                if child.poll() is not None:
                    if child.returncode != 0:
                        raise PipelineGuardError("codex_recovery", "controller_failed")
                    if getattr(robot, "completed_calls", 0) == 0:
                        raise PipelineGuardError("codex_recovery", "no_successful_tool_calls")
                    reason = "model_ended_without_declaration"
            return reason is not None

        try:
            robot = serve(env, folder / "live", boundary["frame"], move_limit=config["movement_budget"],
                          on_ready=launch, should_detach=done)
        except PipelineGuardError as error:
            save(folder / "failure.json", dict(error.record(), time=now(), scored=False,
                 elapsed_seconds=time.monotonic() - started))
            raise
        finally:
            if child is not None:
                CodexSession._stop(child)
    threads = []
    for line in (folder / "events.jsonl").read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "thread.started":
            threads.append(event["thread_id"])
    summary = dict(stop_reason=reason, movements=robot.moves,
                   model_declared_success=robot.phase == "return_declared",
                   parent_thread=boundary["thread_id"], branch_thread=threads[-1] if threads else None,
                   elapsed_seconds=time.monotonic() - started, completed_at=now())
    save(folder / "result.json", summary)
    return robot.last_observation, robot.ended, summary
