# 原版200条中的102条失败分类

更新时间：2026-11-17T07:56:47.180525+00:00。状态：完成。

本次检查全部102条原生SR=0任务，覆盖11场景、seed=2。按已有轨迹、动作、指令和场景底图离线归因，**64条属于偏航或路线方向错误，占失败的62.75%，占全部200条的32.00%**。其中56条选错方向、分支或漏转弯（54.90% / 28.00%），8条掉头沿来路反向回返（7.84% / 4.00%）。另8条证据不足，未计入64条。

## 分类结果

每条只分配一个主要类别；跌倒、卡住、STOP作为另一个维度保留，避免重复计数。

| 主要类别 | 数量 | 占102条失败 | 占全部200条 | 对应纠错组成功 |
|---|---:|---:|---:|---:|
| 选错方向、分支或错过转弯 | 56 | 54.90% | 28.00% | 49/56 |
| 掉头沿来路反向回返 | 8 | 7.84% | 4.00% | 4/8 |
| 沿正确路线未走完即停止／局部徘徊 | 12 | 11.76% | 6.00% | 4/12 |
| 正确路线附近跌倒，无明确选路偏航 | 9 | 8.82% | 4.50% | 1/9 |
| 预热阶段跌倒，尚无策略动作 | 3 | 2.94% | 1.50% | 0/3 |
| 正确路线附近卡住 | 5 | 4.90% | 2.50% | 2/5 |
| 目标区域附近未停，继续走过头 | 1 | 0.98% | 0.50% | 1/1 |
| 证据不足，局部偏移原因不确定 | 8 | 7.84% | 4.00% | 8/8 |

64条偏航/方向错误中，原生最终结束方式为48条未到目标、15条跌倒、1条卡住。这里15条跌倒和1条卡住计入偏航，是因为时序记录显示先进入错误方向或发生反向回返，再结束；这与直接把所有fall/stuck归为物理失败不同。

## 证据口径与限制

- 原版有完整位置轨迹、完整策略动作、官方指令及参考路径；197条有策略trace，本次99条非预热失败均有trace，3条预热失败没有策略动作。99条有初始两帧RGB；`vis_output=False`、`review_output=None`，服务`--save-rgb 2`，没有全程RGB录像。未用纠错组画面冒充原版画面，未重新仿真补图。
- 对102条逐条审阅17张拼图/102张独立场景轨迹图及指令，再对短距离偏移、跌倒前回返等边界例逐动作核对。静态底图来自场景资产投影，只用于定位，不构成碰撞或门可通行的证明。
- 判偏航要求实际行走方向/房间或通道选择与任务参考线路不符，并在失败前持续或没有完成正确路线；不是只检查距离是否超过0.75米。`route_choice`包含开放区域和起步方向错误，因此56条不能全部称为已验证的拓扑分叉错误。
- `route_backtrack`指已经推进后转向并沿来路返回，参考进度明显下降；反向回走可以贴着参考线发生。未达到独立方向错误证据的小范围往返归入未推进或不确定。
- 目标末端走过头单列1条。OS=1仅指曾进入三米XY评分范围，可能隔墙，或在起点便临近目标；不能据此认定进了正确房间。轨迹第0点是初始位姿，OS复核使用其后的评分观测；全部102条复核一致。
- 64条中的51条证据较强、13条证据中等，另8条保留不确定。置信级别是单一审阅者对证据强弱的判断，不是概率或多人一致性。没有全程RGB，不能把本结果表述为已逐帧确认模型视觉推理错误的因果真值。

## 与距离阈值统计的区别

如果只数最大路线距离≥0.75米，会得到65条；它与本次64条不是同一批任务：阈值漏掉7条已判方向错误，同时把1条末端未停和7条不确定局部偏移算进去。因此最终数字来自逐条时序审阅，而非套用纠错脚本阈值。

## 与自动纠错组配对

先冻结102条分类和理由，再关联纠错组同ID/seed的结果；原始分组结果在此前对话已知，但逐条纠错成功/失败没有用于分类。64条中纠错组53条成功、11条失败（53/64=82.81%）；56条选路方向错误中49条成功（87.50%），8条反向回返中4条成功（50.00%）。这是独立运行的对应成绩，不是共享前缀的干预因果证明；纠错使用官方正确参考路线，属于Oracle。

