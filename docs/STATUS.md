# 当前项目状态

2026-11-12：[偏航与累计语义进度 v003 方法及接手](DEVIATION_PROGRESS_V003.md)已冻结在 `codex/jev-online-sampling-v001` 分支；包含34案例原始结果、提示词、运行脚本与本地网页源码，记录no31提前误报限制。本次仅归档，无新增模型调用。

2026-11-12：[全部34个案例](../experiments/deviation_progress/v003/run_20261112_05/README.md)已完成：补跑22条，新请求74次、有效73次，12条的40次记录原样复用；六进程、本地网页。

2026-11-12：[十二条轨迹补齐](../experiments/deviation_progress/v003/run_20261112_04/README.md)已完成：仅补跑六条，新请求17次、有效16次，其余六条的23次记录原样复用；本地网页合并展示。

2026-11-12：[终止节点评审 v003](../experiments/deviation_progress/v003/run_20261112_03/README.md)已完成：26个有效节点（含6个终止节点），23次请求、17次有效、6次偏航判定，DeepSeek六进程；仅本地网页。

2026-11-12：[有效节点联合评审 v002](../experiments/deviation_progress/v002/run_20261112_02/README.md)已完成同六场景重跑，20个有效节点连续编号，19次请求、18次有效、2次偏航判定；旧v001包含已删除节点，不作为本轮结果。网页仅本地使用。

2026-11-12：[六场景偏航与语义进度联合评审](../experiments/deviation_progress/v001/run_20261112_01/README.md)已准备，用户授权DeepSeek六进程离线运行。复用43次节点建立事件和已有去重；端点＋均匀五帧，新增本地可视化。实际状态见新运行目录，不启动导航或网页发布。

2026-11-12 最新：[本地节点去重完整快照](../experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/README.md)已完成34条：298→165节点，206次实际调用含1次格式错误保留双方；源码和结果保存至原交接分支，网页仅本地使用。此条更新下方“尚未接入后续模型”的历史状态。

2026-11-12：[JEV 在线采样 v001](../experiments/crossing_checkpoint/online_sampling_v001/README.md)获用户认可，准备为主要开发机器合并接入；默认总延迟5个反馈步，确认结果固定。独立算法、41组固定样例、本地网页源码及跨机器导出已验证。网页默认关闭采样，曲线和路线始终完整显示；采样器仍只读取当前前缀。源码交接分支为 `codex/jev-online-sampling-v001`，接手先读 [JEV_SAMPLING_HANDOFF.md](JEV_SAMPLING_HANDOFF.md)。用户要求网页仅本地使用；尚未接入实际导航或后续大模型。

2026-11-07 用户随后纠正：发布服务器密码已按明确要求存入仓库专用认证文件，脚本自动读取；
SSH/SCP 默认直连，HTTP 默认快速 HEAD 验证，7892 不可用时直接绕过。完整下载和在线浏览器
检查仅按需执行，避免大文件重复下载拖住交付。见[发布说明](VISUALIZATION_PUBLISHING.md)。

2026-11-07：用户新增持续规则：所有新制作/重导出的 HTML 可视化须发布到其服务器
`134.175.18.101` 并交付经验证的完整网址，规则已写入根 `AGENTS.md`。
统一配置、脚本及认证/验证流程见[可视化发布说明](VISUALIZATION_PUBLISHING.md)。
服务器已建立项目独立静态目录，沿用现有 Nginx；不修改原实验协议或重跑导航/模型。
首次发布记录在 `outputs/visualization_publishing/setup_20261107_01/`：示例已上传，远端哈希及
公网 HTTP 200 通过；完整公网下载/在线交互因网络耗时未完成验证，额外检查已停止。详情见发布说明。

2026-11-06：按用户纠正，human_v002/run_20261106_04保持原标注C为current_view_id，固定七帧[-4,-2,0,+2,+4,+6,+10]，同十例阶段一完成。10响应、9格式有效，sample_11多层字段包装无效原答保留；0阶段二。默认停C的同步HTML已导出验证，GPU0服务保留。03批判断点后移不代表本次协议。

2026-11-06：用户最终指定采样[C-4,C+3,C+6,C+10]，human_v002/run_20261106_03十例阶段一已完成，10次响应均格式有效，共22条分支；语义正确性待复核，阶段二0次。原+1版本02批中止并保留6条响应。同步主视图/俯视地图HTML已导出并通过浏览器检查，Qwen27B GPU0保持待用。

2026-11-06：human_v002/run_20261106_01两例阶段一窗口试验完成。统一采样[C-5,C,C+5,C+10]、current=P=C+10，沿用原英文prompt与Qwen27B；2次响应、0次阶段二。样本11补出卧室分支，样本23仍有首帧/当前帧错配及把墙列为分支；各3条不等于语义正确。GPU0常驻服务保留。同步回放HTML已导出并通过两例12个位置浏览器检查。 [运行记录](../experiments/agent_route_choice/human_v002/run_20261106_01/README.md)。

2026-11-06：用户明确要求Qwen27B在GPU0常驻待用，已启动独立主管PID197411，正在准入/加载。[服务记录](../experiments/agent_route_choice/services/qwen27b_gpu0_20261106_01/README.md)。本次保留授权覆盖正常空闲等待，不适用任务结束即释放规则；实际状态/端口以 `outputs/model_services/qwen27b_gpu0_20261106_01/service.json` 为准，不启动新实验。

2026-11-06：上午无全景原十条提示词已按用户要求[冻结保留](../experiments/agent_route_choice/v001/prompts/frozen_morning_20261106/README.md)，四份英/中文文件逐字节核验，20份实际请求的提示词/schema一致。晚间优化单独预留为 [human_v002](../experiments/agent_route_choice/human_v002/README.md)，仅登记方向，尚无新提示词或运行。

2026-11-06：[人工Crossing离线数据集v001](../experiments/crossing_dataset/seed2_human_v001/README.md)已完成。用户标注已接收，按要求剔除8条零标注，保留61条（34失败、27成功）及128个Crossing点，其中34个为错误选择。完整5439帧、5378个可推理观测，ZIP与只读HTML已交付；数据、因果读取和128点浏览器核验通过。未调用模型或运行导航，尚无方法测评分数。

2026-11-06：[69条标注工具的中文指令版](../experiments/crossing_analysis/seed2_annotation69/exports/run_20261106_02/README.md)已交付，全部导航指令中文显示，英文原文保留在数据中。69条显示及保存后重开验证通过，6409帧与标注协议保持一致。

