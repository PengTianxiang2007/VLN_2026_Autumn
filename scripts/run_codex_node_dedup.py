"""Review raw checkpoint candidates, optionally interleaving text-only route reviews."""
from dataclasses import asdict
import argparse
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.codex_client import CodexConfig, now, save, sha256
from core.codex_node_dedup import PROTOCOL, run_case
from core.codex_checkpoint_review import BINARY_TEMPLATES, MODE, PROMPTS, run_case as run_memory_case


def run_worker(task):
    case, image_root, directory, config, options = task
    try:
        return dict(status="complete", case_number=case["case_number"], worker_pid=os.getpid(),
                    result=(run_memory_case if case.get("mode") == MODE else run_case)(case, image_root, directory, config, **options))
    except Exception as error:
        # Independent cases finish even if one CLI session has a transport error.
        return dict(status="error", case_number=case["case_number"], episode_id=case["episode_id"],
                    worker_pid=os.getpid(), error=f"{type(error).__name__}: {error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Prepared manifest with image_root and cases[].nodes")
    parser.add_argument("--output", type=Path, required=True, help="New immutable run directory")
    parser.add_argument("--codex-bin", default=CodexConfig.binary)
    parser.add_argument("--codex-home", default=CodexConfig.home)
    parser.add_argument("--model", default=CodexConfig.model)
    parser.add_argument("--reasoning-effort", default="medium", choices=("low", "medium", "high", "xhigh"))
    parser.add_argument("--fast", action="store_true", help="Request the Codex Fast (priority) service tier for each turn")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--proxy-url", help="Proxy for this run's Codex child processes")
    parser.add_argument("--workers", type=int, default=1, help="Parallel cases; comparisons within a case stay sequential")
    parser.add_argument("--retry-calls", action="store_true", help="Retry failed Codex calls within each fresh checkpoint review")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    config = CodexConfig(args.codex_bin, args.codex_home, args.model, args.reasoning_effort, args.timeout, args.proxy_url,
                         service_tier="priority" if args.fast else None)
    manifest = json.loads(args.input.read_text(encoding="utf-8"))
    if manifest.get("upstream_policy") != "existing_raw_sampled_nodes":
        parser.error("Input must explicitly use existing_raw_sampled_nodes")
    if not manifest.get("cases"):
        parser.error("Input must contain at least one case")
    templates = {int(n): ROOT/path for n,path in manifest.get("candidate_template_by_case", {}).items()}
    if args.retry_calls or templates:
        if any(c.get("mode") != MODE or c.get("resume_from") or c.get("prompt_revision") not in BINARY_TEMPLATES for c in manifest["cases"]):
            parser.error("Frozen templates and retries require fresh binary checkpoint review cases")
    image_root = Path(manifest["image_root"])
    if not image_root.is_absolute():
        image_root = ROOT / image_root
    folders = [f"C{c['case_number']:02d}_ep{c['episode_id']}" for c in manifest["cases"]]
    if len(set(folders)) != len(folders) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", f) for f in folders):
        parser.error("Duplicate or invalid case identifiers")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.input, out / "input.json")
    sources = [Path(__file__), ROOT / "core/codex_client.py", ROOT / "core/codex_node_dedup.py",
               PROTOCOL / "run_dedup.py", PROTOCOL / "prompt_zh.txt"]
    if any(case.get("mode") == MODE for case in manifest["cases"]):
        sources += [ROOT / "core/codex_checkpoint_review.py", *PROMPTS]
    revisions = {case.get("prompt_revision") for case in manifest["cases"]}
    sources.extend(path for revision, path in BINARY_TEMPLATES.items() if revision in revisions)
    sources.extend(sorted(set(templates.values())-set(sources)))
    if args.retry_calls:
        sources.append(ROOT / "core/codex_shadow_retry.py")
    if any("deviation_review" in case for case in manifest["cases"]):
        from core.codex_deviation_review import REVIEW_PROMPTS
        versions = {c["deviation_review"] for c in manifest["cases"] if "deviation_review" in c}
        sources.extend([ROOT / "core/codex_deviation_review.py",
                        *sorted({REVIEW_PROMPTS[v] for v in versions}),
                        ROOT / "scripts/run_deviation_progress_review.py"])
    hashes = {}
    for source in sources:
        target = out / "source" / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        hashes[str(source.relative_to(ROOT))] = sha256(target)
    git = lambda *args: subprocess.check_output(["git", *args], cwd=ROOT, text=True)
    (out / "source/worktree.patch").write_text(git("diff", "HEAD", "--"), encoding="utf-8")
    state = dict(status="running", started_at=now(), config=asdict(config),
                 git_commit=git("rev-parse", "HEAD").strip(), git_status=git("status", "--short"),
                 source_sha256=hashes, input_sha256=sha256(out / "input.json"), completed_cases=0,
                 target_cases=len(folders), workers=min(args.workers, len(folders)),
                 supervisor_pid=os.getpid(), failed_cases=[], retry_calls=args.retry_calls)
    save(out / "status.json", state)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    results = []
    failures = []
    try:
        tasks = [(case, image_root, out / "cases" / folder, config,
                  dict(candidate_template=templates.get(case["case_number"]), retry_calls=args.retry_calls)
                  if case.get("mode") == MODE else {})
                 for case, folder in zip(manifest["cases"], folders, strict=True)]
        # Pool owns only these workers. On interruption its context terminates
        # them; inherited SIGTERM handlers unwind each Codex call's cleanup.
        with multiprocessing.Pool(processes=state["workers"]) as pool:
            for outcome in pool.imap_unordered(run_worker, tasks, chunksize=1):
                if outcome["status"] == "complete":
                    results.append(outcome.pop("result"))
                else:
                    failures.append(outcome)
                state.update(completed_cases=len(results), failed_cases=failures, updated_at=now())
                save(out / "status.json", state)
                print(json.dumps(outcome, ensure_ascii=False), flush=True)
        results.sort(key=lambda case: case["case_number"])
        save(out / "results.json", dict(cases=results, failures=failures, summary={
            key: sum(c["summary"][key] for c in results)
            for key in ("candidates", "retained", "removed", "model_calls", "uncertain", "format_errors")
        }))
        state.update(status="incomplete" if failures else "complete", completed_at=now())
    except BaseException as error:
        state.update(status="error", error=f"{type(error).__name__}: {error}", completed_at=now())
        raise
    finally:
        save(out / "status.json", state)
    print(json.dumps(dict(status=state["status"], output=str(out)), ensure_ascii=False), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
