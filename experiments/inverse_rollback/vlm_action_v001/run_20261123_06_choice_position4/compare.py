"""Compare the four selected physical endpoints after the new batch completes."""
import json
from pathlib import Path
from statistics import mean


def read(path):
    return json.loads(path.read_bytes())


record = Path(__file__).resolve().parent
series = Path("outputs/inverse_rollback/vlm_action_v001")
run = series / record.name
ids = read(record / "cases.json")
prior = {r["case"]: r for r in read(series / "run_20261123_05_finish22/summary.json")["results"]}
current = {r["case"]: r for r in read(run / "summary.json")["results"]}
cases = read(run / "manifest.json")["cases"]
assert set(current) == set(ids) and all(prior[c["case_id"]]["episode_id"] == c["episode_id"] for c in cases)
pairs = []
for cid in ids:
    pair = dict(case=cid, episode_id=prior[cid]["episode_id"])
    for label, result in (("original", prior[cid]), ("current", current[cid])):
        pair[label] = {k: result[k] for k in ("passed", "xy_m", "yaw_deg", "return_actions", "arrived", "terminal_reason")}
    pairs.append(pair)
report = dict(seed=2, pairs=pairs)
for label in ("original", "current"):
    report[label] = dict(passed=sum(p[label]["passed"] for p in pairs),
                         mean_final_xy_m=mean(p[label]["xy_m"] for p in pairs))
dest = record / "paired_results.json"
dest.with_suffix(".tmp").write_text(json.dumps(report, indent=2) + "\n")
dest.with_suffix(".tmp").replace(dest)
note = (f"\n四例已完成。新版达标 {report['current']['passed']}/4，平均终点误差 "
        f"{report['current']['mean_final_xy_m']:.3f} 米；同批旧版达标 "
        f"{report['original']['passed']}/4，平均终点误差 {report['original']['mean_final_xy_m']:.3f} 米。"
        " [逐例配对结果](paired_results.json)\n")
readme = record / "README.md"
if note not in readme.read_text():
    with readme.open("a") as f:
        f.write(note)
