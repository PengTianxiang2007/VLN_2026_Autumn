"""Summarize matched request times, observed overlap and client warnings."""
from datetime import datetime
import json
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[3] / "outputs/codex_tasks/deviation_progress/codex_memory_v002"
PRIOR = BASE/"run_20261125_05_c27_frames3to7"
NOW = BASE/HERE.name
COUNTS = (3,4,5,6,7)


def read(path):
    return json.loads(path.read_text())


def records(out):
    arms = {}
    identities = {}
    for k in COUNTS:
        arm = out/f"uniform{k}"
        turn = arm/"turns/turn_0007_deviation_END"
        req = read(turn/"request.json")
        resp = read(turn/"response.json")
        session = read(arm/"session.json")
        identities[k] = (req["prompt_sha256"],[i["sha256"] for i in req["images"]],read(turn/"schema.json"),session["config"])
        messages = [m.get("message","") for s in (turn/"events.jsonl").read_text().splitlines()
                    if (m:=json.loads(s)).get("type") in {"error","turn.failed"}]
        stderr = (turn/"stderr.log").read_text().splitlines()
        arms[k] = dict(start=read(turn/"process.json")["started_at"],end=resp["completed_at"],
            elapsed=resp["elapsed_seconds"],verdict=read(arm/"result.json")["verdict"],
            reconnect_events=sum("reconnect" in s.lower() for s in messages+stderr),
            model_list_timeouts=sum("refresh available models" in s and "timed out" in s for s in stderr),
            timeout_log_lines=sum("timed out" in s.lower() or "timeout" in s.lower() for s in stderr+messages),
            output_tokens=resp["usage"]["output_tokens"],cached_tokens=resp["usage"]["cached_input_tokens"])
    times={k:(datetime.fromisoformat(v["start"]),datetime.fromisoformat(v["end"])) for k,v in arms.items()}
    for k,(start,end) in times.items():
        cuts=sorted({start,end}|{t for pair in times.values() for t in pair if start<t<end})
        spans=[(sum(a<=left<b for a,b in times.values()),(right-left).total_seconds()) for left,right in zip(cuts,cuts[1:])]
        arms[k]["peak_in_flight_including_self"]=max(n for n,_ in spans)
        arms[k]["solo_seconds"]=round(sum(t for n,t in spans if n==1),3)
    return arms,identities


def main():
    old,ids=records(PRIOR)
    new,new_ids=records(NOW)
    assert ids==new_ids
    a,b=read(PRIOR/"forks.json"),read(NOW/"forks.json")
    assert a["source_thread_id"]==b["source_thread_id"] and a["before_turn_id"]==b["before_turn_id"]
    delta={k:round(new[k]["elapsed"]-old[k]["elapsed"],3) for k in COUNTS}
    summary=dict(previous=old,repeat=new,delta_seconds=delta,
        mean_previous_seconds=round(mean(x["elapsed"] for x in old.values()),3),
        mean_repeat_seconds=round(mean(x["elapsed"] for x in new.values()),3))
    (NOW/"timing.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(summary,ensure_ascii=False))

if __name__=="__main__":
    main()
