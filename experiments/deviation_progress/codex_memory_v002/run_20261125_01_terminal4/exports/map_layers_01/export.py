"""Adapt the designated 42-case map-layer template to one or more completed terminal-review runs."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
RUN = ROOT / "outputs/codex_tasks/deviation_progress/codex_memory_v002" / HERE.parents[1].name
TEMPLATE = ROOT / "outputs/crossing_checkpoint/online_sampling_v003/run_20261124_01/exports/map_layers_20261125_01/index.html"
PROMPTS = ROOT / "experiments/deviation_progress/codex_memory_v001"
sys.path.insert(0, str(ROOT / "scripts"))
from export_oracle_distance_replay import add_font


def read(p):
    return json.loads(p.read_text())


def uri(path):
    mime = "webp" if path.suffix == ".webp" else "png"
    return f"data:image/{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def between(text, start, end, replacement):
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[:i] + replacement + text[j:]


def prepare_case(c, item, dataset, run):
    eid = c["episode_id"]
    assert item["instruction_en"] == c["instruction_en"]
    terminal = c["terminal_node"]
    fid = terminal["index"]
    image = terminal["images"][0]
    rows = (dataset / "inputs" / eid / "observations.jsonl").read_text().splitlines()
    end = json.loads(rows[-1])
    assert fid == end["step"] == len(item["frames"]) and image["image_id"] == end["native_front"]["sha256"]
    item["frames"].append(dict(frame=fid, position=end["robot_pose"]["position_world_m"], image=image["image_id"], jev=None))
    annotation = read(dataset / "evaluation/episodes" / (eid + ".json"))["annotation"]
    item["referenceErrors"] = [e["decision_interval_steps"] for e in annotation["events"]]
    item["original_success"] = bool(annotation["native_metrics"]["SR"])
    decisions = {d["current_id"]: d for d in c["decisions"]}
    sample = []
    for node in c["nodes"]:
        f = node["index"]
        d = decisions.get(node["id"], {})
        sample.append(dict(id=node["id"], index=f, emittedAt=node["emittedAt"], value=item["frames"][f]["jev"]["probability_yes"],
                           action=d.get("action","unreviewed"), previous=d.get("previous_id"), active=d.get("active_ids_after"),
                           imageFrames=[i["frame"] for i in node["images"] if not i.get("missing")]))
    if "comparisons" in item:
        assert [n["index"] for n in sample] == item["comparisons"]["active"]["frames"]
    item["samples"], item["effective"] = sample, [n for n in sample if n["id"] in c["final_active_ids"]]
    item["terminalReviewed"], item["alarm"], item["end"] = c["terminal_reviewed"], c["rollback_target"], fid
    item["group"] = ("initOnly" if c["stop_reason"] == "terminal_initialization_only" else
                     "alarmed" if c["rollback_target"] else "quiet")
    folder = run / "cases" / (item["case_id"] + "_ep" + eid) / "codex/turns"
    prior_en, item["rounds"] = {}, []
    zh_template = (PROMPTS / "prompt_zh.txt").read_text()
    for r in c["deviation_reviews"]:
        f = next(folder.glob(f'turn_{r["turn"]:04d}_deviation_*'))
        req = read(f / "request.json")
        added = r.get("attached_frames", [])
        assert len(req["images"]) == len(added) and req["resumed_thread_id"] == c["thread_id"]
        a = r["answer"]
        raw = (f / "final.txt").read_text()
        assert json.loads(raw) == a
        is_end = r.get("terminal_node", False)
        if is_end:
            ack = next(folder.glob(f'turn_{r["observation_turn"]:04d}_terminal_observation'))
            attached = read(ack / "request.json")
            assert attached["resumed_thread_id"] == c["thread_id"] and [im["sha256"] for im in attached["images"]] == [image["image_id"]]
        prior = [r["prior_semantic_progress"], ("First effective checkpoint. Earlier route progress is unconfirmed."
                 if r["previous_id"] == r["current_id"] else prior_en[r["previous_id"]])]
        refs = r.get("available_images", r["historical_images"])
        assert all(r["previous_frame"] <= int(n) <= r["current_frame"] for n in refs)
        prompt = zh_template.format(**dict(r, instruction_en=item["instruction_zh"]), observations=json.dumps(refs))
        if added:
            prompt = prompt.replace("会话中已经提供的图像", "本轮可使用的图像").replace(
                "使用本会话中已经提供的视觉观测。", "使用本会话中已经提供的视觉观测和本次请求所附的图像。")
            prompt += "\n" + "\n".join(f"附件 {i:02d} 为 interval/F{frame}，对应动作帧 {frame}。"
                                      for i, frame in enumerate(added, 1))
        item["rounds"].append(dict(a=r["previous_frame"], b=r["current_frame"], answer=a, refs=refs, added=added, terminal=is_end,
            turn=r["turn"], raw=raw, prior=prior, prompts=[prompt,(f/"prompt.txt").read_text()]))
        if a["semantic_progress"]:
            prior_en[r["current_id"]] = a["semantic_progress"]["en"]
    item["initial_index"] = item["rounds"][-1]["b"]
    for key in ("comparisons","pairs","reference_frames"):
        item.pop(key, None)
    return image


def export(out, runs):
    html = TEMPLATE.read_text()
    pattern = r'(<script id="payload" type="application/json">)(.*?)(</script>)'
    bundle = json.loads(re.search(pattern,html,re.S)[2])
    by_eid = {c["episode_id"]: c for c in bundle["cases"]}
    full_root = ROOT / "outputs/visualization_publishing/jev_route53_sampling_v001_web_20261118_01"
    full = json.loads(re.search(pattern, (full_root / "index.html").read_text(), re.S)[2])
    for item in full["cases"]:
        by_eid.setdefault(item["episode_id"], item)
    cases, extra, seen = [], {}, set()
    for run in runs:
        data = read(run / "results.json")
        assert not data["failures"] and read(run / "status.json")["status"] == "complete"
        dataset = ROOT / read(run / "input.json")["image_root"]
        for c in data["cases"]:
            number = c["case_number"]
            item = by_eid[c["episode_id"]]
            item.setdefault("case_id", f"C{number:02d}")
            if number in seen or item["case_id"] != f"C{number:02d}":
                raise ValueError(f"Duplicate or mismatched case {number} in {run}")
            seen.add(number)
            image = prepare_case(c, item, dataset, run)
            extra[image["image_id"]] = dataset / image["path"]
            cases.append(item)
    cases.sort(key=lambda item: int(item["case_id"][1:]))
    maps = {c["scene"]:full["maps"][c["scene"]] for c in cases}
    keys = {f["image"] for c in cases for f in c["frames"]} | {m["image"] for m in maps.values()}
    with ThreadPoolExecutor(max_workers=12) as pool:
        ordered = sorted(keys)
        paths = [extra[k] if k in extra else full_root / full["images"][k] for k in ordered]
        images = dict(zip(ordered, pool.map(uri, paths)))
    summary = dict(candidates=sum(len(c["samples"]) for c in cases),
                   reviews=sum(len(c["rounds"]) for c in cases), alarms=sum(bool(c["alarm"]) for c in cases))
    bundle.update(cases=cases,images=images,maps=maps,summary=summary,tag="codex_memory_v002_terminal4_01")
    html = re.sub(pattern,lambda m:m[1]+json.dumps(bundle,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")+m[3],html,count=1,flags=re.S)
    # Reuse map, curve, media, sliders, case navigation and the reference template's layer legend.
    html = between(html,"const LAYER_ORDER=","let lang=", """const LAYER_ORDER=['active','Astra'];
