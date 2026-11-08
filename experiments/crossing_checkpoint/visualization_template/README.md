# Crossing 默认可视化模板

更新时间：2026-11-05。状态：已完成，模板ID为 `crossing-review-v1`。

## 目的与范围

用户指定 v002 的 `run_20261105_03/crossing_v002_dev5_val15_offline.html` 为以后每次 Crossing 迭代的默认模板。保留地图/RGB旁同步进度条、C/P对照、版本同帧切换、逐帧回答、因果历史、存档状态与复核意见导出；版本、样本数量、成绩和复核结论来自实际数据。

仅调整CPU导出代码和完成后的报告钩子，不启动模型、导航或仿真，不改变预测、评分、标签或seed。已完成实验及历史HTML均保留。

## 实现与验证计划

模板独立保存到core/，不再依赖某次outputs中的冻结布局。通用导出器接受任意已完成且已审计的版本，单版完成即可导出，不等待最终验证。每次导出新建目录；当前迭代入口在诊断完成后调用统一导出流程。

使用v002既有审计报告验证单版、多个开发版本以及开发/验证合集；检查样本和版本信息、数据无损、同步拖动与版本切换。运行涉及公共入口的CPU检查，不执行GPU任务。验证产物保存到 `outputs/crossing_checkpoint/visualization_template/run_20261105_01/`，记录源码快照与实际Git版本。

## 已完成实现

[使用规范](../../../docs/CROSSING_VISUALIZATION_TEMPLATE.md)与AGENTS.md均已登记用户选择。仓库模板为 `core/crossing_campaign_template.html`，版本面板和控制器分别为 `core/crossing_campaign_panel.html`、`core/crossing_campaign.js`；来源与字体路径见 `core/crossing_visualization_template.json`。

`scripts/export_crossing_iteration.py`先审计完成的版本，再用通用模板导出；默认带上同split此前已成功导出的版本，每次新建目录，并通过 `runs/<tag>/visualization.json`登记最新产物。`test_crossing_single_gpu.py`和`run_crossing_development.py`已接入完成钩子；前者只有在诊断与可视化成功后写入完成标记，后者完整导出成功后才标为可审阅。不启动新方法迭代。

## 实际验证

- 既有16项Crossing CPU检查通过，五个修改的Python入口语法通过，现有OpenCV/字体环境可用。
- 单版入口：已有baseline，5条/292观测；完整因果请求、存档和评分严格复核通过，再生成默认模板HTML。
- 下一版入口：已有r01，自动读取baseline导出登记，生成双版10个轨迹/版本视图、584观测；r01也完成严格审计。没有推理重跑。
- 四版合集：原5条开发三版＋15条验证，30个轨迹/版本视图、1791观测。原始四份payload哈希完全相同，03版HTML哈希保持不变。
- Chromium133完整合集检查通过：76次事件跳转、196次标注跳转、7个问题入口、同帧版本切换、笔记隔离/导出、播放/暂停、图层、大图与移动端布局；页面错误0、外部请求0。
- 单版/双版额外检查通过：两处进度条实际鼠标拖动并同步、版本和样本数量动态显示、没有验证/复核说明时正确隐藏相应入口、同帧切换、窄屏无溢出。桌面截图已查看。

首次单版检查在Python3.9执行评分复算时发现距离字段最后一位相差约1e-16，严格断言拒绝继续；失败目录 `single_iteration`保留。定位为 `math.dist`解释器差异后，审计明确复用原Python3.10环境，字体打包仍用已有Python3.9环境；重试目录 `single_iteration_02`通过，没有放宽核验或修改任何分数。

实际命令示例（路径现已存在，勿覆盖重跑）：

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_crossing_iteration.py \
  --output outputs/crossing_checkpoint/dev5_val15/run_20261104_01 \
  --tag baseline --compare-tags \
  --destination outputs/crossing_checkpoint/visualization_template/run_20261105_01/single_iteration_02

backbone/streamvln/.venv/bin/python -B scripts/export_crossing_iteration.py \
  --output outputs/crossing_checkpoint/dev5_val15/run_20261104_01 \
  --tag r01_connectivity \
  --destination outputs/crossing_checkpoint/visualization_template/run_20261105_01/two_iterations
```

## 产物与限制

- [单版HTML](../../../outputs/crossing_checkpoint/visualization_template/run_20261105_01/single_iteration_02/visualization/crossing_review_offline.html)
- [自动双版HTML](../../../outputs/crossing_checkpoint/visualization_template/run_20261105_01/two_iterations/visualization/crossing_review_offline.html)
- [四版合集HTML](../../../outputs/crossing_checkpoint/visualization_template/run_20261105_01/four_versions/crossing_review_offline.html)
- [单版/双版浏览器记录](../../../outputs/crossing_checkpoint/visualization_template/run_20261105_01/single_and_two_version_browser.json)
- [完整合集浏览器记录](../../../outputs/crossing_checkpoint/visualization_template/run_20261105_01/four_versions/browser_validation/browser_verification.json)
- [结果与源码摘要](../../../outputs/crossing_checkpoint/visualization_template/run_20261105_01/adoption_summary.json)

实际Git基线为 `0a805dfcf4457f80300822abb4eff7cabba43aae`，工作区存在未提交内容，以本次source快照和哈希为准。自动完成钩子只做源码与CPU验证，未为了测试报告而启动GPU流程。此工作不构成新检测成绩或新导航实验。后续迭代按统一入口导出即可；没有待运行任务。
