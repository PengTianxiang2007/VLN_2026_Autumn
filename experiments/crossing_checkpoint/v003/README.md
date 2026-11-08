# Crossing v003：通向不同区域的选择节点

更新时间：2026-11-05。用户已授权第2稿在原5条开发样本上做一次离线测评，改为每两个动作步调用一次；新建[固定批次记录](run_20261105_01/README.md)，不运行15条验证。

<!-- CROSSING_V003_BATCH_STATUS_START -->
已完成；5条固定离线样本，每2个动作步调用一次。 TP 4 / FP 2 / FN 9。 GPU已释放。
<!-- CROSSING_V003_BATCH_STATUS_END -->

## 目的与用户定义

用户要求：crossing是一个存在明显多个选择的节点，不同选择通向不同区域，例如在过道口可以分别走向厨房、客厅、厕所。先提供新prompt及新旧prompt中文翻译，暂不开始测评。

用户补充：即使因视角或遮挡只看到一点证据，只要能够推断出通向不同区域的支路，也应计入分支并在满足定义时判为crossing，不必看清完整入口或房间内部。

候选标识：`crossing-v003-region-choice-draft02`。针对旧版将“仍可直行”作为判否理由，以及仅枚举方向而未明确其对应区域的问题，改为围绕“同一节点的分支—区域—视觉证据及其合理推断”判断。

## 提示词与对照

- [新版英文system prompt](prompt_en.txt)
- [新版完整中文翻译](prompt_zh.txt)
- [当前保留baseline英文原文](previous_baseline_en.txt)
- [当前保留baseline完整中文翻译](previous_baseline_zh.txt)
- [最近试验r02英文原文](previous_r02_en.txt)
- [最近试验r02完整中文翻译](previous_r02_zh.txt)
- [来源、文件哈希与准备状态](prompt_manifest.json)
- 第1稿保留：[英文](prompt_revision01_en.txt)、[中文](prompt_revision01_zh.txt)、[原清单](prompt_manifest_revision01.json)。第1稿未测评；第2稿按新授权进入固定5条测评。

对照以实际保留的 `crossing-v1-schema2` 为主；r02虽然最后试验，但没有被选中。本候选替换旧定义段，保留baseline的时间因果、here/ahead/behind、same_place与JSON输出边界。新稿在现有 `branches[].landmark` 中描述分支通向的区域和可见证据，不新增字段，不采用r02的JSON字段重排。判断顺序作为任务说明，尚未更改运行代码。

## 定义差异

1. 明确以同一位置的至少两个不同去向为判据；沿用旧版排除来路的约定，不能把刚走来的通道再次算成新去向。
2. 每个去向可以直接看见，也可以依据局部视觉证据合理推断。视角受限时，部分开口、侧向通道一角或延伸到墙后的地面均可作为证据；不要求完整入口、房间内部或准确房间名称。两个不同卧室也可构成两个去向。
3. 直行与侧向入口可以构成选择节点；无需典型T形/十字形，也无需强制转向。
4. 同一门洞的门前通道与门内空间只算一条分支；走廊上先后出现、位于不同位置的入口不合并成同一节点。
5. 仅绕家具两侧后回到同一区域，不足以构成此定义的crossing。这比旧版“两个可通行绕行分支即可”的表述更严格，属于定义变化，尚未验证与现有几何标注的一致性。
6. 局部证据已足以合理推断支路时，不因“没看全”而输出uncertain，也不自动设为low置信度；confidence反映证据支持程度。现有状态机不接受low置信度作为有效确认票，本次仅调整提示词表述，状态机不变。
7. 在分支描述中区分实际看到的线索和据此推断的区域；完全没有视觉线索支持的出口不计入。仍需区分here/ahead/behind，识别到局部支路不代表机器人已经到达该节点。

## 设置、结果与下一步

上述prompt_manifest记录的是此前仅准备文字的状态。新授权使用第2稿，原5条轨迹的有效调用从292次减为146次（原动作编号0、2、4……）。8张历史RGB和32个已执行动作仍包含中间未调用的步骤；输出schema、存档阈值、模型推理参数和地图评分不变。状态机只在真实回答时更新，计数单位仍为模型观测。

