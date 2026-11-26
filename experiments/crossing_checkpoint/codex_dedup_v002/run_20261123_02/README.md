# VLNVerse C01–C10 · GPT-6 Astra 三帧去重

状态：十条推理完成，可视化已验证并发布。用户在 6.2 调用失败后明确授权改用 GPT-6 Astra，十进程并行，并再次要求可视化。

## 协议

沿用 v001/run_20261123_02 的同十条 seed=2 错误轨迹、89 个原始候选及同一图像源。每端仅 -2、0、+2 原生前视，删除 ±1；开始前缺图明确标记。预计 63 次比较。模型 gpt-6-astra / medium，每轮超时 600 秒；Codex 无固定采样 seed。每例独立新会话，例内顺序 exec/resume，不复用旧五帧历史。

沿用不超过 8 步才比较、same 删旧留新、different/uncertain 保留双方的协议；有效证据仅限三帧标签。只做第一轮去重，不新采样、不追加终止节点、不启动导航、不占 GPU。与旧五帧相比模型和 reasoning 保持相同。

三帧输入与引用校验的定向测试已通过，本轮未再改推理逻辑，不重复测试。GPT-6 Astra 同登录最小请求已成功。实际源码、Git 提交和差异由入口保存在 output/source/ 与 status.json。

## 启动

```bash
.runtime/crossing_vllm27/bin/python -u scripts/run_codex_node_dedup.py --input experiments/crossing_checkpoint/codex_dedup_v002/run_20261123_02/input.json --output outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_02 --workers 10 --model gpt-6-astra --reasoning-effort medium
```

输出：`outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_02/`；逐例历史在 cases/Cxx_ep<episode>/codex/turns/。

## 可视化交付

在现有对照模板增加“GPT-6 Astra · 三帧”独立选项，保留旧 GPT-6 Astra 五帧、Qwen 和 DeepSeek；DeepSeek 只有 C04/C08 去重结果。支持独立勾选、组合并集、原始候选、逐轮原答、对应三帧证据、中英文切换、同步地图/RGB进度条。新建发布版本，不覆盖历史结果。

当前版 SR / 平均 SPL：暂无，已评分 0 条；配对原版 SR / 平均 SPL：暂无，已评分 0 条。

## 运行结果

2026-11-23T22:33:06.887411+00:00 启动，2026-11-23T22:42:05.537186+00:00 完成，耗时 538.6 秒。主管 PID 2496290，10 个独立进程、10 个独立新会话。89 原始候选 → 57 有效节点，删除 32；63 次比较、4 uncertain、0 格式错误、0 调用失败。[逐例摘要](summary.json)。旧五帧保留 56，Qwen 同十条保留 63；节点数量不是去重准确率。

| Case | 原始候选 | 三帧保留 | 旧五帧保留 |
|---|---:|---:|---:|
| C01 | 5 | 3 | 3 |
| C02 | 15 | 12 | 12 |
| C03 | 6 | 3 | 3 |
| C04 | 15 | 6 | 4 |
| C05 | 10 | 6 | 6 |
| C06 | 10 | 9 | 9 |
| C07 | 4 | 4 | 4 |
| C08 | 11 | 7 | 8 |
| C09 | 6 | 3 | 3 |
| C10 | 7 | 4 | 4 |

[可视化导出记录](exports/compare_20261123_01/README.md)。当前与配对原版 SR/平均 SPL 均暂无，已评分 0 条。

新版对照页已[发布](http://134.175.18.101/vln/codex_astra_three_frame_route10_compare_web_20261123_01/index.html)，默认三帧版，保留旧五帧、Qwen 及已有 DeepSeek。完整[离线包](http://134.175.18.101/vln/codex_astra_three_frame_route10_compare_web_20261123_01/compare_20261123_01_offline.zip)可下载；发布哈希与 HTTP 200 通过。主管正常退出，不占本地 GPU。

## 三帧与五帧的调用开销（现有日志分析）

同 63 对比较：三帧平均调用 41.253 秒，五帧 47.551 秒（+15.27%）；十路整批 538.650 秒 vs 607.597 秒（+12.80%）。五帧在 55/63 次配对调用、10/10 条任务累计调用耗时上更慢。三帧总输入 1,797,833 token，五帧 2,599,294（+44.58%）；其中非缓存输入 328,905 vs 518,782（+57.73%）。输出 16,848 vs 19,480（+15.62%）。

原生 token_count 已确认 CLI usage 是任务内累计值，按每任务最后一轮累计汇总，未重复累加；输入包括 prompt、历史和缓存，不是新增图片的独占 token。两组各运行一次且时段不同，缓存、网络、服务端负载和回答变化未控制，因此可报告本批观测差异，不声称稳定因果比例或统计显著性。没有新模型调用或导航实验。[统计摘要](latency_token_comparison.json)。
