# v005 DeepSeek 15 并行接续

最终状态：2026-11-20 13:05:01 UTC 以 `incomplete` 退出，主管已停止。完成 20/53 条（含复用 6 条），33 条因接口错误未完成：13 条 HTTP 524、17 条 HTTP 525、3 条服务端断连。完整完成轨迹共 62 轮：42 次 consistent、19 次 deviated、1 次格式错误。连同未完成轨迹的部分回答，共保留 99 轮有效回答及 2 轮 HTTP 200 格式错误回答；另存 107 次 HTTP 429 退避尝试。以上接口失败不是模型偏航判定；所有成功与失败原答均保留。后续如接续，应复用这些已返回回答；本次查看未启动补跑。最终证据见 `completion.json` 和输出 `status.json`。

最新检查：旧批次已退出，当前为 `reviewing`，15 并行主管 PID 4064299 正常运行。状态快照更新于 12:52:50 UTC：完成 8/53 条，其中复用旧批 6 条、新完成 2 条；已保存 50 轮通过校验的回答（含复用及在途轨迹回答）。当前运行记录了 37 次 HTTP 429 退避尝试，尚无被判定为最终失败的轨迹。动态统计以输出 `status.json` 及逐轮文件为准，不持续人工跟踪。

用户在 53 并行触发网关 HTTP 429 后，明确改为 15 并行。本次继续相同 53 条离线样本，端点 `https://ai.dijinlong.com/v1`，模型 `deepseek-flash`。Prompt、有效节点、前视 PNG、seed 2 轨迹和推理参数与上一批一致。

新主管先等待 `run_20261120_04_deepseek53` 的在途任务收尾，防止两批叠加超过 15 个请求。保留旧运行，复制已完整完成的轨迹；未完成轨迹中请求上下文、Prompt 和参数完全匹配的 HTTP 200 回答也直接复用，不重复付费请求。仅未完成部分进入最多 15 个工作进程。

针对已经发生的 HTTP 429，新增最多六次有上限的退避重试（15/30/60 秒，附少量随机延迟）。每次限流请求和响应另存 `rate_limit_attempts/`。HTTP 200 的语义判断或格式错误不重试；其余传输错误仍单独记录失败。此改动不改变偏航规则、图像采样、进度更新或首次偏航停止。

```bash
PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004_deepseek.py \
  --version v005 --api-base https://ai.dijinlong.com/v1 \
  --workers 15 --cases {1..53} --rate-limit-retries 6 \
  --resume-from outputs/deviation_progress/v005/run_20261120_04_deepseek53 \
  --output outputs/deviation_progress/v005/run_20261120_05_deepseek15
```

凭据仅通过隐藏输入和主管 stdin 传递，不落盘。运行状态与源码快照保存于输出目录；完成时同步本目录 `completion.json`。GPU 3 Qwen 保留不动。确认后台接续正常后结束人工跟踪。

12:47 UTC，后台主管 PID 4064299 已启动，状态为 `waiting_previous`。当时前一批已完成 4 条、失败 46 条、在途 3 条。旧主管终止后，新主管自动复用结果并启动最多 15 个工作进程，无需再次人工启动。凭据认证与模型目录检查已通过；接续逻辑检查包括源版本、端点、参数和 Prompt 一致性。确认后台等待状态后结束人工跟踪。启动命令与状态见 `launch.json`、`startup.json`；动态状态位于 `outputs/deviation_progress/v005/run_20261120_05_deepseek15/status.json`。
