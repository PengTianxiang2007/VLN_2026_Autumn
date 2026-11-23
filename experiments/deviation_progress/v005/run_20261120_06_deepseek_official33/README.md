# v005 DeepSeek 官方接口接续剩余 33 条

2026-11-20 13:48 UTC，[四版本对比可视化](exports/four_versions_20261120_01/README.md)已发布到[原网址](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)，本组 219 轮原答、实际输入清单、累计进度和格式错误原答均保留；支持与 Qwen v003、DeepSeek v003、Qwen v005 勾选比较，最多同时三组。

最终状态：2026-11-20 13:24:49 UTC 全部完成，`phase=complete`，53/53 条、0 条接口失败。汇总包含复用的 20 条和官方接续完成的 33 条，共 219 轮：161 次 consistent、47 次 deviated、11 次格式错误。47 条轨迹触发有效偏航报警，6 条未触发；这不是准确率统计。格式错误的原答均保留且未作为有效判定提交，不额外重跑这些回答。用户要求跟踪至完成，最后的 C45 已结束，跟踪程序随之退出。最终状态见 `completion.json` 和输出 `status.json`，逐条统计见输出 `v005_results.json`。GPU 3 Qwen 继续按用户要求保留。

用户于 2026-11-20 明确要求改用 DeepSeek 官方 URL 和新凭据，将剩余样本全部并行跑完。本次新请求使用 `https://api.deepseek.com`，模型沿用 `deepseek-flash`，33 个工作进程同时处理未完成 case。复用 `run_20261120_05_deepseek15` 已完成的 20 条以及未完成轨迹中上下文、参数、Prompt 完全匹配的已返回 HTTP 200 回答，不重复请求已有结果。

方法、样本和状态协议保持 v005：C01–C53、seed 2 冻结离线轨迹、去重后有效节点及终止节点、原生前视 PNG、A/B 端点加最多五张中间帧、双分类、Completed/Current/Pending 进度、首次有效偏航停止。DeepSeek 参数为 thinking enabled、reasoning_effort high、max_tokens 32768、JSON object、非流式；未指定模型推理 seed。每条内部串行，33 条之间并行。保留已有最多六次 HTTP 429 有限退避机制。

本次由用户明确授权跨端点接续，因此显式使用 `--allow-endpoint-change`。运行清单记录旧、新端点；复用整条记录 `reuse_source.json`，接续轮次记录 `Sxx.provenance.json`。原答不改写。最终汇总包含网关历史回答和官方新回答，不能描述为全部从官方接口重新生成。

```bash
PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004_deepseek.py \
  --version v005 --api-base https://api.deepseek.com \
  --workers 33 --cases {1..53} --rate-limit-retries 6 \
  --resume-from outputs/deviation_progress/v005/run_20261120_05_deepseek15 \
  --allow-endpoint-change \
  --output outputs/deviation_progress/v005/run_20261120_06_deepseek_official33
```

凭据只经隐藏终端和主管 stdin 传递，不保存到命令、代码、日志或运行清单。实际代码、Prompt、参数、Git 提交与哈希由入口冻结。输出 `status.json` 为动态状态，逐轮请求和原答位于 `run/cases/Cxx/`；主管退出后同步本目录 `completion.json`。GPU 3 Qwen 按用户要求保留不动。

状态：已在后台进入 `reviewing`，主管 PID 4097663。启动核对时 33 个工作进程存活且全部发出真实请求；官方接口已有 6 份新回答返回 HTTP 200 并通过 v005 校验，尚无失败轨迹。已复用 20 条完整结果，剩余 33 条接续中。凭据认证和模型目录检查已通过。启动证据见 `startup.json`、完整命令见 `launch.json`。按用户要求确认启动后交后台，不持续人工跟踪到完成。
