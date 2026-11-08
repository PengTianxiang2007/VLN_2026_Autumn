# Oracle pilot10：五组纠正时机比较

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

## 协议与状态

五组各十条已完成，共 50 次导航；复用十条无干预对照，SR=0/10。
从既有 Crossing 错误候选中选取十条，冻结任务和落点；由 Oracle 确认走错后修改位置与朝向，保留 policy memory，可多次干预。
尽早纠正并非走到 crossing 前替模型选路。延迟阈值为到完整正确参考折线的最短水平距离。
仅在原动作队列自然为空时交接；保留原 STOP、跌倒、卡住与预算规则。

## 结果

| 条件 | 全组成功 | 干预任务 | 干预次数 | 无干预成功 |
| --- | --- | --- | --- | --- |
| [确认走错后尽早纠正](early/README.md) | 10/10 | 10 | 18 | 0 |
| [偏移3米](delay_3m/README.md) | 5/10 | 6 | 7 | 1 |
| [偏移5米](delay_5m/README.md) | 0/10 | 1 | 1 | 0 |
| [偏移8米](delay_8m/README.md) | 1/10 | 0 | 0 | 1 |
| [偏移12米](delay_12m/README.md) | 1/10 | 0 | 0 | 1 |

26 次干预 memory 校验均通过。8m/12m 没有干预，不能评估这些距离下的恢复能力。
独立物理运行不完全确定；尽早组有近目标落点和局部碰撞恢复因素，十条选定样本不能代表完整 benchmark 提升。

## 启动与下一步

各条件 README 链接原始 manifest、报告与命令。运行前重新核验 GPU；已完成组不自动重跑。
当前阶段整理结果与可视化；追加不同任务已取消。


## 代码、启动说明与产物

- [完整协议、启动、限制与最终结果](../../../docs/ORACLE_CROSSING_PILOT.md)
- [新版：仅最初十条全成功组，按配对实验模板导出](../../../outputs/oracle_crossing/seed2_10_multi_20261103/oracle_early10_offline.html)
- [推荐：五组动态地图单文件 HTML](../../../outputs/oracle_crossing/oracle_replay_v2_20261104.html)
- [原比较报告](../../../outputs/oracle_crossing/comparison_20261103/index.html)
- [干预实现](../../../core/oracle_crossing.py)
- [memory审计](../../../core/oracle_policy_state.py)
