"""Capture and pair native VLN-PE metrics outside the policy observation channel."""
import json
import math
from pathlib import Path
from statistics import mean
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def measure_prefix(env, task, case, directory):
    """Obtain per-tick TL for a mid-episode start on a separate reset."""
    from run_inverse_rollback import tick_action
    source = (ROOT / case["source"]).parents[1]
    length = int(case["start_frame"])
    obs, ended, _ = tick_action(env, {"stand_still": []}, 500)
    errors = []
    for index in range(length + 1):
        recorded = read(source / f"{index:06d}/metadata.json")
        errors.append(math.dist(obs["globalgps"], recorded["observation_position"]))
        if ended or index == length:
            break
        obs, ended, _ = tick_action(env, recorded["action"], task.robot.controllers["move_by_discrete"].steps_per_action)
    metric, = task.metrics.values()
    write(directory / "prefix_replay.json", dict(frames_compared=len(errors), max_position_error_m=max(errors),
          reproduced=len(errors) == length + 1 and not ended and max(errors) < 1e-4,
          observed_TL=float(metric.current_path_length)))


def track_goal(task, case, directory):
    import numpy as np
    metric, = task.metrics.values()
    position, _ = task._get_robot_poses_without_offset()
    # The warmup and instantaneous placement do not count towards post-takeover TL.
    metric.prev_position = position.copy()
    metric.current_path_length = 0.0

    def finish():
        final, _ = task._get_robot_poses_without_offset()
        metric.ne = np.linalg.norm(final[:2] - metric.goal_position[:2])
        metrics, = metric.calc()
        write(directory / "native_goal.json", dict(episode_id=metrics["episode_id"],
              seed=metrics["reproduction_run_seed"], goal_xy=list(map(float,metric.goal_position[:2])),
              endpoint_xy=final[:2].tolist(), success_distance=metrics["success_distance"],
              NE=float(metrics["NE"]), success=bool(metrics["success"]),
              shortest_path_length=float(metrics["shortest_path_length"]), live_TL=float(metrics["TL"])))
    return finish


def prefix_bounds(case, original, dest):
    if case["phase"] == "terminal":
        return original["TL"], original["TL"], "native_original_terminal"
    replay = read(dest / "prefix_replay.json")
    if replay["reproduced"]:
        return replay["observed_TL"], replay["observed_TL"], "native_replay_matched_to_recorded_frames"
    # Original per-tick TL is known for the entire trajectory. Each observed
    # polyline is a lower bound on the corresponding per-tick path length.
    path = original["pred_path"]
    split = case["start_frame"] + 1  # pred_path starts before warmup
    frame_xy = read(ROOT / case["source"])["observation_position"][:2]
    if math.dist(path[split][:2], frame_xy) > 1e-4:
        raise ValueError("Original path does not match the takeover frame")
    segments = [math.dist(a[:2], b[:2]) for a,b in zip(path,path[1:])]
    return sum(segments[:split]), original["TL"] - sum(segments[split:]), "native_total_and_frame_bounds"


def score_case(out, case, stats):
    dest = out / case["case"]
    entry = dict(case=case["case"], episode_id=case["episode"], seed=2, stop_reason=stats["phase"])
    if stats["phase"] == "technical_error" or not (dest / "result.json").exists():
        return dict(entry, phase="technical_error", declared_goal=None, error=stats.get("error"))
    result = read(dest / "result.json")
    entry.update(declared_goal=result["endpoint_declared"], movements=result["movements"],
                 elapsed_s=stats["case_elapsed_s"], native_terminal=result["native_terminal"])
    snapshot = dest / "native_goal.json"
    for _ in range(100):
        if snapshot.exists() or (dest / "simulator_error.json").exists():
            break
        time.sleep(.1)
    native = read(snapshot)
    original = read((ROOT / case["source"]).parents[2] / "complete.json")["metrics"]
    if any((m["episode_id"], m[seed]) != (case["episode"], 2)
           for m,seed in ((native,"seed"),(original,"reproduction_run_seed"))):
        raise ValueError("Episode/seed mismatch")
    if not math.isclose(native["shortest_path_length"],original["shortest_path_length"]) or native["success_distance"] != original["success_distance"]:
        raise ValueError("Goal metric configuration mismatch")
    lo, hi, source = prefix_bounds(case, original, dest)
    shortest = native["shortest_path_length"]
    def spl(prefix):
        tl = prefix + native["live_TL"]
        return float(native["success"]) * shortest / max(shortest, tl) if tl else 0.0
    lower, upper = spl(hi), spl(lo)
    return dict(entry, phase="scored", success=native["success"], NE=native["NE"],
                spl=lower if lower == upper else None, spl_range=[lower,upper],
                prefix_TL_range=[lo,hi], prefix_source=source, live_TL=native["live_TL"],
                baseline=dict(success=bool(original["success"]), spl=original["spl"], NE=original["NE"]))


def report(out, cases, status):
    files = [out / c["case"] / "score.json" for c in cases]
    entries = [read(p) for p in files if p.exists()]
    scored = [e for e in entries if e["phase"] == "scored"]
    if len({e["episode_id"] for e in scored}) != len(scored):
        raise ValueError("Duplicate scored episode")
    n = len(scored)
    def aggregate(successes, spls):
        return dict(successes=sum(successes), scored=n, sr=sum(successes)/n if n else None,
                    mean_spl=mean(spls) if n and None not in spls else None)
    current = aggregate([e["success"] for e in scored], [e["spl"] for e in scored])
    if n and current["mean_spl"] is None:
        current["mean_spl_range"] = [mean(e["spl_range"][i] for e in scored) for i in (0,1)]
    baseline = aggregate([e["baseline"]["success"] for e in scored], [e["baseline"]["spl"] for e in scored])
    summary = dict(phase=status["phase"], current=current, baseline=baseline,
                   declared_goal=sum(bool(e["declared_goal"]) for e in entries if "declared_goal" in e),
                   pending=len(cases)-len(entries), technical_skips=sum(e["phase"]!="scored" for e in entries),
                   cases=entries)
    write(out / "scores.json", summary)
    return summary


def after_case(out, case, stats, *, refresh=True):
    try:
        row = score_case(out, case, stats)
    except Exception as exc:
        row = dict(case=case["case"], episode_id=case["episode"], phase="scoring_error", error=repr(exc))
    write(out / case["case"] / "score.json", row)
    if refresh:
        report(out, read(HERE / "cases.json"), read(out / "status.json"))