启动命令、seed、源码快照与产物见固定批次记录。v002的15条验证已查看，本批次不调用它们；没有授权后续自动调参。测评完成后遵循[默认可视化模板](../../../docs/CROSSING_VISUALIZATION_TEMPLATE.md)导出，后台写回最终状态并释放本项目GPU。


最新授权：v003第2稿恢复每步调用，仅取原五条中的前三条。记录：`experiments/crossing_checkpoint/v003/run_20261105_02/README.md`。

<!-- CROSSING_V003_DEV3_STRIDE1_STATUS_START -->
已完成；3条固定离线样本，每1个动作步调用一次。 TP 3 / FP 3 / FN 5。 GPU已释放。
<!-- CROSSING_V003_DEV3_STRIDE1_STATUS_END -->


## 第3稿：小幅降低视觉证据门槛（尚未测评）

用户要求再稍微降低prompt门槛。当前`prompt_en.txt`和`prompt_zh.txt`已更新为`crossing-v003-region-choice-draft03`；已测评的第2稿完整保存在`prompt_revision02_en.txt`、`prompt_revision02_zh.txt`及`prompt_manifest_revision02.json`，两次历史运行的冻结源码及结果不变。

本次只新增一个三句段落：一个具体线索即可支持合理可信的第二支路；尚未完全验证时优先crossing/medium；不能仅因身处房间或开放区域而判否。仍要求同一位置的两个不同去向，排除来路、关闭/阻挡的通道、重复路线及完全无视觉依据的出口。here/ahead/behind、same_place、存档确认阈值、输出schema均不变。没有启动模型或评测。

定位证据：逐步三条实验中，kujiale_0036_10_0第44帧在reason里以“房间有出口，但不是路口”判否，故增加第三句；这只是日志线索，并非已通过RGB核验此处确有两条可用支路。diagnostics另显示5次漏检中4次已有crossing/here观测，应继续核查存档合并/首次确认位置匹配，不能把所有漏检归因于门槛。该小改动可能增加误报，效果尚未测评。

校验：英文和中文各仅插入一个段落，其余文字逐字相同；第2稿归档哈希与两轮测评所用prompt一致。下一步等待用户安排测评，不自动启动新批次。


最新授权：第3稿在相同三条上逐步测评，自动导出HTML并释放GPU。记录：`experiments/crossing_checkpoint/v003/run_20261105_03/README.md`。此前“尚未测评”是提示词准备时状态。

<!-- CROSSING_V003_DRAFT03_DEV3_STATUS_START -->
已完成；3条固定离线样本，每1个动作步调用一次。 TP 4 / FP 3 / FN 4。 GPU已释放。
<!-- CROSSING_V003_DRAFT03_DEV3_STATUS_END -->


第3稿追加六条逐步离线测评，记录：`experiments/crossing_checkpoint/v003/run_20261105_04/README.md`。

<!-- CROSSING_V003_DRAFT03_EXTRA6_STATUS_START -->
失败/未完成；6条固定离线样本，每1个动作步调用一次。 GPU已释放。
<!-- CROSSING_V003_DRAFT03_EXTRA6_STATUS_END -->


六条批次run_04在正式调用前因缺少版本选择记录失败，GPU已释放。已补齐并以run_05重启，记录：`experiments/crossing_checkpoint/v003/run_20261105_05/README.md`。

<!-- CROSSING_V003_DRAFT03_EXTRA6_RETRY_STATUS_START -->
已完成；6条固定离线样本，每1个动作步调用一次。 TP 2 / FP 3 / FN 6。 GPU已释放。
<!-- CROSSING_V003_DRAFT03_EXTRA6_RETRY_STATUS_END -->

Qwen第三稿九条统一可视化已完成：原3条＋追加6条，共481观测，单文件保留两个批次入口；默认模板及实际浏览器检查通过，未启动推理。记录 experiments/crossing_checkpoint/v003/combined9_visualization/README.md；HTML outputs/crossing_checkpoint/v003/combined9_export_20261105_01/visualization/qwen_draft03_9_cases.html。
