# Oracle 纠正与恢复

更新时间：2026-11-04。旧五组和新配对语义延迟实验均已完成，结果分别统计。

[pilot10](pilot10/README.md) 为原五组已完成实验：同十条任务、五种纠正时机、允许多次纠正，位置和朝向一起修改，policy memory 保留。

追加 15–20 条不同任务的计划已取消，不得恢复。最初单次干预试跑仅为历史记录，不混入正式多次干预结果。

- [共享前缀三分支语义延迟](paired_delay10/README.md)：2026-11-04 已完成 10/10 条、30 项结果（22 个实际纠正分支、8 项未触发）；完整配对七条各档均 5/7 成功，已导出单文件同步回放 HTML，GPU 已释放；延迟按每条历史错误轨迹语义标定，不固定动作批次或距离。

- 最初十条 10/10 成功的尽早纠正组已按配对实验模板单独重导出离线 HTML（18 次纠正）；入口见 [尽早纠正组](pilot10/early/README.md)。

- [配对延迟的下降原因复核](paired_delay10/README.md)：区分未触发、首事件解除后关闭审阅、纠正后 STOP，以及跨轮错误/前缀差异；总成功率下降不能单独归因于延迟。

2026-11-05：用户授权原十条任务的新真实存档点配对实验（StreamVLN续走 vs Oracle实际动作选路），已完成；不使用正确路径瞬移落点。记录 experiments/oracle_recovery/checkpoint_action10/README.md。

2026-11-06：真实存档十例的可视化已修正为完整“首次走错→复位→续走”时间线，七对十四条恢复边界经原始帧/restore_proof与浏览器核验；新入口 `outputs/oracle_crossing/checkpoint_action10/run_20261105_01/exports/timeline_20261106_02/oracle_checkpoint_timeline.html`。旧模板导出的遗漏已登记，实验未重跑，成绩未改变。
