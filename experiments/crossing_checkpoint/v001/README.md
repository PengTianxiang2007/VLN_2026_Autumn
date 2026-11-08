# Crossing v001：27B 无长思考离线回放

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

## 状态、方法与结果

开发集 8/8 条、573/573 观测完成，模型 Qwen3.8-27B-FP8，版本 qwen27_fp8_dev_v1_nothinking。
只构建 Crossing 存档，不判断此前路线正确、不做错误纠正；不是可恢复物理状态的存档。
输入只含截至当前的 RGB、动作历史与语义记忆；地图、参考路线、未来信息只用于评估。
确认 7 个存档；1m 匹配 TP=5、FP=2、FN=16，Precision=71.43%、Recall=23.81%、F1=35.71%。
地图是几何先验，尚非独立人工金标准。本版未达到扩大验证门槛；40 条验证集未启动。

## 环境、启动及下一步

权重位于 Resource_Peng/models/Qwen3.8-27B-FP8；vLLM 环境为 .runtime/crossing_vllm27。
完整模型启动与回放命令见下方版本指南。先人工复核现有 HTML，再另建版本迭代；本次不运行。
configs/protocol.json 和 task_lists/cohort.json 是原协议的归档，不替代原结果目录。
实现位于 core/crossing_checkpoint.py；历史实现以原运行 source 快照为准。

## 代码、启动说明与产物

- [完整版本说明与27B启动命令](../../../README_CROSSING_CHECKPOINT.md)
- [历史迭代记录](../../../docs/CROSSING_CHECKPOINT.md)
- [原 C / 现 P 可视化](../../../outputs/crossing_checkpoint/seed2_v1_20261103/reports/qwen27_fp8_dev_v1_nothinking_review/crossing_dev8_review.html)
- [原始协议](../../../outputs/crossing_checkpoint/seed2_v1_20261103/protocol.json)
- [当前实现](../../../core/crossing_checkpoint.py)
