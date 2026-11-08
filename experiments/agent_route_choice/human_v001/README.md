# 人工标注数据：无全景 v001 恢复选路

2026-11-06：用户要求保留[上午提示词基准](../v001/prompts/frozen_morning_20261106/README.md)，计划针对晚间情况优化；新方向另记 [human_v002](../human_v002/README.md)，本版34点输入和原始结果继续保留。

2026-11-06：用户明确要求沿用上午已完成十条的无全景离线版本，替换为其手工标注数据，使用本地Qwen27B。已授权开始；本轮不做HTML，确认正常运行后交给后台，不持续人工盯进程。

- [首批34个错误点](run_20261106_01/README.md)：准备与运行记录。
- 输入来自人工数据集61条中的34个错误选择点（33条轨迹）。94个普通Crossing不构造虚假的错误经历。
- 上午v001的英文prompt、两次调用、最多4+4张RGB、完整清单传递、只排除错误支路及本地校验保持一致。核心源码及提示词与上午冻结版本一致。
- 本实验条件是人工提供Crossing与错误事件；不评估检测、自主识错触发、物理复位或最终导航SR。语义选路正确率待独立复核，不把协议通过率当作正确率。

公共实现：`scripts/prepare_human_route_choice.py`、`scripts/run_human_route_choice.py`，复用`core/agent_route_choice.py`与上午`run_case`。原十条及其他实验不覆盖。


2026-11-06T14:49:26.196528+00:00：用户已明确授权共享GPU0，后台主管已启动（PID 44492），单卡单并发，本轮不生成HTML。三次资源准入后加载Qwen27B；确认有效双调用后停止人工持续跟踪。实际状态见 outputs/agent_route_choice/human_v001/run_20261106_01/qwen27b/status.json。


2026-11-06T15:03:14.061403+00:00 启动核验完成：Qwen27B在共享GPU0正常提供服务，首条两次完整响应已保存，finish_reason=stop、网络错误0，实际请求哈希与第二次完整传递第一次JSON核验通过。首例模型弃答且route_description为空，原v001校验拒绝，作为协议无效保留；未修改冻结校验或模型答案，后续样本继续。当前处理进度见status.json；按用户要求停止人工持续跟踪，后台完成34点后自动审计、保存结果、释放服务，本轮不生成HTML。


2026-11-06T15:12:04.148979+00:00：GLM-5.3-Flash人工34点无全景批次已获授权并完成准备，复用Qwen同一输入和v001英文prompt，low思考、最多10个独立worker；4项凭据传输CPU检查通过。密钥仅经stdin进入进程内存，本轮无HTML。记录 experiments/agent_route_choice/human_v001/run_20261106_02/README.md。


2026-11-06T15:12:48.814078+00:00 GLM-5.3-Flash人工34点无全景批次收尾：`blocked_account`，保存0/68次回答，协议有效0/34。worker全部退出True，凭据未落盘True，本轮无HTML；语义正确率待复核。结果 `outputs/agent_route_choice/human_v001/run_20261106_02/glm`。


2026-11-06T15:14:24.003697+00:00 账户阻塞已核验：首个GLM请求返回HTTP429 / code1113“余额不足或无可用资源包，请充值。”仅1次请求、0次模型回答，未展开10进程队列；主管及首个worker已退出。凭据只经无回显stdin与匿名管道进入内存，运行文本扫描未发现凭据，未生成HTML。等待用户充值或替换有额度的key，不自动反复请求；本地Qwen继续。


2026-11-06T15:21:16.872308+00:00 人工标注无全景选路自动收尾：状态 `complete_with_invalid_samples`，处理 34/34 个点，保存 65/68 次回答，协议有效 7/34；语义正确率待复核。本轮按用户要求不生成HTML，GPU释放 True。结果 `outputs/agent_route_choice/human_v001/run_20261106_01/qwen27b`。


2026-11-06：用户追加要求的手工标注 Qwen27B 离线可视化已完成。34例，主视图与俯视地图双进度条同步，展示模型识别/排除/选择、原始回答、失败状态与复核导出；34例及131个关键帧浏览器验证通过，零外部请求，未重跑模型。HTML：`outputs/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/human_qwen27b_review.html`（约116 MiB）。记录：`experiments/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/README.md`。
