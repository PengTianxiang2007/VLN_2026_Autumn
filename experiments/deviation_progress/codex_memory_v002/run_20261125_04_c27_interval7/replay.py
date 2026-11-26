"""Compare two final C27 reviews forked before the recorded terminal decision."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from core.codex_client import CodexConfig, CodexSession, save, sha256
from scripts.run_deviation_progress_review import validate_v005

BASE = ROOT / "outputs/codex_tasks/deviation_progress/codex_memory_v002"
SOURCE = BASE / "run_20261125_02_random5"
EPISODE = "kujiale_0226_38_4"
CASE = SOURCE / "cases" / ("C27_ep" + EPISODE)
TURN = CASE / "codex/turns/turn_0007_deviation_END"
OUT = BASE / HERE.name



def read(path):
    return json.loads(path.read_text())


def fork_reviews(config, source_id, original_prompt, names, out):
    env = dict(os.environ, CODEX_HOME=config.home)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env[key] = config.proxy_url
    with (out / "fork.stderr").open("w") as err, subprocess.Popen(
        [config.binary, "app-server"], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=err, text=True
    ) as rpc:
        def send(msg):
            rpc.stdin.write(json.dumps(msg) + "\n")
            rpc.stdin.flush()

        def call(seq, method, params):
            send(dict(id=seq, method=method, params=params))
            for line in rpc.stdout:
                msg = json.loads(line)
                if msg.get("id") == seq:
                    if "error" in msg:
                        raise RuntimeError(str(msg["error"]))
                    return msg["result"]
            raise RuntimeError("App server closed")

        def turns(tid, seq):
            return call(seq, "thread/read", {"threadId": tid, "includeTurns": True})["thread"]["turns"]

        def texts(turn):
            return [x["text"].strip() for i in turn["items"] if i["type"]=="userMessage"
                    for x in i["content"] if x["type"]=="text"]

        try:
            call(1, "initialize", {"clientInfo": {"name":"vln_interval_pair","version":"1.0"},
                                   "capabilities": {"experimentalApi":True}})
            send({"method":"initialized"})
            history = turns(source_id, 2)
            assert [i for i,t in enumerate(history) if original_prompt.strip() in texts(t)] == [6]
            boundary = history[6]["id"]
            ids = {}
            for i, name in enumerate(names):
                fork = call(3+2*i, "thread/fork", {"threadId":source_id,"beforeTurnId":boundary,
                           "model":config.model,"sandbox":"read-only","approvalPolicy":"never"})
                tid = fork["thread"]["id"]
                assert tid != source_id and tid not in ids.values()
                inherited = turns(tid,4+2*i)
                assert [texts(t) for t in inherited] == [texts(t) for t in history[:6]]
                ids[name] = tid
            save(out/"forks.json",dict(source_thread_id=source_id,before_turn_id=boundary,prior_turns=6,branches=ids))
            return ids
        finally:
            rpc.stdin.close()
            rpc.terminate()


def sampled_request(count, prompt, meta, dataset, observations, episode_id=EPISODE):
    a, b = meta["previous_frame"], meta["current_frame"]
    history = meta["historical_images"]
    if count == 0:
        return prompt, [], [], list(map(int, history))
    divisions = count + 1
    available = set(range(a+1, b)).difference(map(int, history))
    if len(available) < count:
        raise ValueError(f"Only {len(available)} new frames remain between F{a} and F{b}")
    samples = []
    for i in range(1, divisions):
        target = (b-a)*i
        frame = min(available, key=lambda f: (abs((f-a)*divisions-target), -f))
        samples.append(frame)
        available.remove(frame)
    samples.sort()
    paths = []
    attachment_refs = {}
    for i,f in enumerate(samples,1):
        row = observations[f]
        assert row["step"]==f and row["episode_id"]==episode_id
        image = dataset/row["native_front"]["image"]
        assert sha256(image)==row["native_front"]["sha256"]
        attachment_refs[str(f)] = [f"Attachment {i:02d} (F{f})"]
        paths.append(image)
    merged = dict(sorted((history|attachment_refs).items(),key=lambda kv:int(kv[0])))
    old_header = "Already supplied image references, grouped by actual frame: " + json.dumps(history)
    old_line = "Use the visual observations already supplied in this conversation."
    assert prompt.count(old_header)==1 and prompt.count(old_line)==1
    augmented = prompt.replace(old_header, "Available image references, grouped by actual frame: "+json.dumps(merged))
    augmented = augmented.replace(old_line,"Use the visual observations already supplied in this conversation and the numbered images attached to this request.")
    return augmented, paths, samples, list(map(int, merged))


def run_comparison(out, counts, workers, entry_file):
    out.mkdir(exist_ok=False)
    shutil.copy2(entry_file, out/"replay.py")
    if entry_file.resolve() != Path(__file__).resolve():
        shutil.copy2(__file__, out/"comparison_runner.py")
    source_session = read(CASE/"codex/session.json")
    config = CodexConfig(**source_session["config"])
    prompt = (TURN/"prompt.txt").read_text()
    req = read(TURN/"request.json")
    assert not req["images"]
    meta = req["metadata"]
    a,b = meta["previous_frame"],meta["current_frame"]
    history = meta["historical_images"]
    assert (a,b,list(history)) == (7,42,["7","9","42"])
    schema = read(TURN/"schema.json")
    dataset = ROOT / read(SOURCE/"input.json")["image_root"]
    observations = [json.loads(s) for s in (dataset/"inputs"/EPISODE/"observations.jsonl").read_text().splitlines()]
    arms = {("uniform"+str(count) if count else "original"):
            sampled_request(count, prompt, meta, dataset, observations) for count in counts}
    save(out/"protocol.json",dict(frames_by_branch={k:v[2] for k,v in arms.items()},
         historical_frames=list(map(int,history)), workers=workers, git_head=subprocess.check_output(
         ["git","rev-parse","HEAD"],text=True).strip(),source_prompt_sha256=sha256(TURN/"prompt.txt"),
         source_snapshot={str(p.relative_to(ROOT)):sha256(p) for p in (entry_file.resolve(), Path(__file__).resolve(),ROOT/"core/codex_client.py",ROOT/"scripts/run_deviation_progress_review.py")}))
    ids = fork_reviews(config,source_session["thread_id"],prompt,arms,out)

    def review(name):
        sent_prompt, paths, samples, frames = arms[name]
        metadata = dict(meta, attached_frames=samples, allowed_frames=frames) if samples else meta
        session = CodexSession(out/name,config,thread_id=ids[name],turn_count=6)
        response = session.ask(sent_prompt,paths,schema,label="deviation_END",metadata=metadata)
        answer = validate_v005(json.loads(response["text"]),dict(meta,images=[{"frame":f} for f in frames]))
        result = dict(verdict=answer["verdict"],elapsed_seconds=response["elapsed_seconds"],new_images=len(paths),
                      attached_frames=samples,available_frames=frames,
                      cited_frames=sorted({f for e in answer["visual_evidence"] for f in e["frames"]}),
                      reason=answer["reason"]["zh"],segment=answer["segment_summary"]["zh"],usage=response["usage"])
        save(out/name/"result.json",result)
        print(name, result["verdict"], result["elapsed_seconds"], flush=True)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(zip(arms,pool.map(review,arms)))
    save(out/"comparison.json",results)


if __name__=="__main__":
    run_comparison(OUT, (0, 7), 2, Path(__file__))
