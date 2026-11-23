"""Record the outcome of this single C21 run when the supervisor finishes."""
import json
from pathlib import Path
import sys
import time


record = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
out = record.parents[3] / "outputs/inverse_rollback/vlm_action_v001" / record.name


def read(path):
    return json.loads(path.read_text())


while True:
    if (out / "summary.json").exists():
        result, = read(out / "summary.json")["results"]
        assert result["case"] == "C21"
        requests = out / "cases/C21/requests"
        actions = sum(1 for _ in requests.glob("action_*/answer.json"))
        judges = sum(1 for _ in requests.glob("judge_*/answer.json"))
        cause = "模型主动结束回退" if result["arrived"] else "仿真终止（" + result["terminal_reason"] + "）"
        note = (f"C21 已完成。动作调用 {actions} 次，到达判断 {judges} 次，"
                f"实际执行 {result['return_actions']} 个回程动作。{cause}，"
                f"终点距 A {result['xy_m']:.3f} 米，局部达标 {int(result['passed'])}/1。"
                f" [正式结果](../../../../outputs/inverse_rollback/vlm_action_v001/{record.name}/cases/C21/result.json)")
        break
    state_file = out / "status.json"
    if state_file.exists() and read(state_file)["phase"] == "error":
        note = "C21 技术中断，未取得局部回退评分，错误信息见实时状态。"
        break
    time.sleep(10)

readme = record / "README.md"
if note not in readme.read_text():
    with readme.open("a") as f:
        f.write("\n" + note + "\n")
