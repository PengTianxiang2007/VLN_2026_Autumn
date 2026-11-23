"""Consume the RxR JEV run, freeze deduplicated nodes, then run VLNVerse Qwen v006."""
import argparse
from collections import Counter
import csv
import fcntl
import importlib.util
import os
from pathlib import Path
import signal
import sys
import time

from run_rxr_offline_jev import ROOT, SOURCE, SAMPLE, MODEL_CONFIG, read, save, file_hash, now
from core.serial_pipeline import DEDUP, PROMPTS, semantic_settings
from run_agent_route_choice import wait_local
from run_crossing_local_batch import cleanup
from run_deviation_progress_v004 import review_qwen_cases
from run_human_route_choice import start_local
from serve_crossing_vlm import gpu_rows, idle
from test_crossing_single_gpu import gpu_snapshot

VERSION = "v006"
DEVIATION_PROMPT = ROOT / "experiments/deviation_progress" / VERSION / "prompt_zh.txt"
LOCAL_AUTH = "LOCAL-VLLM-NO-AUTH"


def node_inputs(case, candidates):
    nodes = []
    frames = case["frames"]
    for i, candidate in enumerate(candidates, 1):
        t, ready = candidate["index"], candidate["emittedAt"]
        if (candidate["id"] != f"S{i:02d}" or ready != t+5 or ready >= len(frames)-1
                or (nodes and nodes[-1]["index"] >= t)):
            raise ValueError("Unexpected candidate timing or order")
        images = []
        for offset in range(-2,3):
            frame = t + offset
            entry = dict(frame=frame, label="F0" if not offset else f"F{offset:+d}")
            if frame < 0:
                entry["missing"] = True
            else:
                entry.update(path=frames[frame]["path"], image_id=frames[frame]["image"])
            images.append(entry)
        nodes.append(dict(id=candidate["id"],index=t,emittedAt=ready,ready_at_frame=ready,
                          candidate_id=f"C{case['case_number']:02d}:{candidate['id']}:F{t}",images=images))
    return nodes


def freeze_nodes(case, candidates, kept):
    active = set(kept)
    selected = [dict(source_id=c["id"],index=c["index"],emittedAt=c["emittedAt"],terminal_node=False)
                for c in candidates if c["id"] in active]
    if [n["source_id"] for n in selected] != kept:
        raise ValueError("Retained candidate ID mismatch")
    terminal = len(case["frames"])-1
    selected.append(dict(source_id=None,index=terminal,emittedAt=terminal,terminal_node=True))
    for i, node in enumerate(selected,1):
        frame=case["frames"][node["index"]]
        node.update(id=f"S{i:02d}",pose=frame["pose"],rgb=frame["path"],rgb_sha256=frame["image"])
    return selected


def get_service(out, config, locks, update, selected_gpu=None, allow_shared=False):
    service = out / "service"
    service.mkdir(exist_ok=True)
    while True:
        update(phase="waiting_for_gpu",requested_gpu=selected_gpu,allow_shared_gpu=allow_shared)
        for row in gpu_rows():
            if selected_gpu is not None and row["index"] != selected_gpu:
                continue
            if not allow_shared and not idle(row):
                continue
            gpu=row["index"]
            try:
                child, endpoint = start_local(config, gpu, service, locks, allow_shared=allow_shared)
                return child,endpoint,gpu
            except (BlockingIOError,RuntimeError) as error:
                if not isinstance(error,BlockingIOError) and str(error) not in (
                        "GPU admission failed; other processes are preserved","Insufficient host memory"):
                    raise
                for lock in locks:
                    lock.close()
                locks.clear()
        time.sleep(45)


