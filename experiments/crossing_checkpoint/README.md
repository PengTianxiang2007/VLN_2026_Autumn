# Crossing Checkpoint 方法迭代

2026-11-12：[JEV 在线采样 v001](online_sampling_v001/README.md)获用户认可；历史结果不可回改的验证通过。独立参考实现、测试与本地网页源码在交接分支提供，另一台机器按[接手说明](../../docs/JEV_SAMPLING_HANDOFF.md)适配实际运行循环。网页仅本地使用；检测/导航收益尚未建立。

2026-11-09：新的本地 StreamVLN + Isaac Sim 实时 JEV 实验已启动。VLNVerse fine
val_unseen 的新场景`kujiale_0272`全部40条，seed 0，H1 physical；StreamVLN 在
GPU4、Isaac Sim 在GPU5。导航每帧实时提交JEV v004，最多5个未决调用，
`N=11,D=5`。JEV旁路不改变动作或官方成绩。两个先前离线批量运行均已停止且不计入。
见[`jev_live_vlnverse/run_20261109_01_0272_40`](jev_live_vlnverse/run_20261109_01_0272_40/README.md)。

更新时间：2026-11-05。v002已完成，结果与资源释放已核验；已追加统一离线HTML导出。逐项证据见对应实验记录。

[v001](v001/README.md) 已完成 8 条开发轨迹；40 条独立验证轨迹尚未运行。

[单卡单并发部署验证](single_gpu_smoke/README.md)：2026-11-04 用户授权测试现有 27B FP8 在 GPU 0 的单卡单请求能力；已通过三个原开发集请求，测试服务已释放。

后续迭代新建版本目录，写明输入、prompt、状态机及评分变化；不得覆盖历史版本。开发样本上的调参结果不当作独立验证成绩。

[v002：五条开发、十五条验证](v002/README.md)：全部完成。开发基准/r01/r02 F1为42.11%/31.58%/28.57%，两次修改未改善；按验证时间预留退出。冻结基准验证TP3/FP4/FN20，P42.86%/R13.04%/F1 20.00%；未达到目标。1791个方法观测无失败重试，逐帧报告及审计完成，本次GPU已释放。

[统一可视化导出记录](v002/visualization_export/README.md)：当前03版一个HTML包含开发三版和独立验证，支持版本同帧对照、标定/存档与RGB联动、典型问题跳转；地图和RGB正下方均有同步进度条，实际浏览器拖动与布局检查通过。

[默认模板固化](visualization_template/README.md)：用户已指定03版作为后续每轮模板；独立仓库模板和自动导出入口已完成，单/双/四版本CPU及实际浏览器检查通过。以后每轮完成先按该模板导出，再交付结果。

[v003](v003/README.md)：第2稿允许依据视角受限的少量视觉证据推断通向不同区域的支路。用户现授权在原5条轨迹上做一次离线测评，每两动作步调用一次，共146次；其他模型、历史输入、存档阈值和评分不变。[固定批次](v003/run_20261105_01/README.md)自动评分、导出和释放资源。

<!-- CROSSING_V003_BATCH_STATUS_START -->
已完成；5条固定离线样本，每2个动作步调用一次。 TP 4 / FP 2 / FN 9。 GPU已释放。
<!-- CROSSING_V003_BATCH_STATUS_END -->


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

2026-11-07：用户授权三帧Crossing轻量评分，10失败＋20成功、GPU0 Qwen3.5-4B vLLM＋4进程；准备完成。原GPU0 Qwen27B已按核验PID释放，其他用户进程保留。记录 experiments/crossing_checkpoint/lite_v001/run_20261107_01/README.md；实际状态 outputs/crossing_checkpoint/lite_v001/run_20261107_01/status.json。

2026-11-08：用户将当前三帧五级评分版本标记为“最优版本1”（best_v001），冻结登记 experiments/crossing_checkpoint/best_v001/；当前指针 experiments/crossing_checkpoint/current_best.json，网页为web_02机器人位置点修正版。

