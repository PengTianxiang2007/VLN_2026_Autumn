# v005 DeepSeek 53 进程离线评审

最终状态：12:50:24 UTC 以 `incomplete` 结束，6 条完成、47 条失败（46 条 HTTP 429、1 条 HTTP 524）。已完成轨迹为 C11、C13、C16、C25、C26、C31，共 22 轮，17 次 consistent、5 次 deviated。主管已退出；本批结果与可复用的已返回回答由 [15 并行接续](../run_20261120_05_deepseek15/README.md)继承，失败数不代表最终全组结果。

用户于 2026-11-20 明确授权：同一批 C01–C53 全部离线样本，使用 v005，53 个并行进程，通过指定网关 `https://ai.dijinlong.com/v1` 调用 DeepSeek。模型列表已返回 HTTP 200，包含此前使用的 `deepseek-flash`。凭据只通过隐藏终端及主管 stdin 传入，不写入仓库、启动命令、日志或运行清单。

使用与已完成 Qwen v005 相同的 seed 2 轨迹、冻结去重后节点与终止节点、原生前视 PNG、中文 Prompt、最多七帧采样和进度协议。53 条共有 429 个有效节点，是本组最多调用次数；每条内部串行，在首次有效 deviated 或终止节点结束，各自维护 A 和进度。一次节点调用不因语义判断或格式错误重试。已完成的 Qwen 和历史 DeepSeek v004 均不覆盖或重跑。

DeepSeek 推理参数沿用此前配置：`deepseek-flash`、`thinking.type=enabled`、`reasoning_effort=high`、`max_tokens=32768`、`response_format.type=json_object`、`stream=false`，未指定模型推理 seed。本次修改仅为原并行入口增加 `--api-base`，默认端点保持原值。所有图像与进度保存到每条 `run/cases/Cxx/` 的请求、原始响应和状态文件。

```bash
PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004_deepseek.py \
  --version v005 --api-base https://ai.dijinlong.com/v1 \
  --workers 53 --cases {1..53} \
  --output outputs/deviation_progress/v005/run_20261120_04_deepseek53
```

运行目录：`outputs/deviation_progress/v005/run_20261120_04_deepseek53/`。主管状态为 `status.json`，逐条完成摘要为 `v005_results.json`，逐轮日志为 `supervisor.log`。入口冻结实际 Git 提交、源码与 Prompt 哈希、模型参数、数据和节点清单。主管退出时将结果写入本记录的 `completion.json`。

12:43 UTC，主管 PID 4060545 启动，53 个不同工作进程均发出首轮真实请求。网关大量返回 HTTP 429；12:47 UTC 已有 4 条完成、46 条失败、3 条仍在途。用户随后明确改为 15 并行，[15 并行接续主管](../run_20261120_05_deepseek15/README.md)已启动，等待本批在途任务正常收尾，复用已完成结果及上下文匹配的 HTTP 200 回答。保留本批失败原答，不重新发起 53 并行。调用远端服务，不占用新的本地 GPU，不改动用户要求保留的 GPU 3 Qwen。启动记录见 `launch.json` 与 `startup.json`，最终状态以输出目录的 `status.json` 为准。
