# 实验总目录

2026-11-07 起，所有新生成/重导出的 HTML 可视化须按[统一发布规范](../docs/VISUALIZATION_PUBLISHING.md)
上传到用户指定服务器，并在具体实验/导出 README 记录源文件、网址、SHA256、发布时间及在线验证结果。
本地导出成功不等于完成交付；回复必须提供可直接打开的完整网址。历史原件与版本保持不变。

2026-11-06：按用户纠正，human_v002/run_20261106_04保持原标注C为current_view_id，固定七帧[-4,-2,0,+2,+4,+6,+10]，同十例阶段一完成。10响应、9格式有效，sample_11多层字段包装无效原答保留；0阶段二。默认停C的同步HTML已导出验证，GPU0服务保留。03批判断点后移不代表本次协议。

2026-11-06：用户最终指定采样[C-4,C+3,C+6,C+10]，human_v002/run_20261106_03十例阶段一已完成，10次响应均格式有效，共22条分支；语义正确性待复核，阶段二0次。原+1版本02批中止并保留6条响应。同步主视图/俯视地图HTML已导出并通过浏览器检查，Qwen27B GPU0保持待用。

2026-11-06：human_v002/run_20261106_01两例阶段一窗口试验完成。统一采样[C-5,C,C+5,C+10]、current=P=C+10，沿用原英文prompt与Qwen27B；2次响应、0次阶段二。样本11补出卧室分支，样本23仍有首帧/当前帧错配及把墙列为分支；各3条不等于语义正确。GPU0常驻服务保留。同步回放HTML已导出并通过两例12个位置浏览器检查。 [运行记录](agent_route_choice/human_v002/run_20261106_01/README.md)。

2026-11-06：[Qwen27B GPU0待用服务](agent_route_choice/services/qwen27b_gpu0_20261106_01/README.md)已按用户明确保留指令启动，主管PID197411；就绪后保留等待调用，非实验批次。

2026-11-06：[上午v001提示词保留基准](agent_route_choice/v001/prompts/frozen_morning_20261106/README.md)已归档并验证；[晚间human_v002优化方向](agent_route_choice/human_v002/README.md)独立登记，尚未运行。

2026-11-06：[人工Crossing离线数据集v001](crossing_dataset/seed2_human_v001/README.md)已完成。用户上传69条标注后剔除8条零标注，保留61条（34失败/27成功）、128个Crossing（94普通/34错误选择）、5439帧。ZIP、只读HTML、因果读取器及全部文件/标注/浏览器校验通过；未运行模型测评。

2026-11-06：[69条人工标注工具：中文导航指令](crossing_analysis/seed2_annotation69/exports/run_20261106_02/README.md)已完成。全部69条指令已翻译，浏览器逐条显示及保存恢复检查通过；原版保留，未重跑导航。

2026-11-06：[seed2 69条人工标注工具](crossing_analysis/seed2_annotation69/README.md)已交付：39条至少三seed失败＋30条seed2成功，共6409帧。单文件HTML支持双图同步、Crossing/错误选择标注、删除/撤销及完整HTML保存；浏览器验证通过。等待用户上传人工标注，尚未生成金标准或测评分数。

2026-11-06：[seed2的48条跨seed共性筛选](crossing_analysis/seed2_multiseed48/README.md)完成。用户简化为同episode任务失败交集：17条五seed均失败，47条至少两seed失败；不将其他seed的失败原因自动视作Crossing错选。仅离线读取已有数据。

2026-11-06：[无全景v001新版可视化](agent_route_choice/v001/run_20261106_01/exports/run_20261106_03/README.md)已交付：完整737帧、地图/RGB同步双进度条、一键回Crossing，31条支路及原选择保留。737帧实际浏览器验证通过；仅CPU导出，无模型调用。

2026-11-06 已完成：[外部Agent v002 / Qwen27B十条](agent_route_choice/v002/run_20261106_01/README.md)，20次响应、38条支路，第二轮全部证据不足、选择0条。GPU0已释放，中文全景/支路/俯视地图HTML已交付并通过浏览器检查。空路线描述兼容修复仅离线复核，9条通过其余协议，第7条缺全景来路引用；不是9条正确。

2026-11-06：[外部Agent v002 / 本地Qwen27B](agent_route_choice/v002/run_20261106_01/README.md)原十条离线选路已启动，计划20次独立调用，GPU0单卡。新12/16图协议、完整清单传递及两类排除校验已接入，8项CPU检查通过。运行完成后交付中文全景/支路/最终选择/俯视地图HTML；历史准备状态不代表当前状态。

