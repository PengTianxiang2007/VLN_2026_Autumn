# seed2 的48条 Crossing 错选：五 seed 重复错误核对

更新时间：2026-11-06。状态：完成。用户随后要求简化，最终采用“seed2已归因48条与其他seed任务失败的交集”，不要求其他seed也已确认同一错误原因。

## 最终交付口径

48条×5 seed的原始评分与轨迹已核对。按最终任务失败计：17条五个seed均失败，17条恰好四个seed失败，5条恰好三个seed失败，8条恰好两个seed失败，1条仅seed2失败。至少两个seed共同失败47条，至少三个39条，至少四个34条。

- [五个seed均失败的17条](../../../outputs/checkpoint_review/seed2_multiseed48/run_20261106_01/all5_failed.csv)
- [全部48条的共性清单](../../../outputs/checkpoint_review/seed2_multiseed48/run_20261106_01/common_failures.csv)
- [小体积摘要](summary.json)

这里确定seed2属于既有Crossing错选归因；其余seed仅要求原生SR=0，可能含跌倒或卡住，不能把这17条直接表述为五个seed都确认Crossing错选。

简化前的局部轨迹匹配、12张地图对照和10条的RGB关键帧均保留作辅助产物，不作为此次最终筛选条件。原匹配提名为40条至少两seed、26条至少三seed、10条五seed；该计数与最终任务失败交集分开。初次绘图因VLNVerse环境缺matplotlib中止，使用已有StreamVLN环境完成绘图；未安装依赖。首版RGB抽帧包含终止复用及末尾非递增帧，v2在新目录排除后重导出；旧版保留。

## 目的与范围

用户要求从既有 seed2 的48条 Crossing 错选归因中，找出多个 seed 重复发生同类错误的 episode，供后续亲自标定离线测评数据集。固定原48条，比较同一 episode 的 seed 0–4，不新增导航、模型调用或 GPU 工作。

## 方法与证据边界

读取已完成 StreamVLN H1 physical 五 seed 复现的原始 LMDB 轨迹与评分，并对照原 seed2 错选路口、决策帧、错误方向描述。先以局部轨迹顺序匹配提名同路口同错误支路，再逐图核对。最终失败状态与错误支路重复分别统计；成功轨迹中的同类错误也保留。

只有 seed2、seed3 有原始 RGB 录像。seed0、1、4 的结论为坐标轨迹支持，不声称 RGB 语义复核。原 seed2 归因为辅助分析，未被当作用户人工金标准。本次只分析48条在其他 seed 中的对应情况，不代表完成 seed3 全集归因。

## 数据与版本

- 固定来源：`outputs/checkpoint_review/seed2_crossing_attribution_20261103/attribution_reviews.json` 中 `status=crossing` 的48条。
- 五 seed 来源：`outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/`。
- 本次输出：`outputs/checkpoint_review/seed2_multiseed48/run_20261106_01/`，历史结果不覆盖。
- 实际 Git、工作区差异、分析源码快照及输入哈希写入本次 manifest；原复现版本继续引用历史 manifest。
- 公共分析入口：`scripts/analyze_crossing_multiseed.py`；命令与最终结果完成后补齐。

## 结果与下一步

240条对应轨迹与原始评分核对完成，48条既有标签未改写。后续由用户挑选并亲自标定。
