# 跌倒重试实验

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

固定 seed2 原异常失败清单中的 41 条跌倒任务；不等于所有指标中带 fall 的任务集合。

- [Reset](reset/README.md)：41 条完成，19 条再次跌倒，10 条成功。
- [历史动作重放](action_replay/README.md)：40 条适用且完成，22 条跌倒，6 条成功；1 条无历史不适用。
- 直接恢复到跌倒前10个导航动作的状态补测：用户已取消，未执行。

动作重放从起点重新行走，不是直接瞬移回退，也不是物理状态恢复，不能据此回答用户原本的直接回退问题。
本次只归档，不恢复取消实验。

## 代码、启动说明与产物

- [比较与取消状态](../../outputs/experiments/fall41_seed2_20261103/comparison.json)
- [协议更正](../../outputs/experiments/fall41_seed2_20261103/protocol_correction.json)
- [41条原清单](../../outputs/experiments/fall41_seed2_20261103/cohort.json)
