"""Serial adapter for the existing JEV → checkpoint → same-thread deviation review."""
from collections import deque
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from core.codex_client import CodexConfig, now, sha256
from core.codex_serial_config import ROOT
from core.codex_checkpoint_review import DIRECTIONAL_REVISION, MODE, run_case
from core.codex_deviation_review import FrameGapSampler, TERMINAL_VERSION
from scripts.run_codex_shadow import endpoint_node
from core.codex_serial_guard import BoundedSession, PipelineGuardError, score_frame

def append(path, value):
    with path.open("a") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


class ActiveSampler:
    def __init__(self):
        env = {k: v for k, v in os.environ.items() if k != "JEV_API_KEY"}
        node = env.get("VLN_NODE_BINARY") or shutil.which("node")
        if not node:
            raise PipelineGuardError("jev_sampler", "node_not_found")
        try:
            self.child = subprocess.Popen([node, str(ROOT / "scripts/jev_sampler_stdio.cjs")],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
        except OSError as error:
            raise PipelineGuardError("jev_sampler", "node_unavailable") from error
        self.send(dict(reset=True, version="v002", mode="active"))

    def send(self, request):
        self.child.stdin.write(json.dumps(request) + "\n")
        self.child.stdin.flush()
        line = self.child.stdout.readline()
        if not line:
            raise RuntimeError("JEV sampler exited")
        result = json.loads(line)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result

    def close(self):
        self.child.stdin.close()
        try:
            self.child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.child.kill()
            self.child.wait()
        self.child.stdout.close()


def review_stream(folder, config, receive, reply, *, scorer=None, sampler_factory=ActiveSampler):
    """One request stays outstanding until every review it caused has completed.

    Yielding a candidate transfers control to run_case. Its next generator read
    acknowledges the previous boundary; a deviation breaks that loop instead.
    """
    if scorer is None:
        scorer = lambda request: score_frame(request, config)
    start = json.loads((folder / "start.json").read_text())
    episode = start["episode_id"]
    case = dict(case_number=1, episode_id=episode, nodes=[], mode=MODE,
                instruction_en=start["instruction"], prompt_revision=DIRECTIONAL_REVISION,
                observation_offsets=[-2, 0, 2], deviation_review=TERMINAL_VERSION, max_frame_gap=6)
    fronts, history = {}, deque(maxlen=3)
    gap = FrameGapSampler(folder, episode, 6, live_fronts=fronts)
    pending = None
    sampler = sampler_factory()

    def respond(decision, **fields):
        row = dict(episode_id=episode, frame=pending["frame"], decision=decision,
                   completed_at=now(), **fields)
        append(folder / "boundary_decisions.jsonl", row)
        reply(row)

    def candidates():
        nonlocal pending
        while True:
            pending = receive()
            if pending is None:
                raise EOFError("Live navigation closed without a pending STOP review")
            f = pending["frame"]
            if pending["episode_id"] != episode or f != len(fronts):
                raise ValueError("Stale or nonconsecutive live boundary")
            front = pending["native_front"]
            image = (folder / front["image"]).resolve()
            if not image.is_relative_to(folder.resolve()) or sha256(image) != front["sha256"]:
                raise ValueError("Live RGB path/hash mismatch")
            fronts[f] = front
            if pending["stop_requested"]:
                case["terminal_node"] = dict(endpoint_node(1, "END", f, f, fronts, (0,)),
                                             terminal_node=True, stop_requested=True)
                return  # run_case must finish the terminal review before replying.
            history.append(dict(frame=f, rgb=front["image"], rgb_sha256=front["sha256"]))
            request = dict(episode_id=episode, scene=start["scene"], group="codex_serial",
                           frame=f, images=list(history), question_version="v004", dataset=str(folder),
                           output=str(folder / "jev"), model="jev-1.14.0", attempts=1, timeout=config["jev_timeout_seconds"],
                           endpoint=config["jev_endpoint"])
            before = time.monotonic()
            answer = scorer(request)
            append(folder / "jev_calls.jsonl", dict(answer, wall_seconds=time.monotonic() - before))
            raw = sampler.send(dict(value=answer["answer"]["probability_yes"], frame=f)).get("node")
            if raw:
                point = endpoint_node(1, raw["id"], raw["index"], f, fronts, (-2, 0, 2))
                point.update(sampling=raw, published_at=now())
                append(folder / "candidates.jsonl", point)
                yield point
            respond("continue")

    try:
        cfg = CodexConfig(**{k: config[k] for k in
                            ("model", "reasoning_effort", "proxy_url", "timeout_seconds")})
        with redirect_stdout(sys.stderr):
            result = run_case(case, folder, folder / "review", cfg,
                              candidate_stream=candidates(), live_sampler=gap,
                              session_factory=lambda directory, cfg: BoundedSession(directory, cfg, policy=config))
        if result["rollback_target"]:
            last = result["deviation_reviews"][-1]
            respond("deviated", thread_id=result["thread_id"], review_turn=last["turn"],
                    rollback_target=result["rollback_target"], effective_nodes=result["effective_nodes"],
                    review_directory=str(folder / "review"))
        elif pending["stop_requested"] and result["terminal_reviewed"]:
            respond("stop", thread_id=result["thread_id"], stop_reason=result["stop_reason"])
        else:
            raise RuntimeError("Reviewer ended without a deviation or a completed STOP review")
        return result
    finally:
        sampler.close()
