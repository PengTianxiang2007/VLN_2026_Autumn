# 104条历史选路错误任务：逐步180° / 360°及真实位姿采集

状态：准备中（运行02）。用户2026-11-17明确授权开始执行；优先复用保留模型与环境，确认正常后交后台，不持续人工跟踪。

## 目的、范围与协议

早期seed2 Crossing错选归因48条，加运行04原版route_choice全56条，共104个不同episode；不使用人工33条集筛选。seed=2，按官方split顺序运行，原始指令/初始位姿/逐任务种子不变。原版StreamVLN自主导航，无Oracle或外部Agent干预；新轨迹和成功/失败均保存，不要求复现旧失败。

每个原生导航动作前保存一个观测，包含初始状态，终止前再保存一个真实末态；N动作对应N+1个观测。队列里的动作逐个采集，不只在模型生成新动作序列时采集。预热失败保存零动作终止状态。

每观测在真实原生相机光心渲染8张640×480无损PNG，水平视场90°，相对当步机器人朝向0/45/90/135/180/225/270/315°，正角为左转。机器人朝向来自真实根位姿，原生相机光轴偏差单独记录；保留实际相机俯仰/滚转，绕世界Z旋转。180目录以左前/正前/右前顺序硬链接8张中的45/0/315°图；360目录保存全8张。两套为重叠透视图组，未拼成单张全景。

每step记录机器人和原生/取景相机XYZ、wxyz四元数、Euler角、水平heading、光轴、内参、动作、step、物理tick、仿真时间/步、环境偏移、图像SHA256。同时保存原生前视RGB；StreamVLN仍只接收原生前视输入。采集前后逐步验证物理tick/仿真时间、机器人位姿、关节位置/速度和原生相机位姿不变；多视角渲染delta_time=0，不新增转头/移动动作。采集错误停报，不以旧图补缺。

## 环境、版本与启动

继续复用GPU3模型3194667、40617端口，不重载模型；GPU2运行仿真，原生连续循环、seed=2、500 warmup、25000 tick、24GiB RSS边界重启与评分保持。运行01零动作/零评分因相机默认限频不适配冻结仿真时间而停报；其日志与未完成首帧保留。

本轮相机显式frequency=-1，在同一物理状态下更新每个渲染帧。视角切换后等待新渲染帧号，最多3次仅渲染尝试，仍不刷新则失败；保留原来的物理状态不变断言。真实效果待本轮GPU验证，CPU通过不替代真实采集。

准备：`benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_step_multiview.py --output outputs/multiview_capture/v001/run_20261117_02`。
启动完整命令见输出launch_plan.json。复用运行01已生成的本项目Isaac缓存（cache/config/share），环境、系统与其他人的缓存不改；不添加场景缓存或修改原生重启策略。

## 产物与运行记录

输出`outputs/multiview_capture/v001/run_20261117_02/`。manifest/cohort/episode_ids冻结104条/21场景；Git、工作区diff和1329源码保存在code/与manifest。capture/episodes/<id>/attempt_*/steps/<step>/{180,360}/和metadata.json，steps.jsonl逐步索引。status.json是正式评分进度，capture/progress.json是逐步采集进度；自动导出/核验全部104条，完成后保留模型与最后仿真。

当前准备中；确认真实导航和采集后结束持续人工跟踪。未生成新HTML。原轮记录[运行01](../run_20261117_01/README.md)。


运行02实际启动：后台主管PID 2354094；17项CPU检查通过，模型3194667继续复用。完整启动命令：

```
/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/benchmarks/vlnverse/.venv/bin/python -B /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/multiview_capture/v001/run_20261117_02/code/scripts/run_oracle_existing_model.py --campaign /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/multiview_capture/v001/run_20261117_02 --arm baseline --run-id peng_fine_multiview104_20261117_02 --gpu 2 --model-gpu 3 --model-pid 3194667 --port 40617 --model-trace /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/oracle_crossing/distance_v001/run_20261115_05/runs/vlnverse/streamvln/results/peng_fine_distance_native_166c2cb6c4_short/chunk_1794755945472217903/agent_trace.jsonl
```

真实导航及多视角采集待验证。


2026-11-17T09:27:21.709375+00:00 后台收尾：状态 `stopped`，正式评分 0/104；异常：KeyboardInterrupt('Stop requested; borrowed model is retained')。原模型保持加载，进程与结果以输出status.json为准。


2026-11-17T09:28:37.522258+00:00 采集质量修正：前5步40图新帧/位姿/模型原始前视一致性已通过，但人工查看发现360后向视角被H1自身头部大面积遮挡。已正常停止本轮主管与仿真（模型3194667保留），保留所有记录；运行03仅在辅助渲染时隐藏机器人外观、异常安全恢复后继续原生导航，完整重采104条。正式评分数以status.json为准；运行02不是最终交付集。
