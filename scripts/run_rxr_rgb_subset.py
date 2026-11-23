"""Prepare and run a fixed, scene-stratified StreamVLN RxR-CE or R2R-CE RGB recording."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import statistics
import subprocess
import sys

from evaluate import PROJECT, build_command, check_gpu
from core.paths import ensure_data_links, model_root


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def prepare(record, output, count, seed, benchmark="rxr"):
    filename = "val_unseen_guide.json.gz" if benchmark == "rxr" else "val_unseen.json.gz"
    data = model_root("streamvln") / "data/datasets" / benchmark / "val_unseen" / filename
    groups = defaultdict(list)
    with gzip.open(data, "rt") as stream:
        for ep in json.load(stream)["episodes"]:
            lang = ep["instruction"].get("language", "en")
            if benchmark == "rxr" and (ep["info"]["role"] != "guide" or lang not in ("en-US", "en-IN")):
                continue
            scene = Path(ep["scene_id"]).stem
            groups[scene].append(dict(scene=scene, episode_id=str(ep["episode_id"]),
                                      trajectory_id=ep["trajectory_id"], language=lang))
    total = sum(map(len, groups.values()))
    if not 0 < count <= total:
        raise ValueError(f"Expected 1 to {total} episodes")
    quotas = {s: count * len(rows) // total for s, rows in groups.items()}
    order = sorted(groups, key=lambda s: (-(count * len(groups[s]) % total), s))
    for scene in order[:count - sum(quotas.values())]:
        quotas[scene] += 1
    rng = random.Random(seed)
    episodes = []
    for scene in sorted(groups):
        pool = sorted(groups[scene], key=lambda ep: int(ep["episode_id"]))
        episodes.extend(rng.sample(pool, quotas[scene]))
    assert len({ep["episode_id"] for ep in episodes}) == count
    manifest = dict(created=now(), benchmark=benchmark, split="val_unseen", sample_seed=seed,
                    habitat_config_seed=100, source_count=total, count=count,
                    scene_counts=quotas, dataset_sha256=hashlib.sha256(data.read_bytes()).hexdigest(),
                    episodes=episodes)
    if benchmark == "rxr":
        manifest.update(role="guide", guide_sha256=manifest["dataset_sha256"])
    plan = record / "episodes.json"
    if plan.exists() or output.exists():
        raise FileExistsError("Choose a new run ID to prepare a different sample")
    record.mkdir(parents=True, exist_ok=True)
    source = output / "source"
    source.mkdir(parents=True)
    write_json(plan, manifest)
    shutil.copy2(plan, output / plan.name)
    files = ["scripts/run_rxr_rgb_subset.py", "scripts/evaluate.py", "core/paths.py",
             "scripts/run_rxr_roundtrip.py", f"backbone/streamvln/config/vln_{benchmark}.yaml",
             "backbone/streamvln/streamvln/rxr_capture.py"]
    evaluators = (["streamvln_eval_rxr.py", "rxr_dataset.py", "rxr_metrics.py"]
                  if benchmark == "rxr" else ["streamvln_eval.py"])
    files += ["backbone/streamvln/streamvln/" + name for name in evaluators]
    hashes = {}
    for name in files:
        path = PROJECT / name
        shutil.copy2(path, source / path.name)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip()
    write_json(source / "versions.json", dict(commit=commit, sha256=hashes))
    write_json(output / "status.json", dict(state="prepared", target=count, at=now()))
    print(f"Prepared {count} episodes in {len(quotas)} scenes. {quotas}", flush=True)


def score_summary(output, plan):
    rows = [json.loads(line) for line in (output / "result.json").read_text().splitlines()]
    ids = {str(row["episode_id"]) for row in rows}
    if len(ids) != len(rows) or ids != {ep["episode_id"] for ep in plan["episodes"]}:
        raise ValueError("Final result IDs differ from the frozen manifest")
    valid, technical = [], []
    metrics = ["success", "spl", "ne", "os"]
    if plan.get("benchmark", "rxr") == "rxr":
        metrics.append("ndtw")
    for row in rows:
        if all(math.isfinite(row[key]) for key in metrics):
            valid.append(row)
        else:
            technical.append(dict(scene=row["scene_id"], episode_id=row["episode_id"],
                                  reason="nonfinite_native_metric"))
    return dict(total=len(rows), scored=len(valid), successes=sum(int(r["success"]) for r in valid),
                mean_spl=statistics.mean(r["spl"] for r in valid) if valid else None,
                frames=sum(r["frames"] for r in rows), technical=technical)


def run(record, output, gpu):
    plan = json.loads((output / "episodes.json").read_text())
    target = plan["count"]
    benchmark = plan.get("benchmark", "rxr")
    args = argparse.Namespace(backbone="streamvln", benchmark=benchmark, gpu=gpu, sim_gpu=None,
                              mode="physical", resume=None, episodes=0, output=str(output))
    command, env, cwd, _ = build_command(args)
    evaluator = "streamvln_eval_rxr.py" if benchmark == "rxr" else "streamvln_eval.py"
    index = command.index("streamvln/" + evaluator)
    command[index] = str(output / "source" / evaluator)
    command.extend(["--capture_manifest", str(output / "episodes.json")])
    ensure_data_links("streamvln")
    with open(f"/tmp/vln_2026_gpu_{gpu}.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if json.loads((output / "status.json").read_text())["state"] == "complete":
            raise ValueError("This run is already complete")
        resource = check_gpu(gpu, 22000)
        status = dict(state="running", started_at=now(), target=target, gpu=gpu,
                      gpu_at_start=resource, command=command, cwd=str(cwd))
        write_json(output / "status.json", status)
        try:
            with (output / "run.log").open("a") as log:
                worker = subprocess.Popen(command, env=env, cwd=cwd, stdout=log,
                                          stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = worker.wait()
                except BaseException:
                    if worker.poll() is None:
                        os.killpg(worker.pid, signal.SIGTERM)
                        try:
                            worker.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            os.killpg(worker.pid, signal.SIGKILL)
                            worker.wait()
                    raise
                if code:
                    raise subprocess.CalledProcessError(code, command)
            summary = score_summary(output, plan)
            status.update(state="complete", **summary)
            summary_text = (f'{summary["successes"]}/{summary["scored"]} 成功，'
                            f'平均 SPL {summary["mean_spl"]}，技术异常 {len(summary["technical"])} 条，'
                            f'共保存 {summary["frames"]} 帧。')
        except BaseException as error:
            status.update(state="failed", error=str(error))
            summary_text = f"运行中断，原因见 status.json 和 run.log（{error}）。"
            raise
        finally:
            status["finished_at"] = now()
            write_json(output / "status.json", status)
            with (record / "README.md").open("a") as stream:
                stream.write(f'\n{status["finished_at"]} · {summary_text}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("run_id")
    parser.add_argument("--count", type=int, default=400)
    parser.add_argument("--sample-seed", type=int, default=2)
    parser.add_argument("--benchmark", choices=("rxr", "r2r"), default="rxr")
    parser.add_argument("--gpu", type=int)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in (".", ".."):
        parser.error("Expected a run directory name")
    relative = Path("reproduction") / ("streamvln_" + args.benchmark) / args.run_id
    record, output = PROJECT / "experiments" / relative, PROJECT / "outputs" / relative
    if args.action == "prepare":
        prepare(record, output, args.count, args.sample_seed, args.benchmark)
    else:
        if args.gpu is None:
            parser.error("run requires --gpu")
        signal.signal(signal.SIGTERM, signal.default_int_handler)
        run(record, output, args.gpu)


if __name__ == "__main__":
    main()
