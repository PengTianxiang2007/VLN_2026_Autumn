# DeepSeek 对照：C01–C29 偏航识别

固定 seed 2 的前 29 条轨迹，复用 Qwen 组去重后的节点、节点编号、进度锚点规则和真实终止帧。DeepSeek 独立判断语义进度，首次判出偏航即停止该轨迹。每条一个进程，固定偏航 v003 提示词、历史 deepseek-flash 参数与官方接口。[输入清单](selection.json)

运行入口为 `.runtime/crossing_vllm27/bin/python -B scripts/run_route53_deepseek_deviation29.py --prepare`、`--launch`。输入哈希、Git 版本、当前源码快照及请求参数保存在本次输出清单。每个请求与模型原答独立保存。[运行状态](../../../../outputs/deviation_progress/v003/run_20261118_03_deepseek29/status.json)

10:52 UTC 启动。29 条共有 210 个节点，其中 29 个是真实终止节点。逐条核实了与 Qwen 的节点序列相同。进程数按正式请求内的 `worker_pid` 去重统计，启动阶段核实 29 个进程均已发出正式请求。

10:59 UTC，29 个进程完成全部 29 条轨迹，99 次请求中 94 次回答有效。57 次一致、28 次偏航、9 次不确定。5 次回答的 uncertainties 字段未通过校验。28 条轨迹判出明确偏航，4 条实际评审到了终止节点，其中 3 条在终止区间判出偏航，1 条证据不足。[完成记录](completion.json) · [网页与验证](exports/web_20261118_01/README.md)
