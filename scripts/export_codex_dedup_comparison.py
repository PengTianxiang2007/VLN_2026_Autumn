"""Export a completed Codex run using the original dedup replay page."""
import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.codex_client import save, sha256, now
from core.codex_node_dedup import comparison_prompt
from core.codex_checkpoint_review import MODE

QWEN_RUN = ROOT / "outputs/deviation_progress/v003/run_20261118_01_qwen27b"
DEEPSEEK_RUN = ROOT / "outputs/deviation_progress/v003/run_20261118_02_deepseek10"
QWEN_HTML = QWEN_RUN / "exports/all53_dedup_01/index.html"
DEEPSEEK_HTML = DEEPSEEK_RUN / "exports/dedup_01/index.html"


def read(path):
    return json.loads(path.read_text())


def payload(html):
    match = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
    return match, json.loads(match.group(1))


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("Template changed near " + before[:80])
    return text.replace(before, after, 1)


def answer_texts(answer):
    return [answer["reason"], *[m["description"] for m in answer["matched_branches"]],
            *answer["a_only"], *answer["b_only"], *([answer["eligibility_reason"]] if "eligibility_reason" in answer else [])]


def read_translations(record):
    source_texts = read(record / "translation_source.json")
    english_source = bool(source_texts and "en" in source_texts[0])
    lines = (record / ("review_zh.txt" if english_source else "review_en.txt")).read_text().splitlines()
    if len(lines) != len(source_texts):
        raise ValueError("Incomplete display translations")
    translations = {}
    for index, (source, line) in enumerate(zip(source_texts, lines, strict=True), 1):
        number, en = line.split(" ", 1)
        if number != str(index) or source["id"] != f"T{index:04d}" or not en.strip():
            raise ValueError("Translation alignment changed")
        if english_source:
            translations[en] = source["en"]
        else:
            translations[source["zh"]] = en
    return translations


def memory_prompt_zh(request, current, strings):
    metadata = request["metadata"]
    previous = metadata["previous_id"]
    lines = [strings["candidate"].format(candidate_id=current["candidate_id"],
             previous_checkpoint_id=previous or "NONE（尚无保留的回退点）")]
    if previous is None:
        lines.append("目前还没有保留的回退点。请评估资格，并将 relation 设为 not_compared。")
    else:
        lines.append(f"程序指定 {previous} 为上一保留的回退点。即使中间轮次出现过其他候选，也请使用该编号。其图像已在会话历史中提供。")
    lines += [f"当前候选编号为 {current['candidate_id']}，位于动作步 {current['index']}。", strings["contract"]]
    for im in metadata["image_labels"]:
        if im.get("missing"):
            lines.append(f"{im['image_ref']} 不可用，因为当时轨迹尚未开始。")
        else:
            lines.append(f"附件 {im['number']:02d} 为 {im['image_ref']}，动作步 {im['frame']}，本轮引用标签为 {im['label']}。")
    if metadata.get("reused_current_images"):
        lines.insert(0, f"上一次调用在切换连接时中断。请使用本会话中已经提供的图像，继续评审候选 {current['candidate_id']}。")
    return "\n\n".join(lines)


def translate_memory_decision(decision, translations):
    chinese = {english: zh for zh, english in translations.items()}
    decision["reason"] = chinese[decision["reason"]]
    answer = decision.get("answer")
    if answer:
        for key in ("reason", "eligibility_reason"):
            answer[key] = chinese[answer[key]]
        for match in answer["matched_branches"]:
            match["description"] = chinese[match["description"]]
        for key in ("a_only", "b_only"):
            answer[key] = [chinese[text] for text in answer[key]]


