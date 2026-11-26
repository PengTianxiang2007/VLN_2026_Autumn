# H1 常驻摆位至数据集 F65

2026-11-26，使用原进程 3122551 和同一台 H1，场景 kujiale_0036，episode 为 kujiale_0036_0_0，seed 2。目标为原版多视角采集 run_20261117_03 的 F65 终止观测。读取 physical_state_before，设置根位姿、19 个关节的位置和速度以及任务计数。根速度按既有摆位协议置零。只渲染并在原进程等待动作。

Git 基线为 `60c8751e59bdfddbc57a3efbe2955e3352ea02bb`。本次摆位脚本为同目录 [place.py](place.py)。在已核对的项目控制台退出原动作接口后执行以下命令，动作端点就绪后将稳定入口切至新会话。

```python
import runpy
runpy.run_path("experiments/inverse_rollback/pose_hold/run_20261126_02_f65/place.py")["place"](env, task, world, art)
```

已在同一进程完成摆位并挂起，F65 的任务计数为 3202，摆位推进 0 个物理 tick。机身位置、19 个关节的位置和速度、相机位置的读回误差均为 0，机身和相机四元数最大分量误差均为 5.96e-8。稳定动作入口已指向本次 F65 附着。仅设置历史位姿并保留现场，两组导航 SR 与平均 SPL 均暂无，已评分 0 条。

[位姿读回](../../../../outputs/inverse_rollback/pose_hold/run_20261126_02_f65/placement.json) · [现场前视图](../../../../outputs/inverse_rollback/pose_hold/run_20261126_02_f65/front.png) · [动作端点](../../../../outputs/inverse_rollback/pose_hold/run_20261126_02_f65/live/endpoint.json)
