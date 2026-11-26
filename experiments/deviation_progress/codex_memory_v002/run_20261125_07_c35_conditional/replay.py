"""Run C35 through its first alarm or its terminal checkpoint, per fork."""
import concurrent.futures
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core.codex_client import CodexConfig, CodexSession, save, sha256
from core.codex_deviation_review import PROMPT
from experiments.deviation_progress.codex_memory_v002.run_20261125_04_c27_interval7 import replay as shared
from scripts.run_deviation_progress_review import validate_v005

EPISODE = "kujiale_0234_23_1"
CASE = shared.SOURCE / "cases" / ("C35_ep"+EPISODE)
TURNS = CASE / "codex/turns"
OUT = shared.BASE / HERE.name
COUNTS = range(2,7)


def original(turn):
    meta = shared.read(turn/"request.json")["metadata"]
    prompt = (turn/"prompt.txt").read_text()
    assert render(meta) == prompt
    return meta, prompt, shared.read(turn/"schema.json")


def render(meta):
    return PROMPT.read_text().format(**meta, observations=json.dumps(meta["historical_images"]))


def judge(session, label, prepared, meta, schema):
    prompt, paths, samples, frames = prepared
    metadata = dict(meta, attached_frames=samples, allowed_frames=frames)
    response = session.ask(prompt, paths, schema, label=label, metadata=metadata)
    answer = validate_v005(json.loads(response["text"]),dict(meta,images=[{"frame":f} for f in frames]))
    return dict(verdict=answer["verdict"],elapsed_seconds=response["elapsed_seconds"],added=samples,
                allowed=frames,cited=sorted({f for item in answer["visual_evidence"] for f in item["frames"]}),
                reason=answer["reason"]["zh"],semantic_progress=answer["semantic_progress"])


def main():
    OUT.mkdir(exist_ok=False)
    for source in (Path(__file__), Path(shared.__file__), PROMPT):
        name = "comparison_runner.py" if source == Path(shared.__file__) else source.name
        shutil.copy2(source, OUT/name)
    first, first_prompt, schema = original(TURNS/"turn_0007_deviation_S04")
    final, _, final_schema = original(TURNS/"turn_0009_deviation_END")
    assert (first["previous_frame"],first["current_frame"],final["previous_frame"],final["current_frame"])==(0,28,28,44)
    assert first["current_id"]==final["previous_id"] and schema==final_schema
    dataset = ROOT / shared.read(shared.SOURCE/"input.json")["image_root"]
    obs = [json.loads(l) for l in (dataset/"inputs"/EPISODE/"observations.jsonl").read_text().splitlines()]
    def prepare(count, prompt, meta):
        return shared.sampled_request(count,prompt,meta,dataset,obs,episode_id=EPISODE)
    inputs = {n:prepare(n,first_prompt,first) for n in COUNTS}
    terminal = TURNS/"turn_0008_terminal_observation"
    end_request = shared.read(terminal/"request.json")
    rgb = dataset / obs[44]["native_front"]["image"]
    assert sha256(rgb)==end_request["images"][0]["sha256"] and end_request["metadata"]["frame"]==44
    end_prompt = (terminal/"prompt.txt").read_text()
    end_schema = shared.read(terminal/"schema.json")
    old_session = shared.read(CASE/"codex/session.json")
    config = CodexConfig(**old_session["config"])
    save(OUT/"protocol.json",dict(episode=EPISODE,counts=list(COUNTS),workers=4,
         first_history=list(map(int,first["historical_images"])),first_added={n:item[2] for n,item in inputs.items()},
         end_history=list(map(int,final["historical_images"])),end_added=prepare(5,render(final),final)[2],
         git_head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
         sources={str(p.resolve().relative_to(ROOT)):sha256(p) for p in (Path(__file__),Path(shared.__file__),PROMPT,ROOT/"core/codex_client.py",ROOT/"scripts/run_deviation_progress_review.py")}))
    names = [f"uniform{n}" for n in COUNTS]
    ids = shared.fork_reviews(config,old_session["thread_id"],first_prompt,names,OUT)

    def branch(n):
        name = f"uniform{n}"
        folder = OUT/name
        session = CodexSession(folder,config,thread_id=ids[name],turn_count=6)
        stage1 = judge(session,"deviation_S04",inputs[n],first,schema)
        result = dict(first=stage1,terminal_ack_seconds=None,second=None)
        save(folder/"first.json",stage1)
        print(name,"first",stage1["verdict"],stage1["elapsed_seconds"],flush=True)
        if stage1["verdict"]=="consistent":
            ack = session.ask(end_prompt,[rgb],end_schema,label="terminal_observation",metadata=end_request["metadata"])
            if json.loads(ack["text"])!={"ready":True}:
                raise ValueError("Missing terminal image acknowledgement")
            meta = dict(final,prior_semantic_progress=stage1["semantic_progress"]["zh"])
            stage2 = judge(session,"deviation_END",prepare(5,render(meta),meta),meta,schema)
            result.update(second=stage2,terminal_ack_seconds=ack["elapsed_seconds"])
            print(name,"second",stage2["verdict"],stage2["elapsed_seconds"],flush=True)
        save(folder/"result.json",result)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=dict(zip(names,pool.map(branch,COUNTS)))
    save(OUT/"comparison.json",results)

if __name__=="__main__":
    main()
