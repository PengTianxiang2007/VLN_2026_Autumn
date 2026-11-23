# 实际存档回退后自主续走：运行06

2026-11-16 12:59 UTC：已按原Oracle模板发布33条完整回放：[打开网页](http://134.175.18.101/vln/oracle_checkpoint_33_run06_web_20261116_01/oracle_checkpoint_33.html)。原始/参考/本次轨迹、真实存档点、25次回退前后画面与存档记忆证据、双进度条及中英文均通过检查；详见[导出登记](exports/checkpoint_20261116_01/README.md)。

2026-11-16 00:10 UTC检查：已于北京时间11月16日02:05完成33/33，官方成功6/33（18.18%）、SPL16.06%、NE6.0655m。25条触发各一次回退，8条未触发。validation.json通过，3954条模型轨迹记录核验。随后按队列切换到07；旧仿真已退出，原模型仍保留。

2026-11-15 16:59 UTC：resume_20261115_02启动验证通过，正式评分已从9增至10/33。第10条`kujiale_0234_34_4`完成真实导航和评分；原版任务重置时模型历史/动作队列清空，9条旧结果哈希不变。主管3518096、仿真3518229继续后台运行，GPU3原模型PID3194667未重载。证据`resumes/resume_20261115_02/startup_verified.json`。07等待器3518738正常等待06全33条评分及导出后接续。停止人工持续跟踪；实验阈值、回退规则、原版场景与RSS生命周期均未改变。

2026-11-15 16:52 UTC：resume_20261115_02已实际启动，主管3518096、仿真3518229，从9/33继续；模型3194667仍在GPU3/40617，未重载。9条结果SHA256核验不变。07等待器3518738为waiting_for_checkpoint_group；只有06完整导出后才接续。当前仿真初始化中，首条新导航验证待完成。

2026-11-15 16:50 UTC：第一次续跑完成第9条`kujiale_0234_63_3`，官方计数已为9/33、成功0/9；本次轨迹未达到触发条件，未回退，不能称原朝向失败已在相同前缀通过。随后主管轮询碰到原版ResultLogger原位重写JSON的短暂空文件，JSONDecodeError导致仿真退出；9条正式评分与原模型均保留。已在独立`resumes/resume_20261115_02/`修复：读到未写完的JSON时沿用最后完整计数，下次重新读；最终完成仍要求完整评分/仿真保留标记和独立导出验证。9项相关测试通过（此前全套27项通过），实验协议不变，仿真缓存继续使用原代码目录的原缓存。从第10条续跑，后续07新计划为queue_plan_resume_20261115_02.json。

2026-11-15 16:39 UTC：已实际启动断点续跑，主管PID3506858、仿真PID3506983；模型保持PID3194667/GPU3/40617，未重载。启动时正式评分8/33，8条既有结果SHA256全部一致。仿真正在初始化，尚未确认第9条恢复通过；维护版本在`resumes/resume_20261115_01/`，tmux `oracle_checkpoint_resume_20261115_01`。后续07等待器PID3507365，tmux `oracle_extra05_resume_20261115_01`，状态为waiting_for_checkpoint_group。

2026-11-15 16:35 UTC：用户要求继续推进。已修复已有模型启动入口的断点续跑和原版按进度重试逻辑：同一LMDB跳过已评分8条；仿真异常退出允许重试，连续三次无新增评分则停止并保留模型。策略存档RPC键按attempt独立，避免第9条重试时撞上旧存档；旧失败现场不覆盖。检测0.75米、一次实际回退、50tick稳定、15°/0.35米校验、seed和评分均未改变。27项CPU检查通过，独立维护快照及实际命令位于`outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint/resumes/resume_20261115_01/`，原manifest与原code不变；8条结果SHA256已保存。准备复用GPU3模型3194667/40617仅重启仿真，07队列使用`queue_plan_resume_20261115_01.json`。当前尚未把修复视为实际恢复成功。

2026-11-15 16:23 UTC检查：运行已异常中断，官方完成8/33、成功0/8，8条均完成一次回退；终止原因为未到目标6、跌倒1、卡住1。第9条`kujiale_0234_63_3`在动作92触发回退，50tick稳定后朝向偏差17.596202°，超过既有15°恢复校验上限，`OracleCrossing.teleport`抛出RuntimeError；之后Isaac卸载时出现segmentation fault。主要中断原因是恢复校验失败，不是模型退出。仿真PID3230947已退出，原模型3194667仍在GPU3（约27336MiB）；没有修改容差、跳过任务或重跑。原始8条结果保留，异常记录在`failure_diagnosis_20261115_1623.json`。07队列因前置组未完成已停止等待执行，尚未启动。下方16:03为历史启动验证记录。

2026-11-15 16:03 UTC，状态：正常运行，已完成首条正式评分1/33，第二条已导航。首条`kujiale_0257_4_3`已完成真实存档、一次实际回退、策略恢复和回退后的自主续走；恢复证明及原版评分通过，详见`first_checkpoint_verified.json`。这里“通过”指执行与恢复链路，具体导航成败以原始metrics为准。主管PID3230841、仿真PID3230947，继续复用GPU3模型PID3194667及端口40617，未重载模型。原版完整评估循环及任务重置不变，24项针对性CPU检查通过；按用户要求结束持续人工跟踪，由后台续跑。

## 已执行与保留

运行05的short在19条官方评分时停止推进，结果保留；early的33条已完成，medium/long未启动。旧launcher PID3145989和仿真PID3195886已SIGSTOP，内存/显存保留。模型PID3194667保留并恢复响应，端口40617，GPU3；只读`/oracle/state`核验可响应。旧队列写入`stop_after_arm`，禁止再次推进距离组；当前变更记录在05的`checkpoint_handover_20261115_01/`。

## 准备的回退协议

同33任务/34事件，seed 2，偏离正确参考路线0.75米后检测；每个事件首次在距人工分叉点1米内、距参考线不足0.75米且动作队列为空时保存实际状态。仅在存在该事件真实存档时回退，恢复存档位置/朝向、策略记忆、RNG及预算，采用既有50tick稳定流程，每条任务最多一次回退。之后完全由StreamVLN自主续走，不提供正确分支动作、不修正到参考路线落点、不反复纠正。无存档或未触发时保留自然结果。

新路径：`outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint/`。最终执行版本保存在本轮`code/`：复用05不可变源码文件，新增已有模型复用入口与按用户要求的完成后保留钩子；未修改05源码。新manifest只允许checkpoint，旧距离组不在清单中。初始准备状态保留在`prepared_before_execution/`；实际manifest/seal记录1322份源码哈希，基线仍为7ce5f9f加记录的未提交差异。原版run_full字节不变，原版eval只安装Oracle钩子；本轮通过原版run_eval.sh直接连接已有模型，不启动新的模型服务。

模型服务保持原PID、端口和代码快照，因此其追加动作日志和策略存档仍写入05的原服务目录；本轮`borrowed_model.json`记录精确日志起始偏移，完成后提取本轮动作切片交给官方导出核验。策略存档真实路径也由restore证明记录，不把旧目录中的追加文件冒充旧实验结果。

## 当前切换限制

原版仿真在初始化时绑定数据、评分目录和任务配置，Oracle条件从启动环境变量读取，现有进程未提供热换组入口；原版run_full结束时还会同时清理模型和仿真。因此没有直接执行原版完整launcher或关闭现有环境。

用户已回复“是”，允许只重启仿真。旧主管/launcher的finally会无条件清理模型，因此核验PID/启动时间后仅结束这两个主管的精确PID，再退出旧仿真，模型未关闭。完整记录在05的`checkpoint_handover_20261115_01/simulator_replaced_model_retained.json`。

实际命令保存于`execution_command.json`，tmux会话`oracle_checkpoint_20261115_06`：

```bash
python3 -u -B outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint/code/scripts/run_oracle_existing_model.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint --arm checkpoint --run-id peng_fine_distance_checkpoint_20261115_06 --gpu 3 --model-pid 3194667 --port 40617 --model-trace outputs/oracle_crossing/distance_v001/run_20261115_05/runs/vlnverse/streamvln/results/peng_fine_distance_native_166c2cb6c4_short/chunk_1794755945472217903/agent_trace.jsonl
```

原版24000MiB主存预算导致的仿真重启/LMDB续跑保留，仅模型始终常驻；不设置固定任务批次、不改scene缓存。完成全部33条评分后保留仿真，先导出/核验结果，再由明确授权的下一组调度器释放该已完成仿真并接续07。最后一组结束后模型与最后仿真继续保留。异常时停止本轮仿真并保留模型，不自动重跑取消的距离组。

下一步：首条实际存档、回退和自主续走已经验证，停止人工持续跟踪；[额外前移0.5米组](../run_20261115_07_early_plus05/README.md)已按用户选择排队，06完整33条导出验证后自动接续。
