# 三种预先设计的 JEV 采样规则

原轮目标为零漏采；用户随后要求同时保留少量漏采、高采纳率的备选方案。本次纳入原设计阶段全部三条规则，沿用已锁定的 20/22 随机划分和 ±3 步有序一对一匹配口径。登记时保守版验证结果已知，另外两条只在设计集比较过，规则源码已在首次查看验证集前冻结。直接复用保守版验证记录；两种备选各验证一次，均保留，无验证后调参。运行命令为 `python3 -B experiments/crossing_checkpoint/online_sampling_v002/run_20261124_02_tradeoffs/compare.py`。

## 已完成

| 规则 | 20 条设计集，匹配 / 候选 | 设计覆盖 | 22 条留出集，匹配 / 候选 | 验证采纳率 | 验证覆盖 | 较原版少采 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 原版 v001 | 52/171 | 52/52 | 51/174 | 29.31% | 51/51（100%） | — |
| near 邻近合并 | 52/166 | 52/52 | 51/171 | 29.82% | 51/51（100%） | 3（1.72%） |
| plateau 高分区间隔候选后移 | 51/120 | 51/52 | 50/135 | 37.04% | 50/51（98.04%） | 39（22.41%） |
| active 高分区候选后移 | 51/110 | 51/52 | 48/114 | 42.11% | 48/51（94.12%） | 60（34.48%） |

三种规则共用冻结的 v001 检测器。near 遇到与上个已发候选相差不超过 3 步的原始候选时跳过。另两种在此基础上把部分原始候选的代表位置向后移 2 步。plateau 只移动高分区的间隔候选，active 移动高分区激活时的所有候选类型。后移时只用当前已到达的分数，候选在其位置帧加 5 步时发出，轨迹尾部不足等待步数则无输出。每个 episode 独立。匹配容差 ±3 步，在查看设计和验证结果前已固定。

验证集一对一配对后未匹配的参考点：plateau 为 C29 F33；active 为 C45 F130、C21 F72、C29 F38。near 保住全部 51 个，其中 48 个同帧，另外 3 个提前 3 步。此处采纳率仅按与 Astra 参考位置的邻近匹配计算。验证集与设计集可能共享场景；验证集已用于本次比较，再根据该表迭代需另用未参与的样本检验。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

## 产物

[逐例验证结果与实际配对](../../../../outputs/crossing_checkpoint/online_sampling_v002/run_20261124_02_tradeoffs/validation.json) · [指标摘要](summary.json) · [冻结规则和分组哈希](protocol.json) · [20/22 随机分组](../run_20261124_01/split.json) · [双语本地回放](../../../../outputs/crossing_checkpoint/online_sampling_v002/run_20261124_02_tradeoffs/replay/index.html)。

各版本可独立勾选，案例列表保留原 C 编号。页面展示每种方法的匹配数、候选数与漏采参考帧。C29 实测三个命令行模式与冻结输出一致，网页中文 / English 均显示对应帧及漏采。下面的命令使用任一轨迹已有的 scores.json。MODE 可取 near、plateau、active，省略时为 near。

```bash
node scripts/replay_jev_online_sampling.cjs --input "$SCORES" --version v002 --mode "$MODE"
python3 -B experiments/crossing_checkpoint/online_sampling_v002/run_20261124_01/export_local.py --tradeoffs
```

本地导出 SHA256 `8279d383900c85d3b43936eebdabc909333bdc77436699a441184ff3e70066af`。源码快照保存在该运行输出目录的 `source/`。
