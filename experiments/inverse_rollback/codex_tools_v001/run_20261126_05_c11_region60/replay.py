"""Export the C11 area-return branch with its original reviews and actual tool images."""
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
OUTPUT = ROOT / "outputs/inverse_rollback/exports/c11_region60_20261126_01/release01"
sys.path.insert(0, str(HERE.parents[1] / "exports/c11_branch_return_20261126_01"))
import export as template


PROMPT_ZH = """请控制机器人回到回退点 S05（F45）。

结合历史观测，确认当前位置符合回退点定义，并且能看清当时从该回退点看到的其他支路。不强求精确复现原来的位置和朝向，在原来位置附近区域即可。

使用 observe() 查看前视画面，使用 step("forward")、step("turn_left") 或 step("turn_right") 移动或转向。满足上述条件后，调用 step("finish_return") 结束回退。

最多可执行 60 步移动。每次前进或转向计一步。观察和声明到达不计步。如果用完 60 步仍无法确认到达，结束本次尝试。"""
MESSAGES = {
    0: "我会先查看当前画面，回到 F45 木椅与柜子附近，并确认通往房间两侧的路线都可以进入。",
    9: "现在能看到柜子和餐区，这让我确认机器人靠近 S05 旁边的墙。我会回到开阔的地面，查看通往客厅的路线。",
    23: "我已离开墙边，能看到通往餐区的路线和通往摆着茶几的客厅的路线。我会再看一次附近的木椅，确认处在 S05 区域。",
    32: "木椅、沙发边缘和柜子与 S05 区域吻合。刚才的连续转向也确认了客厅与餐区两个方向都可进入，我将在这里声明到达。",
    33: "已回到 S05（F45）附近，核对了通往客厅和餐区的路线，并调用了 `finish_return`。60 步移动预算共用 31 步。",
}


def build():
    previous = (template.OUT / "index.html").read_text()
    original = json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>', previous, re.S)[1])
    case, = original["cases"]
    grid = original["grid"]
    images = {key: original["images"][key] for key in {f["image"] for f in case["frames"]} | {grid["image"]}}
    target = case["frames"][45]["position"]
    result = template.read(RUN / "result.json")
    assert case["episode_id"] == result["episode_id"] and result["stop_reason"] == "finish_return"
    result = {k: result[k] for k in ("parent_thread", "branch_thread", "movements", "cap", "final_m", "nearest_move", "nearest_m")}
    result["target_position"] = target
    receipts = [json.loads(line) for line in (RUN / "live/calls.jsonl").read_text().splitlines()]
    calls = []
    notes = []
    moved = 0
    with (RUN / "codex-events.jsonl").open() as events:
        for line in events:
            event = json.loads(line)
            if event["type"] != "item.completed":
                continue
            item = event["item"]
            if item["type"] == "agent_message":
                n = len(calls)
                notes.append({"call": n, "text": [MESSAGES[n], item["text"].strip()]})
            elif item["type"] == "mcp_tool_call":
                row = receipts[len(calls)]
                feedback = next(b["text"] for b in item["result"]["content"] if b["type"] == "text")
                assert json.loads(feedback) == row["result"]
                action = row["action"] or row["method"]
                acted = action in {"forward", "turn_left", "turn_right"}
                moved += acted
                pose = row["after"]
                img = RUN / row["rgb"]["file"]
                key = row["rgb"]["sha256"]
                assert hashlib.sha256(img.read_bytes()).hexdigest() == key
                if key not in images:
                    images[key] = template.uri(img)
                calls.append(dict(op=action, executed=acted, feedback=True, failed=False, seq=row["sequence"],
                                  image=key, position=pose["position"], heading=template.yaw(pose["quaternion_wxyz"]),
                                  motion=moved, live=row["result"]["live_frame"], taskTicks=row["result"]["task_ticks_advanced"],
                                  worldTicks=row["result"]["physics_ticks_advanced"], utc=row["finished_utc"],
                                  distance=math.dist(pose["position"][:2], target[:2])))
    assert moved == result["movements"] and len(calls) == len(receipts) and calls[-1]["op"] == "finish_return"
    assert [n["call"] for n in notes] == list(MESSAGES)
    closest = next(r for r in calls if r["motion"] == result["nearest_move"])
    summary = dict(
        verdict=["模型已声明到达", "Model declared arrival"],
        notice=["第 31 步后模型声明到达。第 8 步能看到餐区，第 22 步能看到客厅；最终前视图主要是白墙、木椅和柜缘。",
                "The model declared arrival after move 31. The dining area is visible at move 8 and the living area at move 22. The final view is dominated by a white wall, part of the wooden chair and the edge of the cabinet."],
        footer=["整条导航 SR 与平均 SPL，当前版与配对原版均暂无，已评分 0 条。",
                "Full navigation SR and mean SPL are unavailable for both versions, with zero scored paired episodes."],
        events=[[9, "R8 · 餐区视角", "R8 · Dining-area view"], [23, "R22 · 客厅视角", "R22 · Living-area view"],
                [closest["seq"], "R24 · 最接近 F45", "R24 · Closest approach to F45"],
                [len(calls), "R31 · 声明到达", "R31 · Declared arrival"]])
    data = dict(cases=[case], grid=grid, images=images, calls=calls, notes=notes,
                prompt=[PROMPT_ZH, (HERE / "prompt.txt").read_text().strip()], result=result, summary=summary)
    template.render(data, (template.TEMPLATE / "index.html").read_text(), OUTPUT)


if __name__ == "__main__":
    build()
