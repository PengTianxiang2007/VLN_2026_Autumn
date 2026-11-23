# 首次正式评分的真实恢复闭环

2026-11-21，准备后跳过，导航运行 0 条。C13 已取得带正式评分的闭环，条件主管正常退出。下列配置保留作接续记录。按用户要求沿用已冻结各模块与 seed 2。选择同一场景 kujiale_0165 的 C17、C19、C20、C21，均有离线非终止报警和非空 Qwen 局部指令，仅用于选择任务；在线运行从任务起点自然触发。

使用原生连续评估循环，保留每条实际评分，第一条有物理回退、局部运动和记忆交还后原任务运动的任务完成正式评分时退出。未启动的任务单列。同一节点多次审阅时复用该次在线实测位姿的三图。

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_serial_pipeline.py --protocol v006 --stop-after-cycle \
  --episodes kujiale_0165_40_1 kujiale_0165_49_4 kujiale_0165_53_0 kujiale_0165_57_0 \
  --jev-endpoint https://api.easyjev.online/v1/systemone \
  --semantic-service outputs/model_services/qwen27b_gpu3_20261121_01/service.json \
  --output outputs/serial_recovery/v002/run_20261121_04
VLN_MODEL_READY_TIMEOUT=3600 benchmarks/vlnverse/.venv/bin/python -Bu scripts/run_serial_v006.py \
  --campaign outputs/serial_recovery/v002/run_20261121_04 --model-gpu 1 --sim-gpu 3
```

Git 和工作区源码见运行目录的 manifest.json 与 code/。Qwen 复用已有服务；本轮导航模型与仿真按正常或异常退出收尾。
