# 104条历史选路错误任务：逐步180° / 360°及真实位姿采集

状态：准备中。用户2026-11-17明确授权开始执行；优先复用保留模型与环境，确认正常后交后台，不持续人工跟踪。

## 目的、范围与协议

早期seed2 Crossing错选归因48条，加运行04原版route_choice全56条，共104个不同episode；不使用人工33条集筛选。seed=2，按官方split顺序运行，原始指令/初始位姿/逐任务种子不变。原版StreamVLN自主导航，无Oracle或外部Agent干预；新轨迹和成功/失败均保存，不要求复现旧失败。

每个原生导航动作前保存一个观测，包含初始状态，终止前再保存一个真实末态；N动作对应N+1个观测。队列里的动作逐个采集，不只在模型生成新动作序列时采集。预热失败保存零动作终止状态。

每观测在真实原生相机光心渲染8张640×480无损PNG，水平视场90°，相对当步机器人朝向0/45/90/135/180/225/270/315°，正角为左转。机器人朝向来自真实根位姿，原生相机光轴偏差单独记录；保留实际相机俯仰/滚转，绕世界Z旋转。180目录以左前/正前/右前顺序硬链接8张中的45/0/315°图；360目录保存全8张。两套为重叠透视图组，未拼成单张全景。

每step记录机器人和原生/取景相机XYZ、wxyz四元数、Euler角、水平heading、光轴、内参、动作、step、物理tick、仿真时间/步、环境偏移、图像SHA256。同时保存原生前视RGB；StreamVLN仍只接收原生前视输入。采集前后逐步验证物理tick/仿真时间、机器人位姿、关节位置/速度和原生相机位姿不变；多视角渲染delta_time=0，不新增转头/移动动作。采集错误停报，不以旧图补缺。

## 环境、版本与启动

GPU3保留模型PID3194667、端口40617继续使用，不重新加载；原GPU2仿真PID1977525已完成并仅等待释放，无新任务接收能力，因此通过原release标记正常结束后复用同一环境重新启动仿真。仅操作已核验本项目PID；GPU2他人任务不变，不增加并发worker。保留既有.venv、Isaac45、模型资产；最终继续保留模型和最后仿真。

复用原生连续评测、任务重置、25000 tick预算、500 warmup、停止/跌倒/卡住评分及24GiB RSS边界重启。新增记录钩子仅注入本次冻结源码，原run_full.py字节不变。实际Git、未提交差异和源码SHA256保存在输出manifest、git_diff.patch及code/。

准备命令：`benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_step_multiview.py --output outputs/multiview_capture/v001/run_20261117_01`。
完整后台启动命令将记录在输出launch_plan.json；入口`scripts/run_step_multiview.py`复用`scripts/run_oracle_existing_model.py`的已加载模型启动流程。

## 产物与检查

输出：`outputs/multiview_capture/v001/run_20261117_01/`。manifest/cohort/episode_ids冻结清单；capture/episodes/<id>/attempt_*/steps/<step>/{180,360}/与metadata.json；steps.jsonl为逐步总索引。status.json为原生评分进度，capture/progress.json为逐步采集进度。最终自动导出原生成绩并检查104条图像/位姿完整性，结果capture_validation.json；失败见capture_failure.json及日志。

当前仅CPU开发验证，尚未开始新导航。历史结果和人工标注均不修改。未生成新HTML。


实际后台启动：主管PID 2342111，GPU2仿真/GPU3原模型3194667，模型未重载。15项CPU测试与环境检查通过，冻结1329个文件、104任务/21场景。完整命令：

```
/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/benchmarks/vlnverse/.venv/bin/python -B /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/multiview_capture/v001/run_20261117_01/code/scripts/run_oracle_existing_model.py --campaign /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/multiview_capture/v001/run_20261117_01 --arm baseline --run-id peng_fine_multiview104_20261117_01 --gpu 2 --model-gpu 3 --model-pid 3194667 --port 40617 --model-trace /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/oracle_crossing/distance_v001/run_20261115_05/runs/vlnverse/streamvln/results/peng_fine_distance_native_166c2cb6c4_short/chunk_1794755945472217903/agent_trace.jsonl
```

当前等待真实导航与采集验证。


2026-11-17T09:13:18.893749+00:00 后台收尾：状态 `failed`，正式评分 0/104；异常：RuntimeError('Per-step capture failed; see capture_failure.json')。原模型保持加载，进程与结果以输出status.json为准。


2026-11-17T09:17:13.276140+00:00 故障定位：首步第2个视角被Stale capture rendering frame保护拒绝，原生动作0、评分0/104。Isaac Camera默认按照仿真时间限频，冻结时间时get_current_frame的帧元数据不更新。修复为frequency=-1，每个渲染帧更新，并最多等待3次render-only完成；绝不推进物理时间来规避检查。原仿真已退出/GPU释放，模型3194667保留。运行02新目录重新冻结，不覆盖本轮。
