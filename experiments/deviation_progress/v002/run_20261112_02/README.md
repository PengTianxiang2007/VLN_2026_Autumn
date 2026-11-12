# 六场景有效节点联合评审 v002

2026-11-12，已完成。同第4、7、11、14、17、28条；只保留既有去重结果的20个节点，各条重新连续编号。被删除的节点、旧判断和旧语义进度均不参与此次请求。

DeepSeek flash，六独立进程、每条串行，原配置 thinking enabled/high、JSON、max_tokens32768，seed未指定。首个保留节点用单图初始化，之后端点两图＋均匀最多五张中间图；不输入地图/坐标/结果标签。进度为自然语言；uncertain或错误冻结可信锚点；首次偏航后停止该条评审并记录回退目标，未执行真实回退。

网页按原模板本地导出，默认中文完整任务指令，无去重开关、被删节点或旧编号。启动命令：python -u <产物>/run/run_review.py --site <产物> --key-stdin。

源码、prompt及配置冻结在 C:\Users\93232\Documents\Codex\2026-11-12\c-users-93232-desktop-science-cvpr2027\outputs\jev_deviation_progress_v002_20261112_run02\run。保留实际基线提交及原源码哈希，新脚本属于本轮工作区。旧v001含已删除节点，不能作为新版结果。

实际结果：{"cases": 6, "scenes": 6, "calls": 19, "valid": 18, "errors": 1, "initializations": 6, "consistent_segments": 10, "deviations": 2, "uncertain": 0, "cached_nodes": 20, "cached_retained_nodes": 20, "unreviewed_after_stop": 1, "total_tokens": 175818, "peak_inflight_requests": 6, "worker_processes": 6}。

红色区间：[{"case": 7, "nodes": "S01 → S02", "frames": [5, 80]}, {"case": 14, "nodes": "S01 → S02", "frames": [0, 9]}]。

单文件产物：`C:\Users\93232\Documents\Codex\2026-11-12\c-users-93232-desktop-science-cvpr2027\outputs\jev_deviation_progress_v002_6cases_20261112.html`。只做节点链、输入范围、完整中文及页面基本显示检查；未重跑导航，模型判定不是独立准确率。
