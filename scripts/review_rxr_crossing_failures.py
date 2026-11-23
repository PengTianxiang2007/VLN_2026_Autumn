"""Build offline evidence for the frozen RxR 400 reproduction. No policy or simulator rollout."""
import itertools
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import habitat_sim
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/reproduction/streamvln_rxr/run_20261123_01"
OUT = ROOT / "outputs/crossing_analysis/rxr_seed2_400/run_20261123_01"
MESH = ROOT / "backbone/streamvln/data/scene_datasets/mp3d"
RES = .05
RECORD = ROOT / "experiments/crossing_analysis/rxr_seed2_400/run_20261123_01"


def load_mesh(scene):
    pf = habitat_sim.PathFinder()
    if not pf.load_nav_mesh(str(MESH / scene / (scene + ".navmesh"))):
        raise ValueError(scene)
    return pf


def cumulative(points):
    return np.r_[0., np.linalg.norm(np.diff(points, axis=0), axis=1).cumsum()]


def prepare(index, score, pathfinder, custom=None, *, source=SOURCE, output=OUT):
    directory = source / score["capture"]
    meta = json.loads((directory / "episode.json").read_text())
    trace = [json.loads(l) for l in (directory / "trace.jsonl").read_text().splitlines()]
    xyz = np.array([f["pose"]["xyz"] for f in trace])
    ref = np.array(meta["reference_locations"])
    # Compare in all three dimensions, since MP3D routes can cross on different floors.
    keep = np.r_[True, np.linalg.norm(np.diff(ref, axis=0), axis=1) > 1e-5]
    ref = ref[keep]
    ref_arc = cumulative(ref)
    grid = np.linspace(0, ref_arc[-1], max(2, math.ceil(ref_arc[-1] / .08) + 1))
    dense = np.column_stack([np.interp(grid, ref_arc, col) for col in ref.T])
    lengths = cumulative(xyz)
    distances = np.linalg.norm(xyz[:, None] - dense[None, :], axis=2)
    nearest = distances.argmin(axis=1)
    off = distances.min(axis=1)
    progress = grid[nearest]
    end = len(trace) - 1
    excursions = []
    for active, indices in itertools.groupby(range(end + 1), key=lambda i: off[i] > .85):
        steps = list(indices)
        if not active:
            continue
        s, e = steps[0], steps[-1]
        if off[s:e+1].max() < 1.15 or lengths[e] - lengths[max(0, s-3)] < .45:
            continue
        d = s
        while d and off[d] > .38 and lengths[s] - lengths[d] < 2.5:
            d -= 1
        excursions.append((d, s, e, float(off[s:e+1].max())))
    if excursions:
        # Prefer an excursion persisting to termination; show other excursions on request.
        d, s, e, _ = max(excursions, key=lambda v: (v[2] == end,
                           min(v[3], 5.) * min(lengths[v[2]] - lengths[v[0]], 15.)))
    else:
        d = int(progress.argmax())
        s = min(d + 4, end)
        e = end
    outstep = min(e, max(s, int(np.searchsorted(lengths, lengths[d] + 1.55))))
    if custom:
        d, outstep = custom[1:3]
    refnext = int(np.searchsorted(grid, min(grid[-1], progress[d] + 1.8)))
    refnext = min(refnext, len(grid) - 1)
    frames = [max(0, d-5), d, min(end, max(d+3, s)), outstep, (outstep+e)//2, end]
    if custom:
        frames = custom
    case = dict(n=index, id=meta["episode_id"], scene=meta["scene_id"], capture=score["capture"],
                instruction=meta["instruction"].strip(), ne=round(score["ne"],2), os=int(score["os"]),
                decision=d, confirm=outstep, terminal=end, last_action=trace[-1]["action"],
                progress_m=round(float(progress[d]),1), route_m=round(float(grid[-1]),1),
                max_progress=round(float(progress.max()),1), end_progress=round(float(progress[-1]),1),
                end_offset=round(float(off[-1]),1), final_reference_gap=round(float(np.linalg.norm(ref[-1]-meta["goals"][0])),2),
                events=excursions, frames=frames)
    low = np.asarray(pathfinder.get_bounds()[0])
    raster = pathfinder.get_topdown_view(RES, float(xyz[d,1]))
    def panel(local):
        cx, cz = xyz[d,[0,2]]
        if local:
            half = 4.
        else:
            allxz = np.concatenate((xyz[:,[0,2]],ref[:,[0,2]]))
            cx,cz = (allxz.max(0)+allxz.min(0))/2
            half = max(2.,float(np.ptp(allxz,axis=0).max()/2 + .85))
        side = 194
        xx = ((cx-half + np.arange(side)*2*half/side-low[0])/RES).astype(int)
        zz = ((cz-half + np.arange(side)*2*half/side-low[2])/RES).astype(int)
        inside = ((zz[:,None]>=0)&(zz[:,None]<raster.shape[0])&(xx[None,:]>=0)&(xx[None,:]<raster.shape[1]))
        bits = inside & raster[np.clip(zz,0,raster.shape[0]-1)[:,None],np.clip(xx,0,raster.shape[1]-1)[None,:]]
        img = Image.fromarray(np.where(bits,239,148).astype("uint8")).convert("RGB")
        pen = ImageDraw.Draw(img)
        def pt(p):
            return (int((p[0]-cx+half)*side/(2*half)),int((p[2]-cz+half)*side/(2*half)))
        def line(arr,c,w):
            if len(arr)>1: pen.line([pt(p) for p in arr], fill=c,width=w)
        line(ref,"#008434",4)
        line(xyz,"#2556c0",2)
        line(xyz[d:outstep+1],"#ef6000",3)
        for pos,color,r in [(ref[-1],"#008434",4),(xyz[0],"#29a5cb",3),
                            (xyz[-1],"#b82789",4),(dense[refnext],"#ffee40",3),(xyz[d],"#ff5000",3)]:
            x,y=pt(pos);pen.ellipse((x-r,y-r,x+r,y+r),fill=color,outline="black")
        return img
    sheet=Image.new("RGB",(1480,204),"white")
    sheet.paste(panel(False),(0,10));sheet.paste(panel(True),(196,10));pen=ImageDraw.Draw(sheet)
    for col,f in enumerate(frames):
        with Image.open(directory / trace[f]["rgb"]) as im:
            im.thumbnail((177,140)); x=394+col*181;sheet.paste(im,(x,37))
        pen.text((x,17),f"f{f}  {trace[f]['action'] or 'START'}",fill="black")
    pen.text((2,0),f"{index:03d} ep {case['id']}  |  full and local map | D={d} -> {outstep}",fill="black")
    pen.text((395,180),f"OS={case['os']} NE={case['ne']}  route {case['progress_m']}/{case['route_m']}m at D   max={case['max_progress']} end={case['end_progress']} off={case['end_offset']}m  last={case['last_action']}  y: {xyz[d,1]:.1f}->{xyz[-1,1]:.1f} refend {ref[-1,1]:.1f}",fill="black")
    sheet.save(output / ("details" if custom else "cards") / f"{index:03d}.jpg",quality=88)
    return case


def summarize(scores):
    cases = json.loads((OUT / "evidence.json").read_text())
    extra = {c["n"]:c for c in json.loads((OUT/"details/evidence.json").read_text())}
    with (RECORD/"reviews.tsv").open() as stream:
        notes = {int(r["case"]):r for r in csv.DictReader(stream, delimiter="\t")}
    by_id = {r["episode_id"]:r for r in scores}
    metrics = ("success","spl","ne","os","ndtw")
    valid = [r for r in scores if all(math.isfinite(r[k]) for k in metrics)]
    failed = {r["episode_id"] for r in valid if not r["success"]}
    assert len(by_id)==len(scores)==400 and len(cases)==len(failed)==len(notes)==165
    assert failed=={c["id"] for c in cases} and set(notes)=={c["n"] for c in cases}
    rows=[]; subtypes={"wrong_door","wrong_branch","missed_turn"}
    for c in cases:
        n=c["n"]; note=notes[n]; r=by_id[c["id"]]; tag=note["label"]
        assert tag in subtypes | {"uncertain","other"}
        clear=tag in subtypes
        anchor=int(note["decision_override"] or c["decision"])
        confirm=int(note["confirm_override"] or c["confirm"])
        frames=sorted(set(c["frames"]+extra.get(n,{}).get("frames",[])))
        if clear:
            assert note["expected"] and note["actual"] and anchor in frames and confirm in frames and anchor<=confirm
        assert c["last_action"]=="STOP" or c["terminal"]==500
        row=dict(case=n,episode_id=c["id"],scene=c["scene"],termination="STOP" if c["last_action"]=="STOP" else "step_limit",
                 label=tag,decision_step=anchor if clear else "",confirmation_step=confirm if clear else "",
                 expected=note["expected"],actual=note["actual"],reason=note["rationale"],
                 reviewed_rgb_steps=" ".join(map(str,frames)),steps=c["terminal"],NE=r["ne"],OS=r["os"],
                 source_capture=r["capture"],instruction=c["instruction"])
        rows.append(row)
    with (RECORD/"attribution.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    groups={}
    for mode in ("STOP","step_limit","all"):
        selected=[r for r in rows if mode=="all" or r["termination"]==mode]
        counts=Counter(r["label"] for r in selected)
        groups[mode]=dict(failures=len(selected),crossing=sum(counts[t] for t in subtypes),
                          uncertain=counts["uncertain"],other=counts["other"],
                          subtypes={t:counts[t] for t in sorted(subtypes)})
    summary=dict(attempts=len(scores),valid=len(valid),successes=sum(int(r["success"]) for r in valid),
                 mean_spl=sum(r["spl"] for r in valid)/len(valid),technically_invalid=[
                     r["episode_id"] for r in scores if not all(math.isfinite(r[k]) for k in metrics)],
                 groups=groups,matched_unique_episodes=len(rows),extra_review_cases=len(extra),
                 distinct_reviewed_episode_steps=sum(len(r["reviewed_rgb_steps"].split()) for r in rows))
    (RECORD/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    paths=[SOURCE/"result.json",SOURCE/"episodes.json",RECORD/"reviews.tsv",Path(__file__).resolve()]
    (OUT/"sources.json").write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                                for p in paths},indent=2)+"\n")
    shutil.copy2(__file__,OUT/"review_rxr_crossing_failures.py")
    print(json.dumps(summary,indent=2))


