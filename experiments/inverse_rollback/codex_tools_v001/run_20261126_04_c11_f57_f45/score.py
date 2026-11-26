"""Score the local return from operator receipts after the child session has ended."""
from collections import Counter
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
PLACEMENT = ROOT / "outputs/inverse_rollback/pose_hold/run_20261126_03_f57"
MOVES = {"forward", "turn_left", "turn_right"}


def main():
    source = json.loads((PLACEMENT / "placement.json").read_bytes())["source"]
    target_file = (ROOT / source).parents[1] / "000045/metadata.json"
    target = json.loads(target_file.read_bytes())["robot_pose"]
    target_xy = target["position_world_m"][:2]
    all_rows = []
    for directory in (PLACEMENT / "live", OUT / "continued"):
        receipts = directory / "calls.jsonl"
        if not receipts.exists():
            continue
        for line in receipts.read_text().splitlines():
            item = json.loads(line)
            item["directory"] = directory
            all_rows.append(item)
    start, end = all_rows[0]["before"], all_rows[-1]["after"]
    actions = [r for r in all_rows if r["action"] in MOVES and r["after"]["task_ticks"] > r["before"]["task_ticks"]]
    counts = Counter(item["action"] for item in actions)
    declared = any(r.get("result", {}).get("status") == "return_declared" for r in all_rows)
    delta = math.dist(end["position"][:2], target_xy)
    nearest = min(enumerate([start] + [r["after"] for r in actions]),
                  key=lambda pair: math.dist(pair[1]["position"][:2], target_xy))
    photo = next(r for r in reversed(all_rows) if r.get("rgb") and r["after"] == end)
    end_image = photo["directory"] / "frames" / f'{photo["sequence"]:05d}.png'
    assert end_image.is_file()
    result = dict(episode_id="kujiale_0128_fix_20_0", seed=2, parent_thread=json.loads((OUT/"launch.json").read_bytes())["parent"],
                  branch_thread=json.loads((OUT/"continuation.json").read_bytes())["child"], start_frame=57,
                  target_node="S05", target_frame=45, target_source=str(target_file.relative_to(ROOT)),
                  target_position=target["position_world_m"], start=start, end=end, movements=len(actions),
                  actions=dict(counts), independent_observations=sum(r["method"]=="observe" for r in all_rows),
                  task_ticks_advanced=end["task_ticks"]-start["task_ticks"],
                  world_ticks_advanced=end["world_ticks"]-start["world_ticks"],
                  start_horizontal_error_m=math.dist(start["position"][:2], target_xy),
                  final_horizontal_error_m=delta, closest_action_index=nearest[0],
                  closest_horizontal_error_m=math.dist(nearest[1]["position"][:2],target_xy),
                  endpoint_declared=declared, threshold_m=0.35, passed=declared and delta<=0.35,
                  final_frame_image=str(end_image.relative_to(ROOT)),
                  terminal_reason=next((r["result"]["terminal_reason"] for r in all_rows if r.get("result",{}).get("terminal_reason")),None),
                  observed_tool_errors=[r["error"] for r in all_rows if r.get("error")],
                  start_utc=all_rows[0]["started_utc"],end_utc=all_rows[-1]["finished_utc"])
    if (OUT / "truncation.json").exists():
        cutoff = json.loads((OUT / "truncation.json").read_bytes())
        boundary = actions[cutoff["limit"] - 1]
        result.update(stop_reason=cutoff["reason"], limit=cutoff["limit"],
                      at_limit=dict(live_frame=boundary["result"]["live_frame"], time_utc=boundary["finished_utc"],
                                    position=boundary["after"]["position"],
                                    distance_m=math.dist(boundary["after"]["position"][:2],target_xy), declared=False))
    (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
