"""Review candidate eligibility and novelty using images in one Codex thread."""
import copy
import json
from pathlib import Path
import re

from core.codex_client import CodexSession, now, require_ready, save, sha256
from core.codex_node_dedup import output_schema, protocol

CORE = Path(__file__).resolve().parent
MODE = "checkpoint_memory_v003"
PROMPTS = [CORE / "codex_checkpoint_initialization_en.txt", CORE / "codex_checkpoint_candidate_en.txt"]


BINARY_REVISION = "local_route_choice_v006"
BINARY_PROMPT = CORE / "codex_checkpoint_candidate_binary_en.txt"

DIRECTIONAL_REVISION = "local_route_choice_v006_1"
DIRECTIONAL_PROMPT = CORE / "codex_checkpoint_candidate_v006_1_en.txt"
BINARY_TEMPLATES = {BINARY_REVISION: BINARY_PROMPT, DIRECTIONAL_REVISION: DIRECTIONAL_PROMPT}


def review_schema(binary=False):
    schema = output_schema()
    properties = schema["properties"]
    properties["previous_id"] = {"type": ["string", "null"]}
    properties["relation"]["enum"].append("not_compared")
    properties["eligibility"] = {"type": "string", "enum": ["eligible", "not_eligible", "uncertain"]}
    if binary:
        properties["eligibility"]["enum"] = ["eligible", "not_eligible"]
        properties["relation"]["enum"] = ["same", "different", "not_compared"]
    properties["eligibility_reason"] = {"type": "string"}
    schema["required"] = list(properties)
    return schema


def candidate_input(previous, current, image_root, offsets, binary=False, template=None):
    previous_id = previous["candidate_id"] if previous else None
    template = template or (BINARY_PROMPT if binary else PROMPTS[1])
    lines = [template.read_text().format(candidate_id=current["candidate_id"],
             previous_checkpoint_id=previous_id or "NONE (no retained checkpoint yet)")]
    if previous is None:
        lines.append("There is no retained checkpoint yet. Assess eligibility and use relation not_compared.")
    else:
        lines.append(f"The application specifies {previous_id} as the previous retained checkpoint. "
                     "Use that identifier even when other candidates appeared in intervening turns. "
                     "Its images are in the conversation history.")
    lines.append(f"Current candidate ID is {current['candidate_id']}, at action step {current['index']}.")
    contract = ("Return the JSON object required by the output schema. Use English for all natural-language fields. "
                 "Set eligibility to eligible, not_eligible, or uncertain. Explain the available branches in eligibility_reason. "
                 "Use relation not_compared only when there is no previous checkpoint or eligibility is not_eligible. "
                 "For both eligible and uncertain candidates with a previous checkpoint, use same, different, or uncertain. "
                 "For same, list corresponding branches in matched_branches and leave a_only and b_only empty. "
                 "For not_compared, leave matched_branches and a_only empty, and describe current branches in b_only. "
                 "Set previous_id to the specified full ID (or null) and current_id to the current full ID. "
                 "In matched_branches, A refers to the specified historical checkpoint and B to the current candidate. "
                 "Reference their images using A-2, A0, A+2 and B-2, B0, B+2 respectively. "
                 "For same, the application replaces the previous checkpoint with the current candidate as the next reference. "
                 "It excludes not_eligible candidates and keeps both observations if their relation is uncertain.")
    if binary:
        contract = contract.replace("eligible, not_eligible, or uncertain", "eligible or not_eligible").replace(
            "For both eligible and uncertain candidates with a previous checkpoint, use same, different, or uncertain.",
            "For an eligible candidate with a previous checkpoint, choose same or different."
        ).replace(" and keeps both observations if their relation is uncertain", "")
    lines.append(contract)
    images, mapping = [], []
    root = image_root.resolve()
    if [im["frame"] - current["index"] for im in current["images"]] != list(offsets):
        raise ValueError("Candidate observation window differs from configured offsets")
    for offset, im in zip(offsets, current["images"], strict=True):
        label = "F0" if offset == 0 else f"F{offset:+d}"
        if im["label"] != label:
            raise ValueError("Invalid candidate image label")
        stable_id = current["candidate_id"] + "/" + label
        if im.get("missing"):
            if im["frame"] >= 0:
                raise ValueError("Only pre-start frames may be missing")
            lines.append(f"{stable_id} is unavailable because the trajectory had not started.")
            mapping.append(dict(image_ref=stable_id, frame=im["frame"], missing=True))
            continue
        if not 0 <= im["frame"] <= current["ready_at_frame"]:
            raise ValueError("Unavailable or future observation")
        path = (root / im["path"]).resolve()
        if not path.is_relative_to(root) or sha256(path) != im["image_id"]:
            raise ValueError("Image path or hash mismatch")
        images.append(path)
        lines.append(f"Attachment {len(images):02d} is {stable_id}, action step {im['frame']}, "
                     f"reference B{label[1:]} for this turn.")
        mapping.append(dict(number=len(images), image_ref=stable_id, label="B" + label[1:],
                            frame=im["frame"], image_id=im["image_id"]))
    return "\n\n".join(lines), images, dict(previous_id=previous_id, current_id=current["candidate_id"],
                                            image_labels=mapping, mode=MODE)


