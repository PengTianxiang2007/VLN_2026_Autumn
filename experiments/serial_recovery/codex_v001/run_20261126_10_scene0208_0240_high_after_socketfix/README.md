# 0208 / 0240 后续队列：恢复 socket 修复版

2026-11-26 UTC。继续用户授权的两场景队列，不增加并发：GPU0 的 0208 全 25 条接 run05 GPU0；GPU1 的 0240 全 23 条接 [run09](../run_20261126_09_scene0036_gpu1_socketfix/README.md)。seed 2、Codex high、180 移动步、RGB、计时与原生评分不变。排除 0128、0234。

run08 因 GPU1 前置 socket 错误阻塞，核验无导航子进程后已停止等待并记录 superseded；本轮使用新目录、新原生 run ID。源码快照含显式本地 /tmp socket 修复，另保存上游包兼容入口及 SHA256。仍要求各路前置正式评分完整且正常退出、清理，故障不自动跳过。

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_10_scene0208_0240_high_after_socketfix/queue.py
```

实际状态见同名 outputs 的 queue_launch.json、queue_status.json；清单及同 seed 原版成绩见 manifest.json、baseline48.csv。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。
