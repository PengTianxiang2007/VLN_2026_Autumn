# 从 F38 自主走到电视柜前

[交互回放 · 占据地图、第一视角与逐调用标记](http://134.175.18.101/vln/codex_tv_f38_h1_20261126_01/index.html) · [可视化导出记录](../../exports/codex_tv_20261126_01/README.md)

2026-11-26，已完成。复用同一台 Isaac H1，GPU 3，PID 3122551，seed 2，`kujiale_0036_0_0` 的第 38 步动作前。一个新的 Codex CLI 会话根据任务、自行取得的原生 RGB 和动作反馈导航。目标为走到电视柜正前方约一米并面向电视。完整提示见 [prompt.txt](prompt.txt)。

每次调用记录动作或独立观察、UTC、物理计数、位姿与回图。外部保存首尾图以及终点，场景几何只供事后核对。目标声明使用最终文字，物理约束沿用原生任务。结束后在原进程恢复 F38。实验使用 Git 基线 `d551421e95c72a1dd2305e31f308016c7d188e67` 和未提交的机器人工具，本次为动作审计补充 UTC 时间。有效源码和工作区差异另存到运行输出。

从仓库根目录运行以下命令。Codex 0.164.0，gpt-6-astra，medium，代理 7892。每个运行编号只使用一次。

```bash
python3 experiments/inverse_rollback/codex_tools_v001/run_20261126_03_tv/run.py
```

## 目标与终点

Codex 在本次 F65 自行结束会话。起点到终点水平净位移 3.41 米。机身中心位于客厅 `cabinet_0010` 的横向范围内，与柜子中心线横向相距 0.25 米，距柜子朝向客厅的正面包围盒 1.13 米。机身朝向与指向 `television_0000` 屏幕中心的水平夹角为 3.42°。终点图中电视和柜子都在机器人正前方，测量与模型的到达声明一致。[起点前视图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/operator/start.png) · [终点前视图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/operator/end.png) · [终点位姿](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/end.json) · [场景物体边界](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/operator/objects.json)

模型最终回答如下。

> 已停下，正面朝向电视。电视位于视野中央，电视柜正面基本对齐，目测距柜子约一米。

## 动作与观察

按原顺序为主动观察 → 前进 8 次 → 右转 4 次 → 左转 4 次 → 前进 5 次 → 右转 6 次 → 文字报告到达。共 13 次前进、10 次右转、4 次左转，27 个移动均完成且每次推进 50 个物理 tick。独立观察只在开头的 F38 调用过一次，推进 0 tick。首个机器人调用开始于 12:08:55.659 UTC，末次回图完成于 12:10:23.401 UTC，间隔 87.74 秒。28 次调用各返回一张原生前视图，原始 MCP 事件中的 PNG 哈希逐张对应仿真文件。[逐调用时间线与全部画面](timeline.md) · [原始仿真回执](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/calls.jsonl)

会话记录了 14 个不同的已计量模型响应，其中 1 次查找工具、1 次主动观察、11 次发出移动、1 次文字结束。单个移动响应实际下发 1 至 5 个动作。Code Mode 向模型上下文转交了 22 张不同的原图。在连续左转 4 次时只转交末图，在连续右转 5 次时转交后 2 张。六张其余回图均保存在仿真与 MCP 记录中。模型可见图以工具输出进入上下文的图像字节为准。[响应与对外工具代码](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/model-tool-groups.json) · [含位姿、时间与图像哈希的逐调用明细](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/call-timeline.json)

## 现场与计分

结束图和终点位姿在复位前单独存档。原 PID 已在同一仿真内恢复 F38 的关节、机身、步态控制器和任务计数 1901。通过原入口的额外零推进观察确认 F38 仍为 active，这次操作单独记入 live 目录。当前版 SR、平均 SPL 暂无，已评分 0 条。配对原版 SR、平均 SPL 暂无，已评分 0 条。本次成功判定针对用户指定的电视目标。[还原读回](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/restored.json) · [复位后的现场](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/live/frames/00001.png) · [轻量结果摘要](summary.json)
