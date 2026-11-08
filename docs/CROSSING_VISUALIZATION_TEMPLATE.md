# Crossing 默认离线可视化模板

2026-11-05，用户指定当前HTML作为以后每轮迭代的模板。布局基准为[双进度条03版](../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_03/crossing_v002_dev5_val15_offline.html)，SHA256为 `eb9cff5c701770f001d2746014965ed8f507667ac461a443ef7316d06fda8ac2`。旧文件保留。

模板ID：`crossing-review-v1`。每版完成后使用同一模板导出，不再将旧视频目录报告作为最终交付。单版即可导出，不需要等最终验证集完成。

2026-11-07 起，导出的 HTML 还必须按[发布规范](VISUALIZATION_PUBLISHING.md)上传到
用户服务器并验证公网访问，回复中交付完整网址；离线文件仍保留。此规则也适用于预览和重导出。
现有导出器只负责本地生成，不能把“本地导出成功”记作“已发布”；操作者须继续执行发布和在线验证。

## 固定界面与可变数据

- 模型输出、prompt、原始任务指令及其他英文自然语言内容提供完整中文翻译，保留英文原文。
  页面提供“中文 / English”选择，默认中文，切换覆盖正文与详情，保持同一任务/帧/回答；
  翻译仅用于展示，不修改实际请求、原始响应或评分依据。具体要求见[发布规范](VISUALIZATION_PUBLISHING.md)。
- 地图和RGB正下方各有同步进度条，播放、拖动、事件跳转、逐步查看均同步。
- 蓝色C为固定地图标注，红色P为模型确认时的机器人位置；保留逐帧模型回答、历史输入、存档状态和本地复核意见导出。
- 保留开发/验证分组、多版本同帧切换；没有验证或人工复核说明时不显示虚构的验证成绩或结论。
- 版本、样本数量、成绩、图像、提示词输出和复核说明来自对应结果；不固定为5条/15条或三版，也不沿用“两次修改未改善”的历史结论。
- HTML内嵌图像和中文字体，复制单个文件即可离线查看。当前评分界面对应既有1m匹配协议；修改协议时必须同步更新评分说明和模板版本。

模板文件：[布局](../core/crossing_campaign_template.html)、[版本面板](../core/crossing_campaign_panel.html)、[交互控制](../core/crossing_campaign.js)、[配置与来源](../core/crossing_visualization_template.json)。代码不依赖历史outputs中的布局文件。

## 每轮统一入口

在对应运行的scores和diagnostics完成后执行，替换下方输出目录和版本名：

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_crossing_iteration.py \
  --output outputs/crossing_checkpoint/<实验>/<运行编号> \
  --tag <本轮版本名>
```

此命令仅使用CPU读取已完成结果。因果请求、存档重建和评分复算使用原审计环境 `benchmarks/vlnverse/.venv/bin/python`，字体打包使用已有StreamVLN环境；不安装依赖、不启动模型或仿真。若后续实验使用其他审计解释器，可显式指定 `--audit-python`，不要放宽评分一致性检查来掩盖环境差异。

默认把本实验同一split中此前已通过统一入口导出的版本一起放入本次HTML。可用 `--compare-tags <旧版1> <旧版2>` 指定对照，空的 `--compare-tags` 表示仅当前版本；可用 `--annotations <说明.json>` 加入实际复核说明。未导出的旧版可以使用其已有审计报告作为显式对照。不同样本的分数差不解释为方法改进。

产物默认位于 `exports/<tag>/run_<UTC时间>/visualization/crossing_review_offline.html`，并保存审计报告、源码快照、哈希及状态。`runs/<tag>/visualization.json` 指向该版本最新一次成功导出；旧目录始终保留。可通过 `--destination` 指定新的外层导出目录，已存在的目录会被拒绝。

`test_crossing_single_gpu.py` 的迭代队列及 `run_crossing_development.py` 已接入此入口；导出失败会报告失败，不把该版标为可交付。未完成轨迹仍使用前缀预览，不伪装成完整结果。直接调用底层回放器时，由操作者在诊断完成后调用统一导出入口。

仅合并已有审计HTML时使用 `scripts/export_crossing_campaign.py --campaign <目录> --destination <新目录> --tags <版本列表>`；不要求存在最终验证或final_summary。该低层入口与每轮统一入口共用模板。

## 维护与验证记录

[模板固化记录](../experiments/crossing_checkpoint/visualization_template/README.md)记录实际检查范围和产物。后续修改模板需保留来源与版本记录，并检查双进度条同步、版本同帧切换、离线依赖和数据完整性。历史推理结果不因模板更新而重算或覆盖。

## 2026-11-07 三帧五级评分变体

`protocol.json` 的 `kind=crossing_lite` 由统一入口 `scripts/export_crossing_iteration.py` 路由到 `scripts/export_crossing_lite.py`。继承原模板样式与双进度条布局，保留C/P、逐帧回答、实际三帧历史、复核导出及版本控件；本版无存档，明确显示未建立存档。P仅表示展示阈值（默认>=4）的连续高分片段起点，不是确认事件或预测路口中心。原始1–5分及可视化阈值彼此独立，不套用旧版1m/PR/F1评分。原始模板与历史HTML不修改；单文件内嵌原WebP、地图和字体。实际请求重建和CPU浏览器验证在自动收尾时执行。当前首个版本只有一个版本选项。

2026-11-07T03:41:01.901924+00:00：按用户要求更新三帧评分HTML俯视轨迹配色，1–5分浅绿到深绿；t→t+1线段使用起点t的有效原始评分，无评分灰色虚线，原地转向同色点，并加入图例。仅修改core/crossing_lite_review.js；原启动manifest/source快照保留，导出修订与授权哈希见outputs/crossing_checkpoint/lite_v001/run_20261107_01/export_revisions/score_route_colors_20261107_01/。推理源码、prompt、任务与原答未改，不查询/跟踪运行进度。独立CPU预览30条/2589帧/156位置及五档明度、实际Canvas线段颜色、起点评分对应、回放前缀和灰色缺失检查通过；合成配色测试不计模型结果。本轮自动导出会应用此修订。
