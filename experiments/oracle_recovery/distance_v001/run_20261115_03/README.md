# 自动距离 Oracle：常驻模型与同场景批量运行03

日期：2026-11-15。最新状态：用户明确要求采用原版复现机制，当前自定义批次方案已停止。接到指令时首批3条在途，已完成该批并正常退出；3条新增完整结果保留，加02的17条共20条。后续由[原版运行04](../run_20261115_04/README.md)接手。以下为本轮历史方案，不再执行。

## 目的与授权

用户要求避免逐任务重新加载模型和仿真，改为任务之间完整重置状态。
运行02已在无子进程、waiting_for_resources边界停止，完整17条early结果保留；本轮验证源manifest、协议和完成哈希后引用，不覆盖或重跑。
原33任务/34事件、seed2、0.75/1.5/3/4米四档与checkpoint组保持不变。总计165任务，预计新跑148任务。

## 实现与限制

- 一个StreamVLN服务贯穿队列；每个任务调用原生带episode seed的reset，审计历史观测、动作队列、KV缓存和model cache均为空。
- 同组同场景组成一批，每批最多8条；同一仿真进程连续处理任务，32GiB RSS边界可正常退出并继续未完成任务，模型保留。
- 原生task reset重新创建机器人、控制器、传感器、DoneChecker、评分器及种子；仍进行原生500tick热身。只保留无动态刚体的静态场景USD节点；场景资产/位姿/缩放不同或包含动态刚体时使用原生重新加载。
- 各批次共用本轮专属仿真缓存。跨场景启动新仿真；不编辑共享环境。针对安装后端的四个源码文件记录哈希并在运行时核验。
- 四档瞬移内保留干预时记忆，checkpoint组实际存档恢复；任务间清空与任务内干预分开处理。
- 初始物理状态与评分协议保持原生；进程/场景复用改变执行生命周期，不承诺跨运行逐帧或物理轨迹位级一致。17条旧结果与本轮结果记录各自来源。
- 仍逐条真实导航，没有离线替代、动作截断或新增对照组。批次异常保留产物并退出，不自动重放失败任务。

## 版本、验证和命令

基线7ce5f9f加未提交源码，准备工具冻结实际源码/差异/配置。旧12项Oracle检查和新6项批量检查共18项通过；StreamVLN环境检查通过，结果保存在本轮`validation/`。另核对旧17条真实初始记录，均为physics_ticks=1、action_index=0，与新增重置检查一致。GPU多任务复用尚待验证。

```bash
python3 -B scripts/prepare_oracle_distance.py --output outputs/oracle_crossing/distance_v001/run_20261115_03
python3 -B scripts/run_oracle_distance_batch.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_03 --reuse-from outputs/oracle_crossing/distance_v001/run_20261115_02
# 实际后台启动使用03的冻结入口。
python3 -u -B outputs/oracle_crossing/distance_v001/run_20261115_03/code/scripts/run_oracle_distance_batch.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_03 --reuse-from outputs/oracle_crossing/distance_v001/run_20261115_02 --gpu 2 --sim-gpu 3 --execute
```

启动前自动检查所有GPU与主存，只选择空闲卡，不停止他人任务。没有可用卡时等待最多24小时；运行完成/异常清理本轮模型、仿真并记录GPU释放情况。

实际启动：2026-11-15 12:58 UTC前，tmux会话`oracle_distance_20261115_03`，主管PID3066523；命令与上方冻结入口一致，stdout/stderr写`supervisor.log`。17条继承/148条待跑/40批计划已核验。首批early、kujiale_0232，包含`kujiale_0232_2_4`、`kujiale_0232_68_1`、`kujiale_0232_72_1`。目前四卡均有其他任务：0/1为chenziyuan训练，2为chenziyuan评测，3为huangyinuo的SAM3服务；未操作这些进程，当前simulation_started=false。

## 产物与下一步

输出根：`outputs/oracle_crossing/distance_v001/run_20261115_03/`。
`inherited_results.json`记录17条来源和哈希，`batch_plan.json`记录新任务分组，`execution_options.json`保存实际生命周期配置。
每条保存`batch_reset_proof.json`、纠正与观测记录；每批官方导出与Oracle逐条评分交叉核验完成才写`.complete.json`。
`first_batch_verified.json`仅在批次评分通过、至少两条共用仿真PID且发生静态场景复用后生成。
下一步：核验第一批完整导航、记忆重置、场景保留、评分和耗时；正常后停止人工持续跟踪。

最终交接：status为stopped_at_batch_boundary、无异常；本轮新增`kujiale_0232_2_4`、`kujiale_0232_68_1`、`kujiale_0232_72_1`共3条，通过官方导出和Oracle评分交叉核验。`stop_after_batch`与`handover_request.json`记录切换请求，owned_processes为stopped。本轮模型PID3071837、仿真PID3072349已退出。该批次划分和场景缓存是助手新增的实现，用户随后明确否决，当前源码已撤除，不归为原版行为。
