"""Freeze the eight requested Route53 cases and their v002 active candidates."""
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core.codex_client import sha256
from core.codex_node_dedup import prepare_candidates


def read(path):
    return json.loads(path.read_text())


def main():
    source = ROOT / "experiments/crossing_checkpoint/codex_dedup_v006_1"
    originals = [source / n / "input.json" for n in (
        "run_20261124_04_astra_standard_all53", "run_20261124_01_astra_c01_c11")]
    cases = {c["case_number"]: c for p in originals for c in read(p)["cases"]}
    picked = [47, 16, 37, 25, 41, 8, 40, 50]
    source_manifest = read(originals[0])
    manifest = {k: source_manifest[k] for k in ("upstream_policy","dataset_id","image_root","trajectory_seed")}
    manifest.update(sampler_version="v002", sampler_mode="active", max_frame_gap=6, selected=picked, cases=[])
    root = ROOT / manifest["image_root"]
    sources = originals + [Path(__file__), *(ROOT / name for name in (
        "scripts/replay_jev_online_sampling.cjs","core/jev_online_sampler_v002.js",
        "core/jev_online_sampler_v001.js","core/jev_online_sampling_v001.json"))]
    for number in picked:
        c = cases[number]
        eid = c["episode_id"]
        inputs = root / "inputs" / eid
        task = read(inputs / "task.json")
        obs = inputs / "observations.jsonl"
        scores = ROOT / "outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/episodes" / eid / "scores.json"
        sources.extend([inputs / "task.json", obs, scores])
        stream = json.loads(subprocess.check_output(["node","scripts/replay_jev_online_sampling.cjs",
            "--version","v002","--mode","active","--input",str(scores)], cwd=ROOT))
        frames = []
        for i, line in enumerate(obs.read_text().splitlines()):
            row = json.loads(line)
            assert row["episode_id"] == eid and row["step"] == i
            frames.append(dict(image=row["native_front"]["sha256"],path=row["native_front"]["image"]))
        end = len(frames)-1
        assert (stream["version"],stream["mode"],stream["received"]) == ("v002","active",end)
        assert (task["episode_id"],task["seed"]) == (eid,2)
        nodes = prepare_candidates(dict(case_number=number,frames=frames),stream["nodes"])
        for n in nodes:
            n["images"] = [im for im in n["images"] if im["label"] in ("F-2","F0","F+2")]
        terminal = dict(id="END",candidate_id=f"C{number:02}:END:F{end}",index=end,emittedAt=end,
                        ready_at_frame=end,terminal_node=True,images=[dict(frame=end,label="F0",
                        path=frames[end]["path"],image_id=frames[end]["image"])])
        c.update(nodes=nodes,terminal_node=terminal,sampler_version="v002",sampler_mode="active",
                 instruction_en=task["instruction"],deviation_review="codex_memory_v002",max_frame_gap=6)
        assert c["prompt_revision"]=="local_route_choice_v006_1" and not c.get("resume_from")
        manifest["cases"].append(c)
        print(f"C{number:02}  candidates={len(nodes)}  END=F{end}")
    manifest["source_sha256"] = {str(p.relative_to(ROOT)):sha256(p) for p in sources}
    with (HERE / "input.json").open("x") as f:
        json.dump(manifest,f,ensure_ascii=False,indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
