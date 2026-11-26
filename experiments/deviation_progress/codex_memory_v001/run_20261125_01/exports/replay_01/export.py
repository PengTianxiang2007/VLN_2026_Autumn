"""Export the three completed same-thread reviews on the frozen Route53 player."""
import argparse
import base64
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / "scripts"))
from export_oracle_distance_replay import add_font, read

RUN = ROOT / "outputs/codex_tasks/deviation_progress/codex_memory_v001/run_20261125_01"
TEMPLATE = ROOT / "outputs/offline_route_dataset/v001/run_20261118_01/exports/replay_20261118_01"
CORE = ROOT / "core"


def data_uri(path, mime):
    return "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode()


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f"Unexpected template around {before[:60]}")
    return source.replace(before, after)


def screening(d, strings):
    answer = d["answer"]
    english = [answer["eligibility_reason"], answer["reason"],
               *(m["description"] for m in answer["matched_branches"]), *answer["a_only"], *answer["b_only"]]
    if len(english) != len(strings):
        raise ValueError(f"Missing screening translation for {answer['current_id']}")
    translations = dict(zip(english, strings))
    zh = dict(answer, reason=translations[answer["reason"]], eligibility_reason=translations[answer["eligibility_reason"]],
              matched_branches=[dict(m, description=translations[m["description"]]) for m in answer["matched_branches"]],
              a_only=[translations[t] for t in answer["a_only"]], b_only=[translations[t] for t in answer["b_only"]])
    return dict(action=d["action"], before=d["active_ids_before"], after=d["active_ids_after"], answer=[zh, answer])


def build(out):
    result = read(RUN / "results.json")
    records = {c["case_number"]: c for c in result["cases"]}
    assert set(records) == {25, 9, 5} and not result["failures"]
    replay = json.loads((TEMPLATE / "tasks.js").read_text().removeprefix("const REPLAY = ").strip().removesuffix(";"))
    source_tasks = {t["id"]: t for t in replay["tasks"]}
    translations = read(HERE / "screening_zh.json")
    zh_prompt = (HERE.parents[2] / "prompt_zh.txt").read_text()
    tasks, maps = [], {}
    for number in (25, 9, 5):
        c = records[number]
        t = source_tasks[c["episode_id"]]
        scene, eid = t["scene"], t["id"]
        assert t["instruction"][1] == c["instruction_en"]
        maps[scene] = dict(replay["maps"][scene], src=data_uri(TEMPLATE / "maps" / (scene + ".png"), "image/png"))
        t.update(number=number, active=c["final_active_ids"], rollback=c["rollback_target"],
                 candidates=[], reviews=[], front={}, atlas=[])
        for idx in range(len(t["robot"])):
            t["atlas"].append(data_uri(TEMPLATE / "frames" / eid / f"{idx:04}.webp", "image/webp"))
        decisions = {d["current_id"]: d for d in c["decisions"]}
        for n in c["nodes"]:
            entry = dict(id=n["id"], frame=n["index"])
            d = decisions.get(n["id"])
            if d:
                entry.update(screening(d, translations[f'C{number:02}:{n["id"]}']))
                entry["images"] = []
                for im in n["images"]:
                    if im.get("missing"):
                        continue
                    f = im["frame"]
                    entry["images"].append(f)
                    if f not in t["front"]:
                        path = TEMPLATE.parents[1] / "dataset" / im["path"]
                        t["front"][f] = data_uri(path, "image/png")
            t["candidates"].append(entry)
        progress = {}
        case_dir = RUN / "cases" / f"C{number:02}_ep{eid}" / "codex/turns"
        for r in c["deviation_reviews"]:
            folder = next(case_dir.glob(f'turn_{r["turn"]:04}_deviation_*'))
            request = read(folder / "request.json")
            assert request["images"] == [] and request["resumed_thread_id"] == c["thread_id"]
            raw = (folder / "final.txt").read_text()
            a = r["answer"]
            assert json.loads(raw) == a
            init = r["previous_id"] == r["current_id"]
            prior = [r["prior_semantic_progress"], "First effective checkpoint. Earlier route progress is unconfirmed."
                     if init else progress[r["previous_id"]]["en"]]
            if not init:
                assert prior[0] == progress[r["previous_id"]]["zh"]
            refs = r["historical_images"]
            assert all(int(f) in t["front"] and r["previous_frame"] <= int(f) <= r["current_frame"] for f in refs)
            prompt_zh = zh_prompt.format(**dict(r, instruction_en=t["instruction"][0]), observations=json.dumps(refs))
            t["reviews"].append(dict(a=r["previous_frame"], b=r["current_frame"], prior=prior, refs=refs,
                                     answer=a, raw=raw, turn=r["turn"], rollback=r["rollback_target"],
                                     prompt=[prompt_zh, (folder / "prompt.txt").read_text()]))
            if a["semantic_progress"]:
                progress[r["current_id"]] = a["semantic_progress"]
        tasks.append(t)

    html = (CORE / "offline_route_replay.html").read_text()
    player = (CORE / "offline_route_replay_player.js").read_text()
    css = (CORE / "offline_route_replay_style.css").read_text().split("\n", 1)[1]
    html = html.replace("选路错误轨迹回放", "Codex 偏航评审回放").replace("Route-choice replay", "Codex deviation replay")
    html = html.replace("StreamVLN</small>", "StreamVLN · GPT-6 Astra</small>")
    html = html.replace('value="front" data-en', 'value="front" selected data-en').replace('value="180" selected', 'value="180"')
    html = replace_once(html, '<g id="robot">', '<g id="reviewMap"></g><g id="robot">')
    html = replace_once(html, '</div></div>\n<svg', '</div></div><div id="reviewLayers" class="layers inside"></div>\n<svg')
    html = replace_once(html, '<div class="details">', '<section id="reviews" class="card"></section><section id="screening" class="card"></section><div class="details">')
    html = html.replace('Annotated events">错误事件', 'Retrospective annotation">事后归因')
    html = replace_once(html, '<link rel="stylesheet" href="style.css">', '<style>'+css+(HERE / "review.css").read_text()+'</style>')
    player = replace_once(player, "'maps/'+task.scene+'.png'", 'g.src')
    player = replace_once(player, "'frames/'+task.id+'/'+String(step).padStart(4,'0')+'.webp'", 'task.atlas[step]')
    player = replace_once(player, "syncAtlas();\n}", "syncAtlas(); markCurrent();\n}")
    player = replace_once(player, "playLabel();showEvents();setStep(step);", "playLabel();showEvents();renderReview();setStep(step);")
    player = player.replace("text('选路错误轨迹回放','Route-choice replay')", "text('Codex 偏航评审回放','Codex deviation replay')")
    player = replace_once(player, "drawRoutes();setLayers();localize();", (HERE / "review.js").read_text())
    payload = json.dumps(dict(tasks=tasks,maps=maps), ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    html = replace_once(html, '<script src="tasks.js"></script><script src="player.js"></script>',
                        '<script>const REPLAY = '+payload+';</script><script>'+player+'</script>')
    out.mkdir(parents=True, exist_ok=False)
    dest = out / "index.html"
    dest.write_text(html)
    add_font(dest)
    print(f"{dest}: {len(tasks)} cases, {sum(len(t['reviews']) for t in tasks)} reviews, "
          f"{sum(len(t['robot']) for t in tasks)} frames")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    build(parser.parse_args().out)