## 代表案例

| 任务 | 归因 | 原版结束 | 纠错组SR | 审核图 |
|---|---|---|---:|---|
| kujiale_0243_29_2 | 选错方向、分支或错过转弯 | not_reach_goal | 1 | [轨迹图](../../../../../../outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/maps/001_kujiale_0243_29_2.png) |
| kujiale_0159_50_0 | 选错方向、分支或错过转弯 | fall | 1 | [轨迹图](../../../../../../outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/maps/021_kujiale_0159_50_0.png) |
| kujiale_0159_18_3 | 掉头沿来路反向回返 | not_reach_goal | 0 | [轨迹图](../../../../../../outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/maps/024_kujiale_0159_18_3.png) |
| kujiale_0165_45_0 | 选错方向、分支或错过转弯 | not_reach_goal | 1 | [轨迹图](../../../../../../outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/maps/035_kujiale_0165_45_0.png) |
| kujiale_0226_88_0 | 选错方向、分支或错过转弯 | stuck | 0 | [轨迹图](../../../../../../outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/maps/060_kujiale_0226_88_0.png) |
| kujiale_0291_6_3 | 掉头沿来路反向回返 | not_reach_goal | 1 | [轨迹图](../../../../../../outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/maps/096_kujiale_0291_6_3.png) |
| kujiale_0291_12_2 | 选错方向、分支或错过转弯 | fall | 1 | [轨迹图](../../../../../../outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/maps/102_kujiale_0291_12_2.png) |

## 场景统计

| 场景 | 原版失败 | 偏航/方向错误 | 其中选错路 | 其中反向回返 | 不确定 |
|---|---:|---:|---:|---:|---:|
| kujiale_0128_fix | 5 | 3 | 3 | 0 | 2 |
| kujiale_0147 | 12 | 7 | 6 | 1 | 1 |
| kujiale_0159 | 7 | 5 | 3 | 2 | 1 |
| kujiale_0165 | 10 | 9 | 9 | 0 | 0 |
| kujiale_0226 | 14 | 9 | 8 | 1 | 1 |
| kujiale_0243 | 7 | 5 | 4 | 1 | 0 |
| kujiale_0258 | 11 | 5 | 5 | 0 | 1 |
| kujiale_0285 | 8 | 4 | 4 | 0 | 1 |
| kujiale_0290 | 9 | 9 | 9 | 0 | 0 |
| kujiale_0291 | 7 | 3 | 1 | 2 | 0 |
| kujiale_0294 | 12 | 5 | 4 | 1 | 1 |

## 方法版本、命令与验证

分析源码：`scripts/analyze_oracle_baseline_failures.py`，本次Git HEAD `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，工作区有未提交修改；最终脚本副本及SHA256留在输出目录。原导航继续使用历史冻结版本，没有改动历史代码或重跑任务。Codex逐条审阅笔记为 [review_notes.tsv](review_notes.tsv)，与任务ID绑定的冻结记录为 [review.json](review.json)。

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/analyze_oracle_baseline_failures.py \
  --campaign outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200 \
  --output outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01

# 逐条审阅并冻结review.json后，汇总分类和配对成绩；历史结果请使用新输出目录。
benchmarks/vlnverse/.venv/bin/python -B scripts/analyze_oracle_baseline_failures.py \
  --campaign outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200 \
  --output outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01 \
  --finalize --review experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/review.json
```

核验：102条全部覆盖、无重复ID；每条原生SR=0；两组scene、seed和逐任务seed一致；动作数与位置数（动作数+2）全部匹配；末端NE与OS全部独立复算通过；源评分、trace、数据集及场景底图SHA256未变。线段内部投影、重复路线点和纯XY距离三项CPU几何检查通过。三条预热失败与其零策略动作对应。

## 交付文件

- [逐条分类CSV（含任务ID、理由、置信级别、结束方式、配对结果、原始指令和证据路径）](classification.csv)
- [分类汇总JSON](summary.json)；[验证记录](validation.json)
- [全部102张审核图与17张拼图、分类和源证据哈希ZIP](../../../../../../outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/review_evidence_102.zip)

本次仅离线读取已完成结果，模型/仿真服务未更改，没有新导航、API调用或自动恢复已取消队列。不确定8条留待新增真实证据后复核，不因纠错组成功而改判。
