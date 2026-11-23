"""Export the seeded RxR wrong-branch sample from its scored, existing recordings."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import shutil

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUN = Path("crossing_analysis/rxr_seed2_400/run_20261123_01")
EXPORT = Path("exports/random30_20261123_01")
RECORD = ROOT / "experiments" / RUN
OUT = ROOT / "outputs" / RUN / EXPORT
CAPTURE = ROOT / "outputs/reproduction/streamvln_rxr/run_20261123_01"
TILE_W, TILE_H = 640, 480
COLS, ROWS = 3, 3


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def selected():
    with (RECORD / "attribution.csv").open(encoding="utf-8-sig") as stream:
        pool = [r for r in csv.DictReader(stream) if r["label"] in {"wrong_door", "wrong_branch", "missed_turn"}]
    pool.sort(key=lambda r: int(r["episode_id"]))
    assert len(pool) == len({r["episode_id"] for r in pool}) == 80
    return random.Random(2).sample(pool, 30)


def map_slice(pathfinder, ref, pose, goal, decision, dest):
    import numpy as np
    resolution = 0.04
    height = pose[decision][1]
    grid = pathfinder.get_topdown_view(resolution, height)
    lo = pathfinder.get_bounds()[0]
    points = np.array(ref + [r[:3] for r in pose] + [goal])[:, [0, 2]]
    origin = np.array([lo[0], lo[2]])
    left, top = np.floor((points.min(axis=0) - 3 - origin) / resolution).astype(int)
    right, bottom = np.ceil((points.max(axis=0) + 3 - origin) / resolution).astype(int)
    raster = Image.fromarray(np.where(grid, 241, 186).astype("uint8"))
    cropped = raster.crop((left, top, right, bottom))
    cropped.save(dest)
    return dict(x=float(origin[0]+left*resolution), z=float(origin[1]+top*resolution),
                width=cropped.width*resolution, height=cropped.height*resolution, floor=height)


def media():
    from review_rxr_crossing_failures import load_mesh
    OUT.mkdir(parents=True, exist_ok=False)
    scores = {str(r["episode_id"]): r for r in map(json.loads,(CAPTURE / "result.json").read_text().splitlines())}
    rows = selected()
    write_json(RECORD / EXPORT / "sample.json", dict(seed=2, population=80,
               episode_ids=[r["episode_id"] for r in rows], order="numeric episode_id before sampling",
               attribution_sha256=hashlib.sha256((RECORD / "attribution.csv").read_bytes()).hexdigest()))
    cases, meshes = [], {}
    for row in rows:
        key, scene = row["episode_id"], row["scene"]
        score = scores[key]
        assert score["success"] == 0 and score["capture"] == row["source_capture"]
        folder = CAPTURE / row["source_capture"]
        meta = json.loads((folder / "episode.json").read_text())
        trace = list(map(json.loads, (folder / "trace.jsonl").read_text().splitlines()))
        assert str(meta["episode_id"]) == key and meta["instruction"].strip() == row["instruction"].strip()
        assert len(trace) == score["frames"] == int(row["steps"])+1 and trace[-1]["terminal"]
        dest = OUT / "assets" / key
        dest.mkdir(parents=True)
        poses = []
        for i, t in enumerate(trace):
            assert t["step"] == i
            poses.append([*t["pose"]["xyz"], t["pose"]["yaw_deg"], t["action_id"]])
            slot = i % (COLS * ROWS)
            if slot == 0:
                sheet = Image.new("RGB", (TILE_W*COLS, TILE_H*ROWS))
            with Image.open(folder / t["rgb"]) as frame:
                assert frame.size == (TILE_W, TILE_H)
                sheet.paste(frame, ((slot % COLS)*TILE_W, (slot // COLS)*TILE_H))
            if slot == COLS*ROWS-1 or i == len(trace)-1:
                sheet.save(dest / f"{i//(COLS*ROWS)}.jpg", quality=82, subsampling=1)
        ref, goal = meta["reference_locations"], meta["goals"][0]
        if scene not in meshes:
            meshes[scene] = load_mesh(scene)
        decision, confirm = int(row["decision_step"]), int(row["confirmation_step"])
        assert 0 <= decision <= confirm < len(trace)
        geo = map_slice(meshes[scene], ref, poses, goal, decision, dest / "floor.png")
        cases.append(dict(id=key, scene=scene, label=row["label"], termination=row["termination"],
                          decision=decision, confirm=confirm, frames=list(map(int,row["reviewed_rgb_steps"].split())),
                          ne=score["ne"], floor=geo, ref=ref, goal=goal, pose=poses,
                          instruction=meta["instruction"], expected=row["expected"], actual=row["actual"], reason=row["reason"]))
        print(key, len(trace), flush=True)
    write_json(OUT / "captures.json", cases)


def build():
    cases = json.loads((OUT / "captures.json").read_text())
    with (RECORD / EXPORT / "translations.tsv").open() as stream:
        trans = {r["id"]:r for r in csv.DictReader(stream,delimiter="\t")}
    assert set(trans) == {c["id"] for c in cases}
    for c in cases:
        t = trans[c["id"]]
        for field in ("instruction", "expected", "actual", "reason"):
            translated = t[field].strip()
            assert translated
            c[field] = ([translated,c[field]] if field=="instruction" else [c[field],translated])
    data = json.dumps(cases, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    (OUT / "cases.js").write_text("const CASES = " + data + ";\n")
    shutil.copyfile(ROOT / "core/rxr_branch_replay.html", OUT / "index.html")
    assets = ["cases.js"]
    for c in cases:
        prefix = "assets/" + c["id"] + "/"
        assets.append(prefix + "floor.png")
        assets.extend(prefix + f"{i}.jpg" for i in range(math.ceil(len(c["pose"])/(COLS*ROWS))))
    assert all((OUT / x).is_file() for x in assets)
    write_json(OUT / "online_manifest.json", dict(html="index.html",assets=assets))
    print(f"{len(cases)} cases; {sum(len(c['pose']) for c in cases)} frames; {len(assets)} assets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["media", "build"])
    if parser.parse_args().phase == "media":
        media()
    else:
        build()
