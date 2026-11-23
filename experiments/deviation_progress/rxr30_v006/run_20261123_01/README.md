# RxR 30 条离线轨迹：去重回退点与 v006 偏航识别

2026-11-23 10:06:44 UTC 本次语义队列因45分钟启动等待超时失败，最后加载到31/66权重分片，去重和偏航均0/30；主管、服务和EngineCore已清理，旧日志和状态保留。10:19 UTC 已以独立运行[延长启动等待接续](../run_20261123_02_startup_timeout/README.md)，复用本次全部JEV结果。后续语义状态以新运行目录为准。

2026-11-23 10:05 UTC 进度查询：JEV 已完成 4,435/4,435 帧、725 个原始候选；主管 1409469、服务 1410202 均存活，GPU3 的 EngineCore 1454575 占用约 29.1 GiB。日志权重加载至 28/66 分片（42.4%），主状态仍为 loading_qwen，去重 0/30、偏航 0/30，偏航阶段状态文件尚未生成。此次只读查询，未重启或改动运行。离线评审没有新导航评分，当前版及按其已评分 ID 匹配的原版均为“暂无，已评分 0 条”；30 条来源轨迹的原版历史 SR 0/30（0%），平均 SPL 0。

2026-11-23 用户指定暂停 R2R 并将 GPU 3 调给本批 Qwen。JEV 已全部完成，4,435 个有效帧评分，725 个原始候选。09:21 UTC 接续主管 PID 1409469、模型服务 PID 1410202，在 GPU 3 加载本地 Qwen27B。启动时保留其他用户约 2.2 GiB 进程，复用三次低负载与足额显存准入检查，模型显存预算 70%。待 Qwen 就绪后去重，全部有效节点落盘后自动进入 v006。原等待队列已退出。[GPU3 接续源码与配置](../../../../outputs/deviation_progress/rxr30_v006/run_20261123_01/recovery/gpu3_20261123/registration.json)

```bash
tmux -L peng_rxr30_nodes_20261123 new-session -d -s rxr30_gpu3 'exec .runtime/crossing_vllm27/bin/python -Bu scripts/run_rxr_offline_semantics.py outputs/deviation_progress/rxr30_v006/run_20261123_01 --gpu 3 --allow-shared-gpu >> outputs/deviation_progress/rxr30_v006/run_20261123_01/launcher_gpu3.log 2>&1'
```

沿用[已发布的 30 例随机样本](../../../crossing_analysis/rxr_seed2_400/run_20261123_01/exports/random30_20261123_01/sample.json)，8 个场景、4,465 帧。抽样与 Qwen seed 均为 2，原导航 Habitat 配置 seed 100。原版 StreamVLN 在这 30 个既有 episode 全部失败，SR 0/30（0%），平均 SPL 0。离线流程不产生新导航评分。

第一轮读取每条轨迹的原生前视 PNG，按 VLNVerse Route53 的非终止帧窗口向仓库配置的 EasyJEV 提交 v004 请求；共产生 4,435 个帧分数。每条轨迹独立运行冻结的 v001 在线采样器，候选在五步后确认。沿用 v001 双节点去重：相隔至多 8 步时用本地 Qwen 比较两处各自前后两帧与当前帧，相同则删旧留新。保留有效节点步号、确认时刻、原图、位姿和终止节点。第二轮只能在全部 30 条的节点清单落盘之后启动。

第二轮沿用[VLNVerse Qwen v006](../../v006/README.md)，按有效节点顺序，用原英文指令、累计进度、截至 B 的端点和最多 5 张均匀中间前视图判断偏航。首个有效报警后停止本例，保存判定对应区间、报警可用时刻及目标回退点。决策步与确认步的既有归因仅用于事后核对。第二轮没有实际导航、回退或新 SR/SPL。

模型为本地 Qwen3.8-27B-FP8，单卡单并发，temperature 0、top_p 1、max_tokens 8192、关闭 thinking。第一轮 JEV 使用仓库 .env.easyjev.local 的私有配置，24 个并发请求，认证不写进产物。Qwen 排队等任意空闲卡，服务仅在需要语义评审时加载，任务结束清理。Git 基线 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。

```bash
out=outputs/deviation_progress/rxr30_v006/run_20261123_01
.runtime/crossing_vllm27/bin/python -Bu scripts/run_rxr_offline_jev.py "$out" && .runtime/crossing_vllm27/bin/python -Bu scripts/run_rxr_offline_semantics.py "$out"
```

[逐帧评分进度](../../../../outputs/deviation_progress/rxr30_v006/run_20261123_01/jev/status.json) · [去重与偏航阶段进度](../../../../outputs/deviation_progress/rxr30_v006/run_20261123_01/status.json)

2026-11-23 08:30 UTC 在 tmux `peng_rxr30_nodes_20261123:rxr30` 启动。08:42:49 UTC JEV 已取得 980/4,435 个有效评分，处于第一轮请求。episode 837 的 F2 实际返回概率 0.86。Qwen 接续入口已完成真实帧数据与终止节点的 CPU 对接检查，尚未开始去重或偏航推理。原始采集索引、模型提示和实际源码版本见[批次清单](../../../../outputs/deviation_progress/rxr30_v006/run_20261123_01/manifest.json)。Qwen 进入第二轮后，逐例进度另见[偏航识别状态](../../../../outputs/deviation_progress/rxr30_v006/run_20261123_01/deviation/status.json)。
