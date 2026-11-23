# DeepSeek H1 回退 22 例 · 逐帧地图与 RGB 回放

2026-11-23 05:39 UTC 已发布。[打开在线回放](http://134.175.18.101/vln/deepseek_h1_rollback22_20261123_01/index.html) · [发布回执](../../../../outputs/visualization_publishing/publish_20261123_053920_230788/publication.json)。入口及依赖共 3,169 个文件，远端 SHA256 全部匹配，公网入口直连 HEAD 返回 HTTP 200。

2026-11-23 UTC。[全批实验](../../vlm_action_v001/run_20261123_05_finish22/README.md)于 02:50 UTC 完成 22/22，seed 2。C03 与 C19 满足模型自主退出且水平误差 ≤0.35 米的判据，达标 2/22（9.09%），平均终点水平误差 2.403 米。19 例由模型退出，C20 和 C28 用尽物理步数，C25 卡住。物理终止已计入 22 例。整条导航的 SR 与平均 SPL，当前版与同批原版均为“暂无，已评分 0 条”。

导出沿用[昨日实采回放](../paired_rgb_20261122_01/README.md)的历史 RGB、底图、坐标投影、双语原任务指令与界面样式。当前回退取自每例实际运行的动作、根位姿和原生前视，包含 2,548 个回程动作及 22 张 R0。初始掉头的 12 个左转在地图上有轨迹，实拍回程画面从掉头完成的 R0 开始。历史去程可单独播放，共 560 帧。两种模式均由同一帧号驱动地图、当前机器人朝向和 RGB。

地图中橙色实际回退、蓝色历史去程 A→B 和紫色原任务标注路线各有勾选框与独立线宽。A、B 和当前观测位置始终可见，支持缩放、拖动、适配轨迹和完整底图。回程帧同时显示截至相应动作的实际误差和该轮模型的动作或退出判断。

[本地入口](../../../../outputs/inverse_rollback/exports/vlm_h1_22_replay_20261123_01/index.html) · [导出计数与来源哈希](../../../../outputs/inverse_rollback/exports/vlm_h1_22_replay_20261123_01/export.json) · [资源清单](../../../../outputs/inverse_rollback/exports/vlm_h1_22_replay_20261123_01/online_manifest.json) · [本地浏览器检查](../../../../outputs/inverse_rollback/exports/vlm_h1_22_replay_20261123_01/browser.json)。入口 SHA256 为 `0069ee25be674559e149150fd781d098f938d2f6d65167efe32d6611245ecffb`。本次检查覆盖同步进度条、图层开关与独立线宽、中英文切换、末帧观测、物理终止、底图缩放和移动端宽度。

导出入口为 [export_vlm_rollback_replay.py](../../../../scripts/export_vlm_rollback_replay.py)。从仓库根目录运行，重导出使用新的目标目录。

```bash
backbone/streamvln/.venv/bin/python -Bu scripts/export_vlm_rollback_replay.py outputs/inverse_rollback/exports/vlm_h1_22_replay_20261123_01
```