2026-11-06：[外部Agent v002提示词第1稿](agent_route_choice/v002/prompts/draft01/README.md)已完成英文与中文对照，重点修改360°支路盘点与来路识别，第二轮完整清单传递及两类路线排除。仅提示词准备，运行链路尚未接入，无新模型调用。

<!-- AGENT_ROUTE_360_CAPTURE_START -->
2026-11-06T06:58:35.413777+00:00：外部 Agent v002 的原十条360°画面补采完成：八场景、九个Crossing、72张唯一RGB（十条引用80张）。本轮复用64张，新增8张。图像哈希、640×480、固定光心、八方向覆盖、不同方位像素差异及离线浏览器检查通过；模型调用0次、导航动作0次，本次仿真进程已退出。原图与相机元数据位于 `outputs/agent_route_choice/v002/capture_20261106_04/panoramas/`；中文预览位于同目录 `exports/run_20261106_01/crossing_360_zh.html`，原图压缩包为 `crossing_360_images.zip`。尚未进行Qwen支路识别/选路，视觉语义复核另记。
<!-- AGENT_ROUTE_360_CAPTURE_END -->

2026-11-06：[外部 Agent v002 360°补采](agent_route_choice/v002/capture_20261106_04/README.md)已完成：原十条、九个点、72张图，中文离线预览及原图ZIP已生成，图像、浏览器和ZIP校验通过。本项目仿真进程已退出，尚未启动新选路推理；前三轮及复用来源保留。

新 Codex 先读仓库 `AGENTS.md` 和 `docs/STATUS.md`，再阅读对应类别与具体实验 README。
更新时间：2026-11-05（Crossing 03版双进度条HTML已固化为以后每轮默认模板并接入自动导出，验证通过）。状态来自已有结果文件；不将历史 PID 当作实时状态。

| 类别 | 内容 | 当前记录 |
| --- | --- | --- |
| [外部 Agent 复位后选路](agent_route_choice/README.md) | 已知 Crossing，两次独立调用：盘点支路→识错并重新选路 | 2026-11-06 Qwen32B十条/20次响应完成，9条协议有效、sample_07选择已排除支路而无效；语义复核未完成，HTML已导出、GPU已释放。GLM因1113无额度停止，0回答 ；[中文可视化](../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/agent_route_choice_qwen32b_zh.html)已交付并通过浏览器验证 ；[新版：判断帧＋支路＋选择](../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/crossing_branches_choice_zh.html) |
| [原模型复现](reproduction/README.md) | StreamVLN、InternVLA-N1、初始六路验证 | StreamVLN 1250/1250；N1 历史状态 50/825，运行错误阻塞 |
| [Crossing 分析](crossing_analysis/README.md) | 25 条地图复核、seed2 错误归因 | 已有报告；48/250 归因为 crossing 错选 |
| [Crossing 存档点](crossing_checkpoint/README.md) | 27B 离线因果回放与方法迭代 | v001 开发集 8 条完成；40 条验证未运行 |
| [Crossing v002](crossing_checkpoint/v002/README.md) | 5条开发、15条验证，按证据迭代 | 全部完成：两次修改未改善，按预算退出；基准验证TP3/FP4/FN20，F1 20.00%；统一离线HTML、报告审计及实际浏览器检查完成，GPU已释放 |
| [Crossing v003固定5条](crossing_checkpoint/v003/run_20261105_01/README.md) | 第2稿prompt，原5条离线轨迹，每两动作步调用一次 | 146次计划调用；自动评分、按默认模板导出、清理GPU；最新状态见下方 |
| [27B 单卡部署验证](crossing_checkpoint/single_gpu_smoke/README.md) | GPU 0、TP=1、单并发，三个既有八帧请求 | 三个请求通过，测试服务已释放 |
| [Crossing默认可视化模板](crossing_checkpoint/visualization_template/README.md) | 每轮自动导出，地图/RGB旁同步进度条 | 单版、自动双版和完整四版验证通过；不启动推理 |
| [Oracle 恢复](oracle_recovery/README.md) | 原五组及新共享前缀三分支语义延迟 | 原50条完成，尽早全成功组已按新模板单独导出；新配对实验10/10完成，30项结果（22个实际分支、8项未触发），离线HTML与下降原因分析已完成，GPU已释放 |
| [跌倒重试](fall_retry/README.md) | reset 与历史动作重放 | 41+40 条完成；直接回退补测取消 |

