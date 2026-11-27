# 0208 / 0240 后续队列：接续 Node 修复后的 0036

20:36 UTC：GPU1 前置恢复导入失败后，核验本队列没有导航子进程，已停止等待器并由 [run08](../run_20261126_08_scene0208_0240_high_after_bridgefix/README.md)接续。GPU0 前置继续运行，GPU1 改接修复后的 run07；本轮不恢复、不重复启动。

日期：2026-11-26 UTC。用户授权修复并恢复原任务及后续队列。GPU0 接 kujiale_0208 全 25 条，GPU1 接 kujiale_0240 全 23 条，seed 2；明确排除 0128 和已替换的 0234。协议、场景选择和同 seed 原版配对沿用 [run04](../run_20261126_04_scene0208_0240_high_queued/README.md)。

前置改为 [run05 修复重跑](../run_20261126_05_scene0036_high_dual_nodefix/README.md)，使用全新输出与原生 run ID。仍要求前置正式评分完整、正常完成、进程退出和资源释放；技术故障不自动绕过。保留 high、180 步、RGB、计时、10 次请求和原生评分。Node 绝对路径显式传入后续进程。

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_06_scene0208_0240_high_after_nodefix/queue.py
```

实际状态以同名 outputs 目录中的 `queue_launch.json`、`queue_status.json` 为准。`manifest.json`、`baseline48.csv` 冻结任务和成绩；输出另保存实际 Git HEAD、差异、相关源码与队列快照。旧 run04 已阻塞退出，不会重复启动。

当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条；等待任务不计技术跳过。后续按当前版正式评分唯一 episode ID 配对，SPL 包含失败任务。
