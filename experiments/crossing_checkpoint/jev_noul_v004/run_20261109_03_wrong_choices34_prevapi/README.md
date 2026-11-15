# 人工错误选择 34 点：JEV v004 与 Qwen4B 对照

状态：已完成并发布；34/34 有效，三栏中英文可视化通过本地浏览器检查，
在线入口远端 SHA256 与 HTTP 200 检查通过。

## 结论

只对 `seed2_human_v001` 人工标记的 34 个 `wrong_choice` 运行当前最佳
`jev_noul_v004`：

- 34/34 有效，失败 0。
- 29 个本次新调用，5 个通过完整请求 SHA256 与既有 v004 结果精确复用。
- 用户指定并发上限 500；缺失任务一次性全部提交，实际最多 29 个 worker。
- JEV yes 概率均值：0.762。
- JEV ≥ 0.75：19/34。
- JEV < 0.60：4/34；最低为 0.52，没有低于 0.50 的点。
- 同点最初 Qwen4B 分数均值：3.353；分布为 1 分 14 个、5 分 20 个。

这些点均已经是人工确认的错误分支选择，不代表 JEV 分数越高越“正确”。本批只能说明：
JEV v004 把其中大多数位置判断为潜在回退点候选；Qwen4B 在同点呈两极分布。两者量纲
不同，不计算直接相减、准确率、优劣或因果结论。

## 协议

- 数据：`outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001`
- 事件：34 个错误选择点、33 条 episode；`kujiale_0257_82_4` 有 F12/F37 两点。
- Qwen 对照：`outputs/crossing_checkpoint/lite_full_v001/run_20261108_01/annotated_point_scores.json`
- JEV：`jev-1.14.0`，`jev_noul_v004`，单个 `fallback_point` Noul。
- 输入：严格 `t-2,t-1,t` RGB；不输入任务、动作、位置、地图、错误标签、
  成败、参考路线或旧回答。
- 端点：`https://api.site/v1/systemone`（按用户指令切回之前的可用端点）。
- 最大尝试：5；34 个有效结果中 33 个首次成功，1 个第二次尝试成功。
- 凭据：无回显 stdin 进入进程内存，未落盘。

运行目录：
`outputs/crossing_checkpoint/jev_noul_v004/run_20261109_03_wrong_choices34_prevapi`

正式输出：

- `rows.json`：34 条逐点结果。
- `summary.json`：有效数、来源、均值、分布与传输尝试。
- `manifest.json`：协议、端点、并发、数据与 Qwen 来源哈希。
- `reuse_audit.json`：5 个精确复用来源。
- `events/<event_id>/`：请求审计、图片审计、完整请求、原始响应或复用来源。

## 代码

- Runner：
  [`scripts/run_jev_noul_v004_wrong_choices34_concurrent.py`](../../../../../scripts/run_jev_noul_v004_wrong_choices34_concurrent.py)
- 最终 Exporter：
  [`scripts/export_jev_noul_v004_wrong_choices34_template.py`](../../../../../scripts/export_jev_noul_v004_wrong_choices34_template.py)
- 复用的统一 HTML 模板：
  [`scripts/export_jev_noul_compare.py`](../../../../../scripts/export_jev_noul_compare.py)
- 复用的统一前端：
  [`core/jev_noul_compare_review.js`](../../../../../core/jev_noul_compare_review.js)
- 最终浏览器检查：
  [`scripts/check_jev_noul_v004_wrong_choices34_template.cjs`](../../../../../scripts/check_jev_noul_v004_wrong_choices34_template.cjs)

## 可视化检查

最新本地导出：
`outputs/crossing_checkpoint/jev_noul_v004/run_20261109_03_wrong_choices34_prevapi/exports/run_20261109_05_fullwave_template/jev_noul_v004_vs_qwen4b.html`

- 离线 HTML SHA256：
  `6eaad350cf8132ab2a93cfe7922e20863cba569158684b8bed0c8a15b235485a`。
- 直接复用用户指定的 `jev_noul_v004_vs_qwen4b_12cases_nodes_20261109_04`
  对应页面与前端，只替换数据为 34 个错误选择点。
- 34 个 case、3,161 个回放帧、case-level 3,127 个 Qwen 分数和 JEV 概率。
- 为形成真正的 JEV 概率波形，另行完成 33 条轨迹的全逐帧补跑：3,006 个唯一帧，
  2,601 新调用、405 精确复用、0 失败。见
  [`run_20261109_04_fullwave_prevapi`](../../run_20261109_04_fullwave_prevapi/README.md)。
- 每个 case 默认定位到对应错误帧；保留双地图、播放条、逐帧 Qwen 曲线、
  Gaussian/EMA/滑动平均/离线突出度/流式突出度、N=3–31 窗口、D=0–5 延迟、
  横轴节点、地图采样点、双语、提示词、复核及移动端。
- 34/34 case 的初始帧均等于错误帧；零页面错误、零外部请求。
- Qwen 与 JEV 均显示连续逐帧概率波形；浏览器测试确认 `scorePlot` 中实际绘制
  JEV 红色波形，而非孤立单点。
- 浏览器证据：同目录 `browser_verification.json`、`browser_desktop.png`、
  `browser_mobile.png`。

## 发布

- 在线入口：
  http://134.175.18.101/vln/jev_noul_v004_wrong_choices34_qwen4b_template_20261109_05/jev_noul_v004_vs_qwen4b.html
- 发布版本：`jev_noul_v004_wrong_choices34_qwen4b_template_20261109_05`
- 发布时间：2026-11-09T14:41:02Z。
- 在线 HTML：1,563,172 bytes，SHA256
  `844c6cb7860a77fa7ec340db88c71b7ae6534f745fa62ca08d75de5612d0ce13`。
- 发布同时上传 3,049 个拆分资源；全部远端 SHA256 核验通过。
- 公网入口 HEAD：HTTP 200、`text/html`、1,353,305 bytes。
- 发布记录：
  `outputs/visualization_publishing/publish_20261109_144102_400480/publication.json`
- 在线拆分明细：
  `outputs/visualization_publishing/jev_noul_v004_wrong_choices34_qwen4b_template_20261109_05/online_manifest.json`

在线验证范围是入口 HEAD 和全部远端哈希；详细交互检查是在同源本地离线页完成，
没有把 HEAD 检查表述为完整在线浏览器检查。

此前 `..._01`、`..._02` 为另行制作的 34 事件页面，已保留作历史。最终版
`..._template_20261109_05` 按用户明确指定的 12 例/template 版本直接替换数据，
并使用全逐帧 JEV 结果生成真正连续的概率波形。

## 端点变更记录

新 `anyaigc.ai` 端点持续返回共享 `jev-1` 上游 429，阻塞记录保留在
[`../../upstream_probe_anyaigc_20261109/README.md`](../../upstream_probe_anyaigc_20261109/README.md)。
按用户指令切回此前可用的 `api.site` 后，单点探针与 34 点正式结果均成功。
