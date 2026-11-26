# C27 最后一段的两次独立评审

冻结 seed 2、JEV v002 active 的 C27 原会话，从真实终止帧已入会话、原终止评审尚未发出的边界分叉两次。两支仅判 S02（F7）到 END（F42），使用同一份指令、已确认进度和判定标准，GPT-6 Astra 常规档、medium，经 17982。原输入分支复用原提示词及历史中的 F7、F9、F42；补图分支额外传七张原生前视图。把两端之间的时间步等分为八段，七个内部位置取最近的帧号，正好半帧时向上取整。两支并发，每支一次模型调用；调用墙钟耗时从启动 Codex CLI 前至该调用结束，包含请求、图像传输及生成，排除分叉和本地图片准备。

运行命令为 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v002/run_20261125_04_c27_interval7/replay.py`。结果位于 `outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_04_c27_interval7/`。

## 对照结果

原输入为 consistent，84.972 秒；新增 F11、F16、F20、F25、F29、F33、F38 后为 deviated，81.580 秒。补图分支识别出 F11–F16 入书房和随后从桌子左侧经过；原输入只确认靠近门洞和终点窗户。单次并发测量，耗时差不能估计平均补图开销。[两支结果与耗时](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_04_c27_interval7/comparison.json) · [采样与源码哈希](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_04_c27_interval7/protocol.json)。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。
