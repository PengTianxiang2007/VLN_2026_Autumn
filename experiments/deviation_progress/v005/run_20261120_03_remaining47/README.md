# v005 剩余 47 条离线评审

状态：已完成。结束时间 2026-11-20 11:53:28 UTC，补跑耗时约 3 小时 28 分钟。47 条新增结果共 239 轮（204 次 consistent、35 次 deviated）；复用六条后合计 53 条、272 轮（232 次 consistent、40 次 deviated），40 条轨迹报警、13 条未报警、0 次格式错误。统计来自两次运行的 `v005_results.json`，仅描述模型判定，不代表正确性评估。GPU 3 模型按用户要求保留。12:20 UTC，[完整 53 条回放及下载包](exports/web_all53_20261120_01/README.md)已发布，补齐阶段版之外的五条。

2026-11-20 UTC。用户决定只补跑 v005，复用已完成的 C07、C11、C19、C30、C47、C50，补齐 C01–C53 中其余 47 条。使用 GPU 3 常驻 Qwen27B、同一份 v005 Prompt、冻结有效节点、seed 2 轨迹及原请求参数。47 条共 390 个有效节点，每条在首次有效偏航或终止节点结束。预计约 4.7 小时，实际耗时随报警早晚和回答长度变化。

复用六条来自 `outputs/deviation_progress/v005/run_20261120_02_qwen_gpu3`。本次新结果写入 `outputs/deviation_progress/v005/run_20261120_03_remaining47`，每轮输入、原答与累计进度存入 `run/cases/`。完整 53 条的数据来源见 `case_sources.json`。模型按用户要求持续保留。

启动命令与后台 PID 见本目录 `launch.json`。本次评审直接复用原入口，历史回答回放仅在显式 `--check-only` 时执行。实际代码、Prompt 和参数由入口写入运行目录的 `source/` 和 `manifest.json`。

[运行状态](../../../../outputs/deviation_progress/v005/run_20261120_03_remaining47/status.json) · [已完成六条](../run_20261120_02_qwen_gpu3/README.md)

08:25:39 UTC，后台 PID 3851381 已进入 C01 的 S01，首个请求输入单帧 F0。确认启动后按用户要求结束人工跟踪，任务继续后台执行。

11:46 UTC，评审仍在后台运行期间，将当时已完成的 48 条、250 轮结果发布为[阶段回放](exports/web_partial_20261120_02/README.md)，其中包含复用的六条。阶段快照没有纳入尚未完成的评审。
