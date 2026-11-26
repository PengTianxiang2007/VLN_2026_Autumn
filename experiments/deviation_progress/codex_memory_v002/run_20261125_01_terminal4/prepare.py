"""Freeze the four requested v002 active streams and their actual final observations."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core.codex_node_dedup import prepare_candidates


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT / "experiments/crossing_checkpoint/codex_dedup_v006_1/run_20261124_04_astra_standard_all53/input.json"
    prior = load(source)
    dataset = ROOT / prior["image_root"]
    cases = {c["case_number"]: c for c in prior["cases"]}
    sources = [source, Path(__file__), *(ROOT / f for f in (
        "scripts/replay_jev_online_sampling.cjs", "core/jev_online_sampler_v002.js",
        "core/jev_online_sampler_v001.js", "core/jev_online_sampling_v001.json"))]
    manifest = {k: prior[k] for k in ("upstream_policy","dataset_id","image_root","trajectory_seed")}
    manifest.update(sampler_version="v002", sampler_mode="active", cases=[])
    for number in (17, 43, 23, 20):
        c = cases[number]
        eid = c["episode_id"]
        scores = ROOT / "outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/episodes" / eid / "scores.json"
        obs = dataset / "inputs" / eid / "observations.jsonl"
        task_file = obs.with_name("task.json")
        sources.extend([scores, obs, task_file])
        task = load(task_file)
        sampled = json.loads(subprocess.check_output(["node", "scripts/replay_jev_online_sampling.cjs",
            "--version","v002","--mode","active","--input",str(scores)], cwd=ROOT))
        frames = []
        for i, line in enumerate(obs.read_text().splitlines()):
            row = json.loads(line)
            assert row["episode_id"] == eid and row["step"] == i
            frames.append(dict(path=row["native_front"]["image"], image=row["native_front"]["sha256"]))
        t = len(frames) - 1
        assert (sampled["version"],sampled["mode"],sampled["received"]) == ("v002","active",t)
        assert task["episode_id"] == eid and task["seed"] == manifest["trajectory_seed"]
        nodes = prepare_candidates(dict(case_number=number, frames=frames), sampled["nodes"])
        for node in nodes:
            node["images"] = [im for im in node["images"] if im["label"] in ("F-2","F0","F+2")]
        last = dict(frame=t, label="F0", path=frames[t]["path"], image_id=frames[t]["image"])
        terminal = dict(id="END", candidate_id=f"C{number:02}:END:F{t}", index=t, emittedAt=t,
                        ready_at_frame=t, terminal_node=True, images=[last])
        c.update(nodes=nodes, terminal_node=terminal, sampler_version="v002", sampler_mode="active",
                 instruction_en=task["instruction"], deviation_review="codex_memory_v002")
        manifest["cases"].append(c)
        print(f"C{number:02}", [n["index"] for n in nodes], "END", t)
    manifest["source_sha256"] = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    with (HERE / "input.json").open("x") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
