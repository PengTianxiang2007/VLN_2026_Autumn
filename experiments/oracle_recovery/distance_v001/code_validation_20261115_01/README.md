# 自动距离 Oracle 代码验证 01

日期：2026-11-15。状态：完成；仅 CPU，不运行导航。

- 目的：验证距离判据、固定落点、动作队列等待、重复纠正、实际存档回退以及33任务/34事件清单。
- 基线：`7ce5f9f`，本轮新增未提交代码；准备工具保存实际 HEAD、工作区差异和完整源码哈希。
- 样本：原人工集全部34个 wrong_choice 标注，归并33条独立任务；seed=2。
- 默认阈值：0.75/1.5/3/4米，正确参考线前移0.75米为落点；checkpoint组阈值0.75米。
- 输出：`outputs/oracle_crossing/distance_v001/code_validation_20261115_01/`。
- 验证命令：`backbone/streamvln/.venv/bin/python -B -m unittest discover -s tests -p 'test_oracle_distance.py' -v`。
- 该目录中的代码冻结和计划打印不代表任何 GPU 导航成功或实际纠正效果。

结果：10项新增检查通过；冻结33任务/34事件与1319个源码文件，默认计划165个作业，simulation_started=false。
后续又增加落点恰在折点时使用出向朝向、官方参考路线一致性核验、失败后GPU占用记录；正式运行另建run_20261115_01，未改写此历史快照。

全套回归与环境验证见上级README。默认unittest discovery遇到旧test_fall_retries同名导入冲突，使用逐文件隔离导入后执行182项；JEV Python版本限制和仿真专属依赖分别在相应已有环境补验通过。
本次未执行真实位姿设置、模型推理或导航，因此不构成 GPU 通过证明。