2026-11-06：[seed2 69条人工标注工具](../experiments/crossing_analysis/seed2_annotation69/README.md)已完成：39条至少三seed失败＋30条seed2成功，6409帧，约148 MiB单文件HTML。双图同步、标注/删除/撤销、保存后在无缓存浏览器重开均通过。等待用户亲自标注并上传新HTML；未启动导航、模型或GPU，尚未生成用户人工金标准。

2026-11-06：[seed2的48条跨seed共性筛选](../experiments/crossing_analysis/seed2_multiseed48/README.md)完成。按用户最后简化要求，筛同episode最终失败交集：17条五seed均失败，47条至少两seed失败。seed2有既有Crossing错选归因，其他seed的具体错误类型不由失败交集确认。未调用模型或运行导航。

2026-11-06 展示更新：无全景v001已按v002布局重做，加入完整737帧原始录像/俯视地图双进度条，以及一键返回当前Crossing。默认停在判断帧，31条支路与10个原始选择（含第7条矛盾）保持不变。逐帧浏览器检查通过，未调用模型或使用GPU。见[导出记录](../experiments/agent_route_choice/v001/run_20261106_01/exports/run_20261106_03/README.md)。

2026-11-06 当前完成：[外部Agent v002 / 本地Qwen27B十条离线测评](../experiments/agent_route_choice/v002/run_20261106_01/README.md)已完成10/10条、20/20次回答，网络错误0，模型共识别38条支路（含来路），第二轮10条均返回证据不足，最终选择0条。GPU0已释放。未选择时空路线描述曾被旧校验器误拦；仅离线修复兼容后9条协议有效，第7条来路证据缺全景引用；原始回答/状态保留，无额外模型调用。中文全景/支路/排除/未选择原因/俯视地图HTML已导出并通过浏览器检查，语义正确性未建立。下列准备与运行中条目是历史阶段记录。

2026-11-06 最新授权与执行：[外部Agent v002 / Qwen27B十条离线测评](../experiments/agent_route_choice/v002/run_20261106_01/README.md)已启动，GPU0单卡、单并发，使用第1稿英文prompt，12/16张输入、第二次完整传递第一次清单、排除错路及来路。8项CPU协议检查通过；后台自动完成与释放服务。正在制作中文支路/选择/全景/俯视地图HTML。状态以本轮 `outputs/agent_route_choice/v002/run_20261106_01/qwen27b/status.json` 为准；下列“尚未接入/未调用”是此前阶段记录。

2026-11-06：按用户要求编写[外部Agent v002提示词第1稿](../experiments/agent_route_choice/v002/prompts/draft01/README.md)，英文prompt及中文审阅版已准备。第一轮为360°支路盘点＋来路识别；第二轮显式携带第一次完整JSON，排除错误支路和来路。新12/16图消息、schema和校验器尚未接入，未调用模型；72张画面补采结果保持不变。

<!-- AGENT_ROUTE_360_CAPTURE_START -->
2026-11-06T06:58:35.413777+00:00：外部 Agent v002 的原十条360°画面补采完成：八场景、九个Crossing、72张唯一RGB（十条引用80张）。本轮复用64张，新增8张。图像哈希、640×480、固定光心、八方向覆盖、不同方位像素差异及离线浏览器检查通过；模型调用0次、导航动作0次，本次仿真进程已退出。原图与相机元数据位于 `outputs/agent_route_choice/v002/capture_20261106_04/panoramas/`；中文预览位于同目录 `exports/run_20261106_01/crossing_360_zh.html`，原图压缩包为 `crossing_360_images.zip`。尚未进行Qwen支路识别/选路，视觉语义复核另记。
<!-- AGENT_ROUTE_360_CAPTURE_END -->

2026-11-06 外部 Agent v002画面阶段已完成：原十条任务、八场景、九个标定Crossing，每点八方向，共72张唯一图。04轮在用户指定GPU0上补齐最后8张，其余64张按哈希复用；图像、浏览器与ZIP检查通过，九处人工画面核验完成。中文预览和原图包已导出，本项目仿真及收尾进程已退出，原有其他用户进程保留。尚未调用Qwen/GLM进行新判断。见[完成记录与下载](../experiments/agent_route_choice/v002/capture_20261106_04/README.md)。

2026-11-06 当前进度：Qwen32B原十条全部返回两次响应（20/20次，04:16 UTC结束），其中9条通过协议校验；sample_07在第二次回答中将B1判为错误并排除，却又选择B1，保留原始回答并标记无效。尚未语义复核，9条有效回答不代表9条选路正确。离线HTML已导出，本轮服务与子进程全部退出，GPU 0、3已释放。GLM仍因账户无额度（1113）停止，0有效回答，等待充值或新key。 详见[运行批次](../experiments/agent_route_choice/v001/run_20261106_01/README.md)。 已交付[中文单文件可视化](../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/agent_route_choice_qwen32b_zh.html)，20份译文及第七条无效原始回答均可查看，浏览器验证通过。 最新为[支路与选择直观版](../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/crossing_branches_choice_zh.html)：固定判断帧、明确全部支路和最终选择；旧版保留。

更新时间：2026-11-05。Crossing v002的03版双进度条HTML已按用户要求固化为[后续每轮默认模板](CROSSING_VISUALIZATION_TEMPLATE.md)，完成自动导出接入及单/双/四版本CPU与浏览器验证；实验完成与资源释放证据仍为2026-11-04记录。其余条目沿用各实验现有记录。

## 当前研究

在 StreamVLN 等 backbone 外研究 Crossing 语义存档与外部干预恢复。
Crossing 检测方法与 Oracle 理想干预实验是两条独立证据链；Oracle 成功不等于检测方法已有效。

## 已有结果与待办

| 工作 | 状态 | 入口 |
| --- | --- | --- |
| StreamVLN 250条×5seed | 1250条完成，平均SR39.60% | [复现](../experiments/reproduction/streamvln_vlnverse/README.md) |
| InternVLA-N1 825条 | 历史状态50条完成后运行错误阻塞；不是全集完成 | [N1](../experiments/reproduction/internvla_n1_vlnverse/README.md) |
| seed2错误归因 | Crossing错选48/250 | [归因](../experiments/crossing_analysis/seed2_attribution/README.md) |
| Crossing v001 | 开发8条完成；40条验证未启动；下一轮未启动 | [版本](../experiments/crossing_checkpoint/v001/README.md) |
| 27B 单卡单并发部署验证 | 三个八帧请求通过；单卡TP=1、并发1、32K；已释放测试服务 | [部署验证](../experiments/crossing_checkpoint/single_gpu_smoke/README.md) |
| Crossing v002 | 五条开发×三版及十五条验证全部完成。两次修改未改善，按预算退出；基准验证TP3/FP4/FN20，P42.86%/R13.04%/F1 20.00%。1791个方法观测无失败重试，GPU已释放；统一离线HTML及实际浏览器检查完成 | [版本](../experiments/crossing_checkpoint/v002/README.md) |
| Crossing v003固定5条 | 使用第2稿，每两动作步调用一次，共146次计划调用；后台自动评分、模板导出和资源释放，最新状态见下方 | [批次](../experiments/crossing_checkpoint/v003/run_20261105_01/README.md) |
| Oracle十条×五组 | 50条完成；原十条全成功组已按新模板单独导出离线HTML | [Oracle](../experiments/oracle_recovery/pilot10/README.md) |
| 跌倒重试 | reset/replay完成；直接回退补测取消 | [跌倒](../experiments/fall_retry/README.md) |