def validate_review(raw, previous, current, binary=False):
    answer = copy.deepcopy(raw)
    expected_previous = previous["candidate_id"] if previous else None
    if not isinstance(answer, dict) or answer.get("previous_id") != expected_previous or answer.get("current_id") != current["candidate_id"]:
        raise ValueError("Candidate ID mismatch")
    if answer.get("eligibility") not in ("eligible", "not_eligible", "uncertain"):
        raise ValueError("Invalid eligibility")
    if binary and (answer["eligibility"] == "uncertain" or answer.get("relation") == "uncertain"):
        raise ValueError("A binary checkpoint judgment is required")
    for key in ("reason", "eligibility_reason"):
        if not isinstance(answer.get(key), str) or not answer[key].strip():
            raise ValueError("Missing " + key)
    compare = previous is not None and answer["eligibility"] in ("eligible", "uncertain")
    if compare:
        return protocol().validate(answer, previous, current)
    if answer.get("relation") != "not_compared" or answer.get("matched_branches") != [] or answer.get("a_only") != []:
        raise ValueError("Expected not_compared for an ineligible candidate or missing historical checkpoint")
    if not isinstance(answer.get("b_only"), list) or any(not isinstance(v, str) or not v.strip() for v in answer["b_only"]):
        raise ValueError("Invalid current branches")
    return answer


