"""Export measured H1 rollbacks, optionally paired with a rerun of selected cases."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from statistics import mean

from export_roundtrip_comparison import Export, ROOT, ROUTES, json_text, lines, point, read


BASE = ROOT / "outputs/inverse_rollback"
PREVIOUS = BASE / "exports/paired_rgb_20261122_01"
RUN = BASE / "vlm_action_v001/run_20261123_05_finish22"
DATASET = RUN.parent / "run_20261123_02/manifest.json"


def historical_case(cid):
    script = (PREVIOUS / "cases" / (cid + ".js")).read_text().strip()
    return json.loads(script.removeprefix("loadRoundtrip(").removesuffix(");"))


def return_trace(export, cid, leg, src, result, project_pose):
    trace = list(lines(src / "actions.jsonl"))
    turn = [r for r in trace if r["phase"] == "turnaround"]
    moves = [r for r in trace if r["phase"] == "return"]
    if len(turn) != 12 or [r["index"] for r in moves] != list(range(1, result["return_actions"]+1)):
        raise ValueError(f"Incomplete motion trace for {cid}/{leg}")
    turn_path = [project_pose(read(src/"start_B.json")), *map(project_pose, turn)]
    decisions = {int(p.parent.name.split("_")[1]): read(p) for p in (src/"requests").glob("return_*/answer.json")}
    expected = set(range(0, len(moves), 4))
    if result["arrived"]:
        expected.add(len(moves))
    if decisions.keys() != expected:
        raise ValueError(f"Incomplete return decisions for {cid}/{leg}")
    frames = []
    for i, row in enumerate([turn[-1], *moves]):
        img = src / "rgb/return" / f"R{i:04d}.png"
        frames.append(export.frame(cid, leg, i, img, project_pose(row), "turnaround" if i == 0 else row["action"],
                                   tick=row["physical_ticks"], error=row["xy_m"]))
    if abs(frames[-1]["error"] - result["xy_m"]) > 1e-5:
        raise ValueError(f"Terminal pose and score disagree for {cid}/{leg}")
    return dict(turn=turn_path, frames=frames, decisions=decisions, passed=result["passed"], arrived=result["arrived"],
                reason=result["terminal_reason"], error=result["xy_m"], yaw=result["yaw_deg"])


def build_data(out, compare_run=None):
    summary = read(RUN / "summary.json")
    frozen = read(DATASET)["cases"]
    if summary["phase"] != "complete" or [r["case"] for r in summary["results"]] != [c["case_id"] for c in frozen]:
        raise ValueError("The completed rollback results do not match the frozen case list")
    active_run = compare_run or RUN
    results = summary["results"]
    original = {r["case"]:r for r in results}
    if compare_run:
        manifest = read(compare_run/"manifest.json")
        current = read(compare_run/"summary.json")
        selected = {row["case_id"]:row for row in frozen}
        frozen = manifest["cases"]
        if (manifest["seed"] != 2 or any(c != selected[c["case_id"]] for c in frozen)
                or [r["case"] for r in current["results"]] != [c["case_id"] for c in frozen]):
            raise ValueError("Rerun does not match the original episodes and endpoints")
        results = current["results"]
    export = Export(out)
    catalog = []
    history_count = 0
    for result, case in zip(results, frozen):
        cid, eid = result["case"], case["episode_id"]
        old = historical_case(cid)
        if original[cid]["episode_id"] != eid or (old["eid"], old["scene"], old["a"], old["b"]) != (eid, case["scene"], case["A"], case["B"]):
            raise ValueError(f"Mismatched reference route for {cid}")
        original_src = (ROOT / original[cid]["source"]).parent
        geometry = read(ROUTES / "geometry" / old["scene"] / "geometry.json")
        def project(x, y):
            return [round((x - geometry["low"][0]) / geometry["resolution"], 3),
                    round((geometry["high"][1] - y) / geometry["resolution"], 3)]
        def project_pose(row):
            x, y, _, heading = point(row["position"], row["rotation"])
            return [*project(x, y), -heading]

        history = old["legs"]["out"]
        map_path = Path(old["map"]["src"])
        if not (out / map_path).exists():
            shutil.copyfile(PREVIOUS / map_path, out / map_path)
        for f in history:
            dest = out / f["img"]
            dest.parent.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(PREVIOUS / f["img"], dest)
        history_count += len(history)
        episode = read(ROUTES / "dataset/evaluation/episodes" / (eid + ".json"))
        task_route = [project(p[0], p[1]) for p in episode["reference_path"]]
        src = compare_run/"cases"/cid if compare_run else original_src
        current_trace = return_trace(export, cid, "return", src, result, project_pose)
        record = dict(id=cid, eid=eid, scene=old["scene"], map=old["map"], history=history, reference=task_route,
                      **current_trace, instruction=old["instruction"],
                      a=old["a"], b=old["b"], nodes=[n for n in old["nodes"] if n["step"]<=old["b"]],
                      ab=old["ab"])
        entry = dict(id=cid, passed=result["passed"])
        if compare_run:
            record["original"] = return_trace(export, cid, "original", original_src, original[cid], project_pose)
            record.update(nodes=old["nodes"], after=old["after"])
            entry["originalPassed"] = original[cid]["passed"]
        (out/"cases"/(cid+".js")).write_text("loadRollback("+json_text(record)+");\n")
        catalog.append(entry)
    print(f"{len(catalog)} cases, converting {len(export.images)} measured return images",flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in pool.map(export.convert, export.images.items()):
            pass
    aggregate = dict(mean=mean(r["xy_m"] for r in results), passed=sum(r["passed"] for r in results))
    if compare_run:
        previous = [original[r["case"]] for r in results]
        aggregate["original"] = dict(mean=mean(r["xy_m"] for r in previous), passed=sum(r["passed"] for r in previous))
    (out/"catalog.js").write_text("const catalog="+json_text(catalog)+";\nconst aggregate="+json_text(aggregate)+";\n")
    report = dict(cases=len(catalog), return_images=len(export.images), historical_images=history_count,
                  results_sha256=hashlib.sha256((active_run/"summary.json").read_bytes()).hexdigest(),
                  source=str(active_run.relative_to(ROOT)), created_utc=datetime.now(timezone.utc).isoformat())
    if compare_run:
        report.update(original_source=str(RUN.relative_to(ROOT)), original_results_sha256=hashlib.sha256((RUN/"summary.json").read_bytes()).hexdigest(),
                      current_return_images=sum(r["return_actions"]+1 for r in results),
                      original_return_images=sum(r["return_actions"]+1 for r in previous))
    (out/"export.json").write_text(json.dumps(report,indent=2)+"\n")


def finish(out):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    theme = (ROOT/"core/roundtrip_comparison.html").read_text().split("<style>",1)[1].split("</style>",1)[0]
    html = (ROOT/"core/vlm_rollback_replay.html").read_text().replace("/*__ROUNDTRIP_STYLE__*/",theme)
    player = (ROOT/"core/vlm_rollback_replay.js").read_text()
    cfg = read(ROOT/"core/crossing_visualization_template.json")
    chars = set(html + player)
    for p in (out/"cases").glob("*.js"):
        chars.update(p.read_text())
    with TTFont(cfg["font"],fontNumber=0) as font:
        sub = subset.Subsetter()
        sub.populate(text="".join(sorted(chars)))
        sub.subset(font)
        font.save(out/"replay.ttf")
    notice = Path(cfg["font_license"]).read_text().replace("--","—")
    (out/"index.html").write_text(html.replace("</html>","<!-- "+notice+" --></html>"))
    (out/"player.js").write_text(player)
    assets = ["catalog.js","player.js","replay.ttf"]
    for subdir in ("maps","frames","cases"):
        assets.extend(sorted(str(p.relative_to(out)) for p in (out/subdir).rglob("*") if p.is_file()))
    (out/"online_manifest.json").write_text(json_text(dict(html="index.html",assets=assets)))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--compare-run",type=Path,help="Completed rerun to compare with the original H1 batch")
    args=parser.parse_args()
    build_data(args.output, args.compare_run.resolve() if args.compare_run else None)
    finish(args.output)