当前同十条 Oracle 的共享前缀三分支语义延迟实验已完成：10/10 条、30/30 项结果，22 个实际纠正分支、8 项未触发；短/中/长全部任务成功 6/10、5/10、5/10。三档都触发的七条完整配对子集各为 5/7，但成功任务不同，不能推出统一有效延迟界限。第七条中/长档触发前停止；第八、第十条首次偏离自主解除，三档未触发且最终失败。22 个恢复证明及 33 次纠正记忆证明通过。最后一条启动超时已通过仅延长模型就绪等待解决，导航协议未改；全部任务完成后逐 PID 核验进程退出，15:25 UTC 本项目 GPU 占用已释放。已导出约 15.4 MiB 的单文件离线可视化，支持主干/三档同步 RGB 与轨迹回放，浏览器检查通过。见 [配对延迟](../experiments/oracle_recovery/paired_delay10/README.md)。
与旧 10/10 的对照分析已补充：14 个失败结果格中 8 个未干预；第 8、10 条首事件解除后关闭后续审阅，构成协议混杂。六个已干预失败均为预算内原生 STOP，不能把总下降全部归因于延迟。
不是旧距离阈值组重跑。已建立 experiments 分类与 README，不自动启动其他历史授权任务。
追加15–20条Oracle不同任务已取消；直接回退补测已取消；勿恢复。
旧文档“已启动/运行中”及PID只作历史记录。需要续跑时先核验进程、资源和失败原因。

<!-- CROSSING_V003_BATCH_STATUS_START -->
已完成；5条固定离线样本，每2个动作步调用一次。 TP 4 / FP 2 / FN 9。 GPU已释放。
<!-- CROSSING_V003_BATCH_STATUS_END -->

## 接手方式

先读 AGENTS.md → 本文件 → experiments/README.md → 对应实验README。
代码位置见 [代码导航](CODE_LAYOUT.md)。27B已迁入 Resource_Peng/models，旧路径仅为软链接。
完成工作后更新本文件、对应实验README与实验总索引，写清已完成/未完成、产物和下一步。


最新授权：v003第2稿恢复每步调用，仅取原五条中的前三条。记录：`experiments/crossing_checkpoint/v003/run_20261105_02/README.md`。

<!-- CROSSING_V003_DEV3_STRIDE1_STATUS_START -->
已完成；3条固定离线样本，每1个动作步调用一次。 TP 3 / FP 3 / FN 5。 GPU已释放。
<!-- CROSSING_V003_DEV3_STRIDE1_STATUS_END -->


2026-11-05：Crossing v003第3稿prompt已准备，仅小幅降低局部支路线索门槛；未测评、未启动GPU。此前第2稿逐步三条已完成并释放GPU。详见 `experiments/crossing_checkpoint/v003/README.md` 的第3稿记录。


最新授权：第3稿在相同三条上逐步测评，自动导出HTML并释放GPU。记录：`experiments/crossing_checkpoint/v003/run_20261105_03/README.md`。此前“尚未测评”是提示词准备时状态。

<!-- CROSSING_V003_DRAFT03_DEV3_STATUS_START -->
已完成；3条固定离线样本，每1个动作步调用一次。 TP 4 / FP 3 / FN 4。 GPU已释放。
<!-- CROSSING_V003_DRAFT03_DEV3_STATUS_END -->


第3稿追加六条逐步离线测评，记录：`experiments/crossing_checkpoint/v003/run_20261105_04/README.md`。

<!-- CROSSING_V003_DRAFT03_EXTRA6_STATUS_START -->
失败/未完成；6条固定离线样本，每1个动作步调用一次。 GPU已释放。
<!-- CROSSING_V003_DRAFT03_EXTRA6_STATUS_END -->


六条批次run_04在正式调用前因缺少版本选择记录失败，GPU已释放。已补齐并以run_05重启，记录：`experiments/crossing_checkpoint/v003/run_20261105_05/README.md`。

<!-- CROSSING_V003_DRAFT03_EXTRA6_RETRY_STATUS_START -->
已完成；6条固定离线样本，每1个动作步调用一次。 TP 2 / FP 3 / FN 6。 GPU已释放。
<!-- CROSSING_V003_DRAFT03_EXTRA6_RETRY_STATUS_END -->


v004智谱GLM-5.3-Flash：10条、10进程、每步调用，第3稿prompt；准备启动。记录 experiments/crossing_checkpoint/v004/README.md；实时状态 outputs/crossing_checkpoint/v004/run_20261105_01/status.json。

智谱v004十进程批次已启动，已收到通过schema校验的逐步图像回答；不持续人工跟踪。最终状态由 outputs/crossing_checkpoint/v004/run_20261105_01/status.json 提供，HTML自动导出，子进程结束释放内存密钥。


2026-11-05状态核验：智谱v004批次于09:19:50 UTC失败退出，累计26/588次有效回答、0/10条完成。一条请求首次输出达到长度上限，重试时遇到连接重置，随后触发整批停止。全部worker和主管已退出，密钥没有落盘，未生成最终分数或HTML。病例旧running状态只代表中断前状态；以批次status.json为准。未自动重启。

智谱十条已授权重试并跑完：run_20261105_02，复用26条有效回答，流式请求/输出预算/退避修复已登记于experiments/crossing_checkpoint/v004/run_20261105_02/README.md。

最终状态：{"phase": "failed", "error": "RuntimeError: Termination requested", "finished_at": "2026-11-05T09:49:24.434617+00:00", "credential_on_disk": false, "workers_exited": true}

智谱run_02默认max持续长思考，已结束自己的进程；切换run_03统一low重新评测10条、10并发、588次，不混用旧结果。详细记录 experiments/crossing_checkpoint/v004/run_20261105_03/README.md。

最终状态：{"phase": "failed", "error": "RuntimeError: Termination requested", "finished_at": "2026-11-05T10:06:33.405403+00:00", "credential_on_disk": false, "workers_exited": true}

