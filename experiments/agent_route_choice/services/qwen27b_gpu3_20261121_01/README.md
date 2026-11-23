# GPU3 Qwen27B 待用服务：2026-11-21

状态：后台主管和模型服务进程已正常启动，已结束人工跟踪；未探测模型就绪。

用户明确要求先挂起 GPU3 Qwen27B，正常启动后交后台，再继续编写 recovery 第一次调用版本。复用 Qwen3.8-27B-FP8、本地既有环境和上一服务参数；上下文 16384、最多十图、显存比例 0.70、seed 2、单并发。GPU3 已有两个他人进程，检查时合计约 3.8 GiB、GPU 负载 0%，可用显存约 44.6 GiB，主存可用约 342 GiB；保留他人任务，启动器继续执行原有资源准入。

使用 `--process-only`：主管只保持服务进程，不发送健康探针或推理请求，不等待权重加载完成。空闲保留待用，不因本次文档任务结束清理。异常退出沿用既有精确子进程清理。

从仓库根目录启动的命令：

```bash
/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/.runtime/crossing_vllm27/bin/python -Bu /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/scripts/serve_qwen27b_standby.py --config /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/experiments/agent_route_choice/services/qwen27b_gpu3_20261121_01/model.json --output /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/model_services/qwen27b_gpu3_20261121_01 --gpu 3 --allow-shared-gpu --process-only
```

实际以独立后台进程启动，stdin 为 DEVNULL，日志写入 `outputs/model_services/qwen27b_gpu3_20261121_01.supervisor.log`。状态见 [service.json](../../../../outputs/model_services/qwen27b_gpu3_20261121_01/service.json)，服务日志见 [server.log](../../../../outputs/model_services/qwen27b_gpu3_20261121_01/server.log)。

实际 Git、源码快照及哈希见 [registration.json](registration.json) 和 `source/`；已有未提交源码差异记录在 `workspace.patch`。本次未运行支路识别、纠错指令生成或导航，没有评测样本与成绩。

启动确认：主管 PID 993933、模型服务 PID 994127 均存活，工作目录及命令与本项目一致。服务地址 `http://127.0.0.1:56923/v1`，模型名 `route53-qwen27b`。状态 `running`、`readiness=not_probed`；仅证明进程启动，没有就绪或推理通过声明。按用户要求结束人工跟踪，后台继续加载和待用。证据见 [startup_confirmation.json](startup_confirmation.json)。

2026-11-22T16:01:31.613687+00:00，按用户要求已释放。主管通过原生停止流程结束，服务进程清单为空。GPU 3 释放 Qwen 引擎原占用 35,414 MiB，复核时仅剩独立的 RGB 仿真进程 3941366。
