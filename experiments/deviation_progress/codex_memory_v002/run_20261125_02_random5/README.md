# 同会话偏航评审 v002 随机追加五例

16:19:44 UTC 五例全部完成，技术失败 0 例。C42 在 F19→F56（终止帧）、C19 在 F21→F38（终止帧 F49 之前）首次判定偏航，按协议停审。C27、C35 的最后一段分别为 F7→F42、F28→F44，均判为未偏航。C01 首个有效节点是 F65（终止帧），仅初始化，无可比较的区间。原始结果见 [results.json](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_02_random5/results.json)。

16:06:04 UTC 已后台启动，主管 PID `1404086`。启动核对时 C01、C27、C35、C42 的四个 Codex 子进程已发起各自的初始化调用，C19 排队。五例的原始候选数依次为 4、2、4、2、4，终止帧依次为 F65、F42、F44、F56、F49。启动后交后台，后续状态由主管写入 status.json。

2026-11-25。沿用上一批终止节点评审，从冻结的 VLNVerse 53 条 seed 2 轨迹中排除前两批的 C05/C09/C25、C17/C20/C23/C43。在剩余 46 条中按编号排序，以独立抽样 seed 20261125 无放回抽取，顺序为 C01、C27、C35、C42、C19。抽样未读取报警或事后归因。候选来自 JEV v002 active，去重按 v006.1。GPT-6 Astra 常规档、medium，4 个独立工作进程，空位自动接续第 5 例。CPU 调用远端 Codex。首次有效报警停审，否则纳入 END。无导航仿真或 GPU 推理。

基线提交 `e40d9a821ee72516261ee819284e36be7be2eff1`。抽样、输入来源哈希和候选见 [input.json](input.json)。初次冻结清单使用 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v002/run_20261125_02_random5/prepare.py`。实际工作区差异和执行源码快照保存在输出 source/。后台进程使用下列参数：

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_codex_node_dedup.py \
  --input experiments/deviation_progress/codex_memory_v002/run_20261125_02_random5/input.json \
  --output outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_02_random5 \
  --workers 4 --model gpt-6-astra --reasoning-effort medium --timeout 1800 \
  --proxy-url http://127.0.0.1:17982
```

运行中与最终状态见 [status.json](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_02_random5/status.json)，最终原答写入同目录 results.json。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

## 九例合并回放

2026-11-25T16:30:57.799700+00:00 已将五例与上一批四例发布到[原网址](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html)，附[九例离线包](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/replay.zip)，原四例保存在[归档](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01_archive4/index.html)。左栏按 case 编号升序。C01 单列为仅初始化。

本地浏览器已逐例验证选择、筛选顺序、双语回答、证据帧跳转与终止帧。共 493 帧、30 轮。离线源为 `outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_02_random5/exports/combined9_01/index.html`，SHA256 `defa61a29ca2eb7a9f24a05f559912ba30164e95f58e7f42a7bdbb1b15cdde83`。在线目录为 `visualization_publishing/codex_deviation_v002_combined9_map_layers_web_20261125_01`（位于 outputs/）。原网址共 503 个文件通过远端哈希校验，入口 HTTP 200，SHA256 `f3b76c97830b4d193040cef3bf5e8204068e5cc60103032359908c098d81a47e`。[发布记录](../../../../outputs/visualization_publishing/publish_20261125_163057_255700/publication.json)。