智谱low续跑run_04：保留82次成功回答，将实测600秒空等的网络读超时缩至60秒；方法不变。见experiments/crossing_checkpoint/v004/run_20261105_04/README.md。

最终状态：{"phase": "complete", "error": null, "finished_at": "2026-11-05T10:40:48.502818+00:00", "credential_on_disk": false, "workers_exited": true}


智谱v004最终完成：run_20261105_04，GLM-5.3-Flash low，10条/588判定，TP8/FP11/FN12，P42.11%、R40.00%、F1 41.03%。默认模板HTML及588条远端请求审计通过；全部API进程退出，临时凭据未落盘。详见 experiments/crossing_checkpoint/v004/run_20261105_04/README.md。此前max失败记录保留且排除出成绩。

Qwen第三稿九条统一可视化已完成：原3条＋追加6条，共481观测，单文件保留两个批次入口；默认模板及实际浏览器检查通过，未启动推理。记录 experiments/crossing_checkpoint/v003/combined9_visualization/README.md；HTML outputs/crossing_checkpoint/v003/combined9_export_20261105_01/visualization/qwen_draft03_9_cases.html。

2026-11-05：v005第4稿已按用户要求小幅放宽，原10条/588观测、智谱max、10进程、每步调用，准备启动；记录 experiments/crossing_checkpoint/v005/run_20261105_01/README.md。旧版结果保留。

v005第4稿智谱max已启动：run_20261105_01，10个独立worker、每步调用；计划588次。首批回答验证中，最终状态以该批status.json为准。

启动验证通过：10个独立worker存活，已验证6个有效回答及实际远端max请求哈希；提示词与第4稿一致。个别网络读取超时由既有退避自动重试。后台继续，停止人工持续跟踪；完成后自动评分、完整审计、模板导出和进程清理。

Qwen3.5-4B第四稿三条并发已准备：v005/run_20261105_02，GPU0单模型服务、3个episode进程、168次逐步调用；智谱原批次继续。详见 experiments/crossing_checkpoint/v005/run_20261105_02/README.md。

Qwen4B启动记录：{"run": "v005/run_20261105_02", "phase": "loading", "supervisor_pid": 1391704, "server_pid": 1391810, "gpu": 0, "concurrency": 3}。模型加载中，尚未确认有效回答。

Qwen4B run_20261105_02启动验证通过：3个独立episode进程并发，已核验23次有效回答及因果前缀，第四稿prompt一致、关闭思考；服务日志确认同时3请求。停止人工持续跟踪，后台完成后自动评分、释放GPU和导出模板HTML。

Qwen4B三条最终状态：{"phase": "complete", "tag": "qwen35_4b_draft04_dev3", "started_at": "2026-11-05T11:18:08.102884+00:00", "supervisor_pid": 1391704, "gpu": 0, "updated_at": "2026-11-05T11:33:47.236689+00:00", "server_pid": 1391810, "base_url": "http://127.0.0.1:38239/v1", "replay_pid": 1406833, "expected_calls": 168, "concurrency": 3, "gpu_released": true, "error": null, "finished_at": "2026-11-05T11:33:47.236662+00:00"}

最终状态：{"tag": "glm53flash_draft04_max_10", "output": "/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/v005/run_20261105_01", "phase": "failed", "error": "RuntimeError: Worker failure", "finished_at": "2026-11-05T13:25:22.234308+00:00", "credential_on_disk": false, "workers_exited": true}

智谱第四稿max：178/588次，0/10条；超时和HTTP429耗尽重试，worker已退出。未完成片段预览已导出，178条因果请求重建校验通过，不计算最终分数，不启动推理。HTML：outputs/crossing_checkpoint/v005/run_20261105_01/exports/partial_20261105_01/glm_draft04_max_partial178.html。

2026-11-05：用户授权原十条任务的新真实存档点配对实验（StreamVLN续走 vs Oracle实际动作选路），已完成；不使用正确路径瞬移落点。记录 experiments/oracle_recovery/checkpoint_action10/README.md。

真实存档点动作接管十例已完成：7条有效配对（局部正确StreamVLN1/7、Oracle7/7；最终成功2/7与5/7），2条未触发（1成功1失败），1条恢复技术失败。全部从实际存档恢复，Oracle仅执行动作；GPU0已释放。详见 experiments/oracle_recovery/checkpoint_action10/README.md。

2026-11-06：真实存档十例的可视化已修正为完整“首次走错→复位→续走”时间线，七对十四条恢复边界经原始帧/restore_proof与浏览器核验；新入口 `outputs/oracle_crossing/checkpoint_action10/run_20261105_01/exports/timeline_20261106_02/oracle_checkpoint_timeline.html`。旧模板导出的遗漏已登记，实验未重跑，成绩未改变。


2026-11-06T03:53:41.853390+00:00 自动收尾：Agent选路 run_20261106_01/glm；状态 `failed_partial`，完成两次调用 0/10 条，HTML导出 True，GPU释放 不适用。结果 `outputs/agent_route_choice/v001/run_20261106_01/glm`；语义正确率仍待复核。


2026-11-06T03:59:36.574355+00:00 自动收尾：Agent选路 run_20261106_01/glm；状态 `interrupted`，完成两次调用 0/10 条，HTML导出 True，GPU释放 不适用。结果 `outputs/agent_route_choice/v001/run_20261106_01/glm_retry02`；语义正确率仍待复核。


2026-11-06 GLM启动阻塞已确认：服务端错误1113“余额不足或无可用资源包，请充值”。首次glm/及恢复glm_retry02/均无有效回答；已正常停止本轮恢复进程，不再重复请求，等待用户充值或替换key。Qwen32B原批继续，GPU 0、3，监督PID3194485；运行状态以 outputs/agent_route_choice/v001/run_20261106_01/qwen32b/status.json 为准。


2026-11-06T04:16:08.990844+00:00 自动收尾：Agent选路 run_20261106_01/qwen32b；状态 `failed_partial`，完成两次调用 9/10 条，HTML导出 True，GPU释放 True。结果 `outputs/agent_route_choice/v001/run_20261106_01/qwen32b`；语义正确率仍待复核。


2026-11-06：人工标注无全景v001恢复选路已授权并完成准备，34个错误点/33条轨迹、最多68次调用，本地Qwen27B；7项新增及27项既有CPU检查通过。按用户要求本轮不生成HTML，确认正常启动后后台运行并自动释放GPU。当前无完全空闲GPU，GPU0低负载且有他人进程，等待共享资源选择。记录：experiments/agent_route_choice/human_v001/run_20261106_01/README.md。


