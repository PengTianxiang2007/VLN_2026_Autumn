"""Route reviews on the live checkpoint thread, optionally filling gaps in its observations."""
import json
from pathlib import Path

from core.codex_client import require_ready, sha256
from scripts.run_deviation_progress_review import validate_v005


VERSION = "codex_memory_v001"
TERMINAL_VERSION = "codex_memory_v002"
PROMPT = Path(__file__).resolve().parents[1] / "experiments/deviation_progress" / VERSION / "prompt_en.txt"
LANDMARK_VERSION = "codex_memory_v003"
TERMINAL_VERSIONS = (TERMINAL_VERSION, LANDMARK_VERSION)
REVIEW_PROMPTS = {VERSION: PROMPT, TERMINAL_VERSION: PROMPT,
                 LANDMARK_VERSION: PROMPT.parent.parent / LANDMARK_VERSION / "prompt_en.txt"}
INITIAL_PROGRESS = "首次有效节点：此前路线进度未确认。"


class FrameGapSampler:
    def __init__(self, image_root, episode_id, max_gap, *, live_fronts=None):
        if type(max_gap) is not int or max_gap < 1:
            raise ValueError("Maximum review frame gap must be a positive integer")
        self.max_gap = max_gap
        self.root = image_root.resolve()
        self.sent = {}
        if live_fronts is not None:
            self.fronts = live_fronts
            return
        self.fronts = {}
        manifest = self.root / "inputs" / episode_id / "observations.jsonl"
        for line in manifest.read_text().splitlines():
            row = json.loads(line)
            if row["episode_id"] != episode_id or row["step"] in self.fronts:
                raise ValueError("Invalid episode or duplicate observation step")
            self.fronts[row["step"]] = row["native_front"]

    def plan(self, observations, start, end):
        known = {frame:list(refs) for frame,refs in observations.items()}
        for frame, ref in self.sent.items():
            if start <= frame <= end:
                known.setdefault(frame, []).append(ref)
        if start not in known or end not in known:
            raise ValueError("Both review endpoints need existing observations")
        anchors = sorted(known)
        new = [frame for left,right in zip(anchors,anchors[1:])
               for frame in range(left+self.max_gap, right, self.max_gap)]
        paths = []
        for frame in new:
            front = self.fronts[frame]
            path = (self.root / front["image"]).resolve()
            if not path.is_relative_to(self.root) or sha256(path) != front["sha256"]:
                raise ValueError(f"Native front observation mismatch at F{frame}")
            paths.append(path)
        return dict(sorted(known.items())), new, paths


def review_schema():
    def obj(**properties):
        return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)

    def array(items):
        return dict(type="array", items=items)

    string = dict(type="string")
    bilingual = obj(zh=string, en=string)
    return obj(previous_id=string, current_id=string,
               verdict=dict(type="string", enum=["consistent", "deviated"]),
               segment_summary=bilingual, reason=bilingual,
               instruction_evidence=array(obj(quote_en=string, quote_zh=string)),
               visual_evidence=array(obj(frames=array(dict(type="integer")), description=bilingual)),
               semantic_progress={"anyOf": [bilingual, {"type": "null"}]}, uncertainties=array(bilingual))


def review_segment(session, active, seen_nodes, instruction, progress_by_node, prompt_path=PROMPT, sampler=None):
    current = active[-1]
    previous = active[-2] if len(active) > 1 else current
    initialization = previous is current
    progress = INITIAL_PROGRESS if initialization else progress_by_node[previous["id"]]["zh"]
    observations = {}
    for candidate in seen_nodes:
        for image in candidate["images"]:
            frame = image["frame"]
            if not image.get("missing") and previous["index"] <= frame <= current["index"]:
                observations.setdefault(frame, []).append(candidate["candidate_id"] + "/" + image["label"])
    observations = dict(sorted(observations.items()))
    request = dict(previous_id=previous["candidate_id"], current_id=current["candidate_id"],
                   previous_frame=previous["index"], current_frame=current["index"],
                   instruction_en=instruction, prior_semantic_progress=progress)
    paths, added = [], []
    if sampler is not None:
        observations, added, paths = sampler.plan(observations, previous["index"], current["index"])
    new_refs = {f: f"interval/F{f}" for f in added}
    available = dict(sorted((observations | {f:[ref] for f,ref in new_refs.items()}).items()))
    template = prompt_path.read_text()
    if added:
        template = template.replace("Already supplied image references", "Available image references")
        template = template.replace("Use the visual observations already supplied in this conversation.",
            "Use the visual observations already supplied in this conversation and the images attached to this request.")
        template += "\n" + "\n".join(f"Attachment {i:02d} is {new_refs[f]}, action frame {f}."
                                      for i,f in enumerate(added,1))
    prompt = template.format(**request, observations=json.dumps(available))
    request.update(mode="initialization" if initialization else "segment", historical_images=observations)
    if sampler is not None:
        request.update(max_frame_gap=sampler.max_gap, attached_frames=added, available_images=available)
    evidence = dict(request, images=[{"frame": f} for f in available])
    response, answer = session.ask_checked(lambda raw: validate_v005(raw, evidence),
        prompt, paths, review_schema(), label="deviation_" + current["id"], metadata=request)
    if sampler is not None:
        sampler.sent.update(new_refs)
    if answer["verdict"] == "consistent":
        progress_by_node[current["id"]] = answer["semantic_progress"]
    return dict(**request, answer=answer, turn=response["turn"], thread_id=response["thread_id"],
                rollback_target=previous["candidate_id"] if answer["verdict"] == "deviated" else None)


def review_terminal(session, case, image_root, active, progress_by_node, sampler=None):
    """Supply the actual terminal observation, then review its interval in the same thread."""
    terminal = case["terminal_node"]
    image, = terminal["images"]
    t = terminal["index"]
    if (terminal["id"] != "END" or image["frame"] != t or image["label"] != "F0"
            or any(n["ready_at_frame"] >= t for n in case["nodes"])):
        raise ValueError("Invalid terminal endpoint or candidate chronology")
    path = (image_root / image["path"]).resolve()
    if not path.is_relative_to(image_root.resolve()) or sha256(path) != image["image_id"]:
        raise ValueError("Terminal observation path or hash mismatch")
    ref = terminal["candidate_id"] + "/F0"
    message = (f"The trajectory has ended. This is the actual final front RGB, {ref}, at action step {t}. "
               "Record this observation for the next route review. Acknowledge with ready=true.")
    ack, _ = session.ask_checked(require_ready, message, [path], {"type": "object", "additionalProperties": False, "required": ["ready"],
        "properties": {"ready": {"type": "boolean", "enum": [True]}}}, label="terminal_observation",
        metadata=dict(frame=t, image_ref=ref, image_id=image["image_id"]))
    review = review_segment(session, [*active, terminal], [*case["nodes"], terminal],
                            case["instruction_en"], progress_by_node, REVIEW_PROMPTS[case["deviation_review"]], sampler)
    review.update(terminal_node=True, observation_turn=ack["turn"])
    return review
