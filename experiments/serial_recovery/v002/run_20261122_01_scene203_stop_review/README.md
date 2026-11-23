# 203 条配对评测 · 报警立即回退与主任务 STOP 前评审

用户于 2026-11-22 授权停止上一运行，切换到新版，确认开始正常导航后交后台。沿用[前一运行](../run_20261121_06_scene203/README.md)的 8 个场景、203 个唯一 episode、原生执行顺序、seed 2 和 25,000 物理 tick 预算，在全新目录从首条开始。原版逐条匹配[同一份基线](../run_20261121_06_scene203/baseline203.csv)。

新版本在有效偏航判断处清空未执行的主策略动作并回退；主任务提出 STOP 时先评审，通过后再提交给模拟器，偏航则回退。局部 STOP 仍交还主策略。Git 基线为 `7ce5f9f`，工作区源码、配置、清单与逐文件 SHA256 以[本次冻结版本](../../../../outputs/serial_recovery/v002/run_20261122_01_scene203_stop_review/manifest.json)为准。

启动使用项目 v006 主管，导航模型 GPU 1，仿真 GPU 2，复用 GPU 3 的 Qwen27B 服务。EasyJEV 认证从运行时传入。

```bash
VLN_MODEL_READY_TIMEOUT=3600 benchmarks/vlnverse/.venv/bin/python -Bu scripts/run_serial_v006.py \
  --campaign outputs/serial_recovery/v002/run_20261122_01_scene203_stop_review --model-gpu 1 --sim-gpu 2
```

[运行状态](../../../../outputs/serial_recovery/v002/run_20261122_01_scene203_stop_review/status.json)

已完成冻结和对照校验。标准启动器在 tmux 会话 `vln203_stop_20261122` 等待 EasyJEV 隐藏输入。一次性启动检查在观察到首个有效 JEV 响应和主策略动作后写入 `startup_confirmation.json` 并自动退出。准备阶段两组均为暂无，已评分 0 条。
