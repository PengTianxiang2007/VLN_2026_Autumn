# DeepSeek串行恢复：人工错误集33任务

2026-11-16 用户更新：直接使用DeepSeek API开始，允许在剩余显存足够时与他人共享GPU。此指令替代Qwen27B部署计划，不再恢复Qwen队列。当前状态：11:55 UTC因模型返回容器类型不符而失败，0/33完成；原始证据保留，转新运行04。

## 样本与协议

人工标定错误集33条任务、34个历史事件、9场景；沿用`outputs/oracle_crossing/distance_v001/run_20261115_05/cohort.json`，seed2，每条从原生起点在仿真完整重跑。原单条02结果不混入。参考轨迹和标签只标明样本来源，不输入在线判定。

JEV仍调用EasyJEV实时图像接口`https://api.easyjev.online/v1/systemone`/jev-1.14.0；全部六个语义环节恢复原DeepSeek API`https://api.deepseek.com`/deepseek-flash，保留v001去重、v003偏航/进度、单目三阶段选路及v007纠错的提示词和设置。原版25000物理tick预算、局部40动作预算、多次恢复、接管前主任务记忆保存与交还恢复均不改。是否实际触发完整恢复闭环单独统计。

## GPU与生命周期

GPU3继续复用StreamVLN PID3194667/40617，不重载模型。仿真改放显存更充足的GPU2，与已有他人进程共享；保留12000MiB空闲显存准入，新增用户显式授权参数允许高GPU利用率，不再以他人计算活跃拒绝启动。不停止他人进程，不加载Qwen。

上一轮已完成仿真836845在核验归属后正常退出，由本轮新引擎替换。连续任务与场景切换遵循原版；24GiB RSS触发原生退出后继续LMDB未完成任务，不按任务重载模型。原模型及最终引擎继续遵循用户既有保留要求。后台异常只清理自己当前仿真。

## 命令与证据

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_serial_pipeline.py \
  --cohort outputs/oracle_crossing/distance_v001/run_20261115_05/cohort.json \
  --jev-endpoint https://api.easyjev.online/v1/systemone \
  --output outputs/serial_recovery/v001/run_20261116_03_full33

benchmarks/vlnverse/.venv/bin/python -u -B outputs/serial_recovery/v001/run_20261116_03_full33/code/scripts/run_serial_pipeline.py \
  --campaign outputs/serial_recovery/v001/run_20261116_03_full33 \
  --gpu 2 --model-pid 3194667 --port 40617 --allow-active-shared-gpu --keys-stdin --detach
```

凭据只从无回显终端进入主管/仿真环境，未写配置/日志/命令参数。源码、Git提交/未提交差异、提示词/配置/样本hash保存在新运行manifest及code/，不覆盖历史产物。

当前输出：`outputs/serial_recovery/v001/run_20261116_03_full33/`。status/live/chunks逐步更新；最终official_result和validation记录评分与实际恢复证据。正常启动验证后停止人工持续跟踪。

36项CPU检查通过（serial_pipeline、oracle_distance_native、oracle_existing_model），包括新授权共享忙卡仍保留显存容量检查。旧仿真836845已通过release文件正常关闭，StreamVLN3194667身份未变，证据`replaced_simulator.json`。尚无本轮正式导航评分。

## 实际启动

2026-11-16T11:32:31.885101+00:00：主管1066001、仿真1066074，GPU2共享运行，GPU3原模型3194667/40617不变。入场两次空闲33765/33165MiB、利用率80/100%；`allow_active_shared=true`。已通过配置校验并进入场景初始化，正式评分0/33，API及实际动作尚待启动检查。36项CPU检查通过，1344文件源码冻结；实际Git基线`7ce5f9fee30686bae304425bc84c36b3fbedc39c`及未提交快照见manifest。

## 启动验证通过

2026-11-16T11:42:47.090245+00:00：首条`kujiale_0257_4_3`记录11个实际动作、11次有效JEV、2次DeepSeek偏航评审，真实请求HTTP200、finish_reason=stop，未见runtime_failure。原版任务重置后模型step_id=0、pending_count=0，模型PID及启动身份不变。正式评分0/33，完整回退/选路/局部纠错/交还循环尚待后续触发，不将启动通过称为闭环通过。

证据`startup_verified.json`及`startup_gpu_snapshot.csv`。按用户要求停止人工持续跟踪，由主管继续33条并进行最终评分和证据核验。

## 最终失败记录（12:27 UTC查验）

11:55:45 UTC（北京时间19:55:45），首条kujiale_0257_4_3第50个动作后，00069_deviation在初始化新一段时返回完整JSON，但uncertainties为一个{zh,en}对象而非数组，严格校验抛出Invalid uncertainties。主管与本轮仿真已退出，GPU2本次占用已释放，原StreamVLN3194667仍按要求保留。

完成0/33，无官方任务评分。实际50个原任务动作、50次JEV、10个节点、8次去重请求；11次偏航请求包括9次节点评审、1次接管前复核、1次格式失败。9次节点评审为6 consistent、2 uncertain、1 deviated；该deviated在动作队列清空后的复核变为uncertain，所以未执行回退。实际回退/局部动作/交还均0。此结果不能计为导航成功或失败评分，也不能称恢复闭环通过。

修复仅对完整且非空的双语uncertainties对象进行单项数组包装；不修改原答文件、文字、verdict、证据或进度，不重试/重采样模型判断。离线重验全部11份已有偏航响应均通过，其中恰好1份执行包装；无新增API调用。证据`outputs/serial_recovery/v001/format_audit_20261116_01/result.json`，冻结失败答作为测试fixture。缺失翻译、非法结论等仍严格拒绝。

后续：[运行04](../run_20261116_04_full33/README.md)，仍33任务/34事件，同协议新建完整运行，保留03的全部失败记录。
