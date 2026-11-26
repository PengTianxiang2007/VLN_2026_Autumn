# kujiale_0036_0_0 第 38 步 H1 常驻仿真

2026-11-26。用于后续回退实验摆位。seed 2，单个 H1 physical 环境，数据取自原版 104 条多视角采集 run_20261117_03，恢复 38 的动作前边界。使用包含该录制进程的末段 chunk 原始配置、同一角色和场景，无导航模型，未启动实验动作。完整位姿、19 个关节位置和速度从 metadata.json 还原。录制缺少根速度，按既有摆位协议置零。世界时钟从本次启动计，任务物理计数恢复为 1901。常驻至用户下一指令。

Git 基线 d551421，启动前工作区干净。本次新增的启动源码为同目录 hold.py、start.sh。物理 GPU 3。启动命令从仓库根目录执行。

```bash
tmux -L peng_vln_pose_20261126 -f /dev/null new-session -d -s f38 'bash experiments/inverse_rollback/pose_hold/run_20261126_01/start.sh'
```

[实时状态与位姿读回](../../../../outputs/inverse_rollback/pose_hold/run_20261126_01/status.json) · [本次原生前视](../../../../outputs/inverse_rollback/pose_hold/run_20261126_01/front.png)。控制台使用同一 tmux socket 和 f38 会话，三维仿真对象保留在进程中。未进行导航评分。

## 已恢复并常驻

2026-11-26 10:53 UTC，物理 GPU 3，Isaac PID 3122551，控制台已进入等待。第 38 步根位置及全部 19 个关节的位置、速度读回最大绝对差为 0。根四元数最大分量差 5.96e-8，相机位置最大分量差 5.96e-8 米，朝向四元数最大分量差 1.35e-7。摆位后物理推进 0 tick。首次导入辅助脚本时遇到同名包，已改用指定源码路径载入，初次启动日志保留在本轮输出。正式场景日志为 isaac.log。

已有控制台可用 `tmux -L peng_vln_pose_20261126 attach -t f38` 接入。

2026-11-26 随后在同一 PID 接入 [Codex 的观察与单步动作工具](../../codex_tools_v001/run_20261126_01_f38/README.md)。单步实测完成后已还原 F38，该 tmux 会话当前由工具服务占用主线程，交互式 Codex 的接入命令见该记录。
