# lite_v002：20条三帧评分对比最优版本1

状态：待后台准备并启动。用户授权20条，完成后Qwen4B翻译、双语对比可视化、检查和发布，部署后不持续人工跟踪。
目的：当前/最多8步的局部选择；允许有具体局部视觉依据推断部分遮挡的可进入支路；合理推断可得4分，5分要求清晰证据；明确以最后一帧为当前视角。
提示词：prompt_en.txt是实际请求原文，prompt_zh.txt在后处理由Qwen4B生成，仅展示用。
样本：人工集内10失败+10成功，seed20261107，沿用按场景轮转抽样；若未选中kujiale_0113_66_1，将同组最后一条替换为它。该例是用户指出的开发样本，结果不当作独立泛化成绩。最终清单见selection.json。
模型：复用GPU0 Qwen3.5-4B BF16用户保留服务qwen35-4b-standby；服务seed20261108，逐请求seed按旧版episode/frame和20261107派生。4请求worker；服务max_num_seqs1。
输入：t-2,t-1,t原RGB，开头不足3帧只用已有帧；不含指令/地图/标签/旧回答。temperature0、max_tokens256、thinking关闭、结构化1–5分及中文理由。任务末尾复用帧不推理。
对照：复用最优版本1在同20条的评分，不重算；准备阶段核验逐请求RGB清单相同并冻结旧响应摘要、哈希、提示词、译文。新旧同帧切换、分数/理由并排、两条评分曲线，路径按所选版本染色，机器人红点随双时间轴移动；失败任务可切换参考路径。未标帧不是负类；仅报告分数变化，不宣称准确率提高。
翻译：新版本全部展示翻译由本地Qwen4B完成，4个并发请求；批量校验失败自动拆单，保存原始响应及错误。最优版本1已有译文复用。
流程：prepare（数据和对照审计、源码快照）→评分→Qwen4B翻译→同帧对比导出→浏览器检查（包括机器人点）→标准发布→delivery.json及文档自动更新。失败记录状态及日志。保留用户授权待命服务，清理本批worker。
启动：python3 -B scripts/run_crossing_lite_v002.py --output outputs/crossing_checkpoint/lite_v002/run_20261108_01 --prepare experiments/crossing_checkpoint/lite_v002/run_20261108_01；成功后去掉--prepare参数执行。
实际Git和未提交修改：运行目录manifest.json、source/、workspace_status.txt、tracked_worktree.diff。旧最优版本1不覆盖，新版本尚未被标记最优。
产物：outputs/crossing_checkpoint/lite_v002/run_20261108_01；status.json与postprocess_status.json记录阶段；delivery.json保存验证后的网址。

2026-11-08T09:34:56.502540+00:00 v002_20后台流程状态：{"phase": "complete", "pid": 57834, "started_at": "2026-11-08T08:40:54.323042+00:00", "expected_calls": 1824, "updated_at": "2026-11-08T09:34:56.297353+00:00", "service": "http://127.0.0.1:58317/v1", "service_reused": true, "server_max_num_seqs": 1, "finished_at": "2026-11-08T09:34:56.297326+00:00", "url": "http://134.175.18.101/vln/crossing_lite_v002_20_compare_best1_run_20261108_01_web_01/crossing_lite_review.html", "html": "/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/lite_v002/run_20261108_01/exports/final/crossing_lite_review.html", "html_sha256": "02612d5aeca697dcab73fcdc8a813a0564823e57cb15a6c155bf934cfde20c7d", "summary": {"episodes": 20, "groups": {"failure": 10, "success": 10}, "expected_calls": 1824, "attempted_calls": 1824, "responses": 1824, "valid_calls": 1824, "invalid_or_missing": 0, "audited_requests": 1824, "score_histogram": {"1": 1406, "4": 194, "5": 224}, "replay_frames": 1844, "annotation_points": 47, "mean_latency_seconds": 3.183620818345317, "evaluation": "Raw score distribution and exact annotated-point scores only. No unlabeled-frame negatives or PR/F1.", "created_at": "2026-11-08T09:32:59.733707+00:00"}, "comparison": {"episodes": 20, "paired_frames": 1824, "changed": 281, "increased": 38, "decreased": 243, "baseline_histogram": {"1": 1367, "5": 456, "4": 1}, "new_histogram": {"1": 1406, "4": 194, "5": 224}, "diagnostic": [{"episode_id": "kujiale_0113_66_1", "frame": 84, "new": 1, "baseline": 1}], "interpretation": "Score changes only, not accuracy gains; user-selected diagnostic is development data."}, "publication_records": ["/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/visualization_publishing/publish_20261108_093423_410947/publication.json"], "published_at": "2026-11-08T09:34:56.081204+00:00"}
