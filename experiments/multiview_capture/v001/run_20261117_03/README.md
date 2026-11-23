# 104条历史选路错误任务：逐步180° / 360°及真实位姿采集

状态：运行中（运行03），真实启动验证通过，104条继续后台执行。用户2026-11-17明确授权开始执行；复用保留模型与环境，确认正常后不持续人工跟踪。此处不是全104条完成声明，最新评分进度以输出status.json为准。

## 目的、范围与协议

早期seed2 Crossing错选归因48条，加运行04原版route_choice全56条，共104个不同episode；不使用人工33条集筛选。seed=2，按官方split顺序运行，原始指令/初始位姿/逐任务种子不变。原版StreamVLN自主导航，无Oracle或外部Agent干预；新轨迹和成功/失败均保存，不要求复现旧失败。

每个原生导航动作前保存一个观测，包含初始状态，终止前再保存一个真实末态；N动作对应N+1个观测。队列里的动作逐个采集，不只在模型生成新动作序列时采集。预热失败保存零动作终止状态。

每观测在真实原生相机光心渲染8张640×480无损PNG，水平视场90°，相对当步机器人朝向0/45/90/135/180/225/270/315°，正角为左转。机器人朝向来自真实根位姿，原生相机光轴偏差单独记录；保留实际相机俯仰/滚转，绕世界Z旋转。180目录以左前/正前/右前顺序硬链接8张中的45/0/315°图；360目录保存全8张。两套为重叠透视图组，未拼成单张全景。

每step记录机器人和原生/取景相机XYZ、wxyz四元数、Euler角、水平heading、光轴、内参、动作、step、物理tick、仿真时间/步、环境偏移、图像SHA256。同时保存原生前视RGB；StreamVLN仍只接收原生前视输入。采集前后逐步验证物理tick/仿真时间、机器人位姿、关节位置/速度和原生相机位姿不变；多视角渲染delta_time=0，不新增转头/移动动作。采集错误停报，不以旧图补缺。

## 环境、版本与启动

继续复用GPU3模型3194667、40617端口，不重载模型；GPU2仿真。原生连续循环、seed=2、500 warmup、25000 tick、24GiB RSS边界重启与评分保持。

运行01相机仿真时间限频导致首步新帧检查失败，0动作/0评分；运行02频率修复后前5步40图全部检查通过，但后向图像被H1自身头部大面积遮挡。本轮仅在辅助多视角渲染期间临时设置机器人视觉不可见，try/finally恢复原visibility后重新渲染原生相机；碰撞/物理/关节/位姿均不改变，前视原始策略输入先复制保存。每步记录auxiliary_visibility及restored验证。辅助图是“排除自身遮挡的环境观测”，原始前视图保留正常机器人外观。

采集相机frequency=-1，每个渲染帧更新；视角切换后最多等待3次render-only新帧，不推进物理时间。18项CPU检查通过；真实前5步多视角与可见性恢复已通过GPU验证。使用运行01生成的本项目Isaac cache/config/share，不新增场景缓存。

准备：`benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_step_multiview.py --output outputs/multiview_capture/v001/run_20261117_03`。
完整启动命令见输出launch_plan.json。

## 产物与运行记录

当前输出`outputs/multiview_capture/v001/run_20261117_03/`。manifest/cohort/episode_ids为104条/21场景冻结清单；Git、工作区diff和源码哈希保存在manifest及code/。capture/episodes/<id>/attempt_*/steps/<step>/{180,360}/与metadata.json；steps.jsonl为逐步总索引。status.json是评分进度，capture/progress.json是采集进度，startup_verified.json为真实启动证明。最终自动导出原生成绩及全104条采集核验；最后保留模型和仿真。

真实运行正常，已交后台，不持续人工盯进程。旧[运行01](../run_20261117_01/README.md)、[运行02](../run_20261117_02/README.md)保留。未生成HTML。


运行03实际启动：后台主管PID 2366589；18项CPU检查通过，GPU3模型3194667继续复用。完整命令：

```
/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/benchmarks/vlnverse/.venv/bin/python -B /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/multiview_capture/v001/run_20261117_03/code/scripts/run_oracle_existing_model.py --campaign /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/multiview_capture/v001/run_20261117_03 --arm baseline --run-id peng_fine_multiview104_20261117_03 --gpu 2 --model-gpu 3 --model-pid 3194667 --port 40617 --model-trace /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/oracle_crossing/distance_v001/run_20261115_05/runs/vlnverse/streamvln/results/peng_fine_distance_native_166c2cb6c4_short/chunk_1794755945472217903/agent_trace.jsonl
```

## 真实启动验证

2026-11-17前5步真实采集通过，证据见[startup_verified.json](startup_verified.json)。8方向×5步共40张PNG的尺寸、哈希、逐视角新渲染帧、实际相机朝向全部通过；180°的15张引用与对应360°图片逐字节一致。5步机器人heading依次为-74.952°、-88.123°、-102.734°、-117.165°、-131.492°，每一步均以自己的真实朝向定向。

5步采集前后物理时间、tick、根位姿、关节及原生相机位姿均保持一致；机器人外观逐步恢复通过。前2步保存的原生前视RGB与模型服务实际收到并保存的RGB逐像素相同。模型PID 3194667和启动标识未变，未重新加载；原生主管2366591、GPU2仿真2366636、外层后台主管2366589。旧完成仿真1977525通过其保留释放标记正常退出；复用原有Isaac环境。

人工查看首步原生前视、辅助0°/90°/180°/270°图：后向180°已能看到卧室环境，H1头部遮挡已消除；左侧90°面向近墙，符合所在位置，不作缺图替换。辅助图临时隐藏自身外观的处理已逐步写入metadata.json；原生输入保留。

启动核验时正式评分0/104，尚未验证完整episode的终止采集；这项与全104条N+1观测、原生评分对应检查由后台最终验证负责。检查通过后停止持续人工跟踪；发生采集错误将保存失败原因并停止本次采集，不以旧图补齐。


2026-11-18T04:27:15.269416+00:00 后台收尾：状态 `complete_services_retained`，正式评分 104/104；采集完整性通过：9891个观测、79128张多方向原图。原模型保持加载，进程与结果以输出status.json为准。
