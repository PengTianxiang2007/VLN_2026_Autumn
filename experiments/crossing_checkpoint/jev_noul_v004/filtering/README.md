# v004 回退概率滤波可视化

状态：完成并发布；未调用任何模型。2026-11-09用户指定本版的
**v004 prompt + Streaming Prominence** 组合为当前最好 JEV 流水线。

功能仅用于现有 v004 与最初 Qwen4B 对照网页的折线图：

- Gaussian：居中高斯核，`σ=N/6`，半径为 `ceil(3σ)`；
- EMA：因果指数移动平均，`α=2/(N+1)`；
- Moving Average：居中 `N` 帧算术平均；
- Relative Prominence：`max(0, Gaussian(N)-baseline(2N+1))`，再按该轨迹P95归一化；
- Streaming Prominence：输出`i`只使用过去数据与最多`D≤5`个未来观测，宽基线
  和P95只使用截至当前已可获得的历史；达到`i+D`后输出冻结；
- Qwen原始曲线和JEV原始曲线均默认显示，也可独立取消勾选；
- 所有滤波/增强共用滑动参数 `N=3..31`，默认7；流式突出度另有最大延迟
  `D=0..5`，部署默认`D=5`；
- 可同时勾选，叠加在JEV 0–1概率轴上；
- 滤波不改变地图路线、原始JEV概率、Qwen分数或当前值卡片。

部署默认是 Streaming Prominence（`N=7,D=5`）；其余居中滤波和离线突出度保留为
对照。该结果是用户指定的最优组合，不构成独立准确率结论，也不直接作为存档确认规则。

在线版：

http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_nodes_20261109_04/jev_noul_v004_vs_qwen4b.html

- 本地HTML：`outputs/crossing_checkpoint/jev_noul_v004/combined12_qwen/export_20261109_04/jev_noul_v004_vs_qwen4b.html`
- SHA256：`779b6772346d34b8640acfe0c5eddac0d96b8956426548bd71dced12757b10d5`
- 发布记录：`outputs/visualization_publishing/publish_20261109_010450_711851/publication.json`
- 本地浏览器证据：`.../export_20261109_04/browser_verification.json`
- 在线浏览器证据：`outputs/visualization_publishing/online_check_jev_noul_v004_first_20261109_04/browser_verification.json`

验证：三项离线滤波、离线突出度、流式突出度、原始两线切换、窗口N与延迟D滑条、
前缀稳定性、只改折线不改地图、12条轨迹/1050结果、中英切换、复核导出和移动端
均通过；页面错误0、请求失败0。
