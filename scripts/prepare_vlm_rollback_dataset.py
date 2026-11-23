"""Package the frozen 22 H1 rollback point pairs for a future VLM controller."""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path.cwd()  # Run from the repository root, including when using the frozen copy.
PRIOR = Path("outputs/inverse_rollback/v001/run_20261122_03_rgb22")
BACKWARD = Path("outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22")
SELECTION = Path("experiments/inverse_rollback/v001/run_20261122_03_rgb22/cases.csv")
DATA = Path("outputs/offline_route_dataset/v001/run_20261118_01/dataset")
NODES = Path("outputs/deviation_progress/v006/all53_20261121_01/retained_nodes_and_terminals.json")
ACTIONS = ("STOP", "FORWARD", "LEFT", "RIGHT")


def read(path):
    return json.loads(path.read_bytes())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def build_case(folder, case, nodes, seed):
    cid, eid = case["case_id"], case["episode_id"]
    a, b = case["checkpoint_step"], case["alarm_step"]
    task_dir = DATA / "inputs" / eid
    task = read(task_dir / "task.json")
    source = DATA / "provenance/capture_records" / (eid + ".jsonl")
    raw = source.read_bytes()
    if digest(raw) != case["sha256"]:
        raise ValueError(f"{cid}: original capture changed")
    records = {r["step"]: r for r in map(json.loads, raw.splitlines()) if a <= r["step"] <= b}
    obs = {r["step"]: r for r in map(json.loads, (task_dir / "observations.jsonl").read_bytes().splitlines())
           if a <= r["step"] <= b}
    start = records[b]
    if (task["episode_id"] != eid or task["scene"] != case["scene"] or task["seed"] != seed
            or records[a]["robot_pose"] != case["target"] or start["physical_state_before"] != case["historical_start"]
            or start["environment_offset"] != case["historical_offset"] or nodes[a]["id"] != case["node"]):
        raise ValueError(f"{cid}: source identity or A/B state mismatch")

    history = case["history"]
    if len(history) != b - a or b - a < 6:
        raise ValueError(f"{cid}: invalid history or insufficient distinct RGB frames")
    for step, action in enumerate(history, start=a):
        command = {"stop": []} if action == 0 else {"move_by_discrete": [action]}
        if action not in range(4) or records[step]["action"] != command or obs[step + 1]["previous_action"] != command:
            raise ValueError(f"{cid}: action/observation mismatch at F{step}")

    directory = folder / "cases" / cid
    (directory / "rgb").mkdir(parents=True)
    # Match the v006 uniform_between rule on the interior F(A+1)..F(B-1).
    interior = range(a + 1, b)
    sampled = [interior[round(i * (len(interior) - 1) / 4)] for i in range(5)]
    steps = [a, *sampled, b]
    images = []
    for step in steps:
        role = "target_A" if step == a else "alarm_B" if step == b else "history"
        asset = obs[step]["native_front"]
        capture = records[step]
        if (obs[step]["episode_id"] != eid or capture["episode_id"] != eid
                or Path(asset["image"]) != Path(capture["frame_directory"]) / capture["front_image"]):
            raise ValueError(f"{cid}: native RGB source mismatch at F{step}")
        data = (DATA / asset["image"]).read_bytes()
        if digest(data) != asset["sha256"]:
            raise ValueError(f"{cid}: RGB hash mismatch at F{step}")
        local = f"rgb/F{step:04d}.png"
        (directory / local).write_bytes(data)
        images.append(dict(step=step, role=role, image=local, sha256=asset["sha256"]))

    actions = [ACTIONS[k] for k in history]
    write(directory / "reference.json", dict(action_start_step=a, actions=actions, observations=images))
    write(directory / "simulation.json", dict(
        case_id=cid, episode_id=eid, scene=case["scene"], seed=seed, episode_seed=task["episode_seed"],
        historical_environment_offset=case["historical_offset"],
        start_B=dict(node=nodes[b]["id"], step=b, historical_terminal=start["terminal"],
                     historical_phase=start["phase"], physical_state_before=start["physical_state_before"]),
        target_A=dict(node=nodes[a]["id"], step=a, robot_pose=case["target"]),
        ab_horizontal_m=case["ab_xy_m"], capture_record=str(source), capture_sha256=case["sha256"],
    ))
    return dict(case_id=cid, episode_id=eid, scene=case["scene"], A=a, B=b,
                node_A=nodes[a]["id"], node_B=nodes[b]["id"], historical_B_terminal=start["terminal"],
                ab_horizontal_m=case["ab_xy_m"], sampled_steps=steps, action_count=len(actions),
                reference=f"cases/{cid}/reference.json", simulation=f"cases/{cid}/simulation.json")


def build(output):
    prior = read(PRIOR / "manifest.json")
    with SELECTION.open(newline="") as stream:
        selection = list(csv.DictReader(stream))
    cases = prior["cases"]
    identity = [(c["case_id"], c["episode_id"], c["node"], c["checkpoint_step"], c["alarm_step"]) for c in cases]
    frozen = [(r["case_id"], r["episode_id"], r["checkpoint"], int(r["A_frame"]), int(r["B_alarm_frame"])) for r in selection]
    if identity != frozen or len({c["episode_id"] for c in cases}) != 22 or prior["seed"] != 2:
        raise ValueError("The source manifest does not match the frozen 22-case seed-2 selection")
    retained = read(NODES)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        folder = Path(temporary) / "dataset"
        (folder / "source").mkdir(parents=True)
        rows = []
        counts = Counter()
        for c in cases:
            nodes = {n["index"]: n for n in retained[c["episode_id"]]}
            rows.append(build_case(folder, c, nodes, prior["seed"]))
            counts.update(ACTIONS[k] for k in c["history"])

        config = BACKWARD / "source/eval_config.py"
        init_script = BACKWARD / "source/run_inverse_rollback.py"
        for path in (Path(__file__), config):
            shutil.copyfile(path, folder / "source" / path.name)
        distances = [c["ab_xy_m"] for c in cases]
        summary = dict(cases=len(rows), scenes=len({r["scene"] for r in rows}), images=sum(len(r["sampled_steps"]) for r in rows),
                       actions=sum(counts.values()), actions_by_name=dict(counts), terminal_B=sum(r["historical_B_terminal"] for r in rows),
                       ab_horizontal_range_m=[min(distances), max(distances)])
        sources = (SELECTION, PRIOR / "manifest.json", NODES, config, init_script)
        write(folder / "manifest.json", dict(
            schema_version=1, dataset="vlm_action_rollback_v001", seed=prior["seed"], summary=summary,
            git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            source_run_git_head=prior["git_head"], build_script_sha256=digest(Path(__file__).read_bytes()),
            sources_sha256={str(p): digest(p.read_bytes()) for p in sources},
            sampling=dict(total=7, endpoints_included=True, interior_count=5, interior_range="A+1 through B-1",
                          interior_fractions=[0, 0.25, 0.5, 0.75, 1], interior_index_rounding="nearest, ties to even"),
            initialization=dict(config="source/eval_config.py", simulator_code=str(Path(prior["simulator_source"]).relative_to(ROOT)),
                                reference_implementation=str(init_script), robot="h1", warm_up_standing_ticks=500,
                                root_position="B.position + current_environment_offset - historical_environment_offset",
                                root_rotation="B.rotation (quaternion wxyz)", root_world_velocity=[0.0] * 6,
                                joints="B.joints and B.joint_velocities", low_level_controller="warmed, historical state unavailable"),
            cases=rows,
        ))
        folder.rename(output)
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