2026-11-06T14:49:26.196528+00:00：用户已明确授权共享GPU0，后台主管已启动（PID 44492），单卡单并发，本轮不生成HTML。三次资源准入后加载Qwen27B；确认有效双调用后停止人工持续跟踪。实际状态见 outputs/agent_route_choice/human_v001/run_20261106_01/qwen27b/status.json。


2026-11-06T15:03:14.061403+00:00 启动核验完成：Qwen27B在共享GPU0正常提供服务，首条两次完整响应已保存，finish_reason=stop、网络错误0，实际请求哈希与第二次完整传递第一次JSON核验通过。首例模型弃答且route_description为空，原v001校验拒绝，作为协议无效保留；未修改冻结校验或模型答案，后续样本继续。当前处理进度见status.json；按用户要求停止人工持续跟踪，后台完成34点后自动审计、保存结果、释放服务，本轮不生成HTML。


2026-11-06T15:12:04.148979+00:00：GLM-5.3-Flash人工34点无全景批次已获授权并完成准备，复用Qwen同一输入和v001英文prompt，low思考、最多10个独立worker；4项凭据传输CPU检查通过。密钥仅经stdin进入进程内存，本轮无HTML。记录 experiments/agent_route_choice/human_v001/run_20261106_02/README.md。


2026-11-06T15:12:48.814078+00:00 GLM-5.3-Flash人工34点无全景批次收尾：`blocked_account`，保存0/68次回答，协议有效0/34。worker全部退出True，凭据未落盘True，本轮无HTML；语义正确率待复核。结果 `outputs/agent_route_choice/human_v001/run_20261106_02/glm`。


2026-11-06T15:14:24.003697+00:00 账户阻塞已核验：首个GLM请求返回HTTP429 / code1113“余额不足或无可用资源包，请充值。”仅1次请求、0次模型回答，未展开10进程队列；主管及首个worker已退出。凭据只经无回显stdin与匿名管道进入内存，运行文本扫描未发现凭据，未生成HTML。等待用户充值或替换有额度的key，不自动反复请求；本地Qwen继续。


2026-11-06T15:21:16.872308+00:00 人工标注无全景选路自动收尾：状态 `complete_with_invalid_samples`，处理 34/34 个点，保存 65/68 次回答，协议有效 7/34；语义正确率待复核。本轮按用户要求不生成HTML，GPU释放 True。结果 `outputs/agent_route_choice/human_v001/run_20261106_01/qwen27b`。


2026-11-06：用户追加要求的手工标注 Qwen27B 离线可视化已完成。34例，主视图与俯视地图双进度条同步，展示模型识别/排除/选择、原始回答、失败状态与复核导出；34例及131个关键帧浏览器验证通过，零外部请求，未重跑模型。HTML：`outputs/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/human_qwen27b_review.html`（约116 MiB）。记录：`experiments/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/README.md`。


2026-11-06：按用户要求，将上午无全景Qwen32B十条按同步主视图/俯视地图模板重新导出至 `outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_04/crossing_v001_timeline_zh.html`，约55.4 MiB。20份原答、31支路、中英切换及第7条矛盾完整保留；十条全部737帧浏览器检查通过，无新模型调用。导出记录：`experiments/agent_route_choice/v001/run_20261106_01/exports/run_20261106_04/README.md`。


2026-11-06T16:09:23.977981+00:00 Qwen27B GPU0待用服务已就绪：`http://127.0.0.1:37007/v1`，模型名`route-choice-qwen27b-standby`，主管PID197411、API PID198361。图文请求检查通过；按用户明确要求保留，正常空闲不自动释放。状态见 `outputs/model_services/qwen27b_gpu0_20261106_01/service.json`。无新选路实验。

2026-11-06：human_v002/run_20261106_05仅sample_01阶段一提示词开发：01—03稿被用户否决为针对案例；04—11稿改为通用证据阈值逐步放宽，8次均返回前方客厅与后方来路，未识别目标右侧候选，目标未达成。原稿与所有结果保留，七帧及C=37固定，0阶段二，GPU0按用户要求保留。记录 experiments/agent_route_choice/human_v002/run_20261106_05/README.md。

2026-11-06：human_v002/run_20261106_06已授权并启动准备，复用04批十例第一轮原答，第二轮输入七帧上下文+均匀四帧错误经历去重；原C固定。GPU0保留服务上限扩至11图，单并发；完成后导出完整双进度条HTML。记录 experiments/agent_route_choice/human_v002/run_20261106_06/README.md。

2026-11-06：human_v002/run_20261106_06第二轮10/10完成，复用04批第一轮原答；3选择（08/11/23）、7弃答，语义正确性待复核。7例弃答null路线描述不合严格schema，sample_11第一轮额外包装保留；两轮格式均通过2/10。完整965帧HTML已导出，10例40关键位置浏览器检查通过。产物outputs/agent_route_choice/human_v002/run_20261106_06/exports/run_20261106_01/crossing_two_stage_review.html。GPU0新11图服务02按用户要求保留，旧01已停止。

2026-11-06：human_v002/run_20261106_07按用户要求开始第二阶段强制选择十例；第一轮、图片、任务、动作与06批一致，仅改prompt及选择schema/校验，允许错路未知但必须选已有分支。旧版保留，完成后导出完整HTML；服务02保留。

2026-11-06：human_v002/run_20261106_07强制选择第二轮十例完成，10/10选择且第二轮格式通过；第一轮原有sample_11包装问题保留，两轮均有效9/10。输入及第一轮结果不变，仅prompt/schema/校验变化。完整HTML已导出，浏览器10例40关键帧通过。第4例sample_06选B3右侧，语义正确性待复核；强制选择率不是成功率。GPU0服务保留。记录 experiments/agent_route_choice/human_v002/run_20261106_07/README.md。

2026-11-06：human_v002/run_20261106_08仅sample_08第二轮试验启动：先按后续图像匹配实际路线，再排除，最后结合指令强制选择。沿用07批全部输入和schema，仅system修改；新结果/HTML单独保存。

2026-11-06：human_v002/run_20261106_08单例sample_08完成，先观察后排除prompt仍输出排除B3/选择B1，目标未达成。仅system变化审计通过，原答与失败解释保留；完整单例HTML已导出，GPU0保留。

2026-11-06：human_v002/run_20261106_09仅sample_08启动独立视觉识别与替代选路两调用。视觉调用不给任务/动作/错误标签，识别结果程序锁定排除；仅此episode，不重跑第一阶段。

2026-11-06：human_v002/run_20261106_09单例隔离调用完成。视觉识别B1前方，程序排除B1，独立任务选路选择B3右侧（medium）。2次新调用、第一轮复用，实际请求及隔离审计通过；仅单例开发结果，最终选择待复核。单例HTML含两次原答与锁定排除，GPU0保留。

