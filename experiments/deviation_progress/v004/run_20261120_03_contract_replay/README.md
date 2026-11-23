# DeepSeek 六条原答的校验器修复回放

使用 run_20261120_02_deepseek6 的原始请求和回答，复用 v004 的状态机与首次偏航停止规则。只在完整请求一致时重放缓存，模型调用次数为零。修复兼容顶层 `"type": "json_object"`。其余字段、进度、证据、枚举和端点继续接受原校验。

复现命令为 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/v004/run_20261120_03_contract_replay/replay.py NEW_OUTPUT`，目标目录须为新目录。

2026-11-20 06:31:41 UTC 完成。8 项回归测试通过，含真实 C47 S04。六例采用 29 轮原答，5 条报警、0 次格式失败。C47 在 S04（F0→52）报警，回退目标 S01。旧链其后的 S05 保存在原实验。浏览器核验 29 轮双语、155 个图像引用、原答及区间图层。发布文件 527 个，远端哈希通过，入口 HTTP 200。[新版网页](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html) · [离线 ZIP](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/deepseek_v004_six_offline.zip) · [离线 HTML 及哈希](../../../../outputs/deviation_progress/v004/run_20261120_03_contract_replay/exports/replay_01/export.json) · [发布记录](../../../../outputs/visualization_publishing/publish_20261120_063122_613944/publication.json)
