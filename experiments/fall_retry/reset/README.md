# Reset重跑

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

状态：历史运行完成。

从起点重新 reset 运行41条，同一任务种子；41条完成、19条再次跌倒（46.34%）、10条成功。

实际入口 scripts/test_fall_retries.py，运行参数和环境以原 manifest 为准。本实验已结束，直接回退补测已取消，不提供自动续跑操作。仅重新汇总现有数据可用：

```bash
python3 scripts/summarize_fall_retries.py --campaign outputs/experiments/fall41_seed2_20261103
```

此命令会更新原汇总；单纯查看结果无需执行。

## 代码、启动说明与产物

- [原运行配置](../../../outputs/experiments/fall41_seed2_20261103/manifest.json)
- [成绩与协议限制](../../../outputs/experiments/fall41_seed2_20261103/comparison.json)
- [原运行入口](../../../scripts/test_fall_retries.py)
- [重放实现](../../../core/fall_replay.py)
