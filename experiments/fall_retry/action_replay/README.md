# 历史动作重放

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

状态：历史运行完成。

40条适用任务从起点重放原动作到原跌倒前10个导航动作，再继续；不是直接回退。22条跌倒，其中6条在到达交接步之前、16条在交接后；6条成功。1条在导航前跌倒，无可回退历史。

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
