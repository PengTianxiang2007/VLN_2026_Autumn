# 五例回退并进入正确支路（120 步）

**Prompt 版本标记：进入支路，仍需下一步接手**

模型越过支路入口并用第一人称画面确认后，本轮局部恢复结束。后续导航留给下一步接手。五例共用的 [英文 prompt 原文](prompt.txt) 已冻结，SHA256 为 `f7ea9a643df44d069d92aed79387d4af1253d8477454ffcb0fea5f0dd3dc516f`。

2026-11-26。沿用上一版本 C11、C17、C43、C23、C20 的 seed 2、Astra medium 原偏航评审末轮、冻结多视角采集和原生 H1 动作接口。依次从 F57、F91、F58、F17、F47 开始，首选回退点依次为 S05/F45、S09/F68、S04/F30、S02/F7、S03/F41。相同摆位协议和仿真 PID 3122551，GPU 3。独立重新分叉，历史有效节点与原始导航指令从父会话继承。用户代理 7892。

回退后用原始指令、已经完成的路段和第一人称画面选路，实际跨过入口后确认才调用 finish_return。当前区位找不到匹配支路则继续沿历史回退到更早的有效回退点。整个回合物理移动预算 120 步，观察和声明完成不计步；第 121 个移动请求在仿真执行前拒绝。在没有更早回退点或预算耗尽且未确认时，结束并报告进展。模式为 branch_entry，finish_return 记为模型声明进入所选支路，物理轨迹与 RGB 单独保留；初始回退目标的几何误差供参考。

[通用英文 prompt](prompt.txt) · [逐例起点及父会话清单](cases.json) · [实时状态与计时](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_07_five_branch120/status.json)

从仓库根目录启动 `python3 -Bu experiments/inverse_rollback/codex_tools_v001/run_20261126_07_five_branch120/run.py`。Git 基线 `60c8751e59bdfddbc57a3efbe2955e3352ea02bb`。复用上轮未提交的回执、计时和 60 步通用队列，启动时改传 120 步；每例 launch.json 记录对应命令和源码哈希。每例保存摆位用时、分支控制用时和总耗时、起点 front.png、live/frames 原生第一人称图像、live/calls.jsonl、分支回复、result.json 和 timing.json。最后一例结束后保留仿真现场。当前版与配对原版整条导航 SR、平均 SPL 均暂无，已评分 0 条。

## 五例最终结果

队列于 2026-11-26T16:08:34.097557+00:00 结束，整批用时 2020.2 秒。4 例由模型声明已进入所选支路，C23 触发物理终止（原生原因 fall）而未确认进入。0 例用尽 120 步。C43 报告从 S04 回溯到 S03；C20 报告从 S03 经 S02 回溯到 S01。此处记录模型自报和动作回执，未对分支正确性另外评分。

| 案例 | 停止原因 | 移动步数 | 摆位秒数 | 控制秒数 | 总秒数 | 工具 RGB 张数 |
|---|---|---:|---:|---:|---:|---:|
| C11 | finish_return | 26 | 21.6 | 209.3 | 232.1 | 29 |
| C17 | finish_return | 81 | 30.6 | 710.3 | 741.9 | 84 |
| C43 | finish_return | 80 | 31.8 | 348.8 | 382.0 | 84 |
| C23 | physical_terminal | 56 | 23.7 | 334.5 | 359.6 | 58 |
| C20 | finish_return | 52 | 30.6 | 272.4 | 304.2 | 55 |

共保存 310 张工具调用后第一人称 RGB 和 5 张摆位图，原仿真保留在 C20 停点。整条导航 SR 及平均 SPL 当前版与配对原版均暂无，已评分 0 条。

## 双语回放导出

2026-11-26T16:24:12.557462+00:00 已在[原网页](http://134.175.18.101/vln/c11_codex_region60_f57_f45_web_20261126_01/index.html)更新五例回退与进入支路回放，[离线 ZIP](http://134.175.18.101/vln/c11_codex_region60_f57_f45_web_20261126_01/replay.zip)含相同内容。默认 120 步版本，可按同一案例切换之前的 60 步版本。图层区分实际回退、回溯更早节点与选路尝试，阶段交界采用对应模型发言的工具调用边界。C23 的物理跌倒、随后被拒的动作及末次原生画面分别记录。310 张工具回图与 5 张起点图全部收录。

[导出源码](export_recovery.py) · [本地入口](../../../../outputs/visualization_publishing/codex_branch120_five_cases_web_20261126_01/index.html) · [本地离线 ZIP](../../../../outputs/visualization_publishing/codex_branch120_five_cases_web_20261126_01/replay.zip) · [发布回执](../../../../outputs/visualization_publishing/publish_20261126_162307_238835/publication.json) · [稳定入口及哈希](../../../../outputs/visualization_publishing/codex_branch120_five_cases_web_20261126_01/activation.json)。入口 SHA256 为 `c263f14a75e486d834a81033058617d827a47235a291f14154eaab232422f0ed`，离线 ZIP 为 `0e021d365e164c73bc549fdf045c3e3fd5a58169b245bc94ca816c320150fbc7`。所有远端发布资源哈希通过，公网入口和下载均返回 HTTP 200。本地浏览器抽查两版切换、中英文、各例末帧及 C23 的拒绝动作。
