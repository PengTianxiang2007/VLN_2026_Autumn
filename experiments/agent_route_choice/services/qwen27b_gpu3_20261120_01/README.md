# GPU 3 上的 Qwen27B 常驻服务

2026-11-21 04:41:55 UTC，用户明确要求释放 GPU3 服务。核验主管 3800779、服务 3800879 和引擎 3802467 的命令、仓库目录与 GPU 归属后，向主管发送 SIGTERM，沿用其清理流程。最终 `service.json` 为 `stopped`，主管、服务、引擎及资源跟踪子进程均已退出，`cleanup.remaining=[]`。GPU3 从 35,555 MiB 降至最终快照 5 MiB，无计算进程占用。其他 GPU 进程未操作，权重、环境、日志和实验结果保留。此前常驻保留要求已由本次释放命令终止，不自动重启。

释放请求记录：`outputs/model_services/qwen27b_gpu3_20261120_02/release_request_20261121.json`。最终进程清理及 GPU 快照见同目录 `cleanup.json`。

2026-11-20T07:13:18.577343+00:00，按用户指令启动并持续保留，等待后续任务。使用 v004 六例评审的模型名、权重和服务参数，seed 2，上下文 16384，最多十图。仅登记服务进程，无评测样本。启动时检查共享 GPU 的实际负载和可用显存，绑定服务器回环地址。主管没有空闲或加载超时，运行状态与模型推理就绪分开记录。

启动命令、源码哈希和配置来源见 [registration.json](registration.json)。服务 PID、接口和进程状态见 [service.json](../../../../outputs/model_services/qwen27b_gpu3_20261120_02/service.json)，vLLM 输出见 [server.log](../../../../outputs/model_services/qwen27b_gpu3_20261120_02/server.log)。

第一次准入检查中 GPU 负载升至 58%，该次未加载模型。GPU 3 空闲后使用独立输出目录重试，已核验后台进程与 GPU 绑定，随后结束跟踪。实际启动信息见 [launch.json](launch.json)。
