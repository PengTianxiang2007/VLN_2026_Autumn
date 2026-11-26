# C27 终止段补图五档计时复测

沿用 seed 2、JEV v002 active 的 C27 S02（F7）到 END（F42），从原终止判定之前的相同截点独立新建五个分支，各补 3、4、5、6、7 张原生前视图。采用上一轮相同的模型 GPT-6 Astra 常规档、medium、17982 代理、输入、输出合同和最多四路并发。上一轮 7→3 提交，本轮改为 3→7 提交，将最后接续的组从 3 张换为 7 张，观察低耗时是否跟随提交顺序变化。

命令为 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v002/run_20261125_06_c27_frames3to7_repeat/replay.py`。单次计时从调用 Codex CLI 前开始，至该次请求完成，排除本地分叉、读图和并发空位等待。用两轮中各分支的进程起止时间计算真实重叠，用日志核对重连与超时。产物见 `outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_06_c27_frames3to7_repeat/`。

## 结果

| 补图 | 上轮（秒） | 复测（秒） | 复测减上轮（秒） |
|---:|---:|---:|---:|
| 3 | 80.092 | 68.312 | -11.780 |
| 4 | 106.366 | 67.625 | -38.741 |
| 5 | 106.638 | 69.538 | -37.100 |
| 6 | 106.028 | 69.975 | -36.053 |
| 7 | 104.754 | 69.101 | -35.653 |

五组均报警。上轮和本轮平均调用时间分别为 100.776 和 68.910 秒，本轮极差 2.350 秒。两轮同档输入和输出合同经哈希及配置核对，来自同一原始会话截点。上轮四图组出现一次模型列表刷新超时，本轮各组均无该告警。两轮 CLI 公布的推理事件均未记录重连。

复测期间经 17982 对 ChatGPT 首页执行两次无认证 HTTPS HEAD，HTTP 均返回 200，耗时 0.332299 和 0.361277 秒。这是代理侧网页连通性参考，不能分离真实推理请求中的网络、排队、缓存及生成耗时。

[逐组计时、重叠与告警](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_06_c27_frames3to7_repeat/timing.json) · [同代理的网页响应时间](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_06_c27_frames3to7_repeat/proxy_headers_timing.json) · [原始判定](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_06_c27_frames3to7_repeat/comparison.json)。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。
