# v003：扩展至全部34个案例

2026-11-12，已完成。只补跑剩余22条，已完成的12条（4、5、6、7、11、13、14、15、16、17、20、28）直接复用run04，包括40次请求中的7次失败，不重试。34个案例对应33条独立轨迹、9场景；32和33为同一轨迹的两个事件。

沿用v003：有效节点连续编号、追加终止节点、首节点单图初始化、端点＋均匀最多5张中间图。DeepSeek flash、thinking enabled/high、JSON、max_tokens32768、六进程、每条串行，seed未指定。首次偏航后停止评审，没有真实回退或新导航。提示词与配置不变。

本地网页完整中文任务指令、无去重开关，新增与复用来源分别标明。原始结果按case_number关联，旧case_index作为来源保留。

启动：python -u <产物>/run/run_review.py --site <产物> --key-stdin。产物及源码快照：`C:\Users\93232\Documents\Codex\2026-11-12\c-users-93232-desktop-science-cvpr2027\outputs\jev_deviation_progress_v003_terminal_34cases_20261112_run05`；基线、源码及复用文件哈希见manifest。

实际结果：{"cases": 34, "scenes": 9, "calls": 114, "valid": 106, "errors": 8, "initializations": 34, "consistent_segments": 40, "deviations": 33, "uncertain": 5, "terminal_nodes_reviewed": 7, "cached_nodes": 199, "cached_retained_nodes": 199, "unreviewed_after_stop": 85, "total_tokens": 946049, "peak_inflight_requests": 6, "worker_processes": 18, "new_calls": 74, "reused_calls": 40, "new_valid": 73, "new_errors": 1, "new_tokens": 620865, "new_worker_processes": 6, "new_cases": 22, "reused_cases": 12}。

红色区间：[{"case": 1, "nodes": "S01 → S02", "frames": [5, 38]}, {"case": 2, "nodes": "S04 → S05", "frames": [25, 35]}, {"case": 3, "nodes": "S01 → S03", "frames": [0, 36]}, {"case": 4, "nodes": "S02 → S04", "frames": [57, 99]}, {"case": 5, "nodes": "S01 → S02", "frames": [5, 10]}, {"case": 6, "nodes": "S03 → S04", "frames": [59, 70]}, {"case": 7, "nodes": "S01 → S02", "frames": [5, 80]}, {"case": 8, "nodes": "S02 → S03", "frames": [13, 26]}, {"case": 9, "nodes": "S01 → S02", "frames": [5, 10]}, {"case": 10, "nodes": "S02 → S03", "frames": [17, 36]}, {"case": 11, "nodes": "S03 → S04", "frames": [35, 44]}, {"case": 13, "nodes": "S01 → S02", "frames": [8, 23]}, {"case": 14, "nodes": "S01 → S02", "frames": [0, 9]}, {"case": 15, "nodes": "S01 → S02", "frames": [8, 33]}, {"case": 16, "nodes": "S02 → S03", "frames": [16, 21]}, {"case": 17, "nodes": "S05 → S06", "frames": [74, 100]}, {"case": 18, "nodes": "S02 → S03", "frames": [19, 46]}, {"case": 19, "nodes": "S09 → S10", "frames": [127, 132]}, {"case": 20, "nodes": "S03 → S04", "frames": [15, 20]}, {"case": 21, "nodes": "S01 → S02", "frames": [0, 14]}, {"case": 22, "nodes": "S01 → S02", "frames": [0, 17]}, {"case": 23, "nodes": "S01 → S02", "frames": [32, 49]}, {"case": 24, "nodes": "S03 → S04", "frames": [58, 102]}, {"case": 25, "nodes": "S03 → S04", "frames": [39, 66]}, {"case": 26, "nodes": "S01 → S02", "frames": [0, 5]}, {"case": 27, "nodes": "S02 → S04", "frames": [48, 71]}, {"case": 28, "nodes": "S04 → S05", "frames": [43, 63]}, {"case": 29, "nodes": "S01 → S02", "frames": [0, 41]}, {"case": 30, "nodes": "S02 → S03", "frames": [40, 45]}, {"case": 31, "nodes": "S02 → S03", "frames": [13, 23]}, {"case": 32, "nodes": "S03 → S04", "frames": [44, 98]}, {"case": 33, "nodes": "S04 → S06", "frames": [44, 102]}, {"case": 34, "nodes": "S01 → S02", "frames": [5, 15]}]。

单文件产物：`C:\Users\93232\Documents\Codex\2026-11-12\c-users-93232-desktop-science-cvpr2027\outputs\jev_deviation_progress_v003_terminal_34cases_20261112.html`。只做节点链、输入范围、完整中文及页面基本显示检查；未重跑导航，模型判定不是独立准确率。

## GitHub 冻结与接手

2026-11-12 将当前原始方法、网页源码、全部逐请求记录与结果归档到 [snapshot/](snapshot/)，图片继续复用已有 ZIP。
方法、实际中英文 prompt、输入输出、六进程与停止策略、no31 已知误报以及本地恢复命令，见 [方法与接手说明](../../../../docs/DEVIATION_PROGRESS_V003.md)。
原始文件逐字节哈希见 [snapshot_manifest.json](snapshot_manifest.json)。本次没有重跑模型或修改判定。


## 2026-11-17 网页发布

用户已明确要求发布此前仅本地展示的 34 案例页面。本次已完成：[在线查看](http://134.175.18.101/vln/jev_deviation_progress_v003_34cases_web_20261117_01/index.html)；[导出与验证记录](exports/web_20261117_01/README.md)。恢复原资源并补齐字体缺字，全部原始判断不变；3288 文件远端哈希及公网 HTTP 200 通过，无新模型或导航。历史本地限定由本次针对该页面的发布授权更新。
