# StreamVLN / VLNVerse：250 条 × 5 seed

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

## 状态与设置

已完成 1250/1250 条、50/50 个 seed-scene 单元。H1 physical，seed 0–4，每个 seed 250 条，10 个完整 scene。
实际版本以历史 manifest、源码快照及恢复记录为准；无 v2 后缀的早期 campaign 未完成，不作为最终结果。

## 结果

| seed | SR |
| --- | --- |
| 0 | 39.2% |
| 1 | 39.6% |
| 2 | 39.6% |
| 3 | 38.8% |
| 4 | 40.8% |

五 seed 平均 SR 39.60%，样本标准差 0.75 个百分点；平均 SPL 33.24%。seed2 为 99/250 成功。
这是 250 条子集复现，不是完整 825 条 Val Unseen；不同物理运行不保证逐步确定性。

## 启动与下一步

完整命令和固定 scene 清单见下方协议；历史任务已完成，不自动重跑。
查看状态可用 `python3 scripts/reproduce_streamvln_vlnverse.py status --campaign outputs/reproduction/streamvln_scene250_5seeds_20261101_v2`。


## 代码、启动说明与产物

- [原始汇总](../../../outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/summary.json)
- [样本与源码 manifest](../../../outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/manifest.json)
- [逐任务成绩](../../../outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/episodes.csv)
- [协议及启动命令](../../../docs/STREAMVLN_VLNVERSE_SCENE250.md)
- [适配审计](../../../docs/STREAMVLN_VLNVERSE_AUDIT_20261102.md)
- [运行入口](../../../scripts/reproduce_streamvln_vlnverse.py)
