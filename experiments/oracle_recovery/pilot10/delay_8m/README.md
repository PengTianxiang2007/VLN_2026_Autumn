# 偏移8米

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

状态：10/10 已完成。与上级 pilot10 共用十条任务和对照。

全组成功 1/10；实际干预 0 条；纠正 0 次；无干预成功 1 条。
完整协议和限制见上级 README 与原文档。实际源码版本以该组 manifest、code_oracle 快照为准。

启动入口（仅供新获授权的运行参考；旧结果不得覆盖）：

```bash
python3 -B scripts/run_oracle_crossing.py --campaign outputs/oracle_crossing/seed2_10_delay8m_20261103 --arm oracle --gpu <已核验GPU> --sim-gpu <已核验GPU>
```

命令从仓库根目录执行。实时审阅使用 scripts/oracle_crossing_console.py；不能无人审阅地当作自动恢复模型。
该组已结束，不需要继续运行。

## 代码、启动说明与产物

- [实验配置、任务与版本](../../../../outputs/oracle_crossing/seed2_10_delay8m_20261103/manifest.json)
- [原始结果](../../../../outputs/oracle_crossing/seed2_10_delay8m_20261103/report/results.json)
- [该组报告](../../../../outputs/oracle_crossing/seed2_10_delay8m_20261103/report/index.html)
- [运行与审阅说明](../../../../docs/ORACLE_CROSSING_PILOT.md)
