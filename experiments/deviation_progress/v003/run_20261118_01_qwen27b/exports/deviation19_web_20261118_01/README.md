# 53 条去重回放上的前 19 条偏航标记

[回放入口](http://134.175.18.101/vln/qwen27b_route53_dedup_v001_web_20261118_01/index.html)的“显示偏航识别”默认关闭。打开时，俯视地图沿机器人实际位置逐帧标红 A 到 B 的路径，评分波形在同一帧范围显示淡红底色和红色横线。两个图层复用 v003 历史回放的绘制函数。

范围固定为 [C01–C19 的结果快照](snapshot.json)。12 条有明确偏航，7 条没有明确偏航。只收录有效回答中判为 `deviated` 的起止帧，逐一与保留节点的帧号核对。[浏览器检查](browser_marks.json)覆盖全 53 条轨迹，验证两幅图仅在这 12 条发生变化，取消勾选后两幅图均恢复。

本地在线入口源文件为 `outputs/visualization_publishing/qwen27b_route53_dedup_v001_web_20261118_01/index_deviation19.html`，离线文件位于 `outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/all53_dedup_01/index_deviation19.html`。图片和字体沿用该版原资产。[发布记录](publication.json)登记了时间、原入口备份、新旧 SHA256 与公网验证。
