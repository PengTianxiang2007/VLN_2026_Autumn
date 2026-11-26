"""First-stage dedup of existing raw candidates, using Codex as a JSON judge."""
from __future__ import annotations

from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import re

from core.codex_client import CodexConfig, CodexSession, now, save, sha256

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/node_deduplication/v001_run02_all"


@lru_cache(maxsize=1)
def protocol():
    # Reuse the frozen validator and state transition, never its API functions.
    spec = importlib.util.spec_from_file_location("codex_frozen_dedup", PROTOCOL / "run_dedup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def output_schema():
    string = {"type": "string"}
    strings = {"type": "array", "items": string}
    match = {"type": "object", "additionalProperties": False,
             "required": ["description", "a_frames", "b_frames"],
             "properties": {"description": string, "a_frames": strings, "b_frames": strings}}
    properties = dict(previous_id=string, current_id=string,
                      relation={"type": "string", "enum": ["same", "different", "uncertain"]},
                      matched_branches={"type": "array", "items": match},
                      a_only=strings, b_only=strings, reason=string)
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


def prepare_candidates(case, candidates):
    """Adapt the existing dataset frames + JEV candidates, without resampling."""
    nodes = []
    frames = case["frames"]
    for candidate in candidates:
        t, ready = candidate["index"], candidate["emittedAt"]
        if ready != t + 5 or ready >= len(frames) - 1:
            raise ValueError("Unexpected raw candidate availability")
        images = []
        for offset in range(-2, 3):
            frame = t + offset
            entry = dict(frame=frame, label="F0" if offset == 0 else f"F{offset:+d}")
            if frame < 0:
                entry["missing"] = True
            else:
                entry.update(path=frames[frame]["path"], image_id=frames[frame]["image"])
            images.append(entry)
        nodes.append(dict(id=candidate["id"], index=t, emittedAt=ready, ready_at_frame=ready,
                          candidate_id=f"C{case['case_number']:02d}:{candidate['id']}:F{t}", images=images))
    return nodes


def comparison_prompt(offsets):
    if tuple(offsets) not in ((-2, -1, 0, 1, 2), (-2, 0, 2)):
        raise ValueError("Unsupported observation offsets")
    prompt = (PROTOCOL / "prompt_zh.txt").read_text(encoding="utf-8")
    if tuple(offsets) == (-2, 0, 2):
        prompt = prompt.replace("A-2、A-1、A0、A+1、A+2，以及 B-2、B-1、B0、B+1、B+2", "A-2、A0、A+2，以及 B-2、B0、B+2")
        prompt = prompt.replace("标签如 A0、A+1、B-1", "标签如 A0、A+2、B-2")
    return prompt


def comparison_input(a, b, image_root, offsets=(-2, -1, 0, 1, 2)):
    lines = ["本轮只执行图像去重判断，不调用工具，不访问文件或网络。",
             "会话历史仅用于保留交互记录；本轮分支证据仅限下面重新提供的 A/B 图像，不能从更早轮次补充。",
             comparison_prompt(offsets),
             f"A 完整编号：{a['candidate_id']}，动作步 {a['index']}。",
             f"B 完整编号：{b['candidate_id']}，动作步 {b['index']}。",
             f"步数差：{b['index'] - a['index']}。附件图片严格按下面编号顺序提供："]
    images, mapping = [], []
    root = image_root.resolve()
    for group, node in (("A", a), ("B", b)):
        for offset, im in zip(offsets, protocol().evidence(node, group), strict=True):
            expected_label = group + ("0" if offset == 0 else f"{offset:+d}")
            if im["frame"] != node["index"] + offset or im["label"] != expected_label:
                raise ValueError("Invalid observation window")
            caption = f"{im['label']}：实际动作步 {im['frame']}"
            if im.get("missing"):
                if im["frame"] >= 0:
                    raise ValueError("Only pre-start observations may be missing")
                lines.append(caption + "，缺失（轨迹尚未开始，无附件）。")
                mapping.append(dict(label=im["label"], frame=im["frame"], missing=True))
                continue
            if im["frame"] < 0 or im["frame"] > node["ready_at_frame"]:
                raise ValueError("Unavailable/future image")
            path = (root / im["path"]).resolve()
            if not path.is_relative_to(root) or sha256(path) != im["image_id"]:
                raise ValueError("Image path or hash mismatch")
            images.append(path)
            lines.append(f"附件 {len(images):02d} = {caption}。")
            mapping.append(dict(number=len(images), label=im["label"], frame=im["frame"],
                                image_id=im["image_id"]))
    return "\n".join(lines), images, dict(previous_id=a["candidate_id"],
                                       current_id=b["candidate_id"], image_labels=mapping)


def run_case(case: dict, image_root: Path, directory: Path, config: CodexConfig):
    """One case -> one fresh thread; subsequent comparisons explicitly resume it."""
    nodes = case["nodes"]  # Legacy manifest name; these are raw candidates.
    offsets = tuple(case.get("observation_offsets", (-2, -1, 0, 1, 2)))
    comparison_prompt(offsets)
    seen, previous_frame = set(), -1
    for node in nodes:
        if (not re.fullmatch(r"[A-Za-z0-9_-]+", node["id"]) or node["id"] in seen
                or node["index"] <= previous_frame):
            raise ValueError("Candidate IDs must be unique and frames strictly increasing")
        seen.add(node["id"])
        previous_frame = node["index"]
    directory.mkdir(parents=True, exist_ok=False)
    save(directory / "input.json", case)
    session = CodexSession(directory / "codex", config)
    active, decisions = [], []
    state = dict(started_at=now(), status="running", processed=0, active_ids=[])
    save(directory / "state.json", state)
    try:
        for b in nodes:
            a = active[-1] if active else None
            gap = b["index"] - a["index"] if a else None
            needs = a is not None and gap <= 8
            decision = dict(order=len(decisions) + 1, previous_id=a["id"] if a else None,
                            current_id=b["id"], previous_frame=a["index"] if a else None,
                            current_frame=b["index"], step_gap=gap, needs_model=needs,
                            active_ids_before=[n["id"] for n in active])
            if needs:
                prompt, images, metadata = comparison_input(a, b, image_root, offsets)
                response = session.ask(prompt, images, output_schema(),
                                       label=f"{a['id']}_{b['id']}", metadata=metadata)
                decision.update(thread_id=response["thread_id"], turn=response["turn"],
                                response_directory=response["directory"], usage=response["usage"])
                try:
                    raw = json.loads(response["text"])
                    answer = protocol().validate(raw, a, b)
                    decision.update(status="ok", answer=answer, relation=answer["relation"],
                                    reason=answer["reason"], normalized_references=raw != answer)
                except (ValueError, TypeError, KeyError) as error:
                    decision.update(status="format_error", relation="uncertain",
                                    reason="回答校验失败，保留两个候选。", error=str(error))
                save(Path(response["directory"]) / "decision.json", decision)
            else:
                decision.update(status="not_compared", relation="not_compared",
                                reason="首个候选，直接保留。" if a is None else f"间隔 {gap} 步，超过 8 步，直接保留。")
            protocol().apply_decision(active, b, decision["relation"])
            decision.update(action="replace_previous" if decision["relation"] == "same" else "append_current",
                            active_ids_after=[n["id"] for n in active], committed_at=now())
            decisions.append(decision)
            with (directory / "decisions.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(decision, ensure_ascii=False) + "\n")
            state.update(processed=len(decisions), active_ids=decision["active_ids_after"])
            save(directory / "state.json", state)
            print(json.dumps(dict(case=case["case_number"], candidate=b["id"],
                                  relation=decision["relation"], status=decision["status"],
                                  retained=len(active)), ensure_ascii=False), flush=True)
    except BaseException as error:
        save(directory / "state.json", dict(state, status="error", error=f"{type(error).__name__}: {error}",
                                             updated_at=now()))
        raise
    summary = dict(candidates=len(nodes), retained=len(active), removed=len(nodes) - len(active),
                   model_calls=sum(d["needs_model"] for d in decisions),
                   uncertain=sum(d["relation"] == "uncertain" for d in decisions),
                   format_errors=sum(d["status"] == "format_error" for d in decisions))
    result = dict(case, decisions=decisions, final_active_ids=[n["id"] for n in active],
                  effective_nodes=active, summary=summary, thread_id=session.thread_id)
    save(directory / "result.json", result)
    save(directory / "state.json", dict(state, status="complete", completed_at=now(), summary=summary))
    return result