def dedup_cases(out, cases, candidates, endpoint, settings, update):
    spec=importlib.util.spec_from_file_location("rxr_dedup_v001",ROOT / DEDUP / "run_dedup.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SITE, module.RUN, module.API = SOURCE, out/"dedup", endpoint
    original=module.compare
    def checked(*args):
        for attempt in range(3):
            answer=original(*args)
            if answer.get("http_status")==200:
                return answer
            if attempt<2 and answer.get("http_status") in (None,408,429,500,502,503,504):
                time.sleep(15*(attempt+1))
            else:
                raise RuntimeError("Local Qwen dedup transport failed: "+answer.get("error","unknown"))
    module.compare=checked
    prompt=(ROOT / PROMPTS["dedup"]).read_text()
    mapping={}
    counts=Counter()
    for case in cases:
        eid=case["episode_id"]
        update(phase="dedup",current_episode=eid)
        nodes=node_inputs(case,candidates[eid])
        data={k:case[k] for k in ("case_number","case_index","episode_id","real_episode_id","scene")}
        result=module.run_case(dict(data,nodes=nodes),LOCAL_AUTH,prompt,settings)
        mapping[eid]=freeze_nodes(case,nodes,result["final_active_ids"])
        save(out/"effective_nodes"/(eid+".json"),mapping[eid])
        counts.update(result["summary"])
        update(dedup_complete=len(mapping),dedup_counts=dict(counts))
    save(out/"retained_nodes_and_terminals.json",mapping)


def compare_annotations(out, results, frozen):
    file=SAMPLE.parents[2]/"attribution.csv"
    with file.open(encoding="utf-8-sig") as stream:
        truth={row["episode_id"]:row for row in csv.DictReader(stream)}
    rows=[]
    for r in results:
        eid=r["episode_id"]
        label=truth[eid]
        a,b=int(label["decision_step"]),int(label["confirmation_step"])
        alarm=r["first_deviation"]
        entry=dict(episode_id=eid,reference_decision=a,reference_confirmation=b,first_alarm=alarm,
                   format_errors=r["outcomes"].get("format_error",0),alarm_available_step=None,
                   offset_from_confirmation=None,timing="no_alarm")
        if alarm:
            n=next(n for n in frozen[eid] if n["id"]==alarm["current_id"])
            t=n["emittedAt"]
            entry.update(alarm_available_step=t,offset_from_confirmation=t-b,
                         timing="before_decision" if t<a else "decision_to_confirmation" if t<=b else "after_confirmation")
        rows.append(entry)
    save(out/"timing_comparison.json",rows)
    return dict(episodes=len(rows),alarm_episodes=sum(bool(r["first_alarm"]) for r in rows),
                timing_counts=dict(Counter(r["timing"] for r in rows)),
                format_errors=sum(r["format_errors"] for r in rows))


def run(out, gpu=None, allow_shared=False, startup_timeout=2700):
    if read(out/"jev/status.json")["phase"]!="complete":
        raise RuntimeError("JEV sampling is incomplete")
    ids=read(out/"dataset/index.json")["episode_ids"]
    candidates=read(out/"jev/candidates.json")
    if ids!=read(SAMPLE)["episode_ids"] or set(candidates)!=set(ids):
        raise ValueError("JEV candidates differ from the frozen RxR sample")
    cases=[read(out/"dataset"/(eid+".json")) for eid in ids]
    config=read(MODEL_CONFIG)
    config.pop("retention_authorization",None)
    settings=semantic_settings(dict(semantic_provider="qwen_local",semantic_model=config["model"],semantic_seed=2),"dedup")
    state=dict(started_at=now(),pid=os.getpid(),dedup_complete=0,deviation_complete=0,
               target_episodes=len(ids),startup_timeout_seconds=startup_timeout)
    def update(**kw):
        state.update(kw,updated_at=now())
        save(out/"status.json",state)
    signal.signal(signal.SIGTERM,signal.default_int_handler)
    child,locks=None,[]
    os.environ["NO_PROXY"]=os.environ["no_proxy"]="127.0.0.1,localhost"
    try:
        child,endpoint,gpu=get_service(out,config,locks,update,gpu,allow_shared)
        update(phase="loading_qwen",gpu=gpu,service_pid=child.pid)
        wait_local(child,endpoint,config["model"],timeout_seconds=startup_timeout)
        save(out/"service/settings.json",dict(config=config,settings=settings,gpu=gpu,endpoint=endpoint))
        dedup_cases(out,cases,candidates,endpoint,settings,update)
        path=out/"retained_nodes_and_terminals.json"
        frozen=read(path)
        if set(frozen)!=set(ids):
            raise ValueError("Incomplete first-round node list")
        for c in cases:
            c["nodes"]=frozen[c["episode_id"]]
            c["final_active_ids"]=[n["id"] for n in c["nodes"]]
            c["terminal_frame"]=len(c["frames"])-1
            c["image_paths"]={f["image"]:str(SOURCE/f["path"]) for f in c["frames"]}
        update(phase="deviation",dedup_complete=len(cases),current_episode=None,
               frozen_nodes_sha256=file_hash(path))
        results=review_qwen_cases(out/"deviation",cases,DEVIATION_PROMPT.read_text(),
                                  settings,endpoint,gpu,VERSION,transport_retries=2)
        summary=compare_annotations(out,results,frozen)
        update(phase="complete",deviation_complete=len(results),finished_at=now(),summary=summary)
    except BaseException as exc:
        update(phase="failed",error=str(exc))
        raise
    finally:
        try:
            if child is not None:
                report=cleanup(child)
                save(out/"service/cleanup.json",dict(owned=report,snapshot=gpu_snapshot(),at=now()))
                if report["remaining"]:
                    update(phase="cleanup_failed")
                    raise RuntimeError("Owned Qwen subprocesses remain after cleanup")
        finally:
            for lock in locks:
                lock.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--gpu",type=int,help="Restrict the model service to this physical GPU")
    parser.add_argument("--allow-shared-gpu",action="store_true",help="Use the existing low-load and free-memory admission checks")
    parser.add_argument("--startup-timeout",type=int,default=2700,help="Maximum seconds to wait for the owned local model service")
    args=parser.parse_args()
    if args.allow_shared_gpu and args.gpu is None:
        parser.error("--allow-shared-gpu requires an explicitly selected --gpu")
    if args.startup_timeout <= 0:
        parser.error("--startup-timeout must be positive")
    with (args.output/"semantic.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        run(args.output.resolve(),args.gpu,args.allow_shared_gpu,args.startup_timeout)
