# 三例同会话偏航回放

[在线回放](http://134.175.18.101/vln/codex_memory_deviation_three_web_20261125_01/index.html) · [离线 ZIP](http://134.175.18.101/vln/codex_memory_deviation_three_web_20261125_01/replay.zip)。2026-11-25 15:13:19 UTC 发布，C25、C09、C05 共 204 帧，包含 14 轮偏航、19 轮筛选及 C05 停审后的两个原始候选。地图可单独显示有效节点、模型报警区间、记录的回退目标和事后归因区间。选中历史证据帧可跳转到同一帧的地图和 RGB。原始导航与偏航回放共用轨迹，本次没有新增导航评分，两组 SR 和平均 SPL 均暂无，已评分 0 条。

离线源文件为 `outputs/codex_tasks/deviation_progress/codex_memory_v001/run_20261125_01/exports/replay_01/index.html`，在线版位于 `outputs/visualization_publishing/codex_memory_deviation_three_web_20261125_01/`。入口 SHA256 为 `9178885e0e3ddf5231ff76727d26888f7c2c80912db81f6eea1cbf3b623aebf8`。263 个发布文件的远端 SHA256 通过，公网入口直连 HEAD 返回 HTTP 200。[发布记录](../../../../../../outputs/visualization_publishing/publish_20261125_151308_713795/publication.json)。

[本地浏览器核对](browser_check.json)覆盖三例的中英文对应、地图与影像进度条、有效节点数及图像加载。回放复用原离线轨迹模板；展示用筛选译文保存于 screening_zh.json，模型原答和实验结果保持原样。
