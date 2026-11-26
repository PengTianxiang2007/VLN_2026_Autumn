"""Join this run's outward tool calls, metered responses, image deliveries and H1 receipts."""
import base64
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "outputs/inverse_rollback/codex_tools_v001" / HERE.name
REL = "../../../../outputs/inverse_rollback/codex_tools_v001/" + HERE.name


def read(path):
    return json.loads(path.read_bytes())


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def heading(q):
    w, x, y, z = q
    return math.degrees(math.atan2(2*(w*z + x*y), w*w + x*x - y*y - z*z))


def angle(a, b):
    return (a - b + 180) % 360 - 180


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_mcp_images(audit):
    seen = []
    with (OUT / "codex-events.jsonl").open() as stream:
        for line in stream:
            event = json.loads(line)
            item = event.get("item", {})
            if event["type"] != "item.completed" or item.get("type") != "mcp_tool_call" or item["server"] != "vlnverse":
                continue
            inner = item["result"]["content"]
            result = json.loads(next(c["text"] for c in inner if c["type"] == "text"))
            png = next(c for c in inner if c["type"] == "image")
            seq = result["sequence"]
            row = audit[seq]
            sha = digest(base64.b64decode(png["data"], validate=True))
            if (item["status"] != "completed" or result != row["result"]
                    or sha != row["rgb"]["sha256"] or sha != digest((OUT / row["rgb"]["file"]).read_bytes())):
                raise ValueError(f"MCP result or frame mismatch at call {seq}")
            seen.append(seq)
    if sorted(seen) != sorted(audit):
        raise ValueError("Missing MCP image receipt")


def model_trace(source, audit):
    groups, active, pending, responses = [], {}, [], []
    with source.open() as stream:
        for line in stream:
            event = json.loads(line)
            p = event.get("payload", {})
            kind = p.get("type")
            if event["type"] == "response_item" and kind == "custom_tool_call":
                group = dict(code_call_id=p["call_id"], tool=p["name"], issued_utc=event["timestamp"],
                             code=p["input"], sequences=[], model_image_hashes=[])
                groups.append(group)
                pending.append(group)
                active[p["call_id"]] = group
            elif event["type"] == "token_usage_record":
                rid = p["response_id"]
                if rid not in responses:
                    responses.append(rid)
                for group in pending:
                    group["response_id"] = rid
                pending.clear()
            elif event["type"] == "event_msg" and kind == "item_completed":
                item = p["item"]
                if item.get("type") != "McpToolCall" or item.get("server") != "vlnverse":
                    continue
                inner = json.loads(item["result"]["content"][0]["text"])["content"]
                result = json.loads(next(c["text"] for c in inner if c["type"] == "text"))
                seq = result["sequence"]
                if item["status"] != "completed" or result != audit[seq]["result"]:
                    raise ValueError(f"Code Mode call mismatch at {seq}")
                group, = active.values()
                group["sequences"].append(seq)
            elif event["type"] == "response_item" and kind == "custom_tool_call_output":
                group = active.pop(p["call_id"])
                group["completed_utc"] = event["timestamp"]
                for part in p["output"]:
                    if part["type"] == "input_image":
                        prefix, encoded = part["image_url"].split(",", 1)
                        if prefix != "data:image/png;base64":
                            raise ValueError(prefix)
                        group["model_image_hashes"].append(digest(base64.b64decode(encoded, validate=True)))
    if sorted(n for g in groups for n in g["sequences"]) != sorted(audit) or pending or active:
        raise ValueError("Incomplete model-to-simulator alignment")
    return groups, responses


def geometry(end):
    objects = read(OUT / "operator/objects.json")
    assert objects["meters_per_unit"] == 1
    room = {v["path"].split("/")[-1]: v for v in objects["objects"] if "/livingroom_802265/" in v["path"]}
    cabinet, screen = room["cabinet_0010"], room["television_0000"]
    x, y = end["position"][:2]
    tv = [(a+b)/2 for a, b in zip(screen["minimum"], screen["maximum"])]
    bearing = math.degrees(math.atan2(tv[1]-y, tv[0]-x))
    yaw = heading(end["rotation"])
    return dict(cabinet=cabinet["path"], screen=screen["path"], end_xy_m=[x,y], cabinet_front_world_x_m=cabinet["maximum"][0],
                cabinet_y_bounds_m=[cabinet["minimum"][1],cabinet["maximum"][1]],
                between_cabinet_sides=cabinet["minimum"][1] <= y <= cabinet["maximum"][1],
                cabinet_front_distance_m=x-cabinet["maximum"][0],
                cabinet_lateral_offset_from_center_m=y-(cabinet["maximum"][1]+cabinet["minimum"][1])/2,
                screen_center_world_m=tv, screen_center_bearing_deg=bearing, robot_heading_deg=yaw,
                heading_error_to_screen_center_deg=abs(angle(yaw,bearing)),
                heading_error_to_cabinet_normal_deg=abs(angle(yaw,180)))