def main():
    scores = [json.loads(l) for l in (SOURCE/"result.json").read_text().splitlines()]
    if "--summarize" in sys.argv:
        summarize(scores)
        return
    failures=[s for s in scores if s["success"]==0 and all(math.isfinite(s[k]) for k in ("ne","spl","os","ndtw"))]
    assert len(failures)==len({s["episode_id"] for s in failures})==165
    if "--supplement" in sys.argv:
        # Specific alternative time windows identified during the first visual review.
        windows = {
            9:[10,15,24,90,113,127], 21:[20,26,36,54,75,100], 24:[10,22,34,68,95,175],
            32:[31,43,51,56,70,123], 40:[17,32,43,58,89,133], 43:[12,25,39,48,76,105],
            55:[54,65,76,90,102,108], 56:[1,7,18,192,213,260], 59:[0,8,18,26,38,62],
            67:[0,2,10,16,30,64], 75:[0,10,19,32,47,63], 83:[53,65,79,85,95,103],
            88:[45,64,74,90,107,125], 105:[55,70,85,103,125,175], 107:[0,10,18,35,60,79],
            110:[90,111,125,132,145,152], 152:[66,79,94,110,151,273],
            17:[38,55,66,123,159,206], 44:[47,61,75,92,109,126], 51:[137,158,172,195,235,250],
            81:[79,92,103,105,107,109], 82:[88,107,116,118,120,122], 98:[0,12,20,23,25,28],
            156:[13,22,35,62,85,138], 161:[87,102,110,113,116,119],
        }
        rows=[]; folder=OUT/"details"; folder.mkdir(exist_ok=True)
        meshes={}
        for i,window in windows.items():
            row=failures[i-1]; scene=row["scene_id"]
            if scene not in meshes: meshes[scene]=load_mesh(scene)
            rows.append(prepare(i,row,meshes[scene],window))
        (folder/"evidence.json").write_text(json.dumps(rows,ensure_ascii=False))
        for start in range(0,len(rows),5):
            subset=rows[start:start+5]; sheet=Image.new("RGB",(1480,204*len(subset)))
            for n,c in enumerate(subset):
                with Image.open(folder/f"{c['n']:03d}.jpg") as card: sheet.paste(card,(0,n*204))
            sheet.save(folder/f"group_{start//5}.jpg",quality=90)
        return
    prepare_cards(SOURCE, OUT, failures)


def prepare_cards(source, output, failures):
    (output/"cards").mkdir(parents=True,exist_ok=True)
    caselist=[]
    # Only use CPU pathfinders. Each scene's mesh stays read-only.
    for scene, group in itertools.groupby(enumerate(failures,1),key=lambda pair:pair[1]["scene_id"]):
        pf=load_mesh(scene)
        # get_topdown_view uses native state, so prepare these serially per mesh.
        for i,score in group:
            caselist.append(prepare(i,score,pf,source=source,output=output))
    (output/"evidence.json").write_text(json.dumps(caselist,ensure_ascii=False))
    for first in range(1,len(caselist)+1,5):
        subset=caselist[first-1:first+4]
        sheet=Image.new("RGB",(1480,204*len(subset)))
        for n,c in enumerate(subset):
            with Image.open(output/"cards"/f"{c['n']:03d}.jpg") as card:
                sheet.paste(card,(0,n*204))
        sheet.save(output/f"review_{first:03d}.jpg",quality=89)
    print(f"{len(caselist)} evidence cards ready",flush=True)


if __name__=="__main__":
    main()
