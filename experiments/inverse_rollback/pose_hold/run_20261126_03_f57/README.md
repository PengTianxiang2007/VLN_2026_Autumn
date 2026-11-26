# H1 常驻摆位 · kujiale_0128_fix_20_0 第 58 张观测

2026-11-26，用户确认取原版多视角采集 run_20261117_03 中第 58 张观测，即从 0 编号的终止帧 F57。seed 2，在原项目 GPU 3 仿真 PID 3122551 内切换单环境至 kujiale_0128_fix，挂起 H1 供后续操作。Git 基线为 `60c8751e59bdfddbc57a3efbe2955e3352ea02bb`，已有 F65 摆位登记和脚本尚未提交，本次运行源码为 [switch_scene.py](switch_scene.py)。

在原 H1 动作端点正常 detach 后，从该仿真控制台执行：

```python
import runpy
switch = runpy.run_path("experiments/inverse_rollback/pose_hold/run_20261126_03_f57/switch_scene.py")
task, world, art = switch["switch_and_place"](env)
switch["serve"](env, switch["OUT"] / "live", 57)
```

已完成。现场世界坐标 [3.645542621612549, -0.5275841951370239, 0.9435123205184937] 米，航向角 18.86927°。任务计数 2802，摆位推进 0 tick。机身、相机及关节读回通过，机身根速度按既有协议置零。默认动作入口已接入新场景。两组导航 SR 与平均 SPL 均暂无，已评分 0 条。

[位姿读回](../../../../outputs/inverse_rollback/pose_hold/run_20261126_03_f57/placement.json) · [现场前视图](../../../../outputs/inverse_rollback/pose_hold/run_20261126_03_f57/front.png) · [动作端点](../../../../outputs/inverse_rollback/pose_hold/run_20261126_03_f57/live/endpoint.json)
