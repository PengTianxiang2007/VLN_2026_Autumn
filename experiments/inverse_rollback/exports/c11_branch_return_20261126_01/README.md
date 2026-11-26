# C11 偏航与实走回退回放

2026-11-26。仿真 PID 3122551 保留，控制分支的 Codex 客户端 PID 3428565 已退出。数据来自 [C11 回退实验](../../codex_tools_v001/run_20261126_04_c11_f57_f45/README.md) 与原版多视角采集。沿用[用户指定的偏航回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html)的样式、C11 地图投影、原始双语评审及其交互面板。模板入口 SHA256 为 `8a6ba11521083bc5322e248bd9063f58a3e09b42c2e064e8c5da96d45ab9e4a8`。

58 张历史帧和 60 个模型工具调用共 118 个时间点。第一个返回报错的左转实际生效，之后被拒的重试无新回图，页面单独注明。55 个实际移动、4 次独立观察，共 59 条仿真回执。保留五轮评审，地图和历史 JEV 波形只标注本轮最终有效节点 F25、F45 及终止 F57。地图可独立选择原版轨迹、偏航段、实走回退、有效节点、回退目标与限额/截断点。原版个例导航失败，本次局部回退未达标，完整导航 SR 与平均 SPL 当前版及配对原版均暂无，已评分 0 条。

从仓库根目录运行 `backbone/streamvln/.venv/bin/python -B experiments/inverse_rollback/exports/c11_branch_return_20261126_01/export.py`。输出目录按版本独立保存。新增源码见 [export.py](export.py)、[page.html](page.html)、[page.js](page.js)。

## 交付

[公网回放](http://134.175.18.101/vln/c11_codex_return_f57_f45_web_20261126_01/index.html) · [离线 ZIP](http://134.175.18.101/vln/c11_codex_return_f57_f45_web_20261126_01/replay.zip) · [本地离线 HTML](../../../../outputs/inverse_rollback/exports/c11_branch_return_20261126_01/release01/index.html) · [导出清单](../../../../outputs/inverse_rollback/exports/c11_branch_return_20261126_01/release01/export.json) · [浏览器检查](../../../../outputs/inverse_rollback/exports/c11_branch_return_20261126_01/release01/browser-check.json) · [发布回执](../../../../outputs/visualization_publishing/publish_20261126_134523_809338/publication.json)

发布时间 2026-11-26T13:45:32.092724+00:00。离线入口 SHA256 为 `b5e0165d77e3bdb21605414530a3322055d27f21ebec4699fd2305b260771fc1`，在线入口 SHA256 为 `5b30ae18d4d6f4db8f0d4cbb4a4dadf74b0857963f89a0809c8256bd70dca04c`，离线 ZIP 的 SHA256 为 `44947e438461468f82a79f1630cd7ad11c379d202f83fe4619c098f64bdb7852`。远端全部 121 个文件 SHA256 通过，公网入口 HEAD 返回 HTTP 200。本地浏览器检查在线拆分版的关键帧、双语切换、轨迹图层、50 步与实际截断处、错误回执及评审跳转。
