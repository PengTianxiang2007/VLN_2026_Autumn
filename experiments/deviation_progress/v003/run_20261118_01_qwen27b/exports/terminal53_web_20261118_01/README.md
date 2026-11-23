# 53 条回放的固定终止节点

逐条核对 `retained_nodes_and_terminals.json`、原生前视和机器人位姿。53 条轨迹各有一个固定终止节点，共 376 个保留候选加 53 个终止节点，形成 429 个有效节点。旧网页只导入了 4,837 个有 JEV 评分的动作帧。修正后可回放 4,890 个观测，最后 53 张分别来自各轨迹的 `terminal_front.png`。

地图在终止位置绘制菱形和“终点”标记，波形在相同帧绘制终点；“终止节点”按钮和双滑块均能到达该帧，当前节点面板展示评审编号。两种开关状态下终止节点都可见。终止帧不参加 JEV 评分、滤波或候选采样，早先已经明确偏航的轨迹仍按原协议停止评审。偏航结果使用已有 C01–C28 的冻结快照。

[回放入口](http://134.175.18.101/vln/qwen27b_route53_dedup_v001_web_20261118_01/index.html) · [逐轨迹浏览器核验](browser_marks.json) · [稳定网址校验](publication.json) · [离线 ZIP 记录](offline.json)

复现使用 `scripts/export_route53_deepseek_dedup.py`，搭配同组 `all53_web_20261118_01/snapshot.json` 和 `deviation28_web_20261118_01/snapshot.json`。新在线包为 `outputs/visualization_publishing/qwen27b_route53_terminal_web_20261118_01/`，离线包在本轮 `exports/terminal53_01/`。
