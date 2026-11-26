# C35 两段条件补图评审

轨迹为 seed 2 的 C35（kujiale_0234_23_1），JEV v002 active、Astra 常规档、medium，经 17982。五支从 S04 筛选完成、第一次非初始化偏航判断尚未开始的同一历史边界分叉。第一轮 S01（F0）→S04（F28），在原有 9 个不同可引用帧之外分别新增 2–6 个原生前视帧。按区间等分点取最近的未输入中间帧，等距时取较晚帧。已筛掉候选的图像仍按原规则可引用。

第一轮报警即结束该分支。第一轮 consistent 则沿该分支原会话提交真实终止图 F44 并确认，使用该分支第一轮给出的语义进度，在 S04（F28）→END（F44）区间另补 5 张图。最多四支并发，分支内串行。记录各次判定的 CLI 耗时，终止图确认单独计时。启动命令为 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v002/run_20261125_07_c35_conditional/replay.py`。大文件、源快照和结果在同名 outputs/codex_tasks/deviation_progress/codex_memory_v002 目录。

## 结果

| 第一段新增图数 | 新增帧号 | 第一段判定 / 秒 | 终止图确认 / 秒 | 第二段判定 / 秒 |
|---:|---|---|---:|---|
| 2 | F9、F19 | consistent / 91.709 | 46.741 | consistent / 83.233 |
| 3 | F7、F15、F21 | consistent / 79.319 | 59.006 | consistent / 80.177 |
| 4 | F5、F11、F17、F22 | deviated / 85.757 | — | 首轮报警，停审 |
| 5 | F5、F9、F15、F19、F23 | consistent / 88.491 | 49.642 | consistent / 83.289 |
| 6 | F5、F8、F13、F17、F20、F24 | consistent / 92.753 | 48.372 | consistent / 82.677 |

五支完成，无技术失败。仅第一段补四张时报警，模型引用 F11–F22 的相对位置变化，判断实际提前进入卧室。其余四支均在末段实际补入 F31、F33、F36、F39、F41，均未报警。首段共有可引用历史帧 F0、F2、F4、F6、F12、F14、F16、F26、F28；次段原有 F28、F30、F44。事后标注记载应经外部走廊，实际进入套内浴室（F0–F37）。每档只评一次。

[各轮理由与计时](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_07_c35_conditional/comparison.json) · [分叉与来源摘要](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_07_c35_conditional/protocol.json)。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。
