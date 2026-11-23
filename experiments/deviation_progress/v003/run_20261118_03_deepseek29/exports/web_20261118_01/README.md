# 同轨迹 DeepSeek 与 Qwen 偏航标记

[在线回放](http://134.175.18.101/vln/qwen27b_route53_dedup_v001_web_20261118_01/index.html)于 2026-11-18 10:59:39 UTC 更新。两个开关默认关闭。DeepSeek 以紫色虚线和波形顶部紫色横线表示偏航区间，Qwen 沿用红色实线和波形底部红线。可分别或同时勾选，所有轨迹的真实终止节点始终可见。

C01–C29 中，DeepSeek 有 28 条、Qwen 有 19 条判出偏航，18 条两者均判出偏航。该计数仅指轨迹是否有明确偏航。DeepSeek 的 5 个无效回答均为 uncertainties 字段未通过冻结校验，不作为偏航判定。Qwen 与 DeepSeek 的起止帧分别取自各自的有效判定。

[两组逐条快照和文件哈希](snapshot.json) · [全 53 条双开关浏览器检查](browser_marks.json) · [公网哈希和入口备份](publication.json)

离线 HTML 为 `outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_01/index_deepseek29.html`，复用相邻的前视图片与地图。生成入口为 `scripts/export_route53_deepseek_deviation_comparison.py`。
