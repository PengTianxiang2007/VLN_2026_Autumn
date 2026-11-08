# Crossing 地图与错误归因

2026-11-06：用户已提交69条任务的人工标注；[离线数据集v001](../crossing_dataset/seed2_human_v001/README.md)按要求剔除8条零标注，保留61条及128个点（34个错误选择）。完整数据包与只读HTML已完成并通过校验。

2026-11-06：[69条标注工具的中文指令版](seed2_annotation69/exports/run_20261106_02/README.md)已交付。全部导航指令中文显示，原英文与原媒体保留，保存/删除功能验证通过。

2026-11-06：[seed2 69条人工标注工具](seed2_annotation69/README.md)已完成：39条至少三seed失败＋30条seed2成功（每场景3条），6409帧。单文件HTML支持双图同步、两类Crossing标注、逐点删除/撤销及保存后重新打开；浏览器验证通过，等待用户亲自标注。未运行模型或导航。

2026-11-06：[seed2的48条跨seed共性筛选](seed2_multiseed48/README.md)完成。按用户最终简化口径，仅比较同episode最终失败：17条五seed均失败，47条至少两seed失败；其余seed是否Crossing错选不由此确定。

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

这是既有轨迹的离线分析，不是模型预测性能或干预实验。

- [25 条地图复核](map_review25/README.md)
- [seed2 全部 250 条错误归因](seed2_attribution/README.md)

这些先验地图可以用于评估，但不能作为实时 Crossing 检测模型的隐藏输入。
