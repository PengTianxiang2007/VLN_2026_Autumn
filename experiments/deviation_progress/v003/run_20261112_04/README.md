# v003：补齐十二条轨迹

2026-11-12，已完成。仅新调用第5、6、13、15、16、20条；第4、7、11、14、17、28条直接复用run03，包括已有失败记录，不重试。

沿用v003：仅有效节点、连续编号、末尾增加终止节点；首节点单图初始化，端点＋均匀最多五张中间图。DeepSeek flash原配置，六进程、每条串行，seed未指定；首次偏航停止后续评审，未执行真实回退。提示词未改动。

合并十二条本地网页，完整中文任务指令，无去重开关。原始结果按case_number关联，复用记录内部case_index保留原值，网页索引单独维护。

启动：python -u <产物>/run/run_review.py --site <产物> --key-stdin。产物与源码快照：`C:\Users\93232\Documents\Codex\2026-11-12\c-users-93232-desktop-science-cvpr2027\outputs\jev_deviation_progress_v003_terminal_12cases_20261112_run04`；基线和文件哈希见manifest。

实际结果：{"cases": 12, "scenes": 7, "calls": 40, "valid": 33, "errors": 7, "initializations": 12, "consistent_segments": 15, "deviations": 12, "uncertain": 0, "terminal_nodes_reviewed": 4, "cached_nodes": 58, "cached_retained_nodes": 58, "unreviewed_after_stop": 18, "total_tokens": 325184, "peak_inflight_requests": 6, "worker_processes": 12, "new_calls": 17, "reused_calls": 23, "new_valid": 16, "new_errors": 1, "new_tokens": 126536, "new_worker_processes": 6, "new_cases": 6, "reused_cases": 6}。

红色区间：[{"case": 4, "nodes": "S02 → S04", "frames": [57, 99]}, {"case": 5, "nodes": "S01 → S02", "frames": [5, 10]}, {"case": 6, "nodes": "S03 → S04", "frames": [59, 70]}, {"case": 7, "nodes": "S01 → S02", "frames": [5, 80]}, {"case": 11, "nodes": "S03 → S04", "frames": [35, 44]}, {"case": 13, "nodes": "S01 → S02", "frames": [8, 23]}, {"case": 14, "nodes": "S01 → S02", "frames": [0, 9]}, {"case": 15, "nodes": "S01 → S02", "frames": [8, 33]}, {"case": 16, "nodes": "S02 → S03", "frames": [16, 21]}, {"case": 17, "nodes": "S05 → S06", "frames": [74, 100]}, {"case": 20, "nodes": "S03 → S04", "frames": [15, 20]}, {"case": 28, "nodes": "S04 → S05", "frames": [43, 63]}]。

单文件产物：`C:\Users\93232\Documents\Codex\2026-11-12\c-users-93232-desktop-science-cvpr2027\outputs\jev_deviation_progress_v003_terminal_12cases_20261112.html`。只做节点链、输入范围、完整中文及页面基本显示检查；未重跑导航，模型判定不是独立准确率。
