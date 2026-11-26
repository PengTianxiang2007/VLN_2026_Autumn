# C27 终止段补 7 至 3 张图对照

以五个独立的新分支分别判断 seed 2、JEV v002 active 的 C27 S02（F7）到 END（F42）。每支从原终止判定前同一个截点分出，继承同一份导航指令、进度和 F7、F9、F42 的区间观测。沿用上一轮的等距取帧规则，N 张图取 F7 到 F42 的 N 个内分点，四舍五入。补真实前视图，只更新附件编号与可引用帧列表。五支各调用一次 GPT-6 Astra 常规档、medium，经 17982，最多四支并发。7 张组独立重跑。零补图对照沿用上一轮单独计时的实际结果。

执行 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v002/run_20261125_05_c27_frames3to7/replay.py`。计时为单次 Codex CLI 墙钟耗时，不含分叉、准备图片及等待并发空位。

## 结果

| 新增图数 | 新增帧号 | 判定 | 调用耗时（秒） | 相对三图（秒） |
|---:|---|---|---:|---:|
| 7 | F11、F16、F20、F25、F29、F33、F38 | deviated | 104.754 | +24.662 |
| 6 | F12、F17、F22、F27、F32、F37 | deviated | 106.028 | +25.936 |
| 5 | F13、F19、F25、F30、F36 | deviated | 106.638 | +26.546 |
| 4 | F14、F21、F28、F35 | deviated | 106.366 | +26.274 |
| 3 | F16、F25、F33 | deviated | 80.092 | +0.000 |

后续画面消除了入口性质的主要疑问：机器人穿门进入的是带电脑桌、书柜和尽头窗户的房间，并一路走到窗前，而非进入走廊后按顺序经过两个左侧入口再右转进入餐厅。这是已执行的错误房间分支选择，而不仅是缺少地标。即使把桌子视作餐桌，实际经过时桌椅也位于右侧，与指令要求的左侧相反。 四至七图在首批并发，三图接续；每档仅一次调用。前次零补图为 consistent（84.972 秒）。[五支结论、理由与计时](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_05_c27_frames3to7/comparison.json) · [帧清单与源码哈希](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_05_c27_frames3to7/protocol.json)。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。
