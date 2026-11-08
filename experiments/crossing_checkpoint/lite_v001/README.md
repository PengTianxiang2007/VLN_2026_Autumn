# lite_v001：三帧局部多选择评分

当前批次：[10失败＋20成功](run_20261107_01/README.md)。Qwen3.5-4B，掉头算分支，1–5分，与历史8帧存档检测独立。

2026-11-07：三帧评分后台主管1292524、vLLM API1292779已启动加载，端口60859；冻结30条/2559次调用。6项CPU协议测试通过，独立无预测预览30条/2589帧/156关键位置浏览器检查通过（双滑条、复核导出、移动端、零外部请求/JS错误），不计作模型结果。

2026-11-07T03:34:36.957330+00:00 启动核验通过：GPU0 Qwen3.5-4B vLLM、4独立episode进程；前12份真实响应及三帧输入/请求哈希/1–5评分通过，4请求时间区间并发已确认。此刻有效回答12/2559。停止人工持续跟踪；后台自动完成、导出双进度条HTML及请求/浏览器审计，释放本轮服务。

2026-11-07T03:41:01.901924+00:00：按用户要求更新三帧评分HTML俯视轨迹配色，1–5分浅绿到深绿；t→t+1线段使用起点t的有效原始评分，无评分灰色虚线，原地转向同色点，并加入图例。仅修改core/crossing_lite_review.js；原启动manifest/source快照保留，导出修订与授权哈希见outputs/crossing_checkpoint/lite_v001/run_20261107_01/export_revisions/score_route_colors_20261107_01/。推理源码、prompt、任务与原答未改，不查询/跟踪运行进度。独立CPU预览30条/2589帧/156位置及五档明度、实际Canvas线段颜色、起点评分对应、回放前缀和灰色缺失检查通过；合成配色测试不计模型结果。本轮自动导出会应用此修订。

2026-11-07T03:54:38.445077+00:00：三帧Crossing五级评分 outputs/crossing_checkpoint/lite_v001/run_20261107_01 自动收尾：{"phase": "complete", "supervisor_pid": 1292524, "started_at": "2026-11-07T03:27:26.666080+00:00", "gpu": 0, "concurrency": 4, "expected_calls": 2559, "updated_at": "2026-11-07T03:54:38.399180+00:00", "base_url": "http://127.0.0.1:60859/v1", "server_pid": 1292779, "worker_pids": [1300869, 1300871, 1300874, 1300875], "inference_error": null, "gpu_released": true, "finished_at": "2026-11-07T03:54:38.399149+00:00", "error": null, "summary": {"episodes": 30, "groups": {"failure": 10, "success": 20}, "expected_calls": 2559, "attempted_calls": 2559, "responses": 2559, "valid_calls": 2559, "invalid_or_missing": 0, "audited_requests": 2559, "score_histogram": {"1": 1911, "4": 2, "5": 646}, "replay_frames": 2589, "annotation_points": 70, "mean_latency_seconds": 1.2661769690414968, "evaluation": "Raw score distribution and exact annotated-point scores only. No unlabeled-frame negatives or PR/F1.", "created_at": "2026-11-07T03:54:30.690423+00:00"}, "html": "/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/lite_v001/run_20261107_01/exports/final/crossing_lite_review.html"}。未标帧不视为负类，语义准确性待复核。
