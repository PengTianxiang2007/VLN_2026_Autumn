# v004 流式突出度核心采样点

状态：完成并发布；未调用大模型。

仅当页面勾选“流式突出度（≤5步）”时，在折线图横轴底部绘制采样节点：

- 输入为当前 Streaming Prominence 曲线；
- 高点阈值 `0.6`；
- 低矮局部峰阈值 `0.18`，峰谷差至少 `0.03`；
- 局部峰要求至少3帧间隔；
- 连续平台阈值 `0.45`，最少3帧，首个采样点位于平台中心附近，之后每5帧采样；
- 峰和海平台候选合并后仍保证至少3帧间隔；
- 标记包含竖虚线、横轴圆点及 `S01/S02...` 编号；
- 下方文字列出对应原始 frame；
- 默认不改变地图；勾选“在地图上显示采样点”后，会在Qwen/JEV两张俯视图上同步
  画出同样的S编号点；
- 不改变曲线或原始判断结果。

短平台不会再漏掉开头首峰。`kujiale_0113_1_4` 在N=7/D=5下为
F4/F21/F45/F50；`kujiale_0207_41_0` 在N=5/D=5下为
F3/F14/F20/F25/F49。算法在12条轨迹上合计得到约67个候选。

在线页面：

http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_nodes_20261109_04/jev_noul_v004_vs_qwen4b.html

- 本地HTML：`outputs/crossing_checkpoint/jev_noul_v004/combined12_qwen/export_20261109_04/jev_noul_v004_vs_qwen4b.html`
- SHA256：`779b6772346d34b8640acfe0c5eddac0d96b8956426548bd71dced12757b10d5`
- 发布记录：`outputs/visualization_publishing/publish_20261109_010450_711851/publication.json`
- 在线浏览器证据：`outputs/visualization_publishing/online_check_jev_noul_v004_first_20261109_04/browser_verification.json`

限制：这些是候选调用点，尚未经过大模型确认，也不代表真实 Crossing 金标准。