2026-11-06：human_v002/run_20261106_10十例隔离识别/选路已启动（worker488856）。复用原第一轮，09批prompt不变，每例视觉识别→锁定排除→独立任务选路，最多20次新调用。运行后自动导出完整HTML；GPU0服务02保留。

2026-11-06：human_v002/run_20261106_10隔离版十例完成，第一轮原答复用、20次新增响应（识别10＋选路10），10次选择均遵守锁定排除。sample_11原有第一轮格式异常保留；语义正确性待复核。20实际请求重建及隔离审计通过，完整965帧HTML、十例40关键帧浏览器检查通过。产物outputs/agent_route_choice/human_v002/run_20261106_10/exports/run_20261106_01/crossing_two_stage_review.html；GPU0服务保留。

2026-11-07：human_v002/run_20261107_01全部34人工错误点已授权并启动，复用10批十例，补跑24例（最多72次新调用）。轨迹开头缺失历史按边界规则略去，其余同七帧＋隔离识别/选路协议；完成后完整34例HTML。worker1187819，GPU0服务02保留。

2026-11-07：human_v002/run_20261107_01全部34人工错误点/33轨迹完成；10例复用、24例新增72响应，共102原答。34选择均遵守锁定排除；sample_11旧包装问题及sample_31任务引用问题保留，全流程严格格式有效32/34，语义待复核。102请求重建和隔离审计通过，完整3161帧HTML（141.80MiB）及34例131关键帧浏览器检查通过。产物outputs/agent_route_choice/human_v002/run_20261107_01/exports/run_20261106_01/crossing_two_stage_review.html；GPU0服务保留。

2026-11-07：用户授权三帧Crossing轻量评分，10失败＋20成功、GPU0 Qwen3.5-4B vLLM＋4进程；准备完成。原GPU0 Qwen27B已按核验PID释放，其他用户进程保留。记录 experiments/crossing_checkpoint/lite_v001/run_20261107_01/README.md；实际状态 outputs/crossing_checkpoint/lite_v001/run_20261107_01/status.json。

2026-11-07：三帧评分后台主管1292524、vLLM API1292779已启动加载，端口60859；冻结30条/2559次调用。6项CPU协议测试通过，独立无预测预览30条/2589帧/156关键位置浏览器检查通过（双滑条、复核导出、移动端、零外部请求/JS错误），不计作模型结果。

2026-11-07T03:34:36.957330+00:00 启动核验通过：GPU0 Qwen3.5-4B vLLM、4独立episode进程；前12份真实响应及三帧输入/请求哈希/1–5评分通过，4请求时间区间并发已确认。此刻有效回答12/2559。停止人工持续跟踪；后台自动完成、导出双进度条HTML及请求/浏览器审计，释放本轮服务。

2026-11-07T03:41:01.901924+00:00：按用户要求更新三帧评分HTML俯视轨迹配色，1–5分浅绿到深绿；t→t+1线段使用起点t的有效原始评分，无评分灰色虚线，原地转向同色点，并加入图例。仅修改core/crossing_lite_review.js；原启动manifest/source快照保留，导出修订与授权哈希见outputs/crossing_checkpoint/lite_v001/run_20261107_01/export_revisions/score_route_colors_20261107_01/。推理源码、prompt、任务与原答未改，不查询/跟踪运行进度。独立CPU预览30条/2589帧/156位置及五档明度、实际Canvas线段颜色、起点评分对应、回放前缀和灰色缺失检查通过；合成配色测试不计模型结果。本轮自动导出会应用此修订。

2026-11-07T03:54:38.445077+00:00：三帧Crossing五级评分 outputs/crossing_checkpoint/lite_v001/run_20261107_01 自动收尾：{"phase": "complete", "supervisor_pid": 1292524, "started_at": "2026-11-07T03:27:26.666080+00:00", "gpu": 0, "concurrency": 4, "expected_calls": 2559, "updated_at": "2026-11-07T03:54:38.399180+00:00", "base_url": "http://127.0.0.1:60859/v1", "server_pid": 1292779, "worker_pids": [1300869, 1300871, 1300874, 1300875], "inference_error": null, "gpu_released": true, "finished_at": "2026-11-07T03:54:38.399149+00:00", "error": null, "summary": {"episodes": 30, "groups": {"failure": 10, "success": 20}, "expected_calls": 2559, "attempted_calls": 2559, "responses": 2559, "valid_calls": 2559, "invalid_or_missing": 0, "audited_requests": 2559, "score_histogram": {"1": 1911, "4": 2, "5": 646}, "replay_frames": 2589, "annotation_points": 70, "mean_latency_seconds": 1.2661769690414968, "evaluation": "Raw score distribution and exact annotated-point scores only. No unlabeled-frame negatives or PR/F1.", "created_at": "2026-11-07T03:54:30.690423+00:00"}, "html": "/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/lite_v001/run_20261107_01/exports/final/crossing_lite_review.html"}。未标帧不视为负类，语义准确性待复核。

