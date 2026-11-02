# VLNVerse 可视化复盘

用户于 2026-11-02 授权两个 seed 保存可视化。当前选 seed 2、3；启用时两者均尚未开始，
各 10 个完整 scene、250 条任务，共 500 条。此前 seed 0/1 只保存了每条任务最初两张 RGB，
无法还原过去的完整视频。评测继续使用原场景、任务、种子、提示词、动作队列与评分。

## 录制内容

- 每个模型动作对应一帧已有的 640×480 RGB，叠加 seed、episode、动作与指令。
- 旁边绘制参考轨迹和实际轨迹的 XY 示意图；仅用于录像，不传给模型。
- episode 终止观测在环境 reset 前记录。终止时未返回新 RGB 则复用最后一帧，
  在 `steps.jsonl` 中显式标记 `rgb_reused`，位置和最终指标仍取实际终止结果。
- H.264 / CRF 26 / 单 CPU 编码线程，输出 960×640 MP4，6 fps 是动作帧回放速度，
  不是物理实时速度。直接流式压缩，不暂存逐帧 PNG 或整段 RGB/深度张量。
- `case.json` 保存完整指令、参考/实际路径、种子、评分和终止原因；`steps.jsonl`
  按视频帧号保存动作与位置。模型原始生成文本仍在对应 run 的 `agent_trace.jsonl`。

原生 `vis_output=True` 会新增俯视相机。此处使用独立 `review_output` 记录开关，保留
`vis_output=False` 和原传感器配置。查看视频无需服务器 GUI。

## 路径和查看

当前 campaign：`outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/`。

```text
<campaign>/runs/visualization.json             # 选定 seed 的持久化配置
<campaign>/visualization/index.html            # 可直接打开的离线筛选页
<campaign>/visualization/index.jsonl           # 已完成录像的机器可读索引
<campaign>/visualization/seed_2/<scene>/<episode>/attempt_<id>/
    navigation.mp4
    poster.jpg
    trajectory.png
    steps.jsonl
    case.json
    encoder.log
```

seed 3 结构相同。每条任务结束后自动更新索引，失败项优先，可按 seed、scene、SR、
异常终止或 episode/指令关键词筛选；查看新记录时刷新页面。下载查看时保持相对目录结构。
可视化尚未开始时页面显示等待，不将格式测试视频计为评测录像。

`fail_reason` 与官方 SR 分别展示：官方 SR 只看终点距离阈值，因此跌倒等异常终止也可能
被计为 SR=1。分析时可以分别筛选 SR=0 和异常终止，避免混淆。

每次尝试使用独立目录。崩溃前的分片 MP4 和步骤文件尽量保留，未正常结束的 `case.json`
不会标记 complete。记录失败会输出 `VISUALIZATION_ERROR` 并写 `errors.jsonl`，不改导航
动作或评分；已完成记录的页面会标注录像异常。录像使用额外 CPU 和磁盘 I/O，不承诺
GPU 物理仿真逐位重复。

## 配置与验证

runner 每个新运行读取 `VLN_OUTPUT_ROOT/visualization.json`：

```json
{"schema": 1, "seeds": [2, 3], "output_dir": "<campaign>/visualization"}
```

输出必须位于本 campaign 内。配置写入 run.json；resume 拒绝更改既有运行的录像策略。
正在运行的 seed 1 无需停止，未来 seed 2/3 的新进程会读到配置。此项记录层更新保留
旧源码文件、前后哈希和提交记录，模型源码与推理算法不改动。

使用已有仿真环境进行 CPU 验证：

```bash
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 benchmarks/vlnverse/.venv/bin/python \
  -m unittest discover -s tests -p test_vlnverse_review.py -v
```

检查 seed 选择、传感器配置保持不变、H.264 实际编码/解码、帧和动作对应、终止帧在 reset
前归属正确的 episode，以及输入图像和 Python/NumPy 随机状态不被修改。
