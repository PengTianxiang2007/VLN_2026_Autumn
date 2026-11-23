# GPU 3 常驻 Qwen27B 的 v005 六例离线评审

2026-11-20 UTC。使用 v004 同一组 C07、C11、C19、C30、C47、C50 和 seed 2 轨迹，复用同一去重节点、前视图、最多七帧采样与原模型参数。v005 每轮只接受 consistent 或 deviated，每条在首次有效偏航或终止节点结束。服务健康检查已返回 HTTP 200，模型目录已返回 `route53-qwen27b`，API 进程为 3800879。评审结束后继续保留模型。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004.py --version v005 --qwen-service outputs/model_services/qwen27b_gpu3_20261120_02/service.json --cases 7 11 19 30 47 50 --output outputs/deviation_progress/v005/run_20261120_02_qwen_gpu3
```

实际提交、源码快照、请求参数和 Prompt 哈希见[运行清单](../../../../outputs/deviation_progress/v005/run_20261120_02_qwen_gpu3/manifest.json)。[运行状态](../../../../outputs/deviation_progress/v005/run_20261120_02_qwen_gpu3/status.json)随评审更新，逐轮输入与原答保存在该目录的 `run/cases/`。

07:38:14 UTC，独立评审进程 PID 3827248 进入 C07，首个真实请求为 S01、单张 F2。六例已交后台执行。[启动记录](launch.json)

08:06:31 UTC，六例评审全部完成，共 33 轮，28 次 consistent、5 次 deviated、0 次格式错误。模型首次报警分别为 C07 F41→75、C11 F0→5、C19 F19→38、C47 F31→52、C50 F15→33，C30 的 13 轮均为 consistent。以上为模型判定，报警正确性待逐例分析。GPU 3 常驻模型继续保留。[逐例结果](../../../../outputs/deviation_progress/v005/run_20261120_02_qwen_gpu3/v005_results.json)

08:14 UTC，v005 回放与 Qwen v004、DeepSeek v004 对照已发布到用户指定的原网址，默认显示 v005。[网页、下载与发布记录](exports/web_20261120_01/README.md)
