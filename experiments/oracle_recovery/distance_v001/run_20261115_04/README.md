# 自动距离 Oracle：恢复原版复现生命周期04

日期：2026-11-15。最新状态：用户明确要求改用GPU3，本轮已停止并保留日志，由[GPU3运行05](../run_20261115_05/README.md)接手。04在GPU2完成模型加载并启动仿真，但切换时无新增官方评分；旧20条结果保留。以下为历史启动记录。

## 用户要求与范围

用户明确要求“采用原版的，严禁擅作主张”。本轮直接使用仓库原版`benchmarks/vlnverse/runner/run_full.py`和原生`VlnPeEvaluator.eval`循环。
取消先前新增的逐任务启动、同场景固定批次、每批最多8条、32GiB自定义预算、静态场景缓存和常驻模型独立主管。
原版入口逐字保存；评测器仅在eval开头安装距离Oracle钩子，其余源码逐字一致。

样本、seed2、0.75/1.5/3/4米四档、checkpoint组及实际仿真协议均不变。
运行02完成17条；运行03在接到新指令时已有3条在途，已设置完成该批即退出，最终3条完成且评分核验通过。
两轮20条完成结果按manifest/配置/结果哈希引用保留，剩余145条：early13条，其余四组各33条。
03已停止并释放模型/仿真，不恢复其自定义批次方案。不同生命周期下的历史结果保留各自来源，不宣称轨迹位级一致。

## 原版机制与接入方式

- 每个实验条件调用一次原版入口，传入该条件全部剩余episode ID，跨场景由原生环境reset处理。
- 原版任务种子、模型记忆重置、热身、动作队列、物理预算、终止、评分、场景创建/清理、重启与断点续跑机制全部保留。
- 不传`--rss-budget-mib`覆盖值；采用原版入口默认24000MiB。原版达到预算后在任务边界退出，原版launcher重启模型和仿真并从LMDB继续。
- Oracle钩子只在原生模型reset后创建本条Oracle状态、动作前检查距离并纠正、动作后计数、终止时记录结果；纠正过程中自然终止时直接交给原生评分，不额外生成动作。
- 原版正常task reset后记录`native_reset_proof.json`，核验记忆与seed；原生评分/reset返回后记录`native_scoring_complete.json`。
- 无场景缓存monkey patch、无替代eval循环、无固定条数重启。历史03冻结源码保留，相关自定义实现已从当前公共源码移除。

## 版本、测试与命令

基线7ce5f9f加本轮未提交差异，全部执行源码由prepare冻结。18项CPU检查通过，包括原版launcher逐字相等、移除两行钩子安装后整个原版评测器逐字相等、跨场景同一条件不拆分、暖机和模型记忆隔离、纠正时终止不额外执行动作。

环境检查通过，来源/数据/权重元数据见输出`validation/streamvln_environment.json`。原版launcher冻结前后哈希相同，记录于`validation/cpu_summary.json`。计划验证为20条继承、145条剩余、5次原版条件入口调用（early13，其余各33）。

```bash
python3 -B scripts/prepare_oracle_distance.py --output outputs/oracle_crossing/distance_v001/run_20261115_04
python3 -B scripts/run_oracle_distance.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_04 --reuse-from outputs/oracle_crossing/distance_v001/run_20261115_02 --reuse-from outputs/oracle_crossing/distance_v001/run_20261115_03
python3 -u -B outputs/oracle_crossing/distance_v001/run_20261115_04/code/scripts/run_oracle_distance.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_04 --reuse-from outputs/oracle_crossing/distance_v001/run_20261115_02 --reuse-from outputs/oracle_crossing/distance_v001/run_20261115_03 --gpu 2 --sim-gpu 3 --auto-gpu --execute
```

主管只负责实验条件排队、首次资源准入、结果引用及核验；原版launcher负责模型/仿真生命周期。启动前检查所有GPU并核对归属，不停止他人任务。

## 产物、状态和下一步

输出：`outputs/oracle_crossing/distance_v001/run_20261115_04/`。
`inherited_results.json`记录20条来源；`arm_plan.json`记录5次原版启动及其145条任务。
状态区分当前条件已写官方评分的数量与整条件导出验证完成数；每条件完成原版官方导出并与Oracle结果核验后写`.complete.json`。
`first_native_continuation_verified.json`表示至少两条任务在同一仿真进程完成原生评分，明确标注整条件导出仍可能待完成。
实际启动命令为上方冻结入口，tmux会话`oracle_distance_20261115_04`，主管PID3091732；日志`supervisor.log`。13:29 UTC状态为waiting_for_resources，四卡均有其他任务，无启动异常。空闲后自动由原版入口开始；等待不占GPU。实际GPU验证结果待补，不能将CPU检查/队列等待表述为新版仿真已通过；正常运行后按用户要求停止持续人工跟踪。

GPU切换记录：`gpu3_handover.json`保存用户指定GPU3的原因、原版官方Count=0及经核验的主管/launcher/model/evaluator PID。向主管3091732发送SIGTERM，由原版launcher清理3092258/3092277/3092923，不停止其他用户进程。新运行05显式使用GPU3与原版共享参数。
