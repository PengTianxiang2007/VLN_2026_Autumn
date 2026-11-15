# v004 与最初 Qwen4B 的 12 条轨迹对照

状态：完成并发布。

合并当前最好JEV v004已完成的全部12条轨迹：首轮2条加新增10条；5条原导航失败、
7条成功。共1050个有效观测、1062个回放帧。

对照：

- Qwen4B：最初 `best_v001` 三帧1–5分结果，复用既有同帧输出；
- JEV：当前最好v004，单Noul P(回退点候选)；
- Qwen平均分1.891；JEV平均概率0.486；
- 两者量纲不同，仅作描述性同帧对照，不计算准确率或优劣。

网页：

http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_20261108_01/jev_noul_v004_vs_qwen4b.html

- 本地HTML：`outputs/crossing_checkpoint/jev_noul_v004/combined12_qwen/export_20261108_01/jev_noul_v004_vs_qwen4b.html`
- SHA256：`288a6e2e697308b534c6cf9ac37cff96188950d3921d08aa70f610e013663762`
- 发布记录：`outputs/visualization_publishing/publish_20261108_154815_614997/publication.json`
- 在线浏览器证据：`outputs/visualization_publishing/online_check_jev_noul_v004_vs_qwen4b_20261108_01/browser_verification.json`

地图使用同一Qwen轨迹。Qwen按1–5分浅绿到深绿染色，JEV按0–1概率浅橙到深红
染色；仅保留两条路线和当前机器人位置，没有人工点、高分方块或其他路点。

## 滤波版本

折线图现支持Gaussian、EMA、Moving Average、离线Relative Prominence和
Streaming Prominence五种可叠加增强，统一`N=3..31`窗口及`D=0..5`最大延迟。
原始Qwen和JEV曲线也可独立勾选。流式突出度在`i+D`后冻结，后续数据不改写历史。
滤波只影响折线图，不改地图和原始分数。在线入口：
http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_nodes_20261109_04/jev_noul_v004_vs_qwen4b.html 。

勾选流式突出度后，折线图横轴会标出核心采样节点：高点0.6/低峰0.18、
相对峰谷差0.03、局部峰最小间距3帧、最短3帧平台中心起每5帧采样。另有地图勾选项，
可在Qwen/JEV两张俯视图同步显示相同S编号节点。
