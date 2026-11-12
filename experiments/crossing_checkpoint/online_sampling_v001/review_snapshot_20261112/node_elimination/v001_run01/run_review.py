"""One five-frame request per candidate; concurrent processes; key only in memory.

Run with DEEPSEEK_API_KEY in the environment, or --key-stdin. The browser never
receives the key and never calls an API. Completed response files are immutable.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import statistics
import sys
import time
from datetime import datetime, timezone

import httpx

RUN = Path(__file__).resolve().parent
SITE = RUN.parents[1]
API = "https://api.deepseek.com"


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate(answer, node):
    if not isinstance(answer, dict) or answer.get("candidate_id") != node["candidate_id"]:
        raise ValueError("Candidate ID mismatch")
    if answer.get("decision") not in {"keep", "reject", "uncertain"}:
        raise ValueError("Invalid decision")
    if not isinstance(answer.get("reason"), str) or not answer["reason"].strip():
        raise ValueError("Missing reason")
    routes = answer.get("routes")
    if not isinstance(routes, list) or (answer["decision"] == "keep" and len(routes) < 2):
        raise ValueError("Invalid route evidence")
    supplied = {image["label"] for image in node["images"] if not image.get("missing")}
    for route in routes:
        if not isinstance(route, dict) or not isinstance(route.get("description"), str) or not route["description"].strip():
            raise ValueError("Invalid route description")
        frames = route.get("evidence_frames")
        if not isinstance(frames, list) or not frames or any(frame not in supplied for frame in frames):
            raise ValueError("Evidence cites an absent image")
    return answer


def review(case, node, key, prompt, settings, attempt=1):
    started = time.perf_counter()
    result = {"case_number": case["case_number"], "candidate_id": node["candidate_id"],
              "started_at": now(), "worker_pid": os.getpid(), "attempts": attempt, "request_settings": settings}
    suffix = "" if attempt == 1 else f"_retry{attempt-1:02d}"
    output = RUN / "responses" / f"C{case['case_number']:02d}_{node['id']}_F{node['index']}{suffix}.json"
    if output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    try:
        content = [{"type": "text", "text": f"候选编号：{node['candidate_id']}\n候选帧号：{node['index']}\n判断中间的 F0，输出 JSON。下面按时间顺序给出图像，缺失位置明确标注。"}]
        for image in node["images"]:
            label = f"{image['label']}：实际帧 {image['frame']}"
            if image.get("missing"):
                content.append({"type": "text", "text": label + "，图像缺失（轨迹尚未开始）。"})
                continue
            if image["frame"] > node["ready_at_frame"]:
                raise ValueError("Future evidence leak")
            path = (SITE / image["path"]).resolve()
            if not path.is_relative_to(SITE):
                raise ValueError("Image outside the site")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != image["image_id"]:
                raise ValueError("Image hash mismatch")
            mime = mimetypes.guess_type(path.name)[0] or "image/webp"
            content.append({"type": "text", "text": label + ("，这是待审核的候选位置。" if image["label"] == "F0" else "。")})
            content.append({"type": "image_url", "image_url": {
                "url": f"data:{mime};base64," + base64.b64encode(data).decode("ascii"), "detail": "high"}})
        request = {**settings, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}]}
        result["request_sha256"] = hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        result["image_count"] = sum(not image.get("missing", False) for image in node["images"])
        with httpx.Client(timeout=httpx.Timeout(240, connect=30), follow_redirects=False) as client:
            response = client.post(API + "/chat/completions", headers={"Authorization": "Bearer " + key}, json=request)
        result["http_status"] = response.status_code
        response.raise_for_status()
        body = response.json()
        result["response"] = body
        choice = body["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("Incomplete response: " + str(choice.get("finish_reason")))
        result["answer"] = validate(json.loads(choice["message"]["content"]), node)
        result["status"] = "ok"
    except Exception as error:
        result["status"] = "error"
        result["error"] = (type(error).__name__ + ": " + str(error)).replace(key, "[redacted]")[:1200]
    result["completed_at"] = now()
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    save(output, result)
    return result


def pack(manifest, prompt, results):
    lookup = {r["candidate_id"]: r for r in results}
    cases = []
    for case in manifest["cases"]:
        nodes = []
        for node in case["nodes"]:
            result = lookup.get(node["candidate_id"])
            record = {**node, "status": result["status"] if result else "pending"}
            if result:
                record.update({k: result[k] for k in ["answer", "error", "elapsed_seconds", "image_count", "started_at", "completed_at", "attempts", "request_settings"] if k in result})
                record["usage"] = result.get("response", {}).get("usage", {})
                record["response_model"] = result.get("response", {}).get("model")
            nodes.append(record)
        cases.append({**case, "nodes": nodes})
    counts = {decision: sum(r.get("answer", {}).get("decision") == decision for r in results) for decision in ["keep", "reject", "uncertain"]}
    summary = {"requested": sum(len(c["nodes"]) for c in cases), "completed": len(results),
               "errors": sum(r["status"] == "error" for r in results), **counts,
               "max_workers": manifest["max_workers"],
               "worker_processes_in_final_results": len({r["worker_pid"] for r in results}),
               "total_api_attempts": sum(r.get("attempts", 1) for r in results),
               "median_latency_seconds": round(statistics.median([r["elapsed_seconds"] for r in results]), 3) if results else None}
    dataset = {**manifest, "prompt_zh": prompt, "summary": summary, "cases": cases,
               "replay_timing": "Cached verdicts may be applied only after node confirmation and F+2 arrival. Network latency is recorded separately, not simulated as robot steps."}
    save(RUN / "results.json", dataset)
    encoded = json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    (SITE / "node_elimination_results.js").write_text("'use strict';\nwindow.JEV_NODE_ELIMINATION_DATA=" + encoded + ";\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-stdin", action="store_true")
    parser.add_argument("--pack-only", action="store_true")
    parser.add_argument("--retry-incomplete", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    prompt = (RUN / "prompt_zh.txt").read_text(encoding="utf-8")
    manifest["prompt_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
    manifest["request_settings"] = {"model": "deepseek-flash", "response_format": {"type": "json_object"},
                                    "thinking": {"type": "enabled"}, "reasoning_effort": "high", "max_tokens": 8192, "stream": False}
    (RUN / "responses").mkdir(exist_ok=True)
    saved = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((RUN / "responses").glob("*.json"))]
    latest = {}
    for result in saved:
        if result.get("attempts", 1) >= latest.get(result["candidate_id"], {}).get("attempts", 0):
            latest[result["candidate_id"]] = result
    if args.pack_only:
        results = list(latest.values())
        print(json.dumps(pack(manifest, prompt, results), ensure_ascii=False), flush=True)
        return
    key = sys.stdin.readline().strip() if args.key_stdin else os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise SystemExit("Missing DEEPSEEK_API_KEY or stdin key")
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        response = client.get(API + "/models", headers={"Authorization": "Bearer " + key})
        response.raise_for_status()
        models = response.json()
    model = next((m for m in models.get("data", []) if m["id"] == "deepseek-flash"), None)
    if model is None or (model.get("input_modalities") and "image" not in model["input_modalities"]):
        raise SystemExit("The requested account does not expose deepseek-flash with vision")
    save(RUN / "model_catalog.json", models)
    save(RUN / "manifest.json", manifest)
    jobs = [(case, node) for case in manifest["cases"] for node in case["nodes"]]
    settings = manifest["request_settings"]
    attempt = 1
    if args.retry_incomplete:
        jobs = [(case, node) for case, node in jobs if latest.get(node["candidate_id"], {}).get("error", "").endswith("Incomplete response: length") and latest[node["candidate_id"]].get("attempts", 1) == 1]
        settings = {**settings, "max_tokens": 32768}
        manifest["retry_settings"] = {"reason": "length-truncated responses only; original response files preserved", "candidates": [node["candidate_id"] for _, node in jobs], "request_settings": settings}
        save(RUN / "manifest.json", manifest)
        attempt = 2
    print(json.dumps({"model": model["id"], "input_modalities": model.get("input_modalities"), "cases": manifest["case_numbers"], "calls": len(jobs), "workers": manifest["max_workers"]}), flush=True)
    results = list(latest.values())
    pack(manifest, prompt, results)
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(manifest["max_workers"],max(1,len(jobs)))) as pool:
        futures = [pool.submit(review, case, node, key, prompt, settings, attempt) for case, node in jobs]
        for completed_in_batch, future in enumerate(concurrent.futures.as_completed(futures), 1):
            result = future.result()
            latest[result["candidate_id"]] = result
            results = list(latest.values())
            summary = pack(manifest, prompt, results)
            print(json.dumps({"done": completed_in_batch, "total": len(jobs), "candidate": result["candidate_id"], "status": result["status"], "decision": result.get("answer", {}).get("decision"), "seconds": result["elapsed_seconds"], "error": result.get("error")}, ensure_ascii=False), flush=True)
    print(json.dumps({"finished": True, **summary}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
