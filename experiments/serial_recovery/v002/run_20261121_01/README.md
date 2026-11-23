# C01 单条在线验收

2026-11-21，冷启动超过 900 秒，正式评分 0/1。StreamVLN PID 1547406 已退出，GPU 1 已释放，仿真未启动。[运行 02](../run_20261121_02/README.md)延长等待并重试。目标是在一条从起点重走的任务上观察自然报警、实际节点位姿回退、使用新生成指令的局部运动、原任务记忆交还与正式导航评分。

样本为 Route53 C01，VLNVerse fine val_unseen 的 `kujiale_0036_0_0`，导航 seed 2。选择它的依据为离线 v006 在非终止节点报警且 Qwen 两阶段有非空输出。历史节点、报警、支路与指令仅用于选样，均不传入在线执行器。

逐动作前视调用 EasyJEV v004、冻结 v001 采样和去重。去重后相邻的有效节点提供偏航证据，报警时取上一可信节点及其已存进度。两次 Recovery 均用本项目已保留的 Qwen27B，以回退节点实测相机位姿生成三向图，使用本段已获得的四张后续前视。空指令不接管，终止节点报警只登记。局部任务单独清空记忆，局部 STOP 或队列边界的 40 动作预算交还接管前原任务记忆。原生物理预算包含纠错。单条自然未触发也保留正式结果。

输出目录为 `outputs/serial_recovery/v002/run_20261121_01/`。实际源码、Prompt 和配置以运行目录里的 manifest 及代码快照为准。

运行时按帧维持最新的原始候选。新候选判为不同，或去重的 8 步可替换窗口走完，才将前一个候选送入 v006。记录节点发生帧、采样发出帧和在线确认帧。待交还的本地指令使用回退前生成的第二阶段原答。拒绝接管时原任务继续，交还时沿新一段重建采样并带回原可信进度。

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_serial_pipeline.py \
  --protocol v006 --episodes kujiale_0036_0_0 --jev-endpoint https://api.easyjev.online/v1/systemone \
  --semantic-service outputs/model_services/qwen27b_gpu3_20261121_01/service.json \
  --output outputs/serial_recovery/v002/run_20261121_01
benchmarks/vlnverse/.venv/bin/python -Bu scripts/run_serial_v006.py \
  --campaign outputs/serial_recovery/v002/run_20261121_01 --model-gpu 1 --sim-gpu 3
```

EasyJEV 凭据由运行时环境或隐藏输入提供。仿真与本轮 StreamVLN 随实跑结束退出，原 Qwen 服务保留。串行及偏航协议定向 CPU 检查 29 + 4 项通过。

运行冻结 1,362 个源码及资源文件，Git 基线 `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 加本次工作区快照。[运行状态](../../../../outputs/serial_recovery/v002/run_20261121_01/status.json)和[运行清单](../../../../outputs/serial_recovery/v002/run_20261121_01/manifest.json)记录实际版本与进度。