def main():
    audit = {r["sequence"]: r for r in map(json.loads, (OUT / "agent/calls.jsonl").read_text().splitlines())}
    verify_mcp_images(audit)
    with (OUT / "codex-events.jsonl").open() as stream:
        thread = json.loads(stream.readline())["thread_id"]
    sessions = Path("/mnt/nas/gezuhao/PengTianxiang/.codex/sessions/2026/11/26")
    source, = sessions.glob("*" + thread + "*.jsonl")
    groups, response_ids = model_trace(source, audit)
    group_by_seq = {seq: g for g in groups for seq in g["sequences"]}
    image_hashes = {sha for g in groups for sha in g["model_image_hashes"]}
    rows, counts = [], Counter()
    for n, call in audit.items():
        before, after = call["before"], call["after"]
        r, g = call["result"], group_by_seq[n]
        op = call["action"] or call["method"]
        counts[op] += 1
        rows.append(dict(sequence=n, response=response_ids.index(g["response_id"])+1, action=op,
                         started_utc=call["started_utc"], finished_utc=call["finished_utc"],
                         frame_after=r["live_frame"], frame_before=r["live_frame"]-int(op != "observe"),
                         ticks=r["physics_ticks_advanced"], task_tick=after["task_ticks"], world_tick=after["world_ticks"],
                         simulation_time_s=call["rgb"]["simulation_time_s"], status=r["status"],
                         before_xyz_m=before["position"], after_xyz_m=after["position"],
                         after_heading_deg=heading(after["quaternion_wxyz"]),
                         horizontal_m=math.dist(before["position"][:2],after["position"][:2]),
                         yaw_change_deg=angle(heading(after["quaternion_wxyz"]),heading(before["quaternion_wxyz"])),
                         mcp_png_verified=True, model_visible=call["rgb"]["sha256"] in image_hashes,
                         png=call["rgb"]["file"],image_sha256=call["rgb"]["sha256"]))
    begin, end = (read(OUT / name)["state"] for name in ("start.json","end.json"))
    result = geometry(end)
    response_groups = [(i, [r["sequence"] for r in rows if r["response"] == i]) for i in range(1,len(response_ids)+1)]
    summary = dict(thread_id=thread, start_frame=38, end_frame=rows[-1]["frame_after"], counts=dict(counts),
                   total_robot_calls=len(rows), total_physics_ticks=sum(r["ticks"] for r in rows),
                   individual_observe_sequences=[r["sequence"] for r in rows if r["action"]=="observe"],
                   total_returned_images=len(rows), distinct_simulator_images_in_model_context=sum(r["model_visible"] for r in rows),
                   metered_model_responses=len(response_ids), responses_invoking_robot=len({r["response"] for r in rows}),
                   responses_invoking_motion=len({r["response"] for r in rows if r["action"]!="observe"}),
                   motion_actions=sum(v for k,v in counts.items() if k!="observe"),
                   response_groups=response_groups, final_text=(OUT / "codex-final.txt").read_text().strip(),
                   net_horizontal_m=math.dist(begin["position"][:2],end["position"][:2]),
                   path_between_action_boundaries_m=sum(r["horizontal_m"] for r in rows), geometry=result,
                   first_to_last_robot_call_seconds=(datetime.fromisoformat(rows[-1]["finished_utc"])
                                                     -datetime.fromisoformat(rows[0]["started_utc"])).total_seconds(),
                   restored_f38=read(OUT / "restored.json")["verified"])
    write(OUT / "model-tool-groups.json", dict(thread_id=thread, response_ids=response_ids, groups=groups))
    write(OUT / "call-timeline.json", rows)
    write(OUT / "summary.json", summary)
    write(HERE / "summary.json", summary)
    names = dict(forward="前进",turn_left="左转",turn_right="右转",observe="主动观测")
    lines = ["# Codex 电视前导航的逐调用时间线", "",
             "UTC 为仿真端收到调用和回图完成的时间。帧号从本次 F38 起连续递增。模型响应序号来自当前会话的计量响应 ID，同一序号内的操作由同一次模型输出发起。", "",
             "| 调用 | 模型响应 | 开始 UTC | 完成 UTC | 调用 | 帧 | 物理 tick | 水平移动 cm | 朝向变化 ° | 返回前视图 | 图像进入模型上下文 |",
             "|---:|---:|---|---|---|---|---:|---:|---:|---|---|"]
    for r in rows:
        lines.append(f"| {r['sequence']} | {r['response']} | {r['started_utc'][11:23]} | {r['finished_utc'][11:23]} "
                     f"| {names[r['action']]} | {r['frame_before']}→{r['frame_after']} | {r['ticks']} "
                     f"| {100*r['horizontal_m']:.1f} | {r['yaw_change_deg']:+.1f} | [图]({REL}/{r['png']}) "
                     f"| {'是' if r['model_visible'] else '否'} |")
    lines += ["", "## 每次模型响应发出的动作", "",
              "| 模型响应 | 机器人工具调用 | 执行内容 |", "|---:|---|---|"]
    for i, seqs in response_groups:
        if seqs:
            description = "、".join(names[rows[n-1]["action"]] for n in seqs)
        elif any("ALL_TOOLS" in g["code"] for g in groups if g["response_id"]==response_ids[i-1]):
            description = "查找可用工具"
        elif i==len(response_ids):
            description = "文字报告到达"
        else:
            description = "无机器人工具调用"
        lines.append(f"| {i} | {', '.join(map(str,seqs)) or '—'} | {description} |")
    lines += ["", f"[每次调用的完整位姿、时钟与图像哈希]({REL}/call-timeline.json) · "
              f"[模型对外发出的工具代码与响应对应]({REL}/model-tool-groups.json) · [结果](README.md)", ""]
    (HERE / "timeline.md").write_text("\n".join(lines))
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