2026-11-08：部署lite_v002/run_20261108_01，20条（10失败10成功，含kujiale_0113_66_1），八步局部选择与部分可见支路新提示词；后台评分→Qwen4B翻译→与最优版本1同帧对比→检查发布；不持续人工轮询。

2026-11-08：lite_v003 单帧诊断完成。仅在 v002 prompt 中加入“短距离转入附近侧向开口不要求与当前朝向平行”，对 `kujiale_0113_1_4` frame 56 仅调用1次；结果仍为1分，理由与v002相同。单帧未改善，不更新最优版本，不启动整批。

2026-11-08：lite_v004 单帧诊断完成。以 `best_v001` 为底稿，仅加入逐方向显式检查（前方、左侧、右侧、来路，各方向可含多个候选支路）；对 `kujiale_0257_11_2` frame 26 只调用1次，仍返回1分，未改善，不启动整批。

2026-11-08：lite_v005 单帧诊断完成。进一步展开逐方向证据检查，要求各方向枚举多个入口并在全部检查后评分；`kujiale_0257_11_2` frame 26 仍返回1分，未改善，不启动整批。

2026-11-08：lite_v006 双帧诊断完成。显式要求怀疑墙边、门框、柜体或画面边界后的空间延伸，并允许按2—4分表示候选；`kujiale_0207_14_4` F58、F96 均仍返回1分，未改善，不启动整批。

2026-11-08：lite_v007 双帧诊断完成。进一步规定画面边界或遮挡不能直接判成墙壁，只有明确封闭才能支持1分；`kujiale_0207_14_4` F58、F96 仍均为1分，未改善，不启动整批。

2026-11-08：lite_v009—v012完成逐方向状态化迭代。最终v012要求检查门洞内部横纵延续，并把无法正面排除的受限侧面默认标为“可能”。目标F58=2、F96=3、F105=1；47个人工标注帧 `>=3` 从25增至30，20个稳定性控制帧仅3个升至2且无 `>=3`。出现可测效果但仍有降分和未标注控制限制，暂不更新最优版本。

2026-11-08：JEV/System One 节点评分接口 v001 完成。使用中转节点
`https://api.site/v1/systemone`、JEV 1.14 的三帧图像输入、一个五级 Score 和
前/左/右三个 Noul。目标 F58/F96/F105 映射后均为 3 分，但置信度
0.07/0.03/0.00，不能据此宣称优于 Qwen。另起的 40 帧混合控制面板在用户询问后
停止于 10/40，不纳入结论。接口与结果见
[`jev_v001`](jev_v001/README.md)。

2026-11-08：JEV `Noul` 回退点判断 v001 跑通。沿用 v1 的三帧输入和局部路线选择
定义，只发送一个 `fallback_point` Noul；F58/F96/F105 的 yes 概率分别为
0.22/0.32/0.26。返回概率而非 1–5 分，不生成文字理由。见
[`jev_noul_v001`](jev_noul_v001/README.md)。

2026-11-08：JEV Noul v002 完成5条离线轨迹全帧对照，421/421次调用有效、50进程
并发、0失败。网页同步显示Qwen4B 1–5分路径和JEV概率路径，颜色越深数值越高，
默认中文并可切换英文。在线入口：
http://134.175.18.101/vln/jev_noul_v002_five50_vs_qwen_20261108_01/jev_noul_vs_qwen.html 。
结果为同帧描述对照，不宣称准确率或方法优劣。见
[`jev_noul_v002`](jev_noul_v002/README.md)。

