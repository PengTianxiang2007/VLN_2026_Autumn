# v006 C04/C32：GPT-6.1 Terra Fast

两例并行，seed=2，23 个原始候选。复用上一轮 v006 输入与二元判断规则。模型 gpt-6.1-terra，medium，显式请求 Fast（service_tier=priority），17982 代理。每个 case 新会话。完整命令见 launch.json，输出与运行源码快照见 outputs/codex_tasks/checkpoint_dedup/v006/run_20261124_02_terra_fast。时间按候选调用的 response.json/elapsed_seconds 统计，初始化及整例耗时单列。

v006 Terra Fast 两例全部完成，23 次候选调用平均 30.43 秒，中位数 29.21 秒，初始化平均 35.66 秒，两例并行共 508.01 秒。所有请求均带 priority。与上一轮 Astra 对照见 timing.json。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。
