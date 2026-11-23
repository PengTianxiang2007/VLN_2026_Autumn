# DeepSeek 十场景离线节点去重与偏航识别

[在线去重回放](http://134.175.18.101/vln/deepseek_route10_dedup_v001_web_20261118_01/index.html) · [离线导出与发布记录](exports/web_20261118_01/README.md)

本批当前已完成 10/10 条轨迹的去重，93 个候选保留 49 个。C48 在原运行连接中断后补齐最后两对。用户要求偏航识别暂缓，当前调用数为 0。[C48 补跑记录与全批结果](resume_01/README.md)

07:38 UTC 后台启动，主管 PID 3659144。官方目录确认模型为支持图像输入的 DeepSeek-V4.1-Flash。07:39:09 UTC，10 个工作进程均已提交正式请求，15 次请求中 5 次已返回 HTTP 200 并通过校验，判同 4 对、判异 1 对。正常启动后交后台，完成时汇总写入本目录的 `completion.json`。

2026-11-18，用户指定从当前 53 条轨迹中取 10 条覆盖不同场景，使用 10 个进程调用 DeepSeek。先把 19 个场景按名称排序，固定种子 2 均匀无放回抽 10 个，再按选中场景的名称顺序从各自排序的 episode ID 中均匀抽一条。导航数据的 seed 也是 2。抽取保留原始案例编号，可与同轨迹的 [Qwen27B 全量运行](../run_20261118_01_qwen27b/README.md)对应。[固定名单](selection.json)

输入是 93 个原始候选，67 对间隔在 8 步内，需要调用模型。去重 v001 与偏航 v003 分别读取历史快照中的提示词和请求参数。使用官方 DeepSeek 接口、`deepseek-flash`、thinking enabled、high、JSON、max_tokens 32768、非流式，模型请求沿用历史默认 seed。各阶段同时处理十条轨迹，每条轨迹内按时间顺序处理。全批去重后，对各自保留的节点重新编号并加入真实终止观测，直至模型判定首次偏航或轨迹结束。模型读取原生前视和当前阶段需要的文本。结论用于离线识别。

准备命令为 `.runtime/crossing_vllm27/bin/python -B scripts/run_route53_deepseek_subset.py --prepare`，启动命令将末尾选项改为 `--launch`，凭据通过隐藏输入与匿名管道传递。完整 Git 版本、源码、实际请求参数及输入哈希见[运行清单](../../../../outputs/deviation_progress/v003/run_20261118_02_deepseek10/manifest.json)，[实时状态](../../../../outputs/deviation_progress/v003/run_20261118_02_deepseek10/status.json)记录两个阶段的进度。各次原始请求、响应与逐轨迹判定保存在同一输出目录。
