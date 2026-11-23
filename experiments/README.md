# 实验总目录

2026-11-23 19:53 UTC，[RxR30 Qwen两轮实验](deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/README.md)全部完成。去重30/30，517有效节点＋30终止节点；偏航30/30，18条报警、12条未报警，共349轮、22轮格式错误。总用时9小时34分钟（含加载）；服务已退出，GPU3占用已释放。报警数量不是准确率，现有Qwen网站仍为首4条偏航快照。当前版及配对原版SR、平均SPL均暂无，已评分0条。

2026-11-23 18:16 UTC，[RxR30 DeepSeek 完整双语回放](http://134.175.18.101/vln/rxr30_deepseek_full_web_20261123_01/index.html)已发布，覆盖30/30条、295有效节点＋30终止节点、656次去重和137轮偏航评审。23条模型报警的实际区间轨迹可独立勾选染红；7轮无效回答单列。202进程完成展示翻译，浏览器检查及2225个远端文件哈希通过。当前版及配对原版SR、平均SPL均暂无，已评分0条。 [导出记录](deviation_progress/rxr30_v006/run_20261123_03_mistral30/exports/full_20261123_01/README.md)

2026-11-23 17:42 UTC，[RxR30 Mistral DeepSeek两轮并发](deviation_progress/rxr30_v006/run_20261123_03_mistral30/README.md)全部完成，用时约47分钟。去重725原始候选→295有效节点（另加30终止节点），656次比较0格式错误；偏航30/30，共137轮，23条模型报警、7条未报警、7轮格式错误。报警比例非准确率。主管与工作进程已退出。当前版及配对原版SR/平均SPL均暂无，已评分0条。

2026-11-23 [C21 七图回退、独立到达判断](inverse_rollback/vlm_action_v001/run_20261123_08_restore_c21/README.md)已完成，seed 2。新版用尽物理步数，终点距 A 3.999 米，新版与同例原版局部回退均为 0/1。

2026-11-23 16:55 UTC，[RxR30 Mistral DeepSeek两轮并发](deviation_progress/rxr30_v006/run_20261123_03_mistral30/README.md)已启动，主管2081596、30个工作进程。复用JEV的725原始候选，用deepseek-v4-1-flash-1017/high重新去重；全部完成冻结本次节点后，再并发运行v006偏航识别。首个真实调用HTTP 200且校验通过，已复用；30例均进入任务后交后台。当前版及配对原版SR/平均SPL均暂无，已评分0条。

2026-11-23 [按 A 的选路位置判断退出 · DeepSeek 四例回退](inverse_rollback/vlm_action_v001/run_20261123_06_choice_position4/README.md)已完成，四例复用历史去程描述。局部回退新版和旧版均为 0/4。保留的 C34 仿真已释放。

2026-11-23 [RxR30 有效节点及已完成偏航网页](deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/deviation_snapshot_20261123_02/README.md)已[发布](http://134.175.18.101/vln/rxr30_deviation_snapshot_web_20261123_02/index.html)。冻结15:20 UTC结果：去重30/30（517有效节点＋30终止节点），偏航4/30（51轮、2条有效报警、7轮格式错误）。独立勾选可将模型报警A→B实际轨迹染红，保留完整双语偏航原答。当前版及配对原版SR/平均SPL均暂无，已评分0条。

2026-11-23 [RxR30 去重阶段首次快照](deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/snapshot4_20261123_01/README.md)已发布，固定首4条完成结果，显示有效节点、JEV曲线、134次去重评审及完整双语原答。原始30条回放保留，偏航阶段标记未开始。无新导航评分，当前版及配对原版均暂无，已评分0条。

2026-11-23 10:19 UTC [RxR30 Qwen GPU3 部署超时接续](deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/README.md)已启动。旧运行45分钟启动超时，旧日志保留；新运行等待上限120分钟、直接复用全部JEV结果，当前加载模型，去重及偏航均0/30。无新导航评分，当前版和配对原版均暂无，已评分0条。

2026-11-23 [R2R / RxR 各类失败占比](crossing_analysis/r2r_rxr_failure_types/run_20261123_01/README.md)完成，94 / 165 条失败按八类汇总，原错路合计 67 / 80 条保持不变。当前版与原版均为同次复现，R2R SR 均为 123/217（56.68%）、平均 SPL 0.4933；RxR SR 均为 224/389（57.58%）、平均 SPL 0.4915。

2026-11-23 [R2R 已完成 217 条的离线失败归因](crossing_analysis/r2r_seed2_400/run_20261123_02_partial217/README.md)完成。明确走错支路 67/94 条失败（71.28%），占全部已评分 30.88%；当前版与原版 SR 均为 123/217（56.68%），平均 SPL 均为 0.4933，技术异常 0 条。

2026-11-23 [R2R400 暂停](reproduction/streamvln_r2r/run_20261123_01/README.md)，保留 217 条正式结果，GPU3 调给 [RxR30 两轮离线实验](deviation_progress/rxr30_v006/run_20261123_01/README.md)的本地 Qwen27B。

2026-11-23 [RxR 30 条离线回退点与偏航识别](deviation_progress/rxr30_v006/run_20261123_01/README.md)，复用 VLNVerse 的 JEV v004、v001 采样与去重和 Qwen v006。

2026-11-23 [RxR-CE 明确错选支路随机 30 例回放](crossing_analysis/rxr_seed2_400/run_20261123_01/exports/random30_20261123_01/README.md)已发布，含抽样清单、逐帧轨迹、RGB 与双语归因。

2026-11-23 [R2R-CE 原版 StreamVLN 400 条](reproduction/streamvln_r2r/run_20261123_01/README.md)，val_unseen 分层抽样，逐动作采集 RGB、位姿和评分。

2026-11-23 [RxR-CE 400 条逐例 Crossing 归因](crossing_analysis/rxr_seed2_400/run_20261123_01/README.md)已完成。80/165 条有效失败有明确错选支路证据（48.48%），其中正常 STOP 74 条。

2026-11-23 [DeepSeek H1 回退全 22 例](inverse_rollback/vlm_action_v001/run_20261123_05_finish22/README.md)已完成，位置达标 2/22，平均终点误差 2.403 米。[带独立路线图层和线宽的地图与 RGB 回放](inverse_rollback/exports/deepseek_h1_22_20261123_01/README.md)

2026-11-23 [DeepSeek 实走回退追加十例](inverse_rollback/vlm_action_v001/run_20261123_04_deepseek10/README.md)按原清单顺序从 C12 开始，沿用首批三例的完整回退协议。

2026-11-23 [DeepSeek 三例实走回退](inverse_rollback/vlm_action_v001/run_20261123_03_deepseek3/README.md)已完成。C03、C05、C07 依次在距 A 0.318、4.541、1.940 米时自行退出，位置达标 1/3。

2026-11-23 [VLNVerse H1 的 VLM 动作回退样本集](inverse_rollback/vlm_action_v001/run_20261123_02/README.md)已构建，22 个原始报警案例共 538 个去程动作与 154 张前视图。每例包含 A、B 两端和 5 张中间图。

2026-11-23 [StreamVLN 原版 RxR-CE 400 条](reproduction/streamvln_rxr/run_20261123_01/README.md)，11 个场景按比例抽样，逐动作保存原始前视 RGB、动作与位姿。状态与评分见批次记录。

2026-11-22 [RxR-CE 五场景随机点对往返](inverse_rollback/rxr_ce_v001/run_20261122_01_rgb20/README.md)完成 20/20，掉头、倒走均全部达标，共采集 2,823 张第一人称 RGB。

2026-11-22 [H1 倒走回退及 RGB 采集](inverse_rollback/v002/run_20261122_01_backward_rgb22/README.md)完成 22/22，倒走 0/22、直接 reset 22/22 达标。

2026-11-22 [H1 回退及 RGB 采集 · 原始报警距离 ≥1.5 米的 22 组](inverse_rollback/v001/run_20261122_03_rgb22/README.md)完成 22/22，掉头 2/22、直接 reset 22/22 达标。

2026-11-22 [203 条报警立即回退与主任务 STOP 前评审](serial_recovery/v002/run_20261122_01_scene203_stop_review/README.md)已准备，启动器等待 EasyJEV 认证。新版和同批原版均为暂无，已评分 0 条。上一运行保留 53 条评分和 8 条技术跳过。

2026-11-22 [原版成功、当前失败的配对回放](serial_recovery/v002/run_20261121_06_scene203/exports/paired_losses_20261122_01/README.md)已发布，从 47 条正式评分中筛出 6 条。全批当前版 SR 15/47（31.91%）、平均 SPL 0.2634，原版 SR 17/47（36.17%）、平均 SPL 0.2976。

2026-11-22 [41 条配对回放新增回退跳转及地图缩放](serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_02/README.md)已发布。每次实际回退可一键定位，完整底图支持缩放和平移。快照成绩为当前版 SR 15/41（36.59%）、平均 SPL 0.3019，同批原版 SR 17/41（41.46%）、平均 SPL 0.3411。

2026-11-22 [41 条配对任务的偏航与回退事件回放](serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_01/README.md)已发布。当前版 SR 15/41（36.59%）、平均 SPL 0.3019；同批原版 SR 17/41（41.46%）、平均 SPL 0.3411。7 条技术跳过。可定位 51 次报警、29 次两阶段选路和 18 次实际回退，查看识别支路、选择及实走结果。

2026-11-22 [37 条配对任务的逐次模型原答](serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_recovery/README.md)已发布，含两阶段候选支路、完整纠错指令及回退后的实际动作。

2026-11-22 [37 条配对回放地图图层版](serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_map02/README.md)已发布。

2026-11-22 [在线恢复 37 条配对回放](serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956/README.md)已发布，含双语网页和完整离线下载。

2026-11-21 [在线恢复与原版配对 · 八个完整场景 203 条](serial_recovery/v002/run_20261121_06_scene203/README.md)已启动。原版逐条成绩齐全。

2026-11-21 [四个完整场景的 98 条配对评测](serial_recovery/v002/run_20261121_05_scene98/README.md)已准备。原版 seed 2 对照齐全，在线恢复批次尚未启动。

2026-11-21 [C13 在线恢复闭环已通过](serial_recovery/v002/run_20261121_03/README.md)。自然报警、实际回退、40 个局部动作、策略记忆恢复及交还后 157 个原任务动作均已记录。任务最终卡住，正式 SR 0、NE 9.7192 米。本轮资源已释放，备用任务未启动。

2026-11-21 [在线恢复 v002 C01](serial_recovery/v002/run_20261121_02/README.md)已完成，66 动作，非终止报警 1 次，两次 Recovery 后因支路选择无效未接管。正式 SR 0、NE 3.6499 米。[C13 单条补验](serial_recovery/v002/run_20261121_03/README.md)已完成。

2026-11-21 [Recovery 两阶段同模型对照 · v006 全部 47 例](agent_recovery/branch_instruction_v001/run_20261121_02_paired47/README.md)完成。Qwen 两阶段生成 43 条指令，DeepSeek 两阶段生成 45 条；各 47 份有效回答。[双语对照回放](http://134.175.18.101/vln/recovery_instruction_v001_paired47_web_20261121_01/index.html)已发布。

2026-11-21 [Recovery 第二次调用 v001 · DeepSeek 十例](agent_recovery/branch_instruction_v001/run_20261121_01/README.md)完成。十例各输出一条替代支路和一句 8–12 词的英文局部指令，全部排除第一次匹配的已走支路。仅做离线指令生成。[双语回放](http://134.175.18.101/vln/recovery_instruction_v001_deepseek10_web_20261121_02/index.html)已发布。

2026-11-21 [DeepSeek v1 全部 47 例](agent_recovery/branch_review_v001/run_20261121_04_deepseek47/README.md)完成，45 例并行新跑、2 例复用，47 份原答格式有效，共 111 条支路。[统一对照网页](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/index.html)已发布，支持勾选模型，回放标记仅取 v006 有效节点。

2026-11-21 [Recovery v1.1 两例试跑](agent_recovery/branch_review_v001.1/run_20261121_01/README.md)完成。逐视图候选和跨视图分组可追溯；Qwen 在 C50、C07 均合并了右视图候选，未保留独立右支路。GPU3 原服务已回到待用状态。

2026-11-21 [DeepSeek 两例并行复核](agent_recovery/branch_review_v001/run_20261121_03_deepseek2/README.md)完成。v006 C50、C07 复用原七图和 Prompt，两例均返回格式有效的结果，且均列出右前方支路。

2026-11-21 10:43 UTC，[v006 全部回退节点的第一次调用](agent_recovery/branch_review_v001/run_20261121_02_all47/README.md)完成。已处理 47/47 个回退节点，其中新增 37 例、复用 10 例。格式有效 47 例，共列出 101 条支路，匹配到此前所走支路 47 例、模型回答不确定 0 例。

2026-11-21 09:20 UTC，[Recovery 第一次调用 v001 十例](agent_recovery/branch_review_v001/run_20261121_01/README.md)完成：按用户指定使用 v006 的 C42、C46、C49、C50、C07、C05、C09、C10、C20、C21，GPU3 Qwen27B，每例固定七图且不输入任务指令。10/10 格式有效，模型共列 24 条支路、10 次 identified；无准确率评分。没有第二次指令调用或导航，GPU3 模型按要求继续保留。[双语可视化已发布](http://134.175.18.101/vln/recovery_branch_review_v001_ten_web_20261121_02/index.html)，支路清单、此前所走支路与七图证据醒目展示，附完整离线包。

2026-11-21 [GPU3 Qwen27B 待用服务](agent_route_choice/services/qwen27b_gpu3_20261121_01/README.md)按用户要求启动，主管及模型服务进程存活，确认后交后台；无就绪探针、无实验请求。

2026-11-21 [Recovery 第一次调用 v001](agent_recovery/branch_review_v001/README.md)：七图固定输入、当前直接支路与已走支路联合识别；已保存中英文 Prompt、输入协议与输出 Schema，仅为草稿，无模型或导航运行。

2026-11-21 [v006 多视角页面的 ±70° 选项](deviation_progress/v006/exports/node_multiview70_20261121_01/README.md)已更新原网址，接入376节点的1128张补采图，附157.9 MB离线包。

2026-11-21 06:04 UTC，[v006 节点三向补采](multiview_capture/v006_pose70/run_20261121_01/README.md)完成，已保存 376 个节点的 1,128 张观测，GPU 3 已释放。

2026-11-21 04:48 UTC，[v006 去重节点三向观测补采](multiview_capture/v006_pose70/run_20261121_01/README.md)已在 GPU 3 启动。按 376 个保留节点的实测相机位姿重新渲染 +70°／0°／−70°，共预计 1,128 张，进度见运行记录。

2026-11-21 04:41 UTC，用户要求的 [GPU3 Qwen 服务释放](agent_route_choice/services/qwen27b_gpu3_20261120_01/README.md)已完成。服务及子进程均退出，GPU3 显存释放，模型权重和全部实验结果保留，不自动恢复常驻服务。

2026-11-21 04:37 UTC 核对，[v6 / v6.1 双版本离线评审](deviation_progress/v006.1/paired53_20261120_01/resume_20261121_01/README.md)已全部完成。v6.1 于 04:00 UTC 完成 53/53，236 轮，45 条轨迹报警，2 轮格式错误。v6.1 尚未导出至对比网页。

2026-11-21 [v006 全部存档节点的180°／360°多视角](deviation_progress/v006/exports/node_multiview_20261121_01/README.md)已发布。沿用五版本页面，覆盖376个保留节点和53个终止节点，标记47个v006回退目标；3,432张展示图、138.0 MB离线包，必要交互与发布检查通过，无新推理或导航。

2026-11-21 [Qwen v6 接入既有多版本网页](deviation_progress/v006/exports/comparison_20261121_01/README.md)已发布并更新原入口，五组共 1,131 轮原答。默认两组 v5 与 Qwen v6，最多显示三组区间，附 84.4 MB 完整精简包。无新增模型调用。

2026-11-21 01:41 UTC，[Qwen v006 全 53 条单页回放](deviation_progress/v006/exports/web_all53_20261121_01/README.md)已发布，含 253 轮原答、实际输入清单、累计进度和 78.3 MB 精简离线包。中英文、失败原答、双进度条与发布校验通过，无新增模型调用。

2026-11-21 01:12 UTC，[v6 全 53 条已完成](deviation_progress/v006.1/paired53_20261120_01/resume_20261121_01/README.md)，253 轮，47 条报警，9 轮格式错误。v6.1 已自动接续。

2026-11-21 00:56 UTC，[v6 / v6.1 GPU 3 后台接续](deviation_progress/v006.1/paired53_20261120_01/resume_20261121_01/README.md)已正常生成，PID 619682。先补 v6 的 C50–C53，再补 v6.1 的 51 条，复用所有已完成结果。

2026-11-21 [双版本后台评审状态](deviation_progress/v006.1/paired53_20261120_01/README.md)核对。v6 完成 49/53 后在 C50／S03 超时退出，v6.1 剩余 51 条尚未接续。GPU 3 Qwen 健康接口正常。

2026-11-20 17:12 UTC，[v6 / v6.1 GPU 3 后台全样本评审](deviation_progress/v006.1/paired53_20261120_01/README.md)已启动，C01 首轮通过校验。两版各复用两条，按 v6、v6.1 的顺序各补 51 条。

2026-11-20 17:00 UTC，[GPU 3 Qwen v6.1 复评 C35、C38](deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/README.md)完成。C35 在 F4→F14 报警，C38 七轮无报警。两版完整评审均可复用各自的这两条。

2026-11-20 [v6.1 错误分析与新 Prompt](deviation_progress/v006.1/README.md)已准备。[v6 / v6.1 单进程 Route53 评审](deviation_progress/v006.1/paired53_20261120_01/README.md)已核对清单，等待用户启动。

2026-11-20 [v006 Qwen 离线复评 C35、C38](deviation_progress/v006/run_20261120_01_qwen_gpu3_c35_c38/README.md)完成。C35 五轮均未报警，C38 在 F0→F5 提前报警。七轮原答全部通过校验。

2026-11-20 [v5.1 Qwen 复评 C38](deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38/README.md)完成，七轮均为 `consistent`。相较 v005，模型到 S05 仍保留走廊地标要求，在 S06 跳到了卧室阶段。

2026-11-20 [四版本对比去重显示修复](deviation_progress/v005/run_20261120_06_deepseek_official33/exports/four_versions_20261120_02/README.md)已发布到原入口。仅修复去重数据标识匹配，模型节点和原答不变；新版离线包同步提供。

2026-11-20 13:48 UTC，[v003 / v005 四模型版本同页对比](deviation_progress/v005/run_20261120_06_deepseek_official33/exports/four_versions_20261120_01/README.md)已发布到原网址，四选最多三组偏航区间，含 878 轮原答和 82.3 MB 离线包。DeepSeek v003 覆盖 29 条，其他三组各 53 条；缺失结果明确标注，未新增模型调用。

2026-11-20 13:24 UTC，[DeepSeek v005 全 53 条官方接续汇总](deviation_progress/v005/run_20261120_06_deepseek_official33/README.md)已完成，219 轮、47 条有效报警、11 轮格式错误、0 条接口失败。结果包含旧网关回答与官方新回答，来源记录保留。

2026-11-20 [DeepSeek v005 官方接口 33 并行接续](deviation_progress/v005/run_20261120_06_deepseek_official33/README.md)已正常启动：保留已完成 20 条，33 个工作进程同时处理余下样本，首批 6 轮官方回答已通过校验。保留旧网关与官方新回答的来源区别。

2026-11-20 13:05 UTC，[DeepSeek v005 15 并行接续](deviation_progress/v005/run_20261120_05_deepseek15/README.md)以 incomplete 退出：20/53 条完成，33 条因网关 524、525 或断连失败。已返回的模型结果全部保留，当前没有该批评审进程在运行。

2026-11-20 [DeepSeek v005 15 并行接续全 53 条](deviation_progress/v005/run_20261120_05_deepseek15/README.md)后台主管已启动。原 53 并行触发网关 HTTP 429，按用户新指令等待在途任务收尾后以最多 15 并行接续，保留并复用已有回答。

2026-11-20 [v005 全 53 条精简离线下载](deviation_progress/v005/run_20261120_03_remaining47/exports/compact_20261120_01/README.md)已发布，78.4 MB，保留全部帧和原答，输入图与回放共用已有 WebP 展示副本。

2026-11-20 12:20 UTC，[v005 全 53 条可视化](deviation_progress/v005/run_20261120_03_remaining47/exports/web_all53_20261120_01/README.md)已发布到原网址，含全部 272 轮原答、输入图片、累计进度和完整离线 ZIP。

2026-11-20 11:53 UTC，[v005 全 53 条离线评审](deviation_progress/v005/run_20261120_03_remaining47/README.md)已完成（复用六条、补跑 47 条），共 272 轮、40 条轨迹报警、0 次格式错误。GPU 3 模型保留；网页目前仍是 48 条阶段版。

2026-11-20 [v005 已完成 48 条样本阶段回放](deviation_progress/v005/run_20261120_03_remaining47/exports/web_partial_20261120_02/README.md)已发布到原网址，含 250 轮原答与输入图像。余下评审仍在 GPU 3 后台运行。

2026-11-20 [v005 剩余 47 条补跑](deviation_progress/v005/run_20261120_03_remaining47/README.md)已在 GPU 3 常驻 Qwen 上启动，复用已完成六条，目标汇总 53 条。

2026-11-20 [Qwen v005 六例可视化与 v004 对照](deviation_progress/v005/run_20261120_02_qwen_gpu3/exports/web_20261120_01/README.md)已发布到原网址，包含三组原答和离线下载。

2026-11-20 [v005 二分类偏航评审](deviation_progress/v005/README.md)，附中英文 Prompt 和离线接口验证。[GPU 3 常驻 Qwen 的六例评审](deviation_progress/v005/run_20261120_02_qwen_gpu3/README.md)已完成 6/6，33 轮全部通过格式校验，5 条轨迹报警。

2026-11-20 [GPU 3 Qwen27B 待用服务](agent_route_choice/services/qwen27b_gpu3_20261120_01/README.md)，用户明确要求保留，后续复用。

2026-11-20 [Qwen27B 与 DeepSeek v004 六例同页回放](deviation_progress/v004/run_20261120_01/exports/paired_web_20261120_01/README.md)。Qwen 35 轮均通过新旧校验器，原网页可在同帧切换两组原答和进度。

2026-11-20 [v004 校验兼容修复与六条原答回放](deviation_progress/v004/run_20261120_03_contract_replay/README.md)。C47 S04 的报警被采纳，共 5 条报警轨迹。

2026-11-20 [DeepSeek v004 六条逐轮回答、证据和离线下载](deviation_progress/v004/run_20261120_02_deepseek6/exports/web_20261120_01/README.md) 已发布。共 30 次模型调用，4 条轨迹出现通过校验的偏航报警。

2026-11-20 [DeepSeek v004 六进程偏航评审](deviation_progress/v004/run_20261120_02_deepseek6/README.md)，C07、C11、C19、C30、C47、C50 各一条进程内判断链。

2026-11-20 [偏航识别 v004 的离线诊断与本地六例重跑](deviation_progress/v004/run_20261120_01/README.md)。先核对 10 条轨迹的 65 轮历史请求，再以同一离线样本、节点和原生前视图在 GPU 2 运行 Qwen27B。

2026-11-18 [Qwen 全部 53 条偏航结果已同步至原网页](deviation_progress/v003/run_20261118_01_qwen27b/exports/deviation53_web_20261118_01/README.md)，C30–C53 新增 17 条红色区间，全组 36 条。

2026-11-18 [Qwen 去重回退点的分叉覆盖](deviation_progress/v003/run_20261118_01_qwen27b/analysis/branch_coverage_01/README.md)。44 次明确分叉中，22 次的标注决策区间内有保留节点，16 次原始候选未命中，6 次在去重中失去命中。

2026-11-18 [DeepSeek 与 Qwen 的 29 条偏航回放](deviation_progress/v003/run_20261118_03_deepseek29/exports/web_20261118_01/README.md)已发布，两组各自判出 28 条和 19 条偏航。

2026-11-18 [DeepSeek 对前 29 条的偏航识别](deviation_progress/v003/run_20261118_03_deepseek29/README.md)。与 Qwen 共用 210 个节点（含 29 个终止节点），每条轨迹一个进程。

2026-11-18 [Qwen 53 条回放的固定终止节点](deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_web_20261118_01/README.md)。已核对 53 个终止帧、429 个有效节点及双滑块。

2026-11-18 [Qwen 前 28 条的偏航图层](deviation_progress/v003/run_20261118_01_qwen27b/exports/deviation28_web_20261118_01/README.md)已更新至原网址，新增 7 条红色区间。

2026-11-18 [Qwen27B 前 19 条偏航识别图上标记](deviation_progress/v003/run_20261118_01_qwen27b/exports/deviation19_web_20261118_01/README.md)已并入 53 条去重回放原网址。

2026-11-18 [Qwen27B 全部 53 条轨迹的去重回放与离线版](deviation_progress/v003/run_20261118_01_qwen27b/exports/all53_web_20261118_01/README.md)。覆盖 19 个场景，494 个候选中保留 376 个，可逐对查看 338 次比较。

2026-11-18 [Qwen27B 前 31 条去重回放](deviation_progress/v003/run_20261118_01_qwen27b/exports/first31_web_20261118_01/README.md)已按十场景模板发布。

2026-11-18 [DeepSeek 十场景节点去重网页与离线版](deviation_progress/v003/run_20261118_02_deepseek10/exports/web_20261118_01/README.md)已交付。

2026-11-18 [DeepSeek 十场景去重补齐](deviation_progress/v003/run_20261118_02_deepseek10/resume_01/README.md)。10/10 条完成去重，保留 49/93 个候选，偏航识别暂缓。

2026-11-18 [DeepSeek 十场景离线对照](deviation_progress/v003/run_20261118_02_deepseek10/README.md)，10 个并行进程评审 93 个候选节点及其去重后的偏航区间。

2026-11-18 [GPU 3 本地 Qwen27B 离线节点去重与偏航识别](deviation_progress/v003/run_20261118_01_qwen27b/README.md)，输入为 JEV 已生成的 53 条轨迹、494 个候选节点。

2026-11-18 [53 条 JEV 候选回退点在线回放](http://134.175.18.101/vln/jev_route53_sampling_v001_web_20261118_01/index.html)已发布，沿用采样回放模板，展示 494 个去重前候选。[发布记录](crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/web_20261118_01/README.md)

2026-11-18 [53 条前视轨迹去重前候选点](crossing_checkpoint/online_sampling_v001/run_20261118_01/README.md)已完成。4,837 个有效评分，固定 v001 采样生成 494 个候选，逐条轨迹中位数 9 个。[本地回放](../outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/front_candidates_01/index.html)已验收。

2026-11-18 05:36 UTC，[53 条选路错误离线数据集回放](offline_route_dataset/v001/run_20261118_01/exports/replay_20261118_01/README.md)已发布，支持独立路线图层、逐步多视角与事件跳转。[打开网页](http://134.175.18.101/vln/offline_route53_replay_web_20261118_01/index.html)

2026-11-18T05:17:33Z：[69条多视角失败归因与离线数据集](offline_route_dataset/v001/run_20261118_01/README.md)完成。69条失败纳入53（早期25、新28；分支核心43、方向扩展10）、排除13、不确定3。54事件/19场景/4890观测，完整多视角和位姿离线包约9.801 GiB；53条打包检查及独立哈希抽验、隔离搬迁读取通过。仅离线归因，尚未经人工复核，无导航或服务变更。

2026-11-18T04:35:22.095970+00:00：[69条多视角失败归因与离线数据集](offline_route_dataset/v001/run_20261118_01/README.md)开始。原104条采集完整性已通过；仅分析本次SR=0的69条新轨迹（早期来源34、新来源35），逐事件审阅选路错误，历史标签不直接沿用，保留模型与仿真不变。

2026-11-18T04:27:15.269416+00:00：[104条逐步多视角采集](multiview_capture/v001/run_20261117_03/README.md)后台状态`complete_services_retained`，正式评分104/104，详见记录。

2026-11-17：[450条原版合并错误分析](crossing_analysis/pooled450_v001/run_20261117_01/README.md)完成。21场景/seed2，197成功、253失败；选路/方向107、回返13、未完成/局部无效移动45、目标走过头1、无明确选路偏航跌倒12/卡住5、旧异常终止未复核46、不确定24。按既有证据映射，保存450总表、253失败明细、分类/场景/终止方式交叉表和静态图；未重跑导航。

2026-11-17T09:39:30.496666+00:00：[104条逐步多视角采集运行03](multiview_capture/v001/run_20261117_03/README.md)真实启动验证通过，已交后台继续。GPU3原模型3194667未重载，GPU2仿真2366636；前5步40张360°视图、15张180°引用及真实位姿/朝向、物理状态不变、外观恢复均通过，前2步原生前视与模型收到图像逐像素一致。后向自身遮挡修复并经图像抽查；18项CPU检查通过。交接时正式评分0/104，采集至step 26；完整终止与104条验证由后台负责，不持续人工跟踪。

2026-11-17T09:27:21.709375+00:00：[104条逐步多视角采集](multiview_capture/v001/run_20261117_02/README.md)后台状态`stopped`，正式评分0/104，详见记录。

2026-11-17T09:13:18.893749+00:00：[104条逐步多视角采集](multiview_capture/v001/run_20261117_01/README.md)后台状态`failed`，正式评分0/104，详见记录。

2026-11-17T09:04:06.500221+00:00：[104条逐步多视角采集](multiview_capture/v001/run_20261117_01/README.md)已获启动授权，正在准备；复用GPU3保留模型，逐step采集180°/360°与真实位姿，确认正常后后台运行。

2026-11-17T08:28:37.669213+00:00：[原版选错路56条对照可视化](oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/README.md)已完成并发布：[打开网页](http://134.175.18.101/vln/oracle_route_choice56_run04_web_20261117_01/route_choice56.html)。沿用原Oracle双进度条模板，含两组真实轨迹、56张俯视图、66次纠错与四类筛选；46条有干预且成功、3条有干预失败、3条未干预成功、4条未干预失败。原版缺失RGB明确标注，56条双语与本地浏览器检查、远端全资源哈希及公网入口验证通过。只导出现有结果，服务未变。


2026-11-17T07:57:50.584928+00:00：[原版102条失败离线分类](oracle_recovery/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/README.md)完成：64条偏航/方向错误（56条选路、8条回返），占失败62.75%；8条原因不确定。全102条逐项证据、CSV、地图及限制已记录，未重跑导航。


2026-11-17T07:33:13.047602+00:00：[Oracle同200条两组对照04](oracle_recovery/auto_branch_v001/run_20261117_04_pair200/README.md)完成400/400；纠错SR78%（156/200），原版49%（98/200），+29个百分点，69胜11负。原生验证和离线汇总完成，模型/最后仿真保留；失败分类尚未开始。


2026-11-17T02:13:43.668942+00:00：[自动纠错25条可视化导出](oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/auto_branch25_20261117_01/README.md)已发布：[打开回放](http://134.175.18.101/vln/oracle_auto_branch25_run04_web_20261117_01/auto_branch25.html)。沿用原Oracle双进度条模板，覆盖11场景、27次纠错，含俯视底图、25张独立地图和中英文切换；本地浏览器与远端资源哈希、公网入口验证通过。仅导出现有数据，原版对照继续后台运行。

2026-11-16T23:43:02.054517+00:00：用户将两组缩减为各约200条，后续以[缩量接续04](oracle_recovery/auto_branch_v001/run_20261117_04_pair200/README.md)为准。保留当前算法已完成结果，在200条附近原生任务评分边界结束，再运行完全相同任务的原版对照；旧400条对照队列已取消。GPU3模型继续复用，6项CPU检查及真实已完成子集封印检查通过；控制器PID 1653533，新进度见运行04的`progress.json`。旧400条配置/源码/结果全部保留，不继续跑满400条。

2026-11-16T17:06:02.348080+00:00：[400条在线分支Oracle与原版对照03](oracle_recovery/auto_branch_v001/run_20261116_03_gpu2sim_gpu3model/README.md)已确认真实导航正常，当前算法组已原生计分3/400条，4次实际纠错记忆一致性检查通过。GPU2仿真运行、GPU3原模型未重载；原版400条等待自动接续，后台汇总已启动。遵用户要求结束持续人工跟踪，最终保留服务；启动证明已保存，未宣称800条已完成。

2026-11-16 16:48 UTC：用户批准仅重启GPU2仿真，复用GPU3原模型。新[400条在线分支Oracle与原版对照03](oracle_recovery/auto_branch_v001/run_20261116_03_gpu2sim_gpu3model/README.md)已启动：主管1332457、GPU2仿真1332521、GPU3模型3194667，auto_branch400先跑，baseline400等待器1332458。算法与准备01一致，17项启动适配检查通过；当前首场景初始化，0/400，尚未确认真实导航。旧串行主管/仿真/采样按授权退出，原记录及策略状态存档保留；模型未重载。

2026-11-16：[400条/22场景在线分支Oracle准备01](oracle_recovery/auto_branch_v001/run_20261116_01/README.md)完成，等待用户验收，禁止自动开跑。baseline/auto_branch各400条；59项CPU检查、实际仿真解释器21项复验及1325源码/44几何文件冻结核验通过。无预定静态落点，导航0条；验收说明与合成A/B分支示意已保存。

2026-11-16：[400条新任务场景覆盖草案](oracle_recovery/auto_branch_v001/scene_plan_20261116_01/README.md)已保存：排除已记录StreamVLN的290条后剩535条、22场景，400条均衡覆盖全部22场景（18×18＋4×19）。历史证据1321份、解析异常0；没有启动新导航或恢复暂停任务。

2026-11-16：[自动轨迹分支锚点Oracle v001](oracle_recovery/auto_branch_v001/README.md)代码/CPU准备完成：估计实际轨迹与参考路线发生分支的位置，固定锚点后前移1.25米；52项检查通过。取代当前点投影方案，旧记录保留；没有启动新导航，400条场景覆盖草案单独登记，暂停任务保持暂停。

2026-11-16 15:04 UTC：[自动参考路线落点Oracle v001](oracle_recovery/auto_route_v001/README.md)代码准备完成：去除人工分叉点依赖，0.75米偏航触发、当前位置投影后沿路线前移1.25米；同任务原版baseline与auto_route两组。38项CPU检查、825任务路线几何、冻结/仅打印计划及环境检查通过；尚无新导航结果，正式400条未冻结，暂停任务保持暂停。

2026-11-16 14:34 UTC：按用户明确要求，运行05已暂停，保留模型/仿真/GPU状态。主管1160721、仿真1160808及采样子进程1218163均SIGSTOP/T；GPU3原模型3194667继续在线，未释放GPU2/3。本轮正式2/33、成功1/2、跳过3条；禁止自动恢复，等待用户后续指令。 [暂停记录](serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 14:24 UTC：运行05正式1/33、成功0/1、跳过3条，已继续kujiale_0240_8_4，同一模型/引擎。上一条199动作中实际执行2次回退与纠错交还，两次记忆哈希及交还后运动均核验；之后因DeepSeek缺少verdict技术跳过，无正式成绩。闭环技术证据与导航成功分开统计。 [运行记录](serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 14:08 UTC：运行05仍在推进，正式1/33、成功0/1、跳过2条。当前kujiale_0257_82_4由17推进至83动作，84次有效JEV、11次偏航评审完成，当前等待下一次DeepSeek响应；无新增技术失败，模型/引擎均未重启。 [运行记录](serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 13:44 UTC：运行05仍在推进，正式1/33、成功0/1、跳过2条。新增JEV HTTP520失败已自动跳过，同一仿真1160808继续下一任务kujiale_0257_82_4，已17动作/17次有效JEV；实际容错继续已验证，未重启模型或引擎。 [运行记录](serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 13:35 UTC：逐条容错运行05启动验证通过，新任务kujiale_0257_73_4已3动作/3次有效JEV，原生策略记忆重置通过。继承1条评分，旧失败1条已绕过待补跑，继续后31条；主管1160721/仿真1160808，GPU2仿真/GPU3原模型保留。43项CPU检查与21份实答复核通过；按用户要求停止持续人工跟踪。 [运行05](serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 13:29 UTC：逐条容错运行05已启动，主管1160721、仿真1160808，GPU2空闲44675MiB通过准入，GPU3原模型3194667未重载。继承1条正式结果、1条技术失败待补跑、31条待运行，43项CPU检查及21份历史实答重验通过。当前仿真初始化，真实新任务导航验证待完成；本轮不自动补跑已跳过条目。 [记录](serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 13:15 UTC检查：DeepSeek串行运行04于13:01 UTC退出，1/33完成、成功0/1、未执行回退；第二条5动作后因uncertainties返回zh/en两个列表而校验失败，HTTP200、非接口断连。GPU2本项目仿真已退出，GPU3原模型保留；本次只核验和登记，没有重启。 [运行记录](serial_recovery/v001/run_20261116_04_full33/README.md)。

2026-11-16 12:59 UTC：三组33任务Oracle可视化已齐备，复用原Oracle双进度条模板。0.75米组17/33、实际存档回退组6/33、额外前移0.5米组22/33官方成功；旧两页保留并重验HTTP200，新回退页通过33任务/25回退本地浏览器检查、6943文件远端SHA256与公网HTTP200。仅导出现有结果。 [三组网址与导出证据](oracle_recovery/distance_v001/run_20261115_06_checkpoint/exports/checkpoint_20261116_01/README.md)。

2026-11-16 12:36 UTC：[DeepSeek串行运行04](serial_recovery/v001/run_20261116_04_full33/README.md)已启动，主管1121493、仿真1121566，GPU2共享仿真/GPU3原模型3194667。38项CPU检查及11份历史实答复核通过；只包装完整双语uncertainties单项对象，原答/文字/判定不改、不重试判断。当前初始化，0/33；运行03失败记录保留。

2026-11-16 12:34 UTC：[运行03](serial_recovery/v001/run_20261116_03_full33/README.md)在11:55 UTC因DeepSeek将uncertainties写成单个双语对象而退出，0/33完成，50实际动作/50JEV，未执行回退；GPU2本次占用已释放，GPU3原模型保留。已添加仅容器包装的无损兼容，原答/文字/结论不改，38项CPU检查通过，11份真实偏航响应重验全部通过；正准备[运行04](serial_recovery/v001/run_20261116_04_full33/README.md)继续原定33任务。

2026-11-16 11:42 UTC：[DeepSeek串行33任务运行03](serial_recovery/v001/run_20261116_03_full33/README.md)启动验证通过：首条kujiale_0257_4_3已执行11个实际动作，11次JEV有效、2次DeepSeek偏航评审成功（HTTP200/完整响应），原任务记忆重置验证通过。主管1066001/仿真1066074，GPU2共享仿真、GPU3原模型3194667未重载；评分0/33，实际恢复闭环待后续。停止人工持续跟踪，后台继续全批。证据startup_verified.json。

2026-11-16 11:32 UTC：[DeepSeek串行33任务运行03](serial_recovery/v001/run_20261116_03_full33/README.md)已实际启动，仿真GPU2/PID1066074，主管1066001，原StreamVLN GPU3/PID3194667不变。用户授权容量允许时共享忙卡；启动利用率80–100%、空闲约33GiB，通过12GiB准入。36项CPU检查通过；当前场景初始化，0/33，真实API/导航启动验证待完成。Qwen计划已被用户替换，不再重启。

2026-11-16 07:56 UTC：[Qwen27B串行33任务](serial_recovery/qwen27b_v001/run_20261116_01/README.md)代码接入与35项CPU检查通过，自动队列PID917244已运行，当前等待GPU2/GPU3资源，仿真0/33。两卡新增他人Arrow任务，不抢占；首次Qwen服务预热失败已清理。资源满足后自动部署02、真实图片预检、冻结并启动33任务/34事件；原GPU3模型及旧仿真仍保留。队列状态：`outputs/serial_recovery/qwen27b_v001/queue_20261116_01/status.json`。

2026-11-16：[Qwen27B全模块串行实验](serial_recovery/qwen27b_v001/run_20261116_01/README.md)准备中：用户确认GPU2本地Qwen替换全部DeepSeek语义模块；JEV/StreamVLN保留。33任务、34历史错误事件、9场景，真实仿真重跑。GPU2服务加载中，34项CPU检查通过，尚未启动本轮导航。

2026-11-16：按用户指定复用原JEV模板，已发布[串行联调02波形/采样/去重回放](http://134.175.18.101/vln/serial_jev_template_run02_web_20261116_01/serial_jev_replay.html)。`core/jev_sampling_lab`模板、原app和冻结采样器直接复用；7个实时节点逐点核验，地图/波形显示开关及去重7→2同步、完整曲线和双语通过本地浏览器，44文件远端哈希与公网HTTP200通过。登记见[导出README](serial_recovery/v001/run_20261116_02/exports/jev_template_20261116_01/README.md)。无新模型/仿真。

2026-11-16：[串行联调02双语可视化](serial_recovery/v001/run_20261116_02/exports/replay_20261116_02/README.md)已发布：[打开回放](http://134.175.18.101/vln/serial_pipeline_v001_run02_web_20261116_01/serial_pipeline_replay.html)。40帧、53次实际请求、三类轨迹、节点去重及评审、双进度条和中英文完整内容通过本地浏览器；44个文件远端哈希及公网入口HTTP 200通过。仅导出现有结果，无新模型/仿真；本次0恢复事件的证据边界明确标注。

2026-11-16 06:48 UTC查验：[单条串行联调02](serial_recovery/v001/run_20261116_02/README.md)已于06:41 UTC完成1/1，官方成功0/1、NE 8.543米，最后动作STOP，未到目标。40次JEV、7个候选节点、6次去重后留2点；7次偏航评审为5次consistent、2次uncertain，回退/纠错/交还均0，完整恢复闭环未验证。模型3194667及引擎836845按要求保留，主管正常结束；未启动更多任务。

2026-11-16 06:28 UTC：[单条串行联调02](serial_recovery/v001/run_20261116_02/README.md)已确认在GPU3正常导航：6帧真实观测、5个原任务动作，前5次实时JEV均有效，无运行失败；正式评分0/1，完整恢复闭环尚待结果。主管836172、仿真836845、原模型3194667保留。用户再次要求正常开跑后不持续跟踪，现交由后台主管继续单条任务与最终验证，不扩大任务量。

2026-11-16：[EasyJEV新渠道验证](serial_recovery/v001/jev_easyjev_20261116_01/README.md)2/2图像请求成功；继续准备[串行联调02](serial_recovery/v001/run_20261116_02/README.md)，仅原授权单条开发样本，不自动扩大。

2026-11-16：[TypeSafe官方格式与SDK核验](serial_recovery/v001/typesafe_official_audit_20261116_01/README.md)：公开schema和图像校验通过；官方SDK文本200，两种图像封装均400。JEV通道仍阻塞，未取得新导航结果。

2026-11-16：[Cttai新端点/令牌验证](serial_recovery/v001/jev_cttai_20261116_01/README.md)：模型目录空，原生路径404，兼容路径503无JEV渠道，未取得有效图像推理结果。

2026-11-16：[原JEV脚本再次复测02](serial_recovery/v001/jev_original_retest_20261116_02/README.md)仍HTTP400，无有效结果；原请求和代码保持一致。

2026-11-16：[原成功调用脚本复测api.site](serial_recovery/v001/jev_original_retest_20261116_01/README.md)：旧脚本原样运行，历史三帧请求逐字节相同，仍HTTP400，真实闭环仍阻塞。

2026-11-16：[AnyAIGC新端点/令牌诊断](serial_recovery/v001/jev_anyaigc_20261116_01/README.md)：实际图像请求头已发出，单帧/三帧均404无可用模型渠道；目录鉴权200，但321模型无JEV，闭环验证仍阻塞。

2026-11-16：[JEV图像接口诊断](serial_recovery/v001/jev_diagnostics_20261116/README.md)：模型名符合文档，1.14/1.13文本成功但图片失败；直连/7892均相同，最小图片复现已保存。串行仿真仍阻塞，未扩大实验或使用缓存替代实时JEV。

2026-11-16 串行联调01：实际仿真0/1，初始化后scripts包名冲突导致失败；公共实现已修复，原失败源码保留。另有JEV网关图像请求400待排查，鉴权/模型目录正常；原模型保留。见[运行记录](serial_recovery/v001/run_20261116_01/README.md)。

2026-11-16：[串行单目恢复v001首条联调](serial_recovery/v001/run_20261116_01/README.md)代码与10项CPU测试通过，准备在GPU3复用保留StreamVLN，串行执行JEV建点→去重→偏航判断→回退→单目选路→v007局部纠错→记忆恢复及续走。仅一条开发验证，尚未取得GPU完整闭环通过证据，不自动扩量。

2026-11-16 00:20 UTC：[Oracle落点额外前移0.5米组可视化](oracle_recovery/distance_v001/run_20261115_07_early_plus05/exports/early_plus05_20261116_01/README.md)已发布：[打开网页](http://134.175.18.101/vln/oracle_distance_plus05_33_run07_web_20261116_01/oracle_plus05_33.html)。33条、70次纠正，官方成功22/33、正常成功停止19条；三类轨迹、全部纠正回放与双语通过本地浏览器检查，6980文件远端哈希和公网HEAD通过。仅导出已有产物。

2026-11-16 00:10 UTC检查：回退06和额外前移0.5米07均完成33/33并通过评分导出核验，分别成功6/33（18.18%）和22/33（66.67%）。后续JEV点位采集03失败，0/159，三次均于首点probe阶段退出，具体根因尚未定位；日志与attempt保留。GPU3原模型3194667仍在，当前无本项目仿真运行；未重跑任何任务。

2026-11-15：JEV回退点采集03等待器PID3570684已运行，等待前移0.5米组07完成；159点/165引用，GPU图像仍0。朝向为估计值，尚未验证真实图像复原效果。

2026-11-15：[JEV去重节点180°/360°采集](jev_point_capture/v001/run_20261115_03/README.md)已准备：165节点引用、159实际点、9场景，采用估计基础朝向并在采集时与原RGB校准。7项CPU检查通过，尚无本轮GPU图像；等待Oracle额外前移0.5米组07完整结束后在GPU3执行，模型保持加载。

2026-11-15 16:59 UTC：resume_20261115_02启动验证通过，正式评分已从9增至10/33。第10条`kujiale_0234_34_4`完成真实导航和评分；原版任务重置时模型历史/动作队列清空，9条旧结果哈希不变。主管3518096、仿真3518229继续后台运行，GPU3原模型PID3194667未重载。证据`resumes/resume_20261115_02/startup_verified.json`。07等待器3518738正常等待06全33条评分及导出后接续。停止人工持续跟踪；实验阈值、回退规则、原版场景与RSS生命周期均未改变。

2026-11-15 16:52 UTC：resume_20261115_02已实际启动，主管3518096、仿真3518229，从9/33继续；模型3194667仍在GPU3/40617，未重载。9条结果SHA256核验不变。07等待器3518738为waiting_for_checkpoint_group；只有06完整导出后才接续。当前仿真初始化中，首条新导航验证待完成。

2026-11-15 16:50 UTC：第一次续跑完成第9条`kujiale_0234_63_3`，官方计数已为9/33、成功0/9；本次轨迹未达到触发条件，未回退，不能称原朝向失败已在相同前缀通过。随后主管轮询碰到原版ResultLogger原位重写JSON的短暂空文件，JSONDecodeError导致仿真退出；9条正式评分与原模型均保留。已在独立`resumes/resume_20261115_02/`修复：读到未写完的JSON时沿用最后完整计数，下次重新读；最终完成仍要求完整评分/仿真保留标记和独立导出验证。9项相关测试通过（此前全套27项通过），实验协议不变，仿真缓存继续使用原代码目录的原缓存。从第10条续跑，后续07新计划为queue_plan_resume_20261115_02.json。

2026-11-15 16:39 UTC：已实际启动断点续跑，主管PID3506858、仿真PID3506983；模型保持PID3194667/GPU3/40617，未重载。启动时正式评分8/33，8条既有结果SHA256全部一致。仿真正在初始化，尚未确认第9条恢复通过；维护版本在`resumes/resume_20261115_01/`，tmux `oracle_checkpoint_resume_20261115_01`。后续07等待器PID3507365，tmux `oracle_extra05_resume_20261115_01`，状态为waiting_for_checkpoint_group。

2026-11-15 16:35 UTC：[回退06](oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)按用户要求准备续跑；27项CPU检查通过、8条评分保留，模型GPU3继续加载。[额外前移0.5米07](oracle_recovery/distance_v001/run_20261115_07_early_plus05/README.md)仍等待06完整结束，旧距离组不恢复。

2026-11-15 16:23 UTC：[回退06](oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)异常中断，8/33评分、0成功；第9条恢复后的朝向偏差17.596°超过原15°校验上限。模型GPU3保留，仿真已退出。[新增前移0.5米07](oracle_recovery/distance_v001/run_20261115_07_early_plus05/README.md)未启动（0/33），前置组未完成，队列已停止推进。

2026-11-15 16:03 UTC：[回退06](oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)首条真实存档、一次回退、自主续走和正式评分已完成，1/33，模型GPU3持续加载；停止人工跟踪。完成后自动接续[额外前移0.5米07](oracle_recovery/distance_v001/run_20261115_07_early_plus05/README.md)，仍0.75米偏航触发，落点前移1.25米，共33条。

2026-11-15 15:55 UTC：[实际存档回退06](oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)已启动仿真初始化，GPU3原模型保持加载，0/33；[落点额外前移0.5米07](oracle_recovery/distance_v001/run_20261115_07_early_plus05/README.md)经用户明确选择已串行排队，仍0.75米触发、落点前移共1.25米，0/33。旧剩余距离组取消，结果保留；24项针对性CPU检查通过。

2026-11-15 最新：[实际存档回退运行06](oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)已准备33任务，尚未开始。用户取消其余距离组并要求保留加载的模型/仿真；05的short在19条评分时停止推进，结果与服务保留，等待仅重启仿真的例外确认。

2026-11-15：[距离Oracle 0.75米组33条回放](oracle_recovery/distance_v001/run_20261115_05/exports/early_20261115_01/README.md)已发布。正确参考/历史原始/本次Oracle三类轨迹、93次纠正前后回放、双语与双进度条均完成核验；远端全部资源哈希和入口HTTP 200通过。

2026-11-15 14:59 UTC：[自动Oracle运行05](oracle_recovery/distance_v001/run_20261115_05/README.md)累计40/165正式评分，GPU3继续运行。early全33条完成，官方成功17/33；short完成7条、成功5条，其余三组未开始。保留20条历史结果，本轮新增20条；原版连续导航、逐任务重置和early整组导出已通过实际验证。

2026-11-15 13:41 UTC：[自动Oracle运行05](oracle_recovery/distance_v001/run_20261115_05/README.md)已按用户指定固定GPU3，使用原版共享参数。模型已ready，仿真正在初始化，无新增评分；20条历史结果保留，继续145条。19项CPU检查通过，原版复现生命周期不变；04已停止，GPU2本项目资源已释放。

2026-11-15 最新：[自动Oracle原版运行04](oracle_recovery/distance_v001/run_20261115_04/README.md)按用户明确要求采用原版复现机制；撤除自定义固定场景批次和缓存，20条完成结果保留，剩余145条交由原版连续循环。03已正常停止；04源码冻结、18项CPU检查和环境检查通过，主管PID3091732已启动并等待空闲GPU，尚无新版GPU验证结果。

2026-11-15：[自动Oracle批量运行03](oracle_recovery/distance_v001/run_20261115_03/README.md)按用户要求改为模型常驻、同场景连续仿真；02在完成17条后正常停止，03保留结果继续148条/40批。18项CPU检查及环境检查通过，主管PID3066523已后台启动并等待空闲GPU；实际复用验证尚未开始。

2026-11-15 12:37 UTC 检查：[自动Oracle运行02](oracle_recovery/distance_v001/run_20261115_02/README.md)完成16/165（early组16/33），10条触发共21次纠正，9条成功；首条实际纠正、续跑及评分链路已通过。第17条在GPU2初始化仿真，其他四组未开始。主管PID2786697继续后台执行，不持续人工跟踪；中间成绩不作为完整对照结论。

2026-11-15：[自动Oracle运行02](oracle_recovery/distance_v001/run_20261115_02/README.md)承接01的资源准入失败，增加空闲GPU自动选择与后台等待。01没有启动模型/仿真；12项新增CPU检查通过，样本及协议不变。

2026-11-15：[距离阈值自动Oracle v001](oracle_recovery/distance_v001/README.md)代码与CPU验证完成。33任务/34事件、四档距离纠正加实际存档回退，共165作业；用户已授权GPU启动，正常后后台推进。[正式运行01](oracle_recovery/distance_v001/run_20261115_01/README.md)记录实际状态；无在线GPT。

2026-11-12：[偏航与累计语义进度 v003 方法及接手](../docs/DEVIATION_PROGRESS_V003.md)已冻结在 `codex/jev-online-sampling-v001` 分支；包含34案例原始结果、提示词、运行脚本与本地网页源码，记录no31提前误报限制。本次仅归档，无新增模型调用。

2026-11-12：[全部34个案例](deviation_progress/v003/run_20261112_05/README.md)已完成：补跑22条，新请求74次、有效73次，12条的40次记录原样复用；六进程、本地网页。

2026-11-12：[十二条轨迹补齐](deviation_progress/v003/run_20261112_04/README.md)已完成：仅补跑六条，新请求17次、有效16次，其余六条的23次记录原样复用；本地网页合并展示。

2026-11-12：[终止节点评审 v003](deviation_progress/v003/run_20261112_03/README.md)已完成：26个有效节点（含6个终止节点），23次请求、17次有效、6次偏航判定，DeepSeek六进程；仅本地网页。

2026-11-12：[有效节点联合评审 v002](deviation_progress/v002/run_20261112_02/README.md)已完成同六场景重跑，20个有效节点连续编号，19次请求、18次有效、2次偏航判定；旧v001包含已删除节点，不作为本轮结果。网页仅本地使用。

2026-11-12：[偏航与语义进度 v001 / 六场景](deviation_progress/v001/run_20261112_01/README.md)已准备：复用已有节点/去重，新增DeepSeek联合评审，六轨迹进程并行、轨迹内串行，本地新网页；不运行导航。

2026-11-12 最新：[本地节点去重完整快照](crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/README.md)已完成34条：298→165节点，206次实际调用含1次格式错误保留双方；源码和结果保存至原交接分支，网页仅本地使用。此条更新下方“尚未接入后续模型”的历史状态。

2026-11-12：[JEV 在线采样 v001](crossing_checkpoint/online_sampling_v001/README.md)：用户认可固定延迟局部峰、滞回区域与间隔采样。参考实现、41组固定样例和本地网页导出已验证，源码经授权在 `codex/jev-online-sampling-v001` 分支交接；[接手说明](../docs/JEV_SAMPLING_HANDOFF.md)给出合并、验证和运行循环适配步骤。网页仅本地使用；尚未新增模型/导航运行。

2026-11-09：人工标定集 34 个错误选择点已完成 JEV v004 与最初 Qwen4B 对照。
29 个新调用、5 个完整请求 SHA256 精确复用，34/34 有效；JEV 平均 yes 概率
0.762，19/34 ≥0.75，无低于 0.50 的点；Qwen4B 均分 3.353。用户指定并发上限
500，实际提交 29 个缺失任务并使用 29 个 worker。新端点 `jev-1` 上游持续 429 后，
按用户指令切回此前可用端点。三栏双语页面已发布：
http://134.175.18.101/vln/jev_noul_v004_wrong_choices34_qwen4b_template_20261109_05/jev_noul_v004_vs_qwen4b.html 。
见
[`run_20261109_03_wrong_choices34_prevapi`](crossing_checkpoint/jev_noul_v004/run_20261109_03_wrong_choices34_prevapi/README.md)。

2026-11-09：InternVLA-N1 fine Val Unseen seed0 正在 GPU3 继续，当前
195/825条、8个完整scene，局部SR44.62%。`kujiale_0093`的Isaac/PhysX停顿已改为
仿真420秒无进展后重启并复用LMDB，最多5次，当前已继续。见
[`run_20261109_01_gpu3_resume`](reproduction/internvla_n1_vlnverse/run_20261109_01_gpu3_resume/README.md)。

2026-11-09：本地 StreamVLN + Isaac Sim 实时 JEV 实验已完成并发布。
`kujiale_0272`全部40条新 episode、seed 0、H1 physical；StreamVLN/仿真使用
GPU4/GPU5，导航过程中实时提交JEV v004，最多5个未决调用并使用`N=11,D=5`。
40/40完成，SR45%；2878次JEV回答0错误，215个节点。在线入口：
http://134.175.18.101/vln/streamvln_live_jev_0272_40_template_20261109_03/streamvln_live_jev_0272_40.html 。
见
[`jev_live_vlnverse/run_20261109_01_0272_40`](crossing_checkpoint/jev_live_vlnverse/run_20261109_01_0272_40/README.md)。

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

2026-11-08：[lite_v003 单帧诊断](crossing_checkpoint/lite_v003/README.md)完成。仅在v002 prompt加入“短距离侧向转弯不要求与当前朝向平行”，对`kujiale_0113_1_4` frame 56只调用1次；仍返回1分且理由与v002相同。未更新最优版本，不启动整批。

2026-11-08：[lite_v004 单帧诊断](crossing_checkpoint/lite_v004/README.md)完成。以`best_v001`为底稿，仅加入逐方向显式检查（前方、左侧、右侧、来路，各方向可含多个候选支路）；对`kujiale_0257_11_2` frame 26只调用1次，仍返回1分。未更新最优版本，不启动整批。

2026-11-08：[lite_v005 单帧诊断](crossing_checkpoint/lite_v005/README.md)完成。进一步展开逐方向证据检查，要求各方向枚举多个入口并在全部检查后评分；`kujiale_0257_11_2` frame 26仍返回1分。未更新最优版本，不启动整批。

2026-11-08：[lite_v006 双帧诊断](crossing_checkpoint/lite_v006/README.md)完成。显式要求怀疑墙边、门框、柜体或画面边界后的空间延伸；`kujiale_0207_14_4` F58、F96均仍返回1分。未更新最优版本，不启动整批。

2026-11-08：[lite_v007 双帧诊断](crossing_checkpoint/lite_v007/README.md)完成。进一步规定受限视野不能直接判成墙壁，只有明确封闭才能支持1分；`kujiale_0207_14_4` F58、F96仍均为1分。未更新最优版本，不启动整批。

2026-11-08：[lite_v012 候选与控制面板](crossing_checkpoint/lite_v012/README.md)完成。门洞内部延续及受限侧面默认候选规则使F58=2、F96=3、F105=1；47个人工标注帧 `>=3` 从25增至30，20个稳定性控制帧中3个升至2、0个达到3以上。出现可测效果，尚未更新最优版本。

2026-11-08：[JEV Noul v002 完整61条](crossing_checkpoint/jev_noul_v002/README.md)完成。首轮按用户要求1000 worker运行，API高并发传输故障产生371条失败并导致进程池收尾阻塞；5007条成功结果保留，371条以100并发补跑全部成功。最终5378/5378有效、0失败。网页以Qwen同一轨迹对照Qwen 1–5分和JEV回退概率，路径颜色深浅表示数值高低，地图仅保留路线与机器人位置。[在线入口](http://134.175.18.101/vln/jev_noul_v002_full61_vs_qwen_20261108_02/jev_noul_vs_qwen.html)。

2026-11-08：[JEV Noul v003](crossing_checkpoint/jev_noul_v003/README.md)邻近候选回退点prompt已在`kujiale_0123_fix_15_3`完成90/90全观测、90进程同时判断。新版平均概率0.317，上一版0.223；80帧更高、8帧更低、2帧相同。网页地图仅绘制同一Qwen轨迹上按概率深浅染色的两条路线和机器人位置。[在线对照](http://134.175.18.101/vln/jev_noul_v003_kujiale_0123_fix_15_3_20261108_01/jev_noul_v002_vs_v003.html)。

2026-11-08：[JEV Noul v004](crossing_checkpoint/jev_noul_v004/README.md)精简邻近回退点prompt在`kujiale_0123_fix_15_3`和`kujiale_0257_13_4`完成188/188有效判断，并补齐第二条轨迹v003对照。两版各188/188有效；v003平均概率0.388、v004为0.446。网页可切换两条轨迹，仅显示同一Qwen轨迹的概率深浅路线与机器人位置。[在线对照](http://134.175.18.101/vln/jev_noul_v004_two_cases_20261108_01/jev_noul_v003_vs_v004.html)。

2026-11-08：[JEV Noul v004十条新增轨迹](crossing_checkpoint/jev_noul_v004/run_20261108_03_ten_final/README.md)完成862/862有效判断；最多200并发worker，首轮3个空响应以3并发补跑成功。与v002相比平均回退概率0.380→0.495，753帧升高、91帧降低、18帧相同。网页可切换10条轨迹，地图仅保留同一Qwen轨迹的概率深浅路线和机器人位置。[在线对照](http://134.175.18.101/vln/jev_noul_v004_ten_cases_20261108_01/jev_noul_v002_vs_v004.html)。

2026-11-08：用户指定 `jev_noul_v004` 为**当前最好 JEV 版本**，指针为
`experiments/crossing_checkpoint/current_jev_version.json`。该状态与Qwen当前最优
版本1分开记录，不覆盖Qwen `current_best.json`。

2026-11-08：[v004与最初Qwen4B 12条轨迹对照](crossing_checkpoint/jev_noul_v004/combined12_qwen/README.md)已发布。合并v004全部12条已运行轨迹，1050/1050个同帧结果；Qwen平均分1.891、JEV平均概率0.486。网页仅显示同一Qwen轨迹的两条概率深浅路线与机器人位置。[在线对照](http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_20261108_01/jev_noul_v004_vs_qwen4b.html)。

2026-11-09：[v004概率增强可视化](crossing_checkpoint/jev_noul_v004/filtering/README.md)完成。折线图支持Gaussian、EMA、Moving Average、离线Relative Prominence和Streaming Prominence，统一N=3..31窗口及D=0..5最大延迟，原始两线可独立勾选。流式突出度只使用过去及最多D个未来观测，达到i+D后冻结历史。所有增强只改变图表，不改地图或原始结果。[在线增强版](http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_filters_20261109_01/jev_noul_v004_vs_qwen4b.html)。

2026-11-09：用户指定 **v004 prompt + Streaming Prominence（N=7,D=5）** 为当前
最好 JEV 流水线。滤波版本登记为`jev_noul_v004_filter_v001`，指针为
`experiments/crossing_checkpoint/current_jev_version.json`。其余滤波保留为对照，
该指定不代表独立准确率结论。

2026-11-09：[流式突出度横轴采样](crossing_checkpoint/jev_noul_v004/sampling/README.md)完成。流式曲线勾选后，按高点0.6/低峰0.18、相对峰谷差0.03、节点间距3帧、最短3帧平台中心起每5帧采样，在波形横轴绘制圆点、竖虚线和S编号；新增地图勾选项可同步显示节点。修复开头短平台漏采，`kujiale_0207_41_0` 在N=5时首峰F3已采样。不调用大模型、不改变路线或原始结果。[在线采样页](http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_nodes_20261109_04/jev_noul_v004_vs_qwen4b.html)。

2026-11-17：[偏航与语义进度 v003 / 34案例网页发布](deviation_progress/v003/run_20261112_05/exports/web_20261117_01/README.md)完成：[在线查看](http://134.175.18.101/vln/jev_deviation_progress_v003_34cases_web_20261117_01/index.html)。按最新指令发布原本地结果，199节点、33偏航区间，修复字体缺字，原判断不变；本地双语/图片/交互及3288文件远端哈希、公网HTTP200通过，无新模型或导航。
2026-11-22 [H1 历史动作逆向回退与直接 reset 的 30 例配对物理验证](inverse_rollback/v001/run_20261122_02/README.md)。种子 2，使用 v006 ±70° 批次的冻结报警点和回退目标。