def export(run, record, offline, online, previous_run=None, previous_record=None):
    status, results = read(run / "status.json"), read(run / "results.json")
    if status["status"] != "complete" or results.get("failures"):
        raise ValueError("Wait for all requested cases to finish")
    originals = results["cases"]
    ids = [c["episode_id"] for c in originals]
    html = QWEN_HTML.read_text()
    match, bundle = payload(html)
    _, deep_bundle = payload(DEEPSEEK_HTML.read_text())
    deep_summary_path = DEEPSEEK_RUN / "dedup_resume_01/summary.json"
    deep_results = read(deep_summary_path)["case_results"]
    offsets = originals[0].get("observation_offsets", [-2, -1, 0, 1, 2])
    memory = originals[0].get("mode") == MODE
    primary = ("memory" if memory else "astra62" if status["config"]["model"] == "gpt-6.2-astra" else
               "astra3" if offsets == [-2, 0, 2] else "astra")
    tag = online.name
    astra = copy.deepcopy(bundle["dedup"])
    name = "GPT-6.2 Astra" if primary == "astra62" else "GPT-6 Astra"
    astra.update(model=status["config"]["model"], display_model=name, model_detail=name + " · Codex · medium",
                 observation_offsets=offsets, prompt_zh=comparison_prompt(offsets),
                 translations=read_translations(record), cases=copy.deepcopy(originals), phase_note_zh=f"{len(originals)} 条第一轮去重完成",
                 phase_note_en=f"First-stage deduplication complete for {len(originals)} trajectories")
    if offsets == [-2, 0, 2]:
        astra["prompt_en"] = astra["prompt_en"].replace("A-2, A-1, A0, A+1, A+2 and B-2, B-1, B0, B+1, B+2", "A-2, A0, A+2 and B-2, B0, B+2").replace("such as A0, A+1 and B-1", "such as A0, A+2 and B-2")
    if memory:
        prompt_strings = read(ROOT / "core/codex_checkpoint_prompts_zh.json")
        astra.update(mode=MODE, source_language="en", prompt_zh=prompt_strings["candidate"],
                     prompt_en=(run / "source/core/codex_checkpoint_candidate_en.txt").read_text(),
                     initialization_zh=prompt_strings["initialization"],
                     initialization_en=(run / "source/core/codex_checkpoint_initialization_en.txt").read_text())
    models = {primary: astra}
    if previous_run:
        previous_status, previous = read(previous_run / "status.json"), read(previous_run / "results.json")
        if previous_status["status"] != "complete" or previous.get("failures"):
            raise ValueError("Previous run is incomplete")
        old = copy.deepcopy(bundle["dedup"])
        old_offsets = previous["cases"][0].get("observation_offsets", [-2, -1, 0, 1, 2])
        old.update(model=previous_status["config"]["model"], display_model="GPT-6 Astra", model_detail="GPT-6 Astra · Codex · medium",
                   observation_offsets=old_offsets, prompt_zh=comparison_prompt(old_offsets),
                   translations=read_translations(previous_record), cases=copy.deepcopy(previous["cases"]))
        if old_offsets == [-2, 0, 2]:
            old["prompt_en"] = old["prompt_en"].replace("A-2, A-1, A0, A+1, A+2 and B-2, B-1, B0, B+1, B+2", "A-2, A0, A+2 and B-2, B0, B+2").replace("such as A0, A+1 and B-1", "such as A0, A+2 and B-2")
        models["astra3" if old_offsets == [-2, 0, 2] else "astra"] = old
    models.update(qwen=copy.deepcopy(bundle["dedup"]), deepseek=copy.deepcopy(deep_bundle["dedup"]))
    models["deepseek"].update(display_model="DeepSeek", model_detail="DeepSeek-V4.1-Flash")
    provenance = {str(p.relative_to(ROOT)): sha256(p) for p in (run / "results.json", QWEN_HTML, DEEPSEEK_HTML, deep_summary_path,
                  record / "translation_source.json", record / ("review_zh.txt" if memory else "review_en.txt"), Path(__file__),
                  ROOT / "core/codex_dedup_comparison.js")}
    if memory:
        p = ROOT / "core/codex_checkpoint_prompts_zh.json"
        provenance[str(p.relative_to(ROOT))] = sha256(p)
    if previous_run:
        for p in (previous_run / "results.json", previous_record / "translation_source.json", previous_record / "review_en.txt"):
            provenance[str(p.relative_to(ROOT))] = sha256(p)
    for key, model in models.items():
        records = {c["episode_id"]: c for c in model["cases"] if c["episode_id"] in ids}
        model["cases"] = []
        model["source_tag"] = tag
        model.setdefault("observation_offsets", [-2, -1, 0, 1, 2])
        if "prompt_en" not in model:
            model["prompt_en"] = bundle["dedup"]["prompt_en"]
        for i, original in enumerate(originals):
            eid = original["episode_id"]
            if eid not in records:
                continue
            case = records[eid]
            case["case_index"] = i
            # Candidate identities stay paired; three-frame evidence is a subset
            # of the historical five-frame windows, never a different image.
            expected = [(n["id"], n["index"], n["emittedAt"]) for n in original["nodes"]]
            actual = [(n["id"], n["index"], n["emittedAt"]) for n in case["nodes"]]
            if expected != actual:
                raise ValueError("Unpaired candidate/evidence set: " + key + " / " + eid)
            for current, compared in zip(original["nodes"], case["nodes"], strict=True):
                evidence = {im["frame"]: (im.get("image_id"), bool(im.get("missing"))) for im in compared["images"]}
                if any(evidence.get(im["frame"]) != (im.get("image_id"), bool(im.get("missing"))) for im in current["images"]):
                    raise ValueError("Shared evidence differs: " + key + " / " + eid)
            if key in ("qwen", "deepseek"):
                source_run = QWEN_RUN if key == "qwen" else DEEPSEEK_RUN
                result_path = source_run / (deep_results[eid]["result"] if key == "deepseek" else
                                            f"dedup/cases/C{case['case_number']:02d}/result.json")
                provenance[str(result_path.relative_to(ROOT))] = sha256(result_path)
                actual_result = read(result_path)
                if actual_result["final_active_ids"] != case["final_active_ids"]:
                    raise ValueError("Published model results differ from original run")
            for node in case["nodes"]:
                for im in node["images"]:
                    im.pop("path", None)
            for decision in case["decisions"]:
                if decision["needs_model"]:
                    if key not in ("qwen", "deepseek"):
                        folder = Path(decision.pop("response_directory"))
                        decision["elapsed_seconds"] = read(folder / "response.json")["elapsed_seconds"]
                        decision["raw_text"] = (folder / "final.txt").read_text()
                        if key == "memory":
                            decision["prompt_en"] = (folder / "prompt.txt").read_text()
                            current = next(n for n in case["nodes"] if n["id"] == decision["current_id"])
                            decision["prompt_zh"] = memory_prompt_zh(read(folder / "request.json"), current, prompt_strings)
                            translate_memory_decision(decision, model["translations"])
                    else:
                        path = result_path.parent / "requests" / (decision["current_id"] + ".response.json")
                        decision["raw_text"] = read(path)["response"]["choices"][0]["message"]["content"]
                    for text in answer_texts(decision.get("answer") or decision["unvalidated_answer"]):
                        if not model["translations"].get(text):
                            raise ValueError("Missing translation: " + text)
                else:
                    gap = decision["step_gap"]
                    model["translations"][decision["reason"]] = ("First candidate; retain it directly." if gap is None else
                        f"The gap is {gap} steps, exceeding 8; retain the current candidate directly.")
            # Do not duplicate the private case input or CLI metadata in the page.
            model["cases"].append({k: case[k] for k in ("case_number", "case_index", "episode_id", "real_episode_id",
                "nodes", "final_active_ids", "summary", "decisions")})
        model["summary"] = {k: sum(c["summary"][k] for c in model["cases"])
                            for k in ("candidates", "retained", "removed", "model_calls", "uncertain")}
        model["coverage"] = len(model["cases"])
    cases_by_id = {c["episode_id"]: c for c in bundle["cases"]}
    cases = [cases_by_id[eid] for eid in ids]
    for c, result in zip(cases, originals, strict=True):
        c["case_number"] = result["case_number"]
    maps = {c["scene"]: bundle["maps"][c["scene"]] for c in cases}
    images = {f["image"] for c in cases for f in c["frames"]} | {m["image"] for m in maps.values()}
    bundle.update(tag=tag, cases=cases, maps=maps, images={key: bundle["images"][key] for key in sorted(images)},
                  dedup=models[primary], modelReviews=models, primaryModel=primary,
                  summary=dict(valid_calls=sum(len(c["frames"]) for c in cases), candidates=results["summary"]["candidates"],
                               retained=results["summary"]["retained"], comparisons=results["summary"]["model_calls"]))
    content = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html[:match.start(1)] + content + html[match.end(1):]
    html = replace_once(html, "const D=B.dedup;", "let D=B.dedup;")
    html = replace_once(html, "heading.className='muted';heading.textContent=", "if(!node)continue;heading.className='muted';heading.textContent=")
    html = replace_once(html, "String(D.cases[i].case_number)", "String(B.cases[i].case_number)")
    controls = '''<section class="panel" id="modelComparison">
<h2 data-i18n="comparisonTitle"></h2><p data-i18n="comparisonHelp"></p>
<div id="modelFilters"></div><p id="combinationStatus" aria-live="polite"></p>
<div class="comparisonTableWrap"><table id="modelSummary"></table></div>
<p><label for="reviewModel" data-i18n="reviewModelLabel"></label> <select id="reviewModel"></select>
<button type="button" id="showRawCandidates" data-i18n="rawCandidatesButton"></button></p>
<details><summary data-i18n="candidateTableTitle"></summary><div class="comparisonTableWrap"><table id="candidateComparison"></table></div></details>
</section>'''
    html = replace_once(html, '<main class="layout">', controls + '<main class="layout">')
    html = replace_once(html, '<p id="dedupReason"></p>', '<p id="dedupReason"></p><details id="rawAnswer"><summary data-i18n="rawAnswerLabel"></summary><pre id="rawAnswerText"></pre></details>')
    styles = '''<style>
#nodeDeduplicationTop,#dedupControls>.eliminationOption,#dedupControls>[data-i18n="dedupHint"]{display:none!important}
#modelComparison{margin:14px 16px 0}
#modelFilters{display:flex;gap:12px;flex-wrap:wrap}#modelFilters label{display:flex;align-items:center;gap:6px;padding:9px;border:1px solid #cbd5e1;border-radius:6px}
.comparisonTableWrap{overflow-x:auto}#modelComparison table{border-collapse:collapse;width:100%;font-size:13px}
#modelComparison th,#modelComparison td{padding:7px 10px;text-align:left;border-bottom:1px solid #e2e8f0;white-space:nowrap}
.kept{color:#087354}.removed{color:#b83b3b}.unreviewed{color:#64748b}
#rawAnswerText{white-space:pre-wrap;overflow-wrap:anywhere;max-height:400px;overflow:auto}
#combinationStatus{font-weight:600}#reviewModel{max-width:100%;padding:6px}#modelComparison button{margin:4px}
</style>'''
    html = replace_once(html, "</head>", styles + "</head>")
    script = (ROOT / "core/codex_dedup_comparison.js").read_text()
    html = replace_once(html, "</body>", "<script>\n" + script + "\n</script></body>")
    archive = package_replay(html, bundle["images"], QWEN_HTML.parent, offline, online)
    snapshot = dict(created_at=now(), source_sha256=provenance, cases=ids,
                    models={k: dict(coverage=m["coverage"], summary=m["summary"]) for k, m in models.items()},
                    offline=str(offline.relative_to(ROOT)), online=str(online.relative_to(ROOT)),
                    html_sha256=sha256(offline / "index.html"), zip=str(archive.relative_to(ROOT)), zip_sha256=sha256(archive),
                    display_translations="Local assistant translation for display; original responses preserved")
    save(record / "snapshot.json", snapshot)
    print(json.dumps(snapshot["models"], ensure_ascii=False))


