# RxR-CE 原版 400 条中的 Crossing 错选支路

[随机 30 例逐帧双语回放与抽样清单](exports/random30_20261123_01/README.md)

2026-11-23 UTC 已完成离线归因。输入为[原版复现](../../../reproduction/streamvln_rxr/run_20261123_01/README.md)的冻结清单及正式轨迹，抽样 seed 2，Habitat 配置 seed 100。基线提交 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。

沿用[最初 VLNVerse seed 2 归因](../../seed2_attribution/README.md)的判据，逐条对照指令、同次导航 RGB、实际轨迹、参考路线及 MP3D 可行走区域。计入条件为能定位到具体的通路选择、辨认应该进入及实际选择的支路，并有证据支持该错误与任务失败有关。保留其他和不确定标签，每条 episode 计一次。11 条非有限评分单列；有效评分 389 条，其中 224 条成功、165 条失败。技术异常、成功任务不进入失败归因。限步与停止均记录，物理坐标偏离仅用于定位候选。

分析从项目根目录运行：

```bash
backbone/streamvln/.venv/bin/python -B scripts/review_rxr_crossing_failures.py
backbone/streamvln/.venv/bin/python -B scripts/review_rxr_crossing_failures.py --supplement
backbone/streamvln/.venv/bin/python -B scripts/review_rxr_crossing_failures.py --summarize
```

## 结果

**165 条有效失败中，明确错选支路 80 条，占失败的 48.48%，占全部有效评分的 20.57%（80/389）。** 按实际发生的选路判定，后续触及步数上限的 6 条也在此数中。

| 原生终止方式 | 失败任务 | 明确错选支路 | 不确定 | 其他失败 |
| --- | ---: | ---: | ---: | ---: |
| 模型执行 STOP | 141 | 74 | 33 | 34 |
| 达到 500 步且最后一个动作非 STOP | 24 | 6 | 8 | 10 |
| 合计 | 165 | 80 | 41 | 44 |

80 条主标签中，28 条进错门或房间，27 条走错通道分支，25 条漏掉应转的弯或楼梯入口。同一任务仅计一个主标签，包括同一条轨迹上的多次错选。RxR 的不同指令可以共用一条参考路线。

历史 VLNVerse 将明确错选的分子限定在正常 STOP 的失败中，同时保留所有失败作为失败分母。对应 RxR 的 STOP 子集，74 条占全部有效失败的 44.85%（74/165）、全部有效评分的 19.02%（74/389）、正常 STOP 失败的 52.48%（74/141）。VLNVerse 原值分别为 31.79%（48/151）、19.20%（48/250）、45.71%（48/105）。两种仿真环境的异常终止机制不同。

这一批只有原版导航，当前版与原版为同一次运行。双方 SR 同为 224/389（57.58%），平均 SPL 同为 0.4915，包含 165 条失败；进行中 0 条，11 条非有限评分另外保留。

## 判例与证据

- episode 99 的指令要求沿上层扶手经过浴室和能看到床的卧室，继续到走廊末端的空房间。第 71 步附近机器人对准卧室门，第 80 步已经走向白床，最终在卧室内停止，归为进错门。[轨迹及 RGB 关键帧](../../../../outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/cards/109.jpg)
- episode 4536 的指令要求在楼梯转角停下。机器人走上了正确的楼梯，也进入过成功范围，随后继续上楼才停，归为其他失败。[轨迹及 RGB 关键帧](../../../../outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/cards/030.jpg)
- episode 2021 在洗手盆前停下，与文字指令相符，但参考终点与实际进入的门内位置分离，最终 NE 为 3.45 米。将这一例保留为不确定。[补审画面](../../../../outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/details/081.jpg)

165 条均审阅了指令、三维轨迹与参考路线、决策高度的导航网格平面图及原始 RGB 关键帧。25 条另抽取第二组帧，两个阶段共对应 1,053 个不同的 episode/step。绿色为参考路线，蓝色为实际轨迹，橙色高亮待核对段，洋红点为实际终点。候选位置仅用于找帧，多层交叉用高度和楼梯画面核对。判定由 Codex 离线完成，未做独立人工复标或干预后的恢复验证。下一步人工复核可优先选取 41 条不确定案例以及同一指令地标对应多个相似门口的案例。

[165 条逐例明细及明确案例的决策步和确认步](attribution.csv) · [统计与技术异常清单](summary.json) · [逐条审阅记录](reviews.tsv) · [逐例证据图](../../../../outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/cards/) · [原始轨迹和全部 RGB](../../../../outputs/reproduction/streamvln_rxr/run_20261123_01/capture/) · [源码与输入哈希](../../../../outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/sources.json)
