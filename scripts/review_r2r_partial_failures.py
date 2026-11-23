"""Review the paused R2R recording using the same RGB/map evidence as RxR."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image
from review_rxr_crossing_failures import load_mesh, prepare, prepare_cards

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"outputs/reproduction/streamvln_r2r/run_20261123_01"
REL=Path("crossing_analysis/r2r_seed2_400/run_20261123_02_partial217")
OUT=ROOT/"outputs"/REL
RECORD=ROOT/"experiments"/REL


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")


def initial():
    OUT.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(SOURCE/"result.json",OUT/"scores.jsonl")
    scores=list(map(json.loads,(OUT/"scores.jsonl").read_text().splitlines()))
    assert len(scores)==len({str(r["episode_id"]) for r in scores})==217
    failed=[r for r in scores if r["success"]==0]
    assert len(failed)==94
    files=[SOURCE/"result.json",SOURCE/"episodes.json",Path(__file__),ROOT/"scripts/review_rxr_crossing_failures.py"]
    save(OUT/"sources.json",dict(commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
    shutil.copyfile(__file__,OUT/"review_r2r_partial_failures.py")
    prepare_cards(SOURCE,OUT,failed)


def supplement():
    failed=[r for r in map(json.loads,(OUT/"scores.jsonl").read_text().splitlines()) if r["success"]==0]
    windows=json.loads((RECORD/"supplement.json").read_text())
    folder=OUT/"details"
    folder.mkdir(exist_ok=True)
    meshes={}
    cases=[]
    for key,frames in windows.items():
        n=int(key);r=failed[n-1]
        if r["scene_id"] not in meshes:
            meshes[r["scene_id"]]=load_mesh(r["scene_id"])
        cases.append(prepare(n,r,meshes[r["scene_id"]],frames,source=SOURCE,output=OUT))
    save(folder/"evidence.json",cases)
    for first in range(0,len(cases),5):
        group=cases[first:first+5]
        sheet=Image.new("RGB",(1480,204*len(group)))
        for i,c in enumerate(group):
            with Image.open(folder/f"{c['n']:03d}.jpg") as im:
                sheet.paste(im,(0,i*204))
        sheet.save(folder/f"group_{first//5}.jpg",quality=92)


def summarize():
    scores=list(map(json.loads,(OUT/"scores.jsonl").read_text().splitlines()))
    by_id={str(r["episode_id"]):r for r in scores}
    cases=json.loads((OUT/"evidence.json").read_text())
    extra={c["n"]:c for c in json.loads((OUT/"details/evidence.json").read_text())}
    with (RECORD/"reviews.tsv").open() as stream:
        notes={int(r["case"]):r for r in csv.DictReader(stream,delimiter="\t")}
    assert len(cases)==len(notes)==94 and set(notes)=={c["n"] for c in cases}
    rows=[];subtypes={"wrong_door","wrong_branch","missed_turn"}
    for c in cases:
        r=by_id[str(c["id"])];note=notes[c["n"]];tag=note["label"]
        assert tag in subtypes|{"uncertain","other"}
        clear=tag in subtypes
        a=int(note["decision_override"] or c["decision"]);b=int(note["confirm_override"] or c["confirm"])
        frames=sorted(set(c["frames"]+extra.get(c["n"],{}).get("frames",[])))
        if clear:
            assert note["expected"] and note["actual"] and a in frames and b in frames and a<=b
        assert c["last_action"]=="STOP" or c["terminal"]==500
        rows.append(dict(case=c["n"],episode_id=c["id"],scene=c["scene"],
            termination="STOP" if c["last_action"]=="STOP" else "step_limit",label=tag,
            decision_step=a if clear else "",confirmation_step=b if clear else "",
            expected=note["expected"],actual=note["actual"],reason=note["rationale"],
            reviewed_rgb_steps=" ".join(map(str,frames)),steps=c["terminal"],NE=r["ne"],OS=r["os"],
            source_capture=r["capture"],instruction=c["instruction"]))
    with (RECORD/"attribution.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    groups={}
    for mode in ("STOP","step_limit","all"):
        selected=[r for r in rows if mode=="all" or r["termination"]==mode]
        cnt=Counter(r["label"] for r in selected)
        groups[mode]=dict(failures=len(selected),crossing=sum(cnt[t] for t in subtypes),uncertain=cnt["uncertain"],
                          other=cnt["other"],subtypes={t:cnt[t] for t in sorted(subtypes)})
    summary=dict(scored=len(scores),successes=sum(int(r["success"]) for r in scores),
        mean_spl=sum(r["spl"] for r in scores)/len(scores),technical=0,groups=groups,
        scene_counts=dict(Counter(r["scene_id"] for r in scores)),extra_review_cases=len(extra),
        distinct_reviewed_episode_steps=sum(len(r["reviewed_rgb_steps"].split()) for r in rows))
    save(RECORD/"summary.json",summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["prepare","supplement","summarize"])
    args=parser.parse_args()
    {"prepare":initial,"supplement":supplement,"summarize":summarize}[args.action]()
