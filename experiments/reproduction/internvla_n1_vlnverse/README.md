# InternVLA-N1 / VLNVerse seed0

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

## 状态

目标为 33 个 scene、825 条 fine Val Unseen，官方 N1 flash 配置。
本次读取的历史 status.json：50/825 条、2 个 scene 完成，phase=blocked_runtime_error，kujiale_0030 返回错误。
这不是实时进程检查；没有确认全集成功率，不将两条 smoke 的成功当作正式成绩。
两条 smoke 已通过加载和真实动作验证，详见原文档。

## 启动与下一步

状态入口：`python3 scripts/reproduce_internvla_n1_vlnverse.py status`。
重新运行前先检查错误日志与进程归属、修复原因并更新 README；本次整理不恢复队列。
实际启动、环境与 schema 审计见下方说明。Flash 与 StreamVLN physical 协议不同，结果分开报告。

## 代码、启动说明与产物

- [历史状态](../../../outputs/reproduction/internvla_n1_fine825_seed0_20261102/status.json)
- [实验 manifest](../../../outputs/reproduction/internvla_n1_fine825_seed0_20261102/manifest.json)
- [阻塞日志](../../../outputs/reproduction/internvla_n1_fine825_seed0_20261102/worker_logs/kujiale_0030.log)
- [配置与启动说明](../../../docs/INTERNVLA_N1_VLNVERSE.md)
- [队列入口](../../../scripts/reproduce_internvla_n1_vlnverse.py)
