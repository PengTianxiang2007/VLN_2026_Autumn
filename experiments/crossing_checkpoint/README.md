# Crossing Checkpoint 方法迭代

**JEV 采样版本**　v001 原版（当前默认） · v003 覆盖优先（候选） · v002 精简（候选）。[版本记录与验证指标](../../docs/STATUS.md#jev-sampling-selection)

2026-11-25，[早期 48 条 Crossing 错选轨迹三版采样](online_sampling_v003/run_20261125_01_early48/README.md)已完成缓存阶段 33 条，余 15 条缺 1,500 个 JEV 分数。按历史错选帧 ±3 步，v001 命中 20/33、v003 coverage 命中 16/33、v002 active 命中 17/33。当前版和配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，[JEV 采样 v003](online_sampling_v003/run_20261124_01/README.md)完成。复用 22 条留出轨迹，60% 目标档采纳 28/45（62.22%），覆盖 28/51；严格档 13/19（68.42%），覆盖 13/51。四档均已保留。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，[JEV 三种流式采样规则](online_sampling_v002/run_20261124_02_tradeoffs/README.md)完成。排除指定 11 例，随机 20 例设计、22 例验证，±3 步一对一匹配。验证集原版 51/174，保守版 51/171，均衡版 50/135，精简版 48/114；共 51 个 Astra 参考点。当前版及配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

GPT-6 Astra 常规档 v006.1 完成 53 例。494 个原始候选保留 146 个，排除 161 个不合格候选与 187 个重复候选。候选调用均值 94.19 秒。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[完整回放](http://134.175.18.101/vln/astra_standard_v006_1_all53_web_20261124_01/index.html)。

GPT-6 Astra 常规档 v006.1 全 53 例评审已启动。C01/C11 复用，其余 51 例（482 个原始候选）最多 20 路并发，含 C32。记录 codex_dedup_v006_1/run_20261124_04_astra_standard_all53。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。

C32 v006.1 双 Fast 计时完成。GPT-6 Astra 整例 304.07 秒（初始化 37.29 秒，候选均值 32.60 秒），GPT-6.1 Terra 整例 288.79 秒（初始化 35.59 秒，候选均值 30.81 秒）。Terra 本次总耗时少 15.27 秒（5.02%）。Astra 保留 S02/S03/S05/S08，Terra 保留 S02/S08。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。

GPT-6.1 Terra Fast v006.1 九例全部完成，77 个原始候选保留 21 个，排除 26 个不合格候选、30 个重复候选，0 格式错误。Terra v006 同批保留 18 个。九路并行 9 分 16 秒，候选调用均值 32.85 秒。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[九例双语对照](http://134.175.18.101/vln/terra_fast_v006_1_selected9_web_20261124_01/index.html)。

GPT-6 Astra v006.1 已完成 C01/C11 的 12 次候选判断。C01 保留 S05；C11 保留 S04、S07。v006 同批分别保留 0 个、S07。两路并行 18 分 30 秒，0 格式错误。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[双语回放](http://134.175.18.101/vln/astra_v006_1_c01_c11_web_20261124_01/index.html)。

GPT-6 Astra v006 九例已完成，77 个原始候选保留 24 个，23 个不具备回退点资格，30 个因重复被替换。同批 Terra Fast 保留 18 个。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[九例对照网页](http://134.175.18.101/vln/astra_terra_v006_selected9_web_20261124_01/index.html)。

Terra Fast v006 九例全部完成，77 个原始候选保留 18 个，删除 59 个。新跑七例 54 次候选调用平均 27.04 秒，七路并行共 489.4 秒；九例全部候选平均 28.05 秒。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

v006 Terra Fast 两例全部完成，23 次候选调用平均 30.43 秒，中位数 29.21 秒，初始化平均 35.66 秒，两例并行共 508.01 秒。所有请求均带 priority。与上一轮 Astra 对照见 codex_dedup_v006/run_20261124_02_terra_fast/timing.json。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24 12:54 UTC，v006 两例均完成。23 个原始候选保留 4 个，12 次重复替换，7 个不符合资格，0 格式错误。C04 保留 S13，S12 与 S13 均为 eligible/same；C32 保留 S02、S05、S08。两例最终节点与 v005 一致。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，C04/C32 已启动 v006 二元回退点判断，两路并行。记录 codex_dedup_v006/run_20261124_01。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24 12:28 UTC，v005 两例完成，23 个原始候选保留 4 个。C04（15→1）保留 S13，S12 资格合格并替换 S11，随后资格不确定的 S13 判为同一处并替换 S12。C32（8→3）保留 S02、S05、S08，S06 判为新决策，最终由 S08 代表。16 次重复替换，3 个不合格，8 次资格或关系不确定，0 格式错误，无失败 case。当前版和配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，C04/C32 回退点去重 v005 已启动，两例并行，资格不确定亦参与比较，相同则以后一个替换前一个。实验记录 codex_dedup_v005/run_20261124_01。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24 11:53 UTC，局部路线选择 prompt v004 的 C04/C32 两例全部完成，23 原始候选保留 7、删除 16，4 次不确定、0 格式错误、0 调用失败。C04 保留 S04/S05/S06/S07，S12 仍重复；C32 保留 S01/S03/S06，S06 已作为新的下游决策保留。可视化待导出。记录 codex_dedup_v004/run_20261124_01。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，按用户授权启动局部路线选择 prompt v004 的 C04/C32 两路并行重跑，共 23 原始候选，gpt-6-astra / medium，代理 127.0.0.1:17982，两例新会话均已进入初始化调用。记录 codex_dedup_v004/run_20261124_01，旧结果保留。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24 10:57 UTC，Codex 会话历史九例全部完成并[发布可视化](http://134.175.18.101/vln/codex_memory_selected9_web_20261124_01/index.html)。77 原始候选→24 有效节点，删除 53（不符合定义 21、重复 32），4 次不确定保留，最终格式错误 0。同九例旧 Astra 保留 47、Qwen 保留 54；DeepSeek 仅覆盖 C04/C34。双语、模型勾选、图像及进度条检查通过，远端哈希与 HTTP 200 通过。最终汇总 selected9_20261124_01，未启动新导航。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，用户将本次 Codex 代理指定为 127.0.0.1:17982。C05、C11、C19、C32、C34 已完成并复用，C04、C17 各保留 9 条判断，从原会话 S10 接续，记录为 codex_dedup_v003/run_20261124_07_proxy17982。加上已导出的 C01、C03，共 7/9 例完成。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，按用户要求后四例 C17、C19、C32、C34 已在 codex_dedup_v003/run_20261124_06_parallel4 立即四路启动，与 run_20261124_05_restart7 的 C04、C05、C11 合计七路。旧队列四例已登记移交占位，防止重复调用，进度按两轮实际归属汇合。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，C01、C03 新版回退点筛选对照已[发布](http://134.175.18.101/vln/codex_memory_c01_c03_web_20261124_01/index.html)，11 原始候选，新版保留 3、旧 Astra 保留 6、Qwen 保留 8。其余七例按用户要求在 codex_dedup_v003/run_20261124_05_restart7 以 3 路重启，旧记录保留。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，[Codex 会话历史九例](codex_dedup_v003/run_20261124_01/README.md)初始 9 路出现服务超时及 429，现由 run_20261124_03_retry2 的 2 路与 run_20261124_04_c11 的 1 路接续，共 77 原始候选。09:38 UTC 已完成 9 条候选评审、0/9 完整 case。英文初始化、历史图像引用和资格判断已接通，导出待结果齐全。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-23，[GPT-6 Astra 全 53 条三帧去重](codex_dedup_v002/run_20261123_03_all53/README.md)已完成：复用10条、剩余43条一次性并行，合计53条、494原始候选→308有效节点，338次比较、26不确定、0格式/调用错误。Qwen同批保留376；[全集对照页面](http://134.175.18.101/vln/codex_astra_three_frame_route53_compare_web_20261123_01/index.html)已发布，支持各模型独立去重勾选及中英文原答。当前版及配对原版SR、平均SPL均暂无，已评分0条。

2026-11-23 22:45 UTC，[GPT-6 Astra 三帧去重](codex_dedup_v002/run_20261123_02/README.md)十路完成 10/10，89 原始候选→57有效节点，63 次比较、4 uncertain、0 格式/调用错误；耗时约 8 分 59 秒。四版本[对照页](http://134.175.18.101/vln/codex_astra_three_frame_route10_compare_web_20261123_01/index.html)已发布，三帧为默认独立选项，保留旧五帧（56）、Qwen（63）和 DeepSeek（仅 C04/C08）；双语、证据帧、勾选和 929 文件远端哈希及 HTTP 200 通过。当前版与配对原版 SR/平均 SPL 均暂无，已评分 0 条。

2026-11-23，[GPT-6.2 Astra 三帧去重](codex_dedup_v002/run_20261123_01/README.md)十路首轮均被当前 Codex 登录返回 HTTP 400 / model_not_found，完成 0/10、技术失败 10 例；等待可用模型配置。三帧接口及网页新增选项代码已准备，尚未发布新版结果。当前版与配对原版 SR/平均 SPL 均暂无，已评分 0 条。

2026-11-23 22:05 UTC，[Codex 十条三模型去重对照](codex_dedup_v001/run_20261123_02/exports/compare_20261123_03/README.md)已[发布](http://134.175.18.101/vln/codex_astra_route10_dedup_compare_web_20261123_03/index.html)。GPT-6 Astra 89→56，Qwen 89→63，DeepSeek 仅 C04/C08 共 26→9。支持独立去重勾选、并集组合、原始候选、双语原答及离线包；929 文件远端哈希与 HTTP 200 通过。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-23 21:47 UTC，[VLNVerse C01–C10 Codex 去重](codex_dedup_v001/run_20261123_02/README.md)十条全部完成。89 原始候选→56 有效节点，删除 33 个；63 次比较，4 uncertain、0 格式错误、0 调用失败。用户已授权按旧模板导出可勾选模型的去重对照。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-23 21:27 UTC，[Codex / GPT-6 Astra 候选去重接口](codex_dedup_v001/run_20261123_01/README.md)完成：7 项局部检查通过；复用 RxR episode 837 前三个原始候选，两次真实调用均合法返回，确认 exec/resume 同会话，均判 different，保留三个有效节点。每任务/每轮历史已归档。仅接口连通验证，无导航运行；当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-18 用户将[JEV 在线采样 v001](online_sampling_v001/README.md)指定为当前最新固定版本。[53 条前视轨迹候选点](online_sampling_v001/run_20261118_01/README.md)已完成，得到 4,837 个有效评分和 494 个去重前候选。

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
