# R2R-CE 已评分 217 条的错支路归因

2026-11-23 UTC 用户要求统计暂停时已有的两百多条。固定原版运行的 217 个唯一 episode、123 成功、94 失败、技术异常 0 条，未评分的 episode 618 另计。当前版即原版，双方 SR 为 123/217（56.68%），平均 SPL 为 0.4933。样本来自 400 条计划的已完成部分，抽样 seed 2、Habitat 配置 seed 100。

对全部 94 个失败逐例对照原指令、原始 RGB、同次实走轨迹、R2R 参考路径及 MP3D 可行走网格，按此前 RxR 判据识别能定位具体预期与实际通路的错支路，并判断其与失败的关系。按正常 STOP 和限步分别计数，保留不确定和其他失败。参考路径点连线用于寻找审阅窗口，复杂几何需结合 RGB。原始归因由 Codex 离线完成。

基线 Git 提交与输入哈希保存于本次输出 sources.json。原评测继续保持暂停，离线处理使用 CPU。

2026-11-23 09:51 UTC 全部 94 条失败归因完成，12 条补看第二组帧，共审阅 569 个不同的 episode/step。每条任务只计一个主标签。

## 结果

**明确走错支路 67 条，占 94 条失败的 71.28%，占全部 217 条已评分任务的 30.88%。** 其中进错门或房间 24 条、走错通道分支 33 条、漏转弯或楼梯入口 10 条。不确定 10 条，其他失败 17 条。

| 原生终止方式 | 失败任务 | 明确错选支路 | 不确定 | 其他失败 |
| --- | ---: | ---: | ---: | ---: |
| 模型执行 STOP | 83 | 63 | 9 | 11 |
| 达到 500 步且最后一个动作非 STOP | 11 | 4 | 1 | 6 |
| 合计 | 94 | 67 | 10 | 17 |

| 同口径比较 | R2R 本批 | RxR 此前批次 |
| --- | ---: | ---: |
| 有效评分 | 217 | 389 |
| 全部失败 | 94（43.32%） | 165（42.42%） |
| 明确错选支路 | 67 | 80 |
| 明确项占失败 | 71.28% | 48.48% |
| 明确项占全部有效评分 | 30.88% | 20.57% |
| 当前版 / 原版 SR（两者为同一次原版运行） | 均为 123/217（56.68%） | 均为 224/389（57.58%） |
| 当前版 / 原版平均 SPL（含失败） | 均为 0.4933 | 均为 0.4915 |
| 技术异常，单列 | 0 | 11 |

若沿用最初 VLNVerse 只把正常 STOP 中明确错选计入分子的口径，本批为 63/94（67.02%）占全部失败、63/217（29.03%）占全部已评分、63/83（75.90%）占正常 STOP 失败；对应此前 RxR 分别为 44.85%、19.02%、52.48%。主结论采用之前 RxR 的全终止方式口径，包含 4 条最终限步的明确错选。

## 证据与限制

- 例 11 / episode 495：要求走到卧室另一端套内浴室，实际在第 27→36 步选择相邻衣橱门，并停在挂衣杆前，归为进错门。[补审帧](../../../../outputs/crossing_analysis/r2r_seed2_400/run_20261123_02_partial217/details/011.jpg)
- 例 7 / episode 167：已穿过餐厅进入要求等待的大厅，之后继续走到衣橱，归为目标处继续前进的其他失败。[补审帧](../../../../outputs/crossing_analysis/r2r_seed2_400/run_20261123_02_partial217/details/007.jpg)
- 例 83 / episode 1220：在正确楼梯入口反复尝试到 500 步，未进入其他通路，归为通行受阻。[关键帧](../../../../outputs/crossing_analysis/r2r_seed2_400/run_20261123_02_partial217/cards/083.jpg)

本批是原计划 400 条的已完成前缀，覆盖 6/11 场景，各场景已评分数为 55、8、29、55、57、13。不同指令可共用场景及参考路线，以上比例以指令 episode 为单位，不能直接视为整个 R2R-CE 的错误分布，也不能仅凭它和 RxR 的差值推断 benchmark 难度。未评分的 episode 618 不进入任何分母。原评测保持暂停，没有新增导航或干预恢复。

标签由 Codex 对原始指令、RGB 和轨迹离线审阅得出，尚未经独立人工复标；明确错选也不等于回退后必然恢复成功。开放房间家具绕行或地标不能唯一对应的案例保留不确定。下一步可优先人工复核这 10 条不确定案例。

## 产物与复现

```bash
CUDA_VISIBLE_DEVICES='' HABITAT_SIM_LOG=quiet backbone/streamvln/.venv/bin/python -Bu scripts/review_r2r_partial_failures.py prepare
CUDA_VISIBLE_DEVICES='' HABITAT_SIM_LOG=quiet backbone/streamvln/.venv/bin/python -Bu scripts/review_r2r_partial_failures.py supplement
CUDA_VISIBLE_DEVICES='' HABITAT_SIM_LOG=quiet backbone/streamvln/.venv/bin/python -B scripts/review_r2r_partial_failures.py summarize
```

`prepare` 仅用于新目录首次准备，已有冻结运行不可覆盖；补审窗口保存在 `supplement.json`。汇总已核对 94 条失败一一对应、标签全集、明确项的预期/实际通路和已审帧步号。未运行模型推理或导航测试。

[94 条逐例归因及决策/确认步](attribution.csv) · [统计摘要](summary.json) · [审阅记录](reviews.tsv) · [补审窗口](supplement.json) · [输入和源码哈希](../../../../outputs/crossing_analysis/r2r_seed2_400/run_20261123_02_partial217/sources.json) · [冻结评分](../../../../outputs/crossing_analysis/r2r_seed2_400/run_20261123_02_partial217/scores.jsonl) · [全部关键帧](../../../../outputs/crossing_analysis/r2r_seed2_400/run_20261123_02_partial217/cards/)
