# 50 例原生仿真与 Codex 旁路评审

从完整 fine val_unseen 的 825 条中均匀无放回抽取 50 条；抽样 seed 20261125，导航 seed 2。每例原生 StreamVLN / H1 physical 仿真，JEV v004 评分进入 v002 active 采样，Codex v006.1 筛选、同会话 v002 偏航评审、最大帧距 6。每例首次报警记录目标，仿真持续至原生停止。

[冻结清单](manifest.json)。启动命令、Git 提交和 PID 见输出 launch.json，源代码快照在 source/，仿真与远端评审分别计时。

## 运行与计时

原版模型与仿真均使用已协调的 GPU 3。旁路启动入口为 `scripts/run_codex_shadow.py`，两个独立进程分别使用 `score` 和 `review` 模式。只有 score 从私有标准输入读取本轮 JEV 凭据，Codex 使用 17982 和 Astra 常规档。两者在启动真实 episode 时开始消费观测。

每个 attempt 的 navigation.json 记录仿真起止、实际墙钟时间和采集耗时；仿真无需等待远端评审，等待计为 0。score.json 记录 JEV 逐请求累计时间；review.json 分开记录建点、偏航评审耗时、首次报警时刻和目标。整批两个 summary 均相对 launch.json 的启动时间计时，取两者中较晚的完成时刻。分项并行耗时不能直接相加。

首次模型冷启动达到原生默认 900 秒上限，当时尚无 episode 成绩。本次按相同 run ID、清单及协议续启，模型加载时限为 3600 秒。startup_attempt_01/ 保留首次日志，整批墙钟从第一次启动计。

2026-11-25T20:50:28.361936+00:00 已按用户要求停止。首例完成原生仿真，JEV 在 F45 返回 HTTP 520，Codex 已完成初始化及 S01、S02 候选评审，整例偏航评审未完成。 本批 GPU 进程已退出。当前版 SR 0/1（0%），平均 SPL 0；配对原版暂无，已评分 0 条。[停止记录](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_10_live50/restarts/retry_20261125T205429Z/cancellation.json)。

## 从首例评分断点恢复

2026-11-25T20:54:29.566945+00:00 已恢复同一清单，GPU 3 原生导航从 1/50 起续走。首例沿用原始 259 帧、已完成的 JEV 请求、F45 单次重试结果和已有三个成功的 Codex 轮次。在该批实时旁路中，远端调用失败以 2、4、8、16、32、60 秒逐步退避，之后每次等待 60 秒，直到同一请求取得有效回答。JEV 按帧顺序采样，Codex 在原会话内重试当前轮，包括返回格式无效的情况；每次失败和等待时间分别保存在对应帧或会话的 retries.jsonl。采样器与偏航 prompt 沿用本批既有版本。

[恢复记录](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_10_live50/restarts/retry_20261125T205429Z/restart.json)。

2026-11-26T03:03:01.318204+00:00 用户要求停止进程。仿真 50/50 已评分，JEV 进程已退出，剩余 Codex 评审及重试已停止。本批无存活进程。
