# 人工34个错误点 / Qwen27B / 无全景双调用

更新时间：2026-11-06。状态：准备中，尚未加载模型。用户已授权执行；明确本轮不生成HTML，确认正常调用后由后台完成。

## 目的与版本

复用上午无全景v001（原十条、20次响应）流程，将决策帧替换为用户人工标注的错误选择点，检验假设返回该点后外部Agent的局部恢复选路。
上午冻结来源：`outputs/agent_route_choice/v001/preparation_20261106_04`。核心输入/schema/校验器、两份英文prompt、两次执行逻辑与流式答案读取均对照冻结源码。当前网络层比准备时增加了HTTP429退避与脱敏错误记录，不改变本地请求payload或语义重试规则。

## 样本与协议

数据集`crossing_seed2_human_v001-afb4e7868989415c`，34个wrong_choice事件、33条任务、原导航seed2。同一任务的两个错误点保留为两个事件，不能当作统计独立的两个episode。5个第0帧事件保留一张真实当前图，无虚构来路历史。名单和事件UUID保存于cohort.json。

Crossing帧严格使用人工标注，不吸附旧C点、不改成旧归因帧。错误片段端点沿用上午来源中`short_segment(length=1.2)`规则：从该帧沿实际水平轨迹累计到1.2m的记录索引，或可用记录结束；选择其前最后真实RGB。该端点来自固定输入准备规则，不根据模型回答或最终成功调整。不是保证每例错误已经在这1.2m内充分可见；视觉不足允许模型弃答。

第一轮从当前及最近16个真实观测均匀选最多4张，附此前最多32个已执行动作，不给任务或后来错误经历。第二轮同样上下文加最多4张后续错误经历、其间已执行动作、原英文指令、同一模型第一次完整实际JSON。方向锚定原决策帧；只排除识别到的错误支路，不加入全景版强制来路双排除。地图、坐标、参考路线、人工结论均不进入请求；轨迹位置只在离线确定错误片段长度时使用。

原人工页面显示的WebP解码后以PNG无损保存，逐像素一致性核验，满足原v001的image/png编码；不重新抽取不同原视频帧。第一轮无效时不伪造清单，也不执行第二轮；失败留在34点总账，继续余下点。最多68个逻辑请求，不做语义修复或第三轮推理。

## 模型与资源

本地`Resource_Peng/models/Qwen3.8-27B-FP8`，实际config架构`Qwen3_5ForConditionalGeneration`；复用`.runtime/crossing_vllm27`环境，离线加载。TP1、单并发、BF16计算+原生FP8权重、温度0、关闭思考、32K上下文、最多8图、输出8192、请求seed基数20261106（沿用sample/stage哈希派生）。沿用v001 JSON object模式及本地严格校验，不换成v002 schema解码。

请求读取超时120秒、总deadline600秒、最多2次网络尝试；整批推理上限6小时。显存利用率0.75为单请求留足余量，主存至少64GiB。所有卡在启动前检查，选定卡连续检查三次；默认只准入空卡。若用户明确同意共享，允许低负载且为其他任务保留至少4GiB额外空余后再准入；不得停止他人进程。服务端口动态分配，正常/异常/取消均按PID、启动时间和session清理自己的进程。

## 准备与启动

```bash
backbone/streamvln/.venv/bin/python -B scripts/prepare_human_route_choice.py --output outputs/agent_route_choice/human_v001/preparation_20261106_01
python3 -B scripts/run_human_route_choice.py --prepared outputs/agent_route_choice/human_v001/preparation_20261106_01 --output outputs/agent_route_choice/human_v001/run_20261106_01/qwen27b --registration experiments/agent_route_choice/human_v001/run_20261106_01/registration.json --gpu GPU_ID
```

GPU_ID在资源核验后填写；共享参数只有获得明确授权才使用。准备与运行均保留实际Git提交、未提交差异及源码快照，旧结果不覆盖。

## 验证与交付

7项新增CPU输入边界/GPU准入检查、27项既有v001协议检查已通过。实际准备完成后另核验34点、输入图像哈希、PNG像素、因果动作及prompt一致性。前一条有效双调用产生后重建实际请求哈希，并保存`startup_verified.json`；核验后停止人工持续跟踪。

后台保存`status.json`、逐点两次原始请求/响应、有效答案、失败原因、`request_audit.json`、`summary.json`及待复核表，自动更新本README和总索引并释放GPU。HTML不生成，完成状态不以HTML为条件。

人工标注目前仅含Crossing及错选事件，不含正确分叉身份；本轮完成数、选择数、弃答数和协议无效数分别报告，语义正确率保持待复核。结果产生前不宣称改善。启动与最终状态追加于下。


2026-11-06：人工标注无全景v001恢复选路已授权并完成准备，34个错误点/33条轨迹、最多68次调用，本地Qwen27B；7项新增及27项既有CPU检查通过。按用户要求本轮不生成HTML，确认正常启动后后台运行并自动释放GPU。当前无完全空闲GPU，GPU0低负载且有他人进程，等待共享资源选择。记录：experiments/agent_route_choice/human_v001/run_20261106_01/README.md。


2026-11-06T14:49:26.196528+00:00：用户已明确授权共享GPU0，后台主管已启动（PID 44492），单卡单并发，本轮不生成HTML。三次资源准入后加载Qwen27B；确认有效双调用后停止人工持续跟踪。实际状态见 outputs/agent_route_choice/human_v001/run_20261106_01/qwen27b/status.json。


2026-11-06T15:03:14.061403+00:00 启动核验完成：Qwen27B在共享GPU0正常提供服务，首条两次完整响应已保存，finish_reason=stop、网络错误0，实际请求哈希与第二次完整传递第一次JSON核验通过。首例模型弃答且route_description为空，原v001校验拒绝，作为协议无效保留；未修改冻结校验或模型答案，后续样本继续。当前处理进度见status.json；按用户要求停止人工持续跟踪，后台完成34点后自动审计、保存结果、释放服务，本轮不生成HTML。


2026-11-06T15:21:16.872308+00:00 人工标注无全景选路自动收尾：状态 `complete_with_invalid_samples`，处理 34/34 个点，保存 65/68 次回答，协议有效 7/34；语义正确率待复核。本轮按用户要求不生成HTML，GPU释放 True。结果 `outputs/agent_route_choice/human_v001/run_20261106_01/qwen27b`。


2026-11-06：用户追加要求的手工标注 Qwen27B 离线可视化已完成。34例，主视图与俯视地图双进度条同步，展示模型识别/排除/选择、原始回答、失败状态与复核导出；34例及131个关键帧浏览器验证通过，零外部请求，未重跑模型。HTML：`outputs/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/human_qwen27b_review.html`（约116 MiB）。记录：`experiments/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/README.md`。
