# C01 在线恢复，延长冷启动等待

2026-11-21，同条重试。[运行 01](../run_20261121_01/README.md)在导航模型冷启动时触及 900 秒上限并释放 GPU。沿用 C01 `kujiale_0036_0_0`、seed 2、GPU 1 StreamVLN、GPU 3 仿真与已保留的 Qwen27B。JEV、去重、v006 判断、七图两阶段 Recovery、接管交还和原生评分协议均沿用运行 01。加载等待设为 3,600 秒。

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_serial_pipeline.py \
  --protocol v006 --episodes kujiale_0036_0_0 --jev-endpoint https://api.easyjev.online/v1/systemone \
  --semantic-service outputs/model_services/qwen27b_gpu3_20261121_01/service.json \
  --output outputs/serial_recovery/v002/run_20261121_02
VLN_MODEL_READY_TIMEOUT=3600 benchmarks/vlnverse/.venv/bin/python -Bu scripts/run_serial_v006.py \
  --campaign outputs/serial_recovery/v002/run_20261121_02 --model-gpu 1 --sim-gpu 3
```

Git 基线 `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 加工作区源码快照。[源码清单](../../../../outputs/serial_recovery/v002/run_20261121_02/manifest.json) · [运行状态](../../../../outputs/serial_recovery/v002/run_20261121_02/status.json)。

## 实际结果

C01 已获 1/1 条正式评分，66 个原任务动作、66 次实时 JEV。5 个原始候选产生 3 个存档节点（F0、F5、F35），另有 F66 终止节点。F0→F5 实跑判为 consistent。F5→F35 在动作边界 48 报警，目标为 S02／F5。回退点实测相机位姿三向图和四张实走前视均已送入第一次 Recovery。模型只列出 B1，previous_attempt 为 uncertain／null。第二次仍输出 B1 和英文指令，违反排除规则，被原协议校验拒绝，原任务继续。终止节点 F66 的第二次报警只登记。实际回退、局部动作与交还均为 0。

正式 SR 0、SPL 0、NE 3.6499 米、TL 7.5613 米、OS 1，结束原因为 not_reach_goal。StreamVLN 与仿真均退出，GPU 1、3 已核对释放本轮进程，原有 Qwen 服务保留。[原生评分](../../../../outputs/serial_recovery/v002/run_20261121_02/official_result.json) · [执行证据](../../../../outputs/serial_recovery/v002/run_20261121_02/validation.json)。

复核动作边界 48 的报警原答：v006 引用 F27、F34、F35，确认已按要求进入客厅，判偏航的理由是 F35 尚未看到下一步右转进入卧室。其文字没有指出已经走上冲突支路，属于疑似提前报警，尚无人工真值判定。第一次 Recovery 锚定 F5，四张后续前视为 F7、F10、F13、F15，与报警引用的较晚帧不重叠。这个样本同时暴露了报警依据和两模块证据时间范围的差异。
