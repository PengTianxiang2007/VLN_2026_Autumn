# C11 偏航评审分支自主实走返回 S05

2026-11-26。用户确认的实时部署模拟：从 Astra medium 对 C11 的第 12 轮偏航回答之后创建一个 Codex 分支，以通用动作 prompt 将常驻 H1 从 F57 控制到 S05（F45）。父会话 01a21418-31a2-7261-aeff-69b81c8aa1f2，最后已完成 turn 01a21428-71e2-7e02-ad6d-8efb607f16fb。沿用用户 CODEX_HOME、7892 代理、gpt-6-astra medium、原生前视动作接口。单例 kujiale_0128_fix_20_0，seed 2。以现场读回核对，模型自主 finish_return 且终点距 F45 的水平误差 ≤0.35 米计为局部达标，保留实走终点。Git 基线 60c8751e59bdfddbc57a3efbe2955e3352ea02bb。工作区另有 F65 和 F57 摆位及索引修改。此次完整 prompt 见 [prompt.txt](prompt.txt)。

在已摆好 F57 的单例仿真上从仓库根目录执行 `python3 experiments/inverse_rollback/codex_tools_v001/run_20261126_04_c11_f57_f45/run.py`。每个运行编号仅调用一次。动作记录在该次挂起的 F57 接口，分支事件和最终答复保存在本轮独立输出目录。

## 实际结果

按用户追加的 50 动作上限截断。收到并执行指令时已有 55 个移动，核对截断前后均为 55；控制客户端 PID 3428565 已退出，Isaac PID 3122551 保留在现场 F112。共前进 10、左转 21、右转 24。水平距离从 2.016 米降至第 50 步的 0.646 米，最近为第 54 步的 0.534 米，实际终点 0.537 米。分支未调用 finish_return，局部达标 0/1。整条导航 SR、平均 SPL：当前版与配对原版均暂无，已评分 0 条。

首次左转确实推进了 50 个任务 tick 和 91 个世界 tick，旧接口因计数不同返回错误。重试未执行。修复回执后，同一分支从现场 F58 接续动作，原左转仅计一次。两段记录共 60 个 MCP 调用，产生 59 条仿真回执，包含 4 次独立观察。分支 ID 为 `01a21801-225f-7e51-81b5-a33bbb542f98`。

[动作与落点评分](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_04_c11_f57_f45/result.json) · [截断回执](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_04_c11_f57_f45/truncation.json) · [可视化导出](../../exports/c11_branch_return_20261126_01/README.md)