def package_replay(html, images, assets_dir, offline, online):
    html, font_count = re.subn(r'<style id="embedded-font">.*?</style>', '', html, flags=re.S)
    if font_count != 1:
        raise ValueError("Expected the original embedded font")
    if offline.exists() or online.exists():
        raise FileExistsError("Choose fresh export directories")
    offline.mkdir(parents=True)
    (offline / "index.html").write_text(html)
    # The historical font is a subset: include new model text and UI characters.
    font_script = '''from pathlib import Path
import base64, io, json, re, sys
from fontTools.ttLib import TTFont
from scripts.export_oracle_distance_replay import add_font
p=Path(sys.argv[1]); metadata=add_font(p)
s=p.read_text().replace('OracleSans','CrossingSans');p.write_text(s)
encoded=re.search(r'data:font/ttf;base64,([^)]*)',s).group(1)
cmap=TTFont(io.BytesIO(base64.b64decode(encoded))).getBestCmap()
missing={c for c in s if '\\u4e00'<=c<='\\u9fff' and ord(c) not in cmap}
assert not missing, str(missing)
metadata['all_display_chinese_characters_covered']=True
(p.parent/'font_check.json').write_text(json.dumps(metadata,indent=2)+'\\n')
'''
    subprocess.run([str(ROOT / "backbone/streamvln/.venv/bin/python"), "-c", font_script,
                    str(offline / "index.html")], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/prepare_online_visualization.py", "--html", str(offline / "index.html"),
                    "--destination", str(online)], cwd=ROOT, check=True)
    pkg = read(online / "online_manifest.json")
    def copy_asset(name):
        dest = offline / name
        source = assets_dir / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source != dest:
            shutil.copyfile(source, dest)
        target = online / name
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(dest, target)
        return name, sha256(dest)
    with ThreadPoolExecutor(max_workers=8) as pool:
        pkg["assets"].update(pool.map(copy_asset, sorted(set(images.values()) | {"font_license.zip"})))
    pkg.update(release=online.name, html_sha256=sha256(online / "index.html"))
    save(online / "online_manifest.json", pkg)
    archive = offline.parent / (offline.name + "_offline.zip")
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
        for file in sorted(offline.rglob("*")):
            if file.is_file():
                z.write(file, str(file.relative_to(offline)))
    # Make the complete portable package available from the published page.
    shutil.copyfile(archive, online / archive.name)
    pkg["assets"][archive.name] = sha256(archive)
    save(online / "online_manifest.json", pkg)
    return archive


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "record", "offline", "online"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--previous-run", type=Path)
    p.add_argument("--previous-record", type=Path)
    a = p.parse_args()
    if bool(a.previous_run) != bool(a.previous_record):
        p.error("--previous-run and --previous-record are required together")
    export(a.run.resolve(), a.record.resolve(), a.offline.resolve(), a.online.resolve(),
           a.previous_run.resolve() if a.previous_run else None, a.previous_record.resolve() if a.previous_record else None)
