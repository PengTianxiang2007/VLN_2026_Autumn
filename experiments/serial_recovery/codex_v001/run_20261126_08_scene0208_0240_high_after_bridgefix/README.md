# 0208 / 0240 后续队列：接续各路最新有效前置

2026-11-26 UTC。用户授权修复运行故障并继续原队列。GPU0 的 0208 全 25 条接 [run05 GPU0](../run_20261126_05_scene0036_high_dual_nodefix/README.md)；GPU1 的 0240 全 23 条接 [run07 GPU1](../run_20261126_07_scene0036_gpu1_bridgefix/README.md)。seed 2、Codex high、180 移动步、RGB、计时、请求保护与原生评分均不变。明确排除 0128、0234。

旧 run06 已核验只有等待/阻塞状态后停止，没有停止 GPU0 或旧保留仿真。本轮新 run ID 和新目录不覆盖旧记录。前置必须正常完成全部正式评分并释放进程，技术错误不自动跳过；资源准入与每卡一组并发保持不变。新增包兼容入口单独保存源码和 SHA256，启动前核对未变化。

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_08_scene0208_0240_high_after_bridgefix/queue.py
```

实际 PID、状态见同名 outputs 的 `queue_launch.json`、`queue_status.json`；任务与原版成绩见 `manifest.json`、`baseline48.csv`。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。
