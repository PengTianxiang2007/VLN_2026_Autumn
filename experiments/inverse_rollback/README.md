# 历史动作逆向回退

2026-11-26，[五例回退并进入正确支路 · 120 步](codex_tools_v001/run_20261126_07_five_branch120/README.md)已结束，整批用时 33 分 40 秒。4 例声明已进入所选支路，C23 在 56 步触发物理终止。C43、C20 报告使用更早回退点。保留 315 张第一人称 RGB 及 C20 仿真停点。

2026-11-26，[C11 英文区域回退 · 60 步上限](codex_tools_v001/run_20261126_05_c11_region60/README.md)已结束。从 F57 起步，模型在 31 步后声明到达，终点距 F45 水平位置 1.060 米，仿真保留在现场 F88。

2026-11-26，[C11 Codex 实走回退回放](http://134.175.18.101/vln/c11_codex_return_f57_f45_web_20261126_01/index.html)已发布。[运行与导出记录](exports/c11_branch_return_20261126_01/README.md)。控制客户端已退出，H1 保留在 F112，截断点距目标 0.537 米。

[从 F38 到电视前 · 占据地图与动作观测回放](http://134.175.18.101/vln/codex_tv_f38_h1_20261126_01/index.html) · [导出记录](exports/codex_tv_20261126_01/README.md)

2026-11-26 [Codex 从 F38 自主走到电视柜前](codex_tools_v001/run_20261126_03_tv/README.md)，终点距柜子正面 1.13 米，完成 27 个动作，主动观察 1 次，已恢复常驻 F38。

2026-11-26 [Codex 在 F26、F42、F54 连续控制同一台 H1](codex_tools_v001/run_20261126_02_multisite/README.md)，三处四步净移动 39.95–49.37 厘米，20 次调用均收到原生前视图。原仿真已恢复 F38 并常驻。

2026-11-26 [Codex 直接操作常驻 VLNVerse H1](codex_tools_v001/run_20261126_01_f38/README.md)，kujiale_0036_0_0 F38 单步实测通过。两个观察各 0 tick，前进 50 tick，水平位移 2.23 厘米。原进程已恢复 F38，工具持续可用。

2026-11-26 [H1 第 38 步常驻摆位](pose_hold/run_20261126_01/README.md)，kujiale_0036_0_0，供后续回退实验使用。实际状态见运行记录。

[C21 七图回退](vlm_action_v001/run_20261123_08_restore_c21/README.md)直接使用去程原图和动作序列，每执行四个动作单独判断是否复原。

[选路位置版回退 · C15、C21、C31、C34](vlm_action_v001/run_20261123_06_choice_position4/README.md)使用相同去程描述和物理协议，比较加强退出条件后的实际落点。

[DeepSeek 实走回退 22 例逐帧回放](exports/deepseek_h1_22_20261123_01/README.md)同步呈现地图、当前 RGB 和模型动作。

[DeepSeek 实际动作回退全 22 例](vlm_action_v001/run_20261123_05_finish22/README.md)汇总首批、追加十例与最后九例。

[DeepSeek 实际动作回退追加十例](vlm_action_v001/run_20261123_04_deepseek10/README.md)沿用三例协议，单独记录结果。

[DeepSeek 三例实际动作回退](vlm_action_v001/run_20261123_03_deepseek3/README.md)使用 C03、C05、C07，检验闭环控制和到点退出。

[VLM 动作回退样本集 · 原报警 22 例](vlm_action_v001/run_20261123_02/README.md)已完成，含全部去程动作、每例 7 张历史前视图及 B 的 H1 初始化状态。

[RxR-CE 20 组与 H1 22 组 · 完整实采对照回放及发布记录](exports/paired_rgb_20261122_01/README.md)

在原生 VLNVerse H1 物理仿真中，比较按历史动作返回离线节点和直接恢复节点位姿的落点误差。

[v001 · seed 2，30 个案例](v001/run_20261122_02/README.md)
[原始报警距离 ≥1.5 米的 22 组原生 RGB 采集](v001/run_20261122_03_rgb22/README.md)

[v002 · 同 22 组保持 B 点初始朝向的倒走回退](v002/run_20261122_01_backward_rgb22/README.md)

[RxR-CE · 五场景 20 组实走去程、掉头与倒走回退](rxr_ce_v001/run_20261122_01_rgb20/README.md)
