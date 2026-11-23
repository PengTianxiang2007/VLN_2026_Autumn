"""Index the frozen RxR front recordings and apply the VLNVerse JEV v004 + v001 sampler."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import file_hash, read, now
from core.crossing_lite import windows
from scripts.run_jev_noul_five_concurrent import run_task
from scripts.run_deviation_progress_review import save

SOURCE = ROOT / "outputs/reproduction/streamvln_rxr/run_20261123_01"
SAMPLE = ROOT / "experiments/crossing_analysis/rxr_seed2_400/run_20261123_01/exports/random30_20261123_01/sample.json"
POINTER = ROOT / "experiments/crossing_checkpoint/current_jev_version.json"
MODEL_CONFIG = ROOT / "experiments/agent_route_choice/services/qwen27b_gpu3_20261121_01/model.json"


def dataset(out):
    ids = read(SAMPLE)["episode_ids"]
    if len(ids) != len(set(ids)) or len(ids) != 30:
        raise ValueError("The frozen selection must have 30 distinct episodes")
    scores = {str(r["episode_id"]):r for r in map(json.loads,(SOURCE/"result.json").read_text().splitlines())}
    cases = []
    for index, eid in enumerate(ids):
        capture = SOURCE / scores[eid]["capture"]
        episode = read(capture/"episode.json")
        rows = list(map(json.loads,(capture/"trace.jsonl").read_text().splitlines()))
        if str(episode["episode_id"]) != eid or len(rows) != scores[eid]["frames"] or not rows[-1]["terminal"]:
            raise ValueError("Misaligned capture for "+eid)
        frames = []
        for i, row in enumerate(rows):
            if row["step"] != i or row["terminal"] != (i == len(rows)-1):
                raise ValueError("Unexpected frame order for "+eid)
            path = capture/row["rgb"]
            frames.append(dict(frame=i, path=str(path.relative_to(SOURCE)), image=file_hash(path),
                               pose=row["pose"], action=row["action"], terminal=row["terminal"]))
        case=dict(case_index=index,case_number=index+1,episode_id=eid,real_episode_id=eid,
                  scene=episode["scene_id"], instruction_en=episode["instruction"],frames=frames)
        save(out/"dataset"/(eid+".json"),case)
        cases.append(case)
    save(out/"dataset/index.json",dict(episode_ids=ids,frames=sum(len(c["frames"]) for c in cases),
                                      image_root=str(SOURCE),selection_sha256=file_hash(SAMPLE)))
    return cases


def credentials():
    values={}
    for line in (ROOT/".env.easyjev.local").read_text().splitlines():
        parts=shlex.split(line,comments=True)
        if parts and parts[0]=="export":
            parts=parts[1:]
        if len(parts)==1 and "=" in parts[0]:
            k,v=parts[0].split("=",1)
            values[k]=v
    base=values["JEV_BASE_URL"].rstrip("/")
    url=urlsplit(base)
    if url.scheme!="https" or url.username or url.password or url.query or url.fragment:
        raise ValueError("Invalid configured EasyJEV base")
    path=url.path.rstrip("/")
    if path.endswith("/systemone"):
        endpoint=base
    else:
        endpoint=base+("/systemone" if path.endswith("/v1") else "/v1/systemone")
    if not values["JEV_API_KEY"]:
        raise ValueError("Empty EasyJEV credential")
    return endpoint,values["JEV_API_KEY"]


def run(out,workers):
    state=dict(phase="indexing",started_at=now(),pid=os.getpid(),target_episodes=30)
    def update(**kw):
        state.update(kw,updated_at=now())
        save(out/"jev/status.json",state)
    update()
    try:
        pf=read(POINTER)["fixed_pipeline"]
        for name in ("scorer","sampler","config"):
            if file_hash(ROOT/pf[name])!=pf[name+"_sha256"]:
                raise ValueError("Frozen "+name+" hash mismatch")
        if (out/"dataset/index.json").exists():
            cases=[read(out/"dataset"/(eid+".json")) for eid in read(SAMPLE)["episode_ids"]]
        else:
            cases=dataset(out)
        endpoint,key=credentials()
        os.environ["JEV_API_KEY"]=key
        tasks=[]
        for case in cases:
            sequence=[dict(frame=r["frame"],rgb=r["path"],rgb_sha256=r["image"],
                      terminal=r["terminal"],eligible_for_inference=not r["terminal"],rgb_reused=False)
                      for r in case["frames"]]
            for step,images in windows(sequence):
                tasks.append(dict(episode_id=case["episode_id"],scene=case["scene"],group="failure",frame=step,
                                  images=images,question_version="v004",dataset=str(SOURCE),output=str(out/"jev"),
                                  endpoint=endpoint,model="jev-1.14.0",attempts=3,timeout=120))
        def process(task):
            dest=out/"jev/cases"/task["episode_id"]/("F%04d"%task["frame"])
            if (dest/"result.json").is_file():
                result=read(dest/"result.json")
                if (result["phase"]!="complete" or
                    [r["source_sha256"] for r in read(dest/"images.json")]!=[r["rgb_sha256"] for r in task["images"]]):
                    raise ValueError("Cached JEV result differs from input")
                return result
            return run_task(task)
        first=tasks.pop(2)
        update(phase="first_request",episode_id=first["episode_id"],frame=first["frame"],target_requests=len(tasks)+1,
               completed=0,endpoint=endpoint,workers=workers)
        probe=process(first)
        if probe["phase"]!="complete":
            raise RuntimeError(probe["error"])
        scores={(probe["episode_id"],probe["frame"]):probe["answer"]["probability_yes"]}
        update(phase="scoring",completed=1,first_probability=probe["answer"]["probability_yes"])
        for wave in range(1,4):
            pending=[]
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for task,result in zip(tasks,pool.map(process,tasks)):
                    if result["phase"]=="complete":
                        scores[result["episode_id"],result["frame"]]=result["answer"]["probability_yes"]
                    else:
                        pending.append(task)
                    if len(scores)%20==0:
                        update(completed=len(scores),wave=wave)
            if not pending:
                break
            tasks=pending
        if pending:
            save(out/"jev/pending.json",[[t["episode_id"],t["frame"]] for t in pending])
            raise RuntimeError(f"{len(pending)} JEV requests still missing; scores retained")
        update(phase="sampling",completed=len(scores))
        mapping={}
        for c in cases:
            eid=c["episode_id"]
            path=out/"jev/episodes"/eid/"scores.json"
            save(path,[scores[eid,i] for i in range(len(c["frames"])-1)])
            raw=subprocess.check_output(["node",str(ROOT/"scripts/replay_jev_online_sampling.cjs"),
                                        "--input",str(path)],text=True)
            result=json.loads(raw)
            if result["received"]!=len(c["frames"])-1:
                raise ValueError("Sampler length mismatch")
            save(path.parent/"sampling.json",result)
            mapping[eid]=result["nodes"]
        save(out/"jev/candidates.json",mapping)
        update(phase="complete",candidates=sum(map(len,mapping.values())),finished_at=now())
    except BaseException as exc:
        update(phase="failed",error=str(exc))
        raise
    finally:
        os.environ.pop("JEV_API_KEY",None)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--workers",type=int,default=24)
    args=parser.parse_args()
    run(args.output.resolve(),args.workers)