2026-11-08：JEV Noul v002 完整61条离线集完成，最终5378/5378有效。首轮按用户要求
以1000 worker 全量运行；中转API在高并发下出现HTTP/2协议错误、reset和超时，
5007条成功、371条失败且进程池收尾阻塞。保留成功结果后以100并发补跑371条，全部
成功。网页地图使用同一Qwen轨迹，仅绘制按分数/概率深浅染色的路线和机器人位置；
无人工点或JEV高分方块。[完整在线对照](
http://134.175.18.101/vln/jev_noul_v002_full61_vs_qwen_20261108_02/jev_noul_vs_qwen.html)。

2026-11-08：JEV Noul v003邻近候选回退点版本在
`kujiale_0123_fix_15_3` 上完成90/90全观测并发判断，90个worker同时提交。新版
平均概率0.317，上一版v002为0.223；80帧升高、8帧降低、2帧相同。网页采用Qwen
同一轨迹，仅绘制概率深浅路线和机器人位置。[在线对照](
http://134.175.18.101/vln/jev_noul_v003_kujiale_0123_fix_15_3_20261108_01/jev_noul_v002_vs_v003.html)。

2026-11-08：JEV Noul v004精简邻近回退点prompt在两条完整轨迹上完成188/188有效
判断，并补齐第二条轨迹的v003对照。v003平均概率0.388、v004为0.446；149帧升高、
33帧降低、6帧相同。网页支持两条轨迹切换，仅绘制同一Qwen轨迹的概率深浅路线和
机器人位置。[在线对照](
http://134.175.18.101/vln/jev_noul_v004_two_cases_20261108_01/jev_noul_v003_vs_v004.html)。

2026-11-08：JEV Noul v004继续在10条新增轨迹上完成862/862有效判断，使用最多200
并发worker；首轮859成功、3个空响应以3并发补跑后全部成功。与v002相比，平均回退
概率0.380→0.495，753帧升高、91帧降低、18帧相同。网页支持10条轨迹切换，地图仅
显示同一Qwen轨迹的概率深浅路线和机器人位置。[在线对照](
http://134.175.18.101/vln/jev_noul_v004_ten_cases_20261108_01/jev_noul_v002_vs_v004.html)。

2026-11-08：用户指定 `jev_noul_v004` 为**当前最好 JEV 版本**。指针保存在
`experiments/crossing_checkpoint/current_jev_version.json`；该指针与Qwen的
`current_best.json`相互独立，不覆盖Qwen最优版本1。

2026-11-08：v004已完成的全部12条轨迹与最初Qwen4B `best_v001` 合并对照页发布。
共1050/1050个同帧结果、1062回放帧；Qwen平均分1.891、JEV平均概率0.486。
路径仅保留Qwen 1–5分与JEV 0–1概率深浅染色及机器人位置。[在线对照](
http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_20261108_01/jev_noul_v004_vs_qwen4b.html)。

2026-11-09：为v004/Qwen4B对照折线图新增Gaussian、EMA、Moving Average、
离线Relative Prominence和Streaming Prominence五种可叠加增强、`N=3..31`窗口
及`D=0..5`最大延迟，原始两线可独立勾选。流式突出度在`i+D`后冻结，后续数据
不改写历史；滤波仅改变图表不改地图和原始分数。[增强在线版](
http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_nodes_20261109_01/jev_noul_v004_vs_qwen4b.html)。

2026-11-09：用户指定 **v004 prompt + Streaming Prominence（N=7,D=5）**
为当前最好 JEV 流水线。滤波版本登记
`experiments/crossing_checkpoint/jev_noul_v004/filtering/version.json`；
当前组合指针为`experiments/crossing_checkpoint/current_jev_version.json`。
该指定不代表独立准确率结论。

2026-11-09：为后续大模型调用增加横轴采样点。勾选流式突出度时，按
`高点0.6/低峰0.18、相对峰谷差≥0.03、节点间距≥3帧、最短3帧平台中心起每5帧`生成核心
节点，并在折线图横轴绘制竖虚线、圆点及编号；新增地图勾选项可同步显示节点。
修复开头短平台导致首峰漏采：`kujiale_0113_1_4` 首峰F4已采样；
`kujiale_0207_41_0` 在N=5/D=5时首峰F3已采样。节点仅用于选择后续大模型输入帧，
尚未调用模型。
[在线采样页](
http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_nodes_20261109_04/jev_noul_v004_vs_qwen4b.html)。