<!-- CROSSING_V003_BATCH_STATUS_START -->
已完成；5条固定离线样本，每2个动作步调用一次。 TP 4 / FP 2 / FN 9。 GPU已释放。
<!-- CROSSING_V003_BATCH_STATUS_END -->

## 存放与命名

每个类别和每个具体实验目录都必须有 README。使用清晰稳定的名称；方法迭代用 v001/v002，具体运行使用 run_日期_序号。
公共实现继续放 core/、scripts/；实验专属配置、任务清单、轻量摘要放本目录并纳入版本管理。
大体积轨迹、日志、视频、HTML 放 outputs/，README 用相对链接关联。历史产物和冻结源码不搬动、不改写。
新实验建议使用 outputs/<类别>/<实验>/<运行编号>/，保存 manifest.json、status.json、logs/、results/、summary.json、report/。
模型放 Resource_Peng/models，数据、场景等放 Resource_Peng/assets，不进入仓库。

## 必须及时记录

1. 开始前：建立 README，固定问题、方法版本、样本清单、seed、指标、停止条件和命令。
2. 修改时：同步记录方法变化；修改协议不能覆盖旧版结果。修复代码要标注受影响运行。
3. 收尾时：补齐结果、限制、产物位置、状态、下一步和更新时间，同时更新本索引与 docs/STATUS.md。
4. 重跑使用新运行目录；记录实际 Git 提交和工作区差异/源码快照，不能拿整理时的 HEAD 冒充历史版本。
5. 正常结束、失败、取消后释放自己的闲置 GPU。停止前核实进程归属。不得自动恢复取消的任务。

模板见 [具体实验 README 模板](TEMPLATE.md)。文档里的命令供查阅，不代表新一轮运行授权。
历史文档可能记录旧状态，当前索引与对应最新原始结果优先；索引不替代原始证据。


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

2026-11-07：[Oracle十条四条件回放发布](oracle_recovery/four_conditions_publication/README.md)完成：尽早组＋短/中/长语义延迟，双语任务指令与按需媒体，原实验未重跑。[在线入口](http://134.175.18.101/vln/oracle_four_conditions_20261107_01/index.html)。仅三档延迟共享前缀，尽早组为独立历史运行。

2026-11-07：Qwen27B人工错误集[双语在线选路回放](http://134.175.18.101/vln/qwen27b_human33_20261107_01/crossing_two_stage_review.html)已发布。33条轨迹/34错误点完整保留；用户提供人工选路复核18/33（54.5%），无逐点标签映射，不混为导航成功率。467条英文自然语言完整翻译可切换，原回答不变；本地34例/3161帧及双滑条检查、全部远端哈希与入口HEAD通过。记录：experiments/agent_route_choice/human_v002/run_20261107_01/exports/online_20261107_01/README.md。未启动新模型或导航。

2026-11-07：七例独立R2R纠错指令生成与部署检查已准备；见 experiments/agent_recovery/r2r_v001/run_20261107_01/README.md。按用户要求后台运行，不持续跟踪；物理恢复尚未执行。


后台部署结果：{"phase": "failed", "pid": 1855535, "started_at": "2026-11-07T09:24:00.232022+00:00", "gpu": 0, "qwen_pid": 1855958, "base_url": "http://127.0.0.1:43351/v1", "updated_at": "2026-11-07T09:48:57.696716+00:00", "sample": "sample_34", "instructions": 7, "streamvln_pid": 1866191, "error": "KeyboardInterrupt: Termination requested", "finished_at": "2026-11-07T09:48:57.696700+00:00", "gpu_released": true}。仅指令生成和环境加载检查；七例物理恢复尚未执行。

2026-11-07：用户明确停止七例v001部署队列，原因是指令过长并延伸至房间/后续路线；向已核验主管1855535发送SIGTERM。旧七条结果保留且不执行。新最小局部纠正prompt见 experiments/agent_recovery/r2r_v002/，仅方向输入，未调用模型或导航，不自动重启。

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

2026-11-08：外部Agent局部纠正 **[v007](agent_recovery/r2r_v007/README.md)为用户指定的当前最优prompt**；[七例结果](agent_recovery/r2r_v007/run_20261108_01/README.md)，[统一指针](agent_recovery/current_best.json)。保留原答，不重跑；实际恢复导航尚未验证。

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
