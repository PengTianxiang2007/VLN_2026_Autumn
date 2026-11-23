# H1 倒序倒走回退 · 22 组原始报警点对

[全部 22 组掉头与倒走回退的实采对照回放](http://134.175.18.101/vln/roundtrip_rxr20_h1_22_rgb_20261122_01/index.html?case=C03) · [导出与校验记录](../../exports/paired_rgb_20261122_01/README.md)

2026-11-22 18:03 UTC 完成 22/22 组。倒走回退 0/22 达标，平均水平误差 1.907 米、平均朝向误差 56.64°。同组直接 reset 22/22 达标，平均水平误差 0.0173 米、朝向误差 0.32°。[逐例结果](../../../../outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22/summary.json)

本轮验证机器人从原报警点 B 的历史朝向出发，能否靠倒走和转向返回存档点 A。样本、历史位姿、scene、seed 2、动作边界、物理环境配置均继承[前序掉头回退实验](../../v001/run_20261122_03_rgb22/README.md)。22 个原始点对水平直线距离均 ≥1.5 米。前序完成 22/22 且仿真退出后，主管在 GPU 3 重新检查准入，自动接续本轮。

逐例按相反顺序读取非停止动作，前进换成后退，左右转互换，不追加掉头。后退使用 H1 原生步态，纵向指令 −1 m/s，角速度 0，动作周期 50 个物理步，与原生前进时长一致。回退从 B 的实测机器人根位姿与关节状态初始化，沿用前序的根速度置零和末尾 50 步站稳。途中由 H1 实际执行，只在结束时用 A 评分。每例另执行直接 reset 对照，保持原组间顺序与评分条件。落点须距 A ≤0.35 米、朝向差 ≤15°，且可继续行动。

每组保留原生前视 RGB、逐动作位姿和最终误差。后退在 `inverse_trace.jsonl` 中记为动作 4；`command_forward_mps` 是下发速度，`body_forward_displacement_m` 是这一步实际水平位移在步初机器人朝向上的投影，负值表示向后。B 起始帧先在原物理步同步关节与相机并记录 `camera_root_xy_m`，可据此判断刚放置时的相机位置。整条导航的 SR 与平均 SPL，两组均为“暂无，已评分 0 条”。

从仓库根目录提交队列的命令如下。冻结脚本按前序终态接续；主管的等待阶段只使用 CPU。

```bash
prior=outputs/inverse_rollback/v001/run_20261122_03_rgb22
out=outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22
python3 -B scripts/run_inverse_rollback.py prepare-backward --after-run "$prior" --output "$out"
tmux -L peng_inverse_backward22_20261122 new-session -d -s backward22 'export VLN_INVERSE_PROJECT="$PWD"; out=outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22; exec python3 -Bu "$out/source/run_inverse_rollback.py" run --output "$out" --gpu 3 >> "$out/supervisor.log" 2>&1'
```

提交前逐例核对了 22 组的原始 A、B 和历史动作，倒序后共 530 个非停止动作，其中 391 个后退。CPU 检查核实后退连续 50 个控制步向原步态接口传 −1 m/s，之后左右转符号和正向速度设置正确。倒走的实际步幅、跌倒与落点由仿真测量。

[冻结清单、Git 版本与源码哈希](../../../../outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22/manifest.json) · [队列状态](../../../../outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22/status.json) · [配对结果](../../../../outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22/summary.json)
