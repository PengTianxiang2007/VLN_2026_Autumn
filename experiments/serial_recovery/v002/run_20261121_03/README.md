# C13 在线回退与交还补验

2026-11-21，完成，取得 1 次真实闭环和 1 条正式评分。14:20:26 UTC StreamVLN 就绪，14:20:40 UTC 启动仿真，14:32 UTC 仍在初始化场景。C01 已走通实时报警和两次 Recovery，因第二次输出违反支路选择协议，实际接管次数为 0。本轮沿用[运行 02](../run_20261121_02/README.md)全部协议，在一条历史观测中有明确过门运动的 C13 验收实际回退、局部运动、交还及正式评分。

VLNVerse fine val_unseen，`kujiale_0147_56_4`，seed 2。离线 v006 在 F2→F15 报警，Qwen 看见之后穿过右侧玻璃门，并给出一条替代支路。历史观测仅用于选样，在线从起点重新判定。

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_serial_pipeline.py \
  --protocol v006 --episodes kujiale_0147_56_4 --jev-endpoint https://api.easyjev.online/v1/systemone \
  --semantic-service outputs/model_services/qwen27b_gpu3_20261121_01/service.json \
  --output outputs/serial_recovery/v002/run_20261121_03
VLN_MODEL_READY_TIMEOUT=3600 benchmarks/vlnverse/.venv/bin/python -Bu scripts/run_serial_v006.py \
  --campaign outputs/serial_recovery/v002/run_20261121_03 --model-gpu 1 --sim-gpu 3
```

版本为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 加工作区实际源码。[运行清单](../../../../outputs/serial_recovery/v002/run_20261121_03/manifest.json) · [运行状态](../../../../outputs/serial_recovery/v002/run_20261121_03/status.json)。

## 实际接管

本轮在线建点为 S01／F10、S02／F43。v006 在动作边界 56 对该区间自然报警。第一次 Recovery 把实际已走的淋浴间支路识别为 B1，第二次选择 B2，原始英文指令为 “Turn right toward the wall with the sunflower painting.”。返回 S01 实测位姿后执行了 40 个局部动作，达到预算后交还。接管前后原任务记忆内容 SHA256 一致，动作序号 96 起已由原策略继续运动。

[同次决策与回退点](../../../../outputs/serial_recovery/v002/run_20261121_03/episodes/kujiale_0147_56_4/attempt_1795271649754660772/recovery_001/decision.json) · [位姿恢复](../../../../outputs/serial_recovery/v002/run_20261121_03/episodes/kujiale_0147_56_4/attempt_1795271649754660772/recovery_001/pose_restore.json) · [记忆交还](../../../../outputs/serial_recovery/v002/run_20261121_03/episodes/kujiale_0147_56_4/attempt_1795271649754660772/recovery_001/memory_restore.json)。

## 正式评分与收尾

全程 253 个动作，原任务 213 个、局部 40 个，交还后原任务执行 157 个动作。一次实际回退，一次记忆恢复，一次交还。原生结束原因为 stuck，SR 0、SPL 0、NE 9.7192 米、TL 11.8538 米。验证记录 full_chain_observed=true，官方 Count=1。StreamVLN 1674937、仿真 1677368 已退出并释放 GPU，保留原 Qwen 服务。备用队列 04 跳过，未启动导航。

[原生评分](../../../../outputs/serial_recovery/v002/run_20261121_03/official_result.json) · [完整闭环记录](../../../../outputs/serial_recovery/v002/run_20261121_03/validation.json)。