def run_case(case, image_root, directory, config, *, candidate_stream=None, live_sampler=None,
             candidate_template=None, retry_calls=False, session_factory=None):
    deviation_enabled = "deviation_review" in case
    gap_sampler = None
    if deviation_enabled:
        from core.codex_deviation_review import FrameGapSampler, REVIEW_PROMPTS, TERMINAL_VERSIONS, review_segment, review_terminal
        if (case["deviation_review"] not in REVIEW_PROMPTS or case.get("prompt_revision") != DIRECTIONAL_REVISION
                or not case.get("instruction_en") or case.get("resume_from")):
            raise ValueError("Interleaved deviation review requires a fresh v006.1 case and its instruction")
        if candidate_stream is None and case["deviation_review"] in TERMINAL_VERSIONS and not case.get("terminal_node"):
            raise ValueError("Terminal-aware review requires the final observation")
        if "max_frame_gap" in case:
            gap_sampler = live_sampler if candidate_stream is not None else FrameGapSampler(image_root, case["episode_id"], case["max_frame_gap"])
    reviews, progress_by_node = [], {}
    template = candidate_template or BINARY_TEMPLATES.get(case.get("prompt_revision"))
    binary = template is not None
    nodes = case["nodes"]
    offsets = tuple(case.get("observation_offsets", ()))
    if offsets != (-2, 0, 2):
        raise ValueError("Memory checkpoint review requires the agreed three-frame observations")
    ids = [node["id"] for node in nodes]
    frames = [node["index"] for node in nodes]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in ids) or frames != sorted(set(frames)):
        raise ValueError("Candidate identifiers or ordering are invalid")
    live = candidate_stream is not None
    directory.mkdir(parents=True, exist_ok=live)
    decision_log = directory / "decisions.jsonl"
    committed = {d["current_id"]:d for d in map(json.loads, decision_log.read_text().splitlines())} if live and decision_log.exists() else {}
    save(directory / "input.json", case)
    active, decisions = [], []
    prior = Path(case["resume_from"]) if case.get("resume_from") else None
    old_session = {}
    if prior:
        old_input = json.loads((prior / "input.json").read_text())
        if old_input.get("prompt_revision") != case.get("prompt_revision") or old_input["nodes"] != nodes or old_input["episode_id"] != case["episode_id"]:
            raise ValueError("Resume input differs from original case")
        decisions = [json.loads(line) for line in (prior / "decisions.jsonl").read_text().splitlines()]
        if [d["current_id"] for d in decisions] != ids[:len(decisions)]:
            raise ValueError("Resume decisions are not a chronological prefix")
        retained = decisions[-1]["active_ids_after"] if decisions else []
        active = [node for node in nodes if node["id"] in retained]
        old_session = json.loads((prior / "codex/session.json").read_text())
        if not old_session.get("thread_id"):
            raise ValueError("Resume requires an existing Codex thread")
        (directory / "decisions.jsonl").write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in decisions))
    if session_factory is not None:
        session = session_factory(directory / "codex", config)
    elif live or retry_calls:
        from core.codex_shadow_retry import ShadowSession
        session = ShadowSession(directory / "codex", config)
    else:
        session = CodexSession(directory / "codex", config, thread_id=old_session.get("thread_id"),
                               turn_count=old_session.get("turns", 0))
    state = dict(started_at=now(), status="running", processed=len(decisions), active_ids=[n["id"] for n in active])
    save(directory / "state.json", state)
    try:
        if prior:
            old_state = json.loads((prior / "state.json").read_text())
            initialization = dict(directory=old_state.get("initialization_directory",
                str(prior / "codex/turns/turn_0001_initialization")))
            if json.loads((Path(initialization["directory"]) / "final.txt").read_text()) != {"ready": True}:
                raise ValueError("Original initialization was not acknowledged")
        else:
            initialization, _ = session.ask_checked(require_ready, PROMPTS[0].read_text(), [],
                {"type": "object", "additionalProperties": False, "required": ["ready"],
                 "properties": {"ready": {"type": "boolean", "enum": [True]}}},
                label="initialization", metadata=dict(mode=MODE))
        state["initialization_directory"] = initialization["directory"]
        for current in (candidate_stream if candidate_stream is not None else nodes[len(decisions):]):
            if candidate_stream is not None:
                nodes.append(current)
            previous = active[-1] if active else None
            prompt, images, metadata = candidate_input(previous, current, image_root, offsets, binary, template)
            if current["id"] == case.get("reuse_pending_images"):
                prompt = (f"The previous call was interrupted while switching the connection. Continue the review of candidate {current['candidate_id']} "
                          "using its images already supplied in this conversation.\n\n" + prompt)
                images = []
                metadata["reused_current_images"] = True
            if live or retry_calls:
                response, checked = session.ask_checked(lambda raw: validate_review(raw, previous, current, binary),
                    prompt, images, review_schema(binary), label=current["id"], metadata=metadata)
            else:
                response = session.ask(prompt, images, review_schema(binary), label=current["id"], metadata=metadata)
            decision = dict(order=len(decisions) + 1, previous_id=previous["id"] if previous else None,
                current_id=current["id"], previous_frame=previous["index"] if previous else None,
                current_frame=current["index"], step_gap=current["index"] - previous["index"] if previous else None,
                needs_model=True, active_ids_before=[node["id"] for node in active],
                thread_id=response["thread_id"], turn=response["turn"], response_directory=response["directory"],
                usage=response["usage"], current_images_from_history=metadata.get("reused_current_images", False))
            try:
                raw = json.loads(response["text"])
                answer = checked if live or retry_calls else validate_review(raw, previous, current, binary)
                decision.update(status="ok", answer=answer, relation=answer["relation"],
                    eligibility=answer["eligibility"], reason=answer["reason"], normalized_references=raw != answer)
            except (ValueError, TypeError, KeyError) as error:
                if binary:
                    raise ValueError(f"{current['candidate_id']}: invalid binary review: {error}") from error
                decision.update(status="format_error", relation="uncertain", eligibility="uncertain",
                    reason="Response validation failed. Retain the candidate with an uncertainty marker.", error=str(error))
            if decision["eligibility"] == "not_eligible":
                action = "reject_current"
            elif decision["relation"] == "same":
                active[-1] = current
                action = "replace_previous"
            else:
                active.append(current)
                action = "append_current"
            decision.update(action=action, active_ids_after=[node["id"] for node in active], committed_at=now())
            if current["id"] in committed:
                old = committed[current["id"]]
                if any(old[k] != decision[k] for k in ("turn","action","active_ids_after","answer")):
                    raise ValueError("Replayed candidate decision differs from saved decision")
                decision = old
            else:
                save(Path(response["directory"]) / "decision.json", decision)
                with decision_log.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(decision, ensure_ascii=False) + "\n")
            decisions.append(decision)
            state.update(processed=len(decisions), active_ids=decision["active_ids_after"], updated_at=now())
            save(directory / "state.json", state)
            print(json.dumps(dict(case=case["case_number"], candidate=current["id"],
                eligibility=decision["eligibility"], relation=decision["relation"], retained=len(active))), flush=True)
            if deviation_enabled and action != "reject_current":
                review = review_segment(session, active, nodes[:len(decisions)], case["instruction_en"],
                                        progress_by_node, REVIEW_PROMPTS[case["deviation_review"]], gap_sampler)
                reviews.append(review)
                save(directory / "deviation_reviews.json", reviews)
                state.update(deviation_reviews=len(reviews), last_verdict=review["answer"]["verdict"])
                save(directory / "state.json", state)
                if review["answer"]["verdict"] == "deviated":
                    break
        else:
            if deviation_enabled and case["deviation_review"] in TERMINAL_VERSIONS:
                reviews.append(review_terminal(session, case, image_root, active, progress_by_node, gap_sampler))
                save(directory / "deviation_reviews.json", reviews)
                state.update(deviation_reviews=len(reviews), last_verdict=reviews[-1]["answer"]["verdict"])
    except BaseException as error:
        save(directory / "state.json", dict(state, status="error", error=f"{type(error).__name__}: {error}", updated_at=now()))
        raise
    summary = dict(candidates=len(nodes), retained=len(active), removed=len(nodes) - len(active),
        model_calls=len(decisions), initialization_calls=1,
        uncertain=sum(d["relation"] == "uncertain" or d["eligibility"] == "uncertain" for d in decisions),
        format_errors=sum(d["status"] == "format_error" for d in decisions),
        not_eligible=sum(d["eligibility"] == "not_eligible" for d in decisions),
        duplicates=sum(d["relation"] == "same" for d in decisions))
    result = dict(case, mode=MODE, decisions=decisions, final_active_ids=[node["id"] for node in active],
        effective_nodes=active, summary=summary, thread_id=session.thread_id,
        initialization_directory=initialization["directory"])
    if deviation_enabled:
        summary.update(candidates=len(decisions), removed=len(decisions) - len(active),
                       deviation_calls=len(reviews), unreviewed_candidates=len(nodes) - len(decisions))
        result.update(deviation_reviews=reviews, rollback_target=reviews[-1]["rollback_target"] if reviews else None)
        result["stop_reason"] = ("first_deviation" if result["rollback_target"] else
                                 "all_candidates_reviewed" if reviews else "no_effective_checkpoint")
        if case["deviation_review"] in TERMINAL_VERSIONS:
            terminal_done = reviews[-1].get("terminal_node", False)
            result["terminal_reviewed"] = terminal_done
            result["review_nodes"] = [*active, case["terminal_node"]] if terminal_done else list(active)
            if terminal_done and not result["rollback_target"]:
                result["stop_reason"] = "terminal_reviewed" if active else "terminal_initialization_only"
    save(directory / "result.json", result)
    save(directory / "state.json", dict(state, status="complete", completed_at=now(), summary=summary))
    return result
