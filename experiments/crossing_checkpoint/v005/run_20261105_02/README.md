# 第四稿 Qwen3.5-4B 三条并发离线测评

更新时间：2026-11-05T11:17:44.435903+00:00。状态：已准备。

目的：用户要求同时用Qwen4B跑3个case，允许多进程。使用与当前智谱批次相同第四稿宽松prompt；原Qwen三条0036_10_0、0113_1_4、0208_21_4，共168次逐步调用。不会停止智谱云API批次。

设置：本地已有Qwen3.5-4B BF16权重；GPU0单个vLLM服务，3个独立episode进程共享，max_num_seqs=3、显存比例0.50、32K上下文、输出8192，关闭思考（沿用本地Qwen既有设置）。8图/32动作、存档确认和1m匹配不变。导航seed2、逐请求seed算法不变；并发和模型变化不承诺旧版逐token等价。

启动前双次空卡检查及进程归属检查，仅GPU0；其他GPU任务不动。复用.runtime/crossing_vllm27环境（vLLM0.19.1支持Qwen3_5），权重离线加载，无需下载或仿真。模型config、现有下载manifest哈希和shard存在性已核验。

Git：0a805dfcf4457f80300822abb4eff7cabba43aae，工作区未提交差异已保存；versions/冻结同一第四稿core与原replay，orchestration_source保存主管、清理、导出及模板源码。没有修改共享检测器或正在运行的智谱脚本。

命令：`benchmarks/vlnverse/.venv/bin/python -B scripts/run_crossing_local_batch.py --output outputs/crossing_checkpoint/v005/run_20261105_02`。

退出：模型启动最多2700秒，回放最多8小时，每请求600秒、最多一次重试；固定这一批，不自动调参。完成、异常、取消均清理本次独立session且核验PID启动时间，仅本项目子进程；评分后先释放GPU再用CPU分析及默认双进度条模板导出。保留失败日志，不覆盖历史输出。

产物：outputs/crossing_checkpoint/v005/run_20261105_02；status.json、service_01/server.log、runs/qwen35_4b_draft04_dev3/、cleanup.json，HTML exports/final/visualization/crossing_review_offline.html。当前无成绩；三条为既有开发样本，不是独立盲测。确认有效并行请求后停止人工持续监控。

Qwen4B启动记录：{"run": "v005/run_20261105_02", "phase": "loading", "supervisor_pid": 1391704, "server_pid": 1391810, "gpu": 0, "concurrency": 3}。模型加载中，尚未确认有效回答。

Qwen4B run_20261105_02启动验证通过：3个独立episode进程并发，已核验23次有效回答及因果前缀，第四稿prompt一致、关闭思考；服务日志确认同时3请求。停止人工持续跟踪，后台完成后自动评分、释放GPU和导出模板HTML。

Qwen4B三条最终状态：{"phase": "complete", "tag": "qwen35_4b_draft04_dev3", "started_at": "2026-11-05T11:18:08.102884+00:00", "supervisor_pid": 1391704, "gpu": 0, "updated_at": "2026-11-05T11:33:47.236689+00:00", "server_pid": 1391810, "base_url": "http://127.0.0.1:38239/v1", "replay_pid": 1406833, "expected_calls": 168, "concurrency": 3, "gpu_released": true, "error": null, "finished_at": "2026-11-05T11:33:47.236662+00:00"}