2026-11-07 在线加载修复：原单文件包含约62 MiB内嵌媒体，初始化脚本位于文件末尾，慢网下载未结束时只显示框架。已生成媒体按需加载版本，HTML 3,799,721字节、2600个图片/字体资源，全部远端SHA256验证通过。
新网址：[在线回放](http://134.175.18.101/vln/crossing_lite_v001_online_20261107_01/crossing_lite_review.html)。
本地浏览器验证30条/2589帧/156位置、2559有效回答、双滑条、复核导出及移动端通过，零JS错误。
记录与原始来源哈希：`outputs/visualization_publishing/online_20261107_01/`；发布清单：`outputs/visualization_publishing/publish_20261107_072020_383244/publication.json`。原离线文件保留，未重跑模型或导航。

2026-11-07：[Oracle十条四条件回放发布](../experiments/oracle_recovery/four_conditions_publication/README.md)完成：尽早组＋短/中/长语义延迟，双语任务指令与按需媒体，原实验未重跑。[在线入口](http://134.175.18.101/vln/oracle_four_conditions_20261107_01/index.html)。仅三档延迟共享前缀，尽早组为独立历史运行。

2026-11-07 完整复位时间线已发布：[打开网页](http://134.175.18.101/vln/oracle_checkpoint7_20261107_01/bilingual.html)。原十条/七条有效配对、两条未触发、一条技术失败保持不变，默认StreamVLN恢复续走，另保留Oracle动作对照；新增中英文任务指令选择与媒体按需加载。原始实验JSON未修改，未重跑模型或导航。本地十条及双语帧位置检查通过，全部远端资源SHA256和公网入口HEAD通过。发布记录：`outputs/visualization_publishing/publish_20261107_074544_142571/publication.json`；展示、源文件哈希、数据审计及浏览器证据在 `outputs/visualization_publishing/oracle_checkpoint7_20261107_01/`。

2026-11-07：Qwen27B人工错误集[双语在线选路回放](http://134.175.18.101/vln/qwen27b_human33_20261107_01/crossing_two_stage_review.html)已发布。33条轨迹/34错误点完整保留；用户提供人工选路复核18/33（54.5%），无逐点标签映射，不混为导航成功率。467条英文自然语言完整翻译可切换，原回答不变；本地34例/3161帧及双滑条检查、全部远端哈希与入口HEAD通过。记录：experiments/agent_route_choice/human_v002/run_20261107_01/exports/online_20261107_01/README.md。未启动新模型或导航。

2026-11-07：七例独立R2R纠错指令生成与部署检查已准备；见 experiments/agent_recovery/r2r_v001/run_20261107_01/README.md。按用户要求后台运行，不持续跟踪；物理恢复尚未执行。


后台部署结果：{"phase": "failed", "pid": 1855535, "started_at": "2026-11-07T09:24:00.232022+00:00", "gpu": 0, "qwen_pid": 1855958, "base_url": "http://127.0.0.1:43351/v1", "updated_at": "2026-11-07T09:48:57.696716+00:00", "sample": "sample_34", "instructions": 7, "streamvln_pid": 1866191, "error": "KeyboardInterrupt: Termination requested", "finished_at": "2026-11-07T09:48:57.696700+00:00", "gpu_released": true}。仅指令生成和环境加载检查；七例物理恢复尚未执行。

2026-11-07：用户明确停止七例v001部署队列，原因是指令过长并延伸至房间/后续路线；向已核验主管1855535发送SIGTERM。旧七条结果保留且不执行。新最小局部纠正prompt见 experiments/agent_recovery/r2r_v002/，仅方向输入，未调用模型或导航，不自动重启。

停止核验：本轮GPU进程已全部退出，GPU0仅剩他人4234MiB服务，空闲44277MiB；status.json明确标为cancelled。未执行仿真恢复。

2026-11-07：局部纠正prompt v003已保存于 experiments/agent_recovery/r2r_v003/，限制关键分支纠正的移动范围，允许必要的靠近＋转向＋少量前进；取代v002机械方向映射，仅文本修改，无模型或导航运行，v001保持取消。

2026-11-07：用户授权v003七例局部纠正prompt生成，准备后台运行；记录 experiments/agent_recovery/r2r_v003/run_20261107_01/README.md。Qwen27B、原选路＋C帧画面，7次请求，无导航/仿真。


2026-11-07 v003七例局部纠正命令后台收尾：状态`complete`，完成7/7，GPU释放True；原答语义待复核，无导航或仿真。产物 `outputs/agent_recovery/r2r_v003/run_20261107_01`。

2026-11-07：v004局部导航prompt已保存于 experiments/agent_recovery/r2r_v004/，仅当前画面＋已选方向＋局部入口描述，删除原任务路线字段、实验背景与固定动作示例。仅供审阅，无模型/仿真调用；旧运行器未接入新版。

2026-11-07：v005七例新prompt生成已准备后台资源等待；见 experiments/agent_recovery/r2r_v005/run_20261107_01/README.md。使用C画面＋原选择方向＋分支视觉landmark，不传任务或旧route_description；当前无可准入GPU，等待24小时以内，未运行模型/导航。

2026-11-07：按用户要求准备v005 Qwen3-4B现有服务文字版七例；接口HTTP401，自动审批拒绝读取他人凭据，推理0/7。见 experiments/agent_recovery/r2r_v005/run_20261107_02_qwen4b_text/README.md。原27B资源等待队列保留。


2026-11-07 v005七例局部纠正命令后台收尾：状态`cancelled`，完成0/7，GPU释放True；原答语义待复核，无导航或仿真。产物 `outputs/agent_recovery/r2r_v005/run_20261107_01`。

2026-11-07：用户切换DeepSeek多模态，v005/run_20261107_03_deepseek准备七进程并行，复用原图文输入。原Qwen27B资源等待队列已停止；Qwen4B未调用。密钥仅内存传递，无导航或仿真。


DeepSeek v005七例图文并行收尾：{"phase": "complete", "supervisor_pid": 2542551, "started_at": "2026-11-07T16:26:11.859144+00:00", "model": "deepseek-flash", "concurrency": 7, "expected_calls": 7, "completed": 7, "credential_on_disk": false, "navigation_executed": false, "simulation_started": false, "updated_at": "2026-11-07T16:26:19.457060+00:00", "worker_pids": [2542581, 2542582, 2542583, 2542584, 2542585, 2542586, 2542587], "semantic_review": "pending", "workers_exited": true, "finished_at": "2026-11-07T16:26:19.457044+00:00"}；产物 outputs/agent_recovery/r2r_v005/run_20261107_03_deepseek。无导航或仿真。

2026-11-07：v006 DeepSeek七例多模态新prompt对比已准备，除prompt外请求逐项一致；见 experiments/agent_recovery/r2r_v006/run_20261107_01/README.md。七进程各一次，无导航/仿真。


DeepSeek r2r_v006七例图文并行收尾：{"phase": "complete", "supervisor_pid": 2570826, "started_at": "2026-11-07T16:41:56.622603+00:00", "model": "deepseek-flash", "concurrency": 7, "expected_calls": 7, "completed": 7, "credential_on_disk": false, "navigation_executed": false, "simulation_started": false, "updated_at": "2026-11-07T16:42:04.566564+00:00", "worker_pids": [2570830, 2570831, 2570832, 2570833, 2570834, 2570835, 2570837], "semantic_review": "pending", "workers_exited": true, "finished_at": "2026-11-07T16:42:04.566548+00:00"}；产物 outputs/agent_recovery/r2r_v006/run_20261107_01。无导航或仿真。

2026-11-08：v007最新简短prompt七例DeepSeek图文并行准备完成，仅更换prompt；见 experiments/agent_recovery/r2r_v007/run_20261108_01/README.md。无导航/仿真，v006保留。


DeepSeek r2r_v007七例图文并行收尾：{"phase": "complete", "supervisor_pid": 3885224, "started_at": "2026-11-08T05:20:06.223152+00:00", "model": "deepseek-flash", "concurrency": 7, "expected_calls": 7, "completed": 7, "credential_on_disk": false, "navigation_executed": false, "simulation_started": false, "updated_at": "2026-11-08T05:20:12.214645+00:00", "worker_pids": [3885259, 3885260, 3885261, 3885262, 3885263, 3885264, 3885265], "semantic_review": "pending", "workers_exited": true, "finished_at": "2026-11-08T05:20:12.214630+00:00"}；产物 outputs/agent_recovery/r2r_v007/run_20261108_01。无导航或仿真。

2026-11-08：用户已指定局部纠正指令 **v007为当前最优prompt**，保留七例DeepSeek多模态结果。[版本记录](../experiments/agent_recovery/r2r_v007/README.md)，[当前指针](../experiments/agent_recovery/current_best.json)。7/7生成完成，未执行导航；不自动重跑。

2026-11-08：v007全量34点/33轨迹重新生成已准备，34独立进程，全部新调用（含旧七例），DeepSeek多模态；见 experiments/agent_recovery/r2r_v007/run_20261108_02_all34/README.md。上游11/31格式问题保留，不重新选路；未启动导航/仿真。


DeepSeek r2r_v00734例图文并行收尾：{"phase": "complete", "supervisor_pid": 3897400, "started_at": "2026-11-08T05:29:33.811152+00:00", "model": "deepseek-flash", "concurrency": 34, "expected_calls": 34, "completed": 34, "credential_on_disk": false, "navigation_executed": false, "simulation_started": false, "updated_at": "2026-11-08T05:29:41.709800+00:00", "worker_pids": [3897401, 3897402, 3897403, 3897404, 3897405, 3897406, 3897407, 3897408, 3897409, 3897410, 3897411, 3897412, 3897413, 3897414, 3897415, 3897416, 3897417, 3897418, 3897419, 3897420, 3897421, 3897422, 3897423, 3897424, 3897425, 3897426, 3897427, 3897428, 3897429, 3897430, 3897431, 3897432, 3897433, 3897434], "semantic_review": "pending", "workers_exited": true, "finished_at": "2026-11-08T05:29:41.709785+00:00"}；产物 outputs/agent_recovery/r2r_v007/run_20261108_02_all34。无导航或仿真。

2026-11-08：用户要求GPU0挂起本项目Qwen3.5-4B；配置与启动器已准备，尚未启动。停止GPU0他人ljh服务的SIGTERM操作被自动审批拒绝（缺少所有者/管理员授权），未执行；待授权或对方释放。记录 experiments/agent_route_choice/services/qwen4b_gpu0_20261108_01/README.md。

2026-11-08：用户确认管理员/所有者授权后，GPU0原Qwen3-4B API2294080及引擎2294951已正常退出，释放约41GiB，SAM3保留。本项目Qwen3.5-4B常驻主管3935702已启动，后台自动就绪检查；实际状态outputs/model_services/qwen4b_gpu0_20261108_01/service.json。用户明确要求挂起待用，不因空闲清理。

2026-11-08：新增完整61条人工集三帧评分后台实验，登记 `experiments/crossing_checkpoint/lite_full_v001/run_20261108_01/README.md`；5378次评分，完成后自动可视化及发布。不重跑导航，不持续人工轮询。

2026-11-08T07:42:49.132117+00:00 full61后台流程状态：{"phase": "failed", "pid": 3955960, "started_at": "2026-11-08T06:07:30.349439+00:00", "expected_calls": 5378, "updated_at": "2026-11-08T07:42:48.945430+00:00", "service": "http://127.0.0.1:58317/v1", "service_reused": true, "server_max_num_seqs": 1, "error": "CalledProcessError: Command '['/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/backbone/streamvln/.venv/bin/python', '-B', '/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/scripts/crossing_lite_full_finish.py', '/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/lite_full_v001/run_20261108_01']' died with <Signals.SIGTERM: 15>.", "finished_at": "2026-11-08T07:42:48.945408+00:00"}

机器人位置点修正版已发布：http://134.175.18.101/vln/crossing_lite_full61_run_20261108_01_web_02/crossing_lite_review.html 。48组双时间轴/参考路径开关/完整轨迹开关位置及可见像素检查通过，远端资源SHA256和公网HTTP验证通过。发布记录：outputs/visualization_publishing/publish_20261108_081302_517506/publication.json。

2026-11-08：用户将当前三帧五级评分版本标记为“最优版本1”（best_v001），冻结登记 experiments/crossing_checkpoint/best_v001/；当前指针 experiments/crossing_checkpoint/current_best.json，网页为web_02机器人位置点修正版。

2026-11-08：部署lite_v002/run_20261108_01，20条（10失败10成功，含kujiale_0113_66_1），八步局部选择与部分可见支路新提示词；后台评分→Qwen4B翻译→与最优版本1同帧对比→检查发布；不持续人工轮询。

2026-11-08T09:34:56.502540+00:00 v002_20后台流程状态：{"phase": "complete", "pid": 57834, "started_at": "2026-11-08T08:40:54.323042+00:00", "expected_calls": 1824, "updated_at": "2026-11-08T09:34:56.297353+00:00", "service": "http://127.0.0.1:58317/v1", "service_reused": true, "server_max_num_seqs": 1, "finished_at": "2026-11-08T09:34:56.297326+00:00", "url": "http://134.175.18.101/vln/crossing_lite_v002_20_compare_best1_run_20261108_01_web_01/crossing_lite_review.html", "html": "/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/lite_v002/run_20261108_01/exports/final/crossing_lite_review.html", "html_sha256": "02612d5aeca697dcab73fcdc8a813a0564823e57cb15a6c155bf934cfde20c7d", "summary": {"episodes": 20, "groups": {"failure": 10, "success": 10}, "expected_calls": 1824, "attempted_calls": 1824, "responses": 1824, "valid_calls": 1824, "invalid_or_missing": 0, "audited_requests": 1824, "score_histogram": {"1": 1406, "4": 194, "5": 224}, "replay_frames": 1844, "annotation_points": 47, "mean_latency_seconds": 3.183620818345317, "evaluation": "Raw score distribution and exact annotated-point scores only. No unlabeled-frame negatives or PR/F1.", "created_at": "2026-11-08T09:32:59.733707+00:00"}, "comparison": {"episodes": 20, "paired_frames": 1824, "changed": 281, "increased": 38, "decreased": 243, "baseline_histogram": {"1": 1367, "5": 456, "4": 1}, "new_histogram": {"1": 1406, "4": 194, "5": 224}, "diagnostic": [{"episode_id": "kujiale_0113_66_1", "frame": 84, "new": 1, "baseline": 1}], "interpretation": "Score changes only, not accuracy gains; user-selected diagnostic is development data."}, "publication_records": ["/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/visualization_publishing/publish_20261108_093423_410947/publication.json"], "published_at": "2026-11-08T09:34:56.081204+00:00"}
