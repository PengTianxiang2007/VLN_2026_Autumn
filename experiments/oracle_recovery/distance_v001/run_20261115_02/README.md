# 自动距离 Oracle：33任务/34事件，正式运行02

日期：2026-11-15。最新状态：用户要求改为模型/仿真批量复用，本队列完成17条early任务后，在waiting_for_resources且无子进程的边界停止；已完成结果保留，由[运行03](../run_20261115_03/README.md)按哈希引用继续剩余任务。以下为历史运行过程。

## 目的与协议

承接用户“代码完成后在GPU开始，正常后停止持续人工跟踪”的授权。
运行01仅在资源准入时退出，没有任何导航。本轮模型、样本、seed、阈值和落点全部不变；仅调度器增加等待和自动选空闲卡。
33条任务/34事件，StreamVLN，H1 physical，seed2；early/short/medium/long阈值0.75/1.5/3/4米，另checkpoint组0.75米，共165作业。
保留原生终止规则；四档瞬移保留干预时记忆、多次纠正；checkpoint恢复真实存档并只回退一次。细节见上级README。

## 版本与验证

基线7ce5f9f加本轮未提交源码，prepare保存差异/源码与配置哈希。新增12项CPU检查通过，包括忙卡不共享、单卡空闲时独立运行、资源等待不加载模型。
旧全套回归和环境检查记录沿用代码验证01；调度器改动不改变推理协议。

## 命令

```bash
python3 -B scripts/prepare_oracle_distance.py --output outputs/oracle_crossing/distance_v001/run_20261115_02
python3 -u -B scripts/run_oracle_distance.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_02 --gpu 2 --sim-gpu 3 --auto-gpu --resource-wait-hours 24 --execute
```

GPU2/3只是优先选择。每次启动重新检查所有GPU；两张空闲时分卡，只有一张空闲时模型/仿真同卡；任何有计算进程或占用≥1GiB/负载>10%的卡都不准入，不共享、不停止他人进程。
无可用卡时每30秒更新等待状态，不占用GPU；单任务资源等待上限24小时。队列只运行一个导航作业，逐条正常退出释放服务。

## 产物与状态

`outputs/oracle_crossing/distance_v001/run_20261115_02/`保存manifest/cohort/seal、code、status、supervisor.log、oracle_records、runs。
首个发生实际纠正并完成官方评分的任务写入`first_intervened_episode_verified.json`，之后后台自行推进。
首次完整任务已在本次12:37 UTC检查核验：`kujiale_0036_0_0`发生3次实际纠正，最终成功，官方评分完成；存在`first_intervened_episode_verified.json`、对应`.complete.json`和Oracle结果。下列早期记录保留当时状态。

启动记录：tmux `oracle_distance_20261115_02`，主管PID2786697；实际命令如上，已确认进程存活。
首次状态为waiting_for_resources、simulation_started=false、completed=[]，原因是没有完全空闲且至少32000MiB显存的GPU。
GPU0/1为chenziyuan训练，GPU2为panyingxie的CARLA，GPU3为chenziyuan评测；均未操作。
空闲后自动启动，最多等待24小时；本次未取得任何首条GPU导航或实际复位通过证据。

2026-11-15 08:29 UTC按用户要求检查：已离开资源等待，当前任务为early / 0.75米 / `kujiale_0036_0_0`。准入连续两次记录GPU3占用1MiB、负载0%，自动选择模型与仿真同卡；启动器PID2792969、模型服务PID2792992。模型加载约8分钟，线程诊断位于`adapter.py:31`的模型`.to()`；两分钟一次的`Timeout`是faulthandler定时栈输出，未观察到异常退出。尚无`ready.json`、evaluator进程、完成标记或`first_intervened_episode_verified.json`；`status.json`中`simulation_started=true`仅表示启动器已启动，不代表仿真已开始。

此时GPU3另有chenziyuan路径的评估进程PID2792981（在本次空闲准入后启动），并非本项目进程，未操作。没有因此重启本次加载或改变实验条件。队列继续后台运行，本次仅检查状态并同步记录，未新增实验或持续轮询。

2026-11-15 12:37 UTC按用户要求再次检查：16个完成标记与主管记录一致，均为early组；10条发生纠正，共21次。16条官方结果为9成功、2卡住、5未到终点；成功中6条触发纠正、3条未触发。未触发成功不能归因于恢复，当前是未完成组的中间统计，无新增无干预对照，不推断净收益。

当前`kujiale_0232_23_2`为第17条，模型/仿真均用GPU2；模型已ready，仿真已加载场景机器人，尚无本条Oracle记录。主管PID2786697、启动器PID3046378、模型PID3046407、仿真PID3047532存活；前16条owned_processes均记录stopped。short/medium/long/checkpoint各0/33。没有重启、追加或改变条件；确认已完成链路后继续后台推进，不持续人工跟踪。

交接记录：输出根`handover_request.json`保存停止原因、完成数量和经核验的主管命令。主管2786697已收到SIGTERM并正常清理，status为stopped，17个完成标记保留；未中断任何在途episode，也未操作其他用户进程。
