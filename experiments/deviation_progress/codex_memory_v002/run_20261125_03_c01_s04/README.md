# C01 S04 单候选复判

目的：在正式 v006.1 候选资格提示词中加入“视野受限时，少量可见证据仍可支持另一条可能通往不同空间区域的当地路线”，检验 C01:S04:F38 的二分类结果。

沿用 seed 2 的冻结轨迹，JEV v002 active。由原会话 S04 轮之前分叉；沿用已发生的初始化与 S01–S03 上下文，唯一模型调用为 S04 候选资格判断。上一有效节点为空。三张原图为 F36、F38、F40，GPT-6 Astra 常规档、medium，代理 17982。使用原 schema 与校验函数。

命令：`python3 -B experiments/deviation_progress/codex_memory_v002/run_20261125_03_c01_s04/replay.py`。产物位于 `outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_03_c01_s04/`。

2026-11-25T16:50:31.462300+00:00 完成，仅 1 次模型判定。C01 S04（F38）由原判 `not_eligible` 改为 `eligible`，按筛选规则保留。F36 右缘木门框及其另一侧地面支持一条可能独立的向右路线，F38/F40 支持向前继续进入客厅。门后目的地尚未确认。 [该轮原答](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_03_c01_s04/codex/turns/turn_0005_S04/final.txt)。Git HEAD 为 `e40d9a821ee72516261ee819284e36be7be2eff1`，本次未提交的 prompt 和运行脚本快照位于上述输出目录。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。