const SAMPLING_VERSIONS=[{id:'active',title:'rawActive',description:'rawActive',color:'#c93c76'},
{id:'Astra',title:'effectiveNodes',description:'effectiveNodes',color:'#54218b'}];
""")
    html = between(html,"    const session=fullSampling(version),allNodes=","  });\n  return {values:fullCurve()", """    const nodes=version.id==='active'?c().samples:c().effective;
    return {version,nodes,allNodes:nodes,upstreamNodes:nodes,dedupRecord:null};
""")
    html = between(html,"  const active=state.versions.flatMap","function renderElimination", """  const n=c().effective.find(n=>n.index===index),end=index===c().end&&c().terminalReviewed;
  $('currentNodeStatus').hidden=!n&&!end;$('currentNodeStatus').textContent=end?'END':(n?.id||'');
  $('rgb').classList.toggle('isNode',!!n||end);
}
""")
    html = html.replace("  const [x,y]=xy(row().position);","  routeLayer(ctx,xy);\n  const [x,y]=xy(row().position);")
    html = html.replace("  sampleHitPoints=[];", "  roundPlot(ctx,x,y(1),axisY);\n  sampleHitPoints=[];")
    html = html.replace("  renderElimination(state);renderDedup(state);", "  reviewPanel();")
    html = between(html,"  $('caseStats').textContent=t('caseStats'","  loadNote();draw();","  $('caseStats').textContent=caseSummary(c());\n")
    html = between(html,"  const values=[['candidateCount'","  for(const [label,value]of values)",
        "  const values=[['rawActive',B.summary.candidates],['trajectories',B.cases.length],['roundsLabel',B.summary.reviews],['alarmsLabel',B.summary.alarms]];\n")
    html = html.replace("${t(item.group)} · ${item.frames.length}", "${t(item.group)} · ${t(item.original_success?'baselineWin':'baselineFail')} · ${t('unscored')} · ${item.frames.length}")
    html = html.replace('<option value="design" data-i18n="design">','<option value="alarmed" data-i18n="alarmed">').replace(
        '<option value="validation" data-i18n="validation">','<option value="quiet" data-i18n="quiet">')
    html = html.replace('<option value="quiet" data-i18n="quiet"></option>', '<option value="quiet" data-i18n="quiet"></option><option value="initOnly" data-i18n="initOnly"></option>')
    html = html.replace('<h3 data-i18n="plot">','<div id="routeReviews"></div><h3 data-i18n="plot">',1)
    html = html.replace("createVersionControls();\nfor(const id", (HERE/"extension.js").read_text()+"\ncreateVersionControls();\nfor(const id",1)
    html = between(html,"// Optional local review link;","const controls = $('samplingVersions')","</script><script>\n")
    html = html.replace("updateLanguage();\n</script></body>", "setupTerminalReplay();\n</script></body>")
    html = html.replace("</head>","<style>"+(HERE/"extension.css").read_text()+"</style></head>",1)
    # An unscored terminal RGB must not advance the historical score stream.
    html = html.replace("while(session.cursor<index){const frame=++session.cursor,result=", "while(session.cursor<Math.min(index,c().end-1)){const frame=++session.cursor,result=")
    html = html.replace("for(const frame of c().frames){const result=model.push", "for(const frame of c().frames.slice(0,c().end)){const result=model.push")
    html = re.sub(r'<style id="embedded-font">.*?</style>', '', html, flags=re.S)
    out.mkdir(parents=True,exist_ok=False)
    destination=out/"index.html";destination.write_text(html);add_font(destination)
    print(summary, sum(len(c["frames"]) for c in cases), "trajectory frames")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--run", type=Path, action="append", help="Completed run output directory, repeat to merge")
    args = parser.parse_args()
    export(args.output, args.run or [RUN])
