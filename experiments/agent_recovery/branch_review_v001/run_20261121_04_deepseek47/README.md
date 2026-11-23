# DeepSeek v1 · v006 全部 47 个回退节点

官方 deepseek-flash，七图和原 v1 Prompt 逐例取自 Qwen 全量请求，temperature=0、top_p=1、max_tokens=4096、关闭 thinking，接口未指定 seed。复用 C50、C07，剩余 45 例各一进程同时运行。初次传输失败记录保留，瞬时接口错误允许有限退避接续。原始请求与响应在 outputs/agent_recovery/branch_review_v001/run_20261121_04_deepseek47/。

启动命令为 .runtime/crossing_vllm27/bin/python -Bu experiments/agent_recovery/branch_review_v001/run_20261121_04_deepseek47/run.py，凭据通过标准输入仅传入内存。

2026-11-21T11:00:29.281428+00:00 完成。新增 45 个独立 worker 同时启动，复用 2 例，无传输重试。47/47 原答格式有效，共列出 111 条支路，47 例均匹配了此前所走支路。对应的 Qwen v1 结果为 47/47、101 条支路。支路数统计以各自原答为准，编号仅在单个模型的单例回答内有效。

双语展示译文在本地整理，与原答单独保存；网站支持勾选单个模型或同时勾选两个模型。

[Qwen / DeepSeek 全量对照网站](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/index.html) · [离线包](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/recovery_qwen_deepseek_v006_47_offline.zip)。
