# 30 例 H1 逆动作回退，运行 02

30/30 组配对物理回退已完成，主管正常退出。逆动作达标 4/30，平均水平误差 1.125 米、朝向误差 47.08°；直接 reset 达标 30/30，平均水平误差 0.0177 米、朝向误差 0.46°。[地图与第一人称回放导出记录](exports/replay_20261122_01/README.md)

已正常启动并交后台。GPU 3 主管 PID 3686409，首个 Isaac PID 3686428。C13 已通过 F15 报警位姿读回，返回 F2 的第一个左转动作实际执行 50 个物理 tick 后完成，机器人仍可行动。此处记录启动确认，最终几何误差随后台结果更新。

沿用[运行 01 的实验协议](../run_20261122_01/README.md)，30 个 case 和两组物理动作定义均相同。修正原生数据加载器的参数传递。使用项目原有 Isaac、H1 和动作控制器。启动时检查 GPU 3 余量和即时负载，主管持有单实例锁。

```bash
python3 -B scripts/run_inverse_rollback.py prepare --count 30 --output outputs/inverse_rollback/v001/run_20261122_02
tmux -L peng_inverse30_20261122 new-session -d -s rollback30 'exec python3 -Bu scripts/run_inverse_rollback.py run --output outputs/inverse_rollback/v001/run_20261122_02 --gpu 3 >> outputs/inverse_rollback/v001/run_20261122_02/supervisor.log 2>&1'
```

[冻结样本和源码版本](../../../../outputs/inverse_rollback/v001/run_20261122_02/manifest.json) · [主管与 GPU 状态](../../../../outputs/inverse_rollback/v001/run_20261122_02/status.json) · [当前案例](../../../../outputs/inverse_rollback/v001/run_20261122_02/progress.json) · [首个逆动作实测](../../../../outputs/inverse_rollback/v001/run_20261122_02/startup.json) · [两组落点和逐对差值](../../../../outputs/inverse_rollback/v001/run_20261122_02/summary.json)。
