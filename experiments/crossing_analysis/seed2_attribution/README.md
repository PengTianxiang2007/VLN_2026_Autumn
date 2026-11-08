# seed2 Crossing 错误归因

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

状态：已完成既有报告。250 条中成功 99、失败 151；Crossing 错选归因 48 条，占全部 19.20%、失败 31.79%。
排除异常失败 46 条（跌倒 41、卡住 5）；另有不确定 16、其他失败 41。
这是离线辅助证据归因，不是独立人工金标准，也不是干预已证实的因果效应。
入口 scripts/analyze_crossing_failures.py，具体口径和逐条证据保存在原始目录。
后续 Oracle 使用该候选池，不能把候选池的比例直接当作恢复成功率。

## 代码、启动说明与产物

- [归因 HTML](../../../outputs/checkpoint_review/seed2_crossing_attribution_20261103/index.html)
- [原始统计](../../../outputs/checkpoint_review/seed2_crossing_attribution_20261103/summary.json)
- [其他失败分类](../../../outputs/checkpoint_review/seed2_crossing_attribution_20261103/remaining_failure_breakdown.json)
- [分析入口](../../../scripts/analyze_crossing_failures.py)
