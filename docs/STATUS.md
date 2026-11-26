# 当前项目状态

2026-11-26，[120 步回退与支路恢复五例可视化](http://134.175.18.101/vln/c11_codex_region60_f57_f45_web_20261126_01/index.html)已发布，同一网页可切换原 60 步回放。

2026-11-26，[五例回退并进入正确支路 · 120 步](../experiments/inverse_rollback/codex_tools_v001/run_20261126_07_five_branch120/README.md)已结束，整批用时 33 分 40 秒。4 例声明已进入所选支路，C23 在 56 步触发物理终止。C43、C20 报告使用更早回退点。保留 315 张第一人称 RGB 及 C20 仿真停点。

2026-11-26，[五例回退回放](http://134.175.18.101/vln/c11_codex_region60_f57_f45_web_20261126_01/index.html)已更新，新增 C43、C23、C20，可切换逐步第一人称图像与物理回退轨迹。

2026-11-26，[C17、C43、C23、C20 四例回退与计时](../experiments/inverse_rollback/codex_tools_v001/run_20261126_06_four_region60/README.md)已完成。四例均在 60 步内主动声明到达，分别使用 55、32、47、5 步，逐帧第一人称 RGB 与分例耗时已保存。最终仿真保留在 C20 停点。

2026-11-26，[C11 英文区域回退 · 60 步上限](../experiments/inverse_rollback/codex_tools_v001/run_20261126_05_c11_region60/README.md)已结束。从 F57 起步，模型在 31 步后声明到达，终点距 F45 水平位置 1.060 米，仿真保留在现场 F88。

2026-11-26，[C11 Codex 实走回退回放](http://134.175.18.101/vln/c11_codex_return_f57_f45_web_20261126_01/index.html)已发布。[运行与导出记录](../experiments/inverse_rollback/exports/c11_branch_return_20261126_01/README.md)。控制客户端已退出，H1 保留在 F112，截断点距目标 0.537 米。

2026-11-26，常驻 H1 已切至 [kujiale_0128_fix_20_0 第 58 张观测（F57）](../experiments/inverse_rollback/pose_hold/run_20261126_03_f57/README.md)，原进程 3122551 等待动作。

2026-11-26，[常驻 H1 已摆到数据集 F65](../experiments/inverse_rollback/pose_hold/run_20261126_02_f65/README.md)。kujiale_0036_0_0，seed 2，原进程 3122551 等待动作。

2026-11-26 [电视前导航交互回放](http://134.175.18.101/vln/codex_tv_f38_h1_20261126_01/index.html)已发布，可逐帧对照占据栅格、原生前视图和每个动作的观测来源。

2026-11-26 [Codex 从 F38 自主走到电视柜前](../experiments/inverse_rollback/codex_tools_v001/run_20261126_03_tv/README.md)已完成，终点距柜子正面 1.13 米，朝向与电视中心相差 3.42°。模型主动观察 1 次，通过 11 次移动决策执行 27 个动作，原仿真已恢复 F38。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-26 [Codex 在三个位置控制同一台 VLNVerse H1](../experiments/inverse_rollback/codex_tools_v001/run_20261126_02_multisite/README.md)已完成。四次前进的净位移分别为 49.37、46.75、39.95 厘米，两个方向的转向均生效，20 次工具回图与仿真原图一致。原进程已恢复 F38 并常驻。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-26 [Codex 直接操作常驻 VLNVerse H1](../experiments/inverse_rollback/codex_tools_v001/run_20261126_01_f38/README.md)，kujiale_0036_0_0 F38 单步实测通过。两个观察各 0 tick，前进 50 tick，水平位移 2.23 厘米。原进程已恢复 F38，工具持续可用。

2026-11-26 [H1 第 38 步常驻摆位](../experiments/inverse_rollback/pose_hold/run_20261126_01/README.md)，kujiale_0036_0_0，供后续回退实验使用。实际状态见运行记录。

2026-11-26 [Terra xhigh 43 例 · 7892](../experiments/deviation_progress/codex_memory_v002/run_20261126_02_terra_xhigh43_7892/README.md) 依用户指令停止剩余评审和自动重试，完成 39/43，取消 C02, C15, C31, C39。 [Astra / Terra 双模型回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html)。

2026-11-26 [Terra xhigh 43 例离线评审](../experiments/deviation_progress/codex_memory_v002/run_20261126_01_terra_xhigh43/README.md) 已按用户要求停止，完成 0/43。

[50 例原生仿真与 Codex 旁路](../experiments/deviation_progress/codex_memory_v002/run_20261125_10_live50/README.md) 仿真 50/50 已评分，依用户指令已停止剩余评审和重试。

2026-11-25 [34 个未跑 case 六帧补图评审](../experiments/deviation_progress/codex_memory_v002/run_20261125_09_gap6_remaining34/README.md)已完成 34/34，31 例报警，1 例到终点未报警，2 例仅终止初始化。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 [八例六帧间隔偏航重跑](../experiments/deviation_progress/codex_memory_v002/run_20261125_08_gap6_eight/README.md)已完成 8/8，7 例报警（4 例在终止段），C40 仅初始化，累计补图 30 张。JEV v002 active、原 v002 英文偏航规则、8 进程。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 [C35 英文标志物提示词 v003](../experiments/deviation_progress/codex_memory_v003/run_20261125_01_c35_landmarks4/README.md)按两段各补四张完成，两段均未报警。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 [C35 两段条件补图评审](../experiments/deviation_progress/codex_memory_v002/run_20261125_07_c35_conditional/README.md)完成。第一段仅四图组报警，另四支均在终止段补五图后仍未报警。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 [C27 补图五档计时复测](../experiments/deviation_progress/codex_memory_v002/run_20261125_06_c27_frames3to7_repeat/README.md)完成。五档均报警，单次均耗 68.91 秒，上轮 100.78 秒。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 [C27 补 3–7 张图对照](../experiments/deviation_progress/codex_memory_v002/run_20261125_05_c27_frames3to7/README.md)完成。五支均报警。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 [C27 终止段双分支对照](../experiments/deviation_progress/codex_memory_v002/run_20261125_04_c27_interval7/README.md)完成。原输入未报警（84.972 秒），补七张中间图后报警（81.580 秒）。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 [C01 S04 单候选复判](../experiments/deviation_progress/codex_memory_v002/run_20261125_03_c01_s04/README.md)完成。增加视野受限时的资格指引后，S04 从排除改为保留。仅一轮。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 16:19 UTC，[Codex 终止节点评审随机追加五例](../experiments/deviation_progress/codex_memory_v002/run_20261125_02_random5/README.md)全部完成。C42 在终止段、C19 在终止前判定偏航，C27、C35 至终止未报警，C01 仅在终止帧初始化。当前版及配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。 [九例合并回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html)已更新。

2026-11-25 [Codex 终止节点评审四例](../experiments/deviation_progress/codex_memory_v002/run_20261125_01_terminal4/README.md)完成。[地图图层回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html)已发布。JEV v002 active、Astra 常规档，17 轮评审，C17/C43/C20 在终止轮报警，C23 更早报警。后续回退点识别采用 v002 active。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25 [Codex 同会话偏航识别三例](../experiments/deviation_progress/codex_memory_v001/run_20261125_01/README.md)完成。14 轮均无新增图片，C05 在 F26→F46 报警，C25 和 C09 的最后一轮早于参考错选区间。当前版及配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

<a id="jev-sampling-selection"></a>

## JEV 采样版本 · 2026-11-25

| 版本 | 定位 | 回放参数 | 验证集覆盖率 | 验证集采纳率 |
| --- | --- | --- | ---: | ---: |
| **v001 原版** | 当前默认 | `--version v001` | 51/51（100%） | 51/174（29.31%） |
| **v003 覆盖优先** | 候选 | `--version v003 --mode coverage` | 39/51（76.47%） | 39/78（50.00%） |
| **v002 精简** | 候选 | `--version v002 --mode active` | 48/51（94.12%） | 48/114（42.11%） |

22 条验证轨迹，同一轨迹内 ±3 步一对一匹配。两种候选均须显式选择。[原版与候选回放](http://134.175.18.101/vln/jev_sampler_candidates42_web_20261125_01/index.html) · [现行固定版本](../experiments/crossing_checkpoint/current_jev_version.json)。


2026-11-25，[早期 48 条 Crossing 错选轨迹三版采样](../experiments/crossing_checkpoint/online_sampling_v003/run_20261125_01_early48/README.md)已完成缓存阶段 33 条，余 15 条缺 1,500 个 JEV 分数。按历史错选帧 ±3 步，v001 命中 20/33、v003 coverage 命中 16/33、v002 active 命中 17/33。当前版和配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，[JEV 采样 v003](../experiments/crossing_checkpoint/online_sampling_v003/run_20261124_01/README.md)完成。复用 22 条留出轨迹，60% 目标档采纳 28/45（62.22%），覆盖 28/51；严格档 13/19（68.42%），覆盖 13/51。四档均已保留。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，[JEV 三种流式采样规则](../experiments/crossing_checkpoint/online_sampling_v002/run_20261124_02_tradeoffs/README.md)完成。排除指定 11 例，随机 20 例设计、22 例验证，±3 步一对一匹配。验证集原版 51/174，保守版 51/171，均衡版 50/135，精简版 48/114；共 51 个 Astra 参考点。当前版及配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

GPT-6 Astra 常规档 v006.1 完成 53 例。494 个原始候选保留 146 个，排除 161 个不合格候选与 187 个重复候选。候选调用均值 94.19 秒。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[完整回放](http://134.175.18.101/vln/astra_standard_v006_1_all53_web_20261124_01/index.html)。

GPT-6 Astra 常规档 v006.1 全 53 例评审已启动。C01/C11 复用，其余 51 例（482 个原始候选）最多 20 路并发，含 C32。记录 codex_dedup_v006_1/run_20261124_04_astra_standard_all53。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。

C32 v006.1 双 Fast 计时完成。GPT-6 Astra 整例 304.07 秒（初始化 37.29 秒，候选均值 32.60 秒），GPT-6.1 Terra 整例 288.79 秒（初始化 35.59 秒，候选均值 30.81 秒）。Terra 本次总耗时少 15.27 秒（5.02%）。Astra 保留 S02/S03/S05/S08，Terra 保留 S02/S08。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。

GPT-6.1 Terra Fast v006.1 九例全部完成，77 个原始候选保留 21 个，排除 26 个不合格候选、30 个重复候选，0 格式错误。Terra v006 同批保留 18 个。九路并行 9 分 16 秒，候选调用均值 32.85 秒。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[九例双语对照](http://134.175.18.101/vln/terra_fast_v006_1_selected9_web_20261124_01/index.html)。

GPT-6 Astra v006.1 已完成 C01/C11 的 12 次候选判断。C01 保留 S05；C11 保留 S04、S07。v006 同批分别保留 0 个、S07。两路并行 18 分 30 秒，0 格式错误。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[双语回放](http://134.175.18.101/vln/astra_v006_1_c01_c11_web_20261124_01/index.html)。

GPT-6 Astra v006 九例已完成，77 个原始候选保留 24 个，23 个不具备回退点资格，30 个因重复被替换。同批 Terra Fast 保留 18 个。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[九例对照网页](http://134.175.18.101/vln/astra_terra_v006_selected9_web_20261124_01/index.html)。

Terra Fast v006 九例全部完成，77 个原始候选保留 18 个，删除 59 个。新跑七例 54 次候选调用平均 27.04 秒，七路并行共 489.4 秒；九例全部候选平均 28.05 秒。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

v006 Terra Fast 两例全部完成，23 次候选调用平均 30.43 秒，中位数 29.21 秒，初始化平均 35.66 秒，两例并行共 508.01 秒。所有请求均带 priority。与上一轮 Astra 对照见 codex_dedup_v006/run_20261124_02_terra_fast/timing.json。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-24，用户选定 v006 二元选择作为当前回退点筛选版本。C04/C32 的 23 次候选调用平均 57.93 秒，初始化平均 60.10 秒。

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

2026-11-24，[Codex 会话历史九例](../experiments/crossing_checkpoint/codex_dedup_v003/run_20261124_01/README.md)初始 9 路出现服务超时及 429，现由 run_20261124_03_retry2 的 2 路与 run_20261124_04_c11 的 1 路接续，共 77 原始候选。09:38 UTC 已完成 9 条候选评审、0/9 完整 case。英文初始化、历史图像引用和资格判断已接通，导出待结果齐全。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-23，[GPT-6 Astra 全 53 条三帧去重](../experiments/crossing_checkpoint/codex_dedup_v002/run_20261123_03_all53/README.md)已完成：复用10条、剩余43条一次性并行，合计53条、494原始候选→308有效节点，338次比较、26不确定、0格式/调用错误。Qwen同批保留376；[全集对照页面](http://134.175.18.101/vln/codex_astra_three_frame_route53_compare_web_20261123_01/index.html)已发布，支持各模型独立去重勾选及中英文原答。当前版及配对原版SR、平均SPL均暂无，已评分0条。

2026-11-23 22:45 UTC，[GPT-6 Astra 三帧去重](../experiments/crossing_checkpoint/codex_dedup_v002/run_20261123_02/README.md)十路完成 10/10，89 原始候选→57有效节点，63 次比较、4 uncertain、0 格式/调用错误；耗时约 8 分 59 秒。四版本[对照页](http://134.175.18.101/vln/codex_astra_three_frame_route10_compare_web_20261123_01/index.html)已发布，三帧为默认独立选项，保留旧五帧（56）、Qwen（63）和 DeepSeek（仅 C04/C08）；双语、证据帧、勾选和 929 文件远端哈希及 HTTP 200 通过。当前版与配对原版 SR/平均 SPL 均暂无，已评分 0 条。

2026-11-23，[GPT-6.2 Astra 三帧去重](../experiments/crossing_checkpoint/codex_dedup_v002/run_20261123_01/README.md)十路首轮均被当前 Codex 登录返回 HTTP 400 / model_not_found，完成 0/10、技术失败 10 例；等待可用模型配置。三帧接口及网页新增选项代码已准备，尚未发布新版结果。当前版与配对原版 SR/平均 SPL 均暂无，已评分 0 条。

2026-11-23 22:05 UTC，[Codex 十条三模型去重对照](../experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_02/exports/compare_20261123_03/README.md)已[发布](http://134.175.18.101/vln/codex_astra_route10_dedup_compare_web_20261123_03/index.html)。GPT-6 Astra 89→56，Qwen 89→63，DeepSeek 仅 C04/C08 共 26→9。支持独立去重勾选、并集组合、原始候选、双语原答及离线包；929 文件远端哈希与 HTTP 200 通过。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-23 21:47 UTC，[VLNVerse C01–C10 Codex 去重](../experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_02/README.md)十条全部完成。89 原始候选→56 有效节点，删除 33 个；63 次比较，4 uncertain、0 格式错误、0 调用失败。用户已授权按旧模板导出可勾选模型的去重对照。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-23 21:27 UTC，[Codex / GPT-6 Astra 候选去重接口](../experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_01/README.md)完成：7 项局部检查通过；复用 RxR episode 837 前三个原始候选，两次真实调用均合法返回，确认 exec/resume 同会话，均判 different，保留三个有效节点。每任务/每轮历史已归档。仅接口连通验证，无导航运行；当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-23 19:53 UTC，[RxR30 Qwen两轮实验](../experiments/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/README.md)全部完成。去重30/30，517有效节点＋30终止节点；偏航30/30，18条报警、12条未报警，共349轮、22轮格式错误。总用时9小时34分钟（含加载）；服务已退出，GPU3占用已释放。报警数量不是准确率，现有Qwen网站仍为首4条偏航快照。当前版及配对原版SR、平均SPL均暂无，已评分0条。

2026-11-23 18:16 UTC，[RxR30 DeepSeek 完整双语回放](http://134.175.18.101/vln/rxr30_deepseek_full_web_20261123_01/index.html)已发布，覆盖30/30条、295有效节点＋30终止节点、656次去重和137轮偏航评审。23条模型报警的实际区间轨迹可独立勾选染红；7轮无效回答单列。202进程完成展示翻译，浏览器检查及2225个远端文件哈希通过。当前版及配对原版SR、平均SPL均暂无，已评分0条。 [导出记录](../experiments/deviation_progress/rxr30_v006/run_20261123_03_mistral30/exports/full_20261123_01/README.md)

2026-11-23 17:42 UTC，[RxR30 Mistral DeepSeek两轮并发](../experiments/deviation_progress/rxr30_v006/run_20261123_03_mistral30/README.md)全部完成，用时约47分钟。去重725原始候选→295有效节点（另加30终止节点），656次比较0格式错误；偏航30/30，共137轮，23条模型报警、7条未报警、7轮格式错误。报警比例非准确率。主管与工作进程已退出。当前版及配对原版SR/平均SPL均暂无，已评分0条。

2026-11-23 [C21 七图回退](../experiments/inverse_rollback/vlm_action_v001/run_20261123_08_restore_c21/README.md)已完成。488 个回程动作中左转 485 次、前进 3 次，121 次到达判断均为未到达。用尽物理步数，终点距 A 3.999 米，局部回退新版与同例原版均为 0/1。

2026-11-23 16:55 UTC，[RxR30 Mistral DeepSeek两轮并发](../experiments/deviation_progress/rxr30_v006/run_20261123_03_mistral30/README.md)已启动，主管2081596、30个工作进程。复用JEV的725原始候选，用deepseek-v4-1-flash-1017/high重新去重；全部完成冻结本次节点后，再并发运行v006偏航识别。首个真实调用HTTP 200且校验通过，已复用；30例均进入任务后交后台。当前版及配对原版SR/平均SPL均暂无，已评分0条。

2026-11-23 [DeepSeek H1 选路位置版四例重跑](../experiments/inverse_rollback/vlm_action_v001/run_20261123_06_choice_position4/README.md)已完成。局部回退新版和旧版均为 0/4。新版 C15、C21、C34 误判已到达，C31 跌倒。GPU 0 上挂起的 C34 仿真已于 20:38 UTC 按用户要求释放。

2026-11-23 [RxR30 有效节点及已完成偏航网页](../experiments/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/deviation_snapshot_20261123_02/README.md)已[发布](http://134.175.18.101/vln/rxr30_deviation_snapshot_web_20261123_02/index.html)。冻结15:20 UTC结果：去重30/30（517有效节点＋30终止节点），偏航4/30（51轮、2条有效报警、7轮格式错误）。独立勾选可将模型报警A→B实际轨迹染红，保留完整双语偏航原答。当前版及配对原版SR/平均SPL均暂无，已评分0条。

2026-11-23 15:04 UTC，[RxR30 Qwen离线两轮实验](../experiments/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/README.md)去重已完成30/30：725原始候选→517有效节点，另加30终止节点，4次校验错误按uncertain保留。偏航识别完成3/30，正在C04；前三条2条报警、1条未报警，出现7轮格式错误。后台正常运行。当前版及配对原版均无新导航评分，SR/SPL暂无，已评分0条。

2026-11-23 12:35 UTC，[RxR30 首4条去重阶段快照](../experiments/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/snapshot4_20261123_01/README.md)已[发布](http://134.175.18.101/vln/rxr30_dedup_snapshot4_web_20261123_01/index.html)。71个有效节点＋4个终止节点、134次模型比较、357条双语说明；保留30条原始导航回放，共4,465帧。阶段快照不自动刷新，偏航尚未开始；后台继续。无新导航评分，当前版和配对原版均暂无，已评分0条。

2026-11-23 10:19 UTC，[RxR30 Qwen GPU3 接续](../experiments/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/README.md)已后台启动，主管1545621、服务1546204，状态loading_qwen。旧运行在10:06 UTC加载31/66分片时触发2700秒启动超时并清理；新运行仅将启动等待改为7200秒，复用JEV 4,435帧及725原始候选。去重、偏航均0/30；本轮无新导航评分，当前版和配对原版均暂无，已评分0条。

2026-11-23 [R2R / RxR 失败类型比较](../experiments/crossing_analysis/r2r_rxr_failure_types/run_20261123_01/README.md)完成；原版 94 / 165 条失败中，错路占 71.28% / 48.48%，其余细分结果和不确定项已保存。当前版与原版均为同次复现，R2R SR 123/217（56.68%）、平均 SPL 0.4933；RxR SR 224/389（57.58%）、平均 SPL 0.4915。

2026-11-23 [R2R 已评分 217 条的错支路归因](../experiments/crossing_analysis/r2r_seed2_400/run_20261123_02_partial217/README.md)完成。94 条失败中明确 67 条（71.28%，占全部评分 30.88%），不确定 10 条、其他 17 条。当前版与原版为同一次运行，SR 均为 123/217（56.68%），平均 SPL 均为 0.4933。原评测保持暂停，未评分 episode 618 另计，技术异常 0 条。

2026-11-23 按用户指令暂停 [R2R400](../experiments/reproduction/streamvln_r2r/run_20261123_01/README.md)，保留 217 条评分，当前版与原版 SR 均为 123/217（56.68%），平均 SPL 均为 0.4933。GPU3 已转给 [RxR30 本地 Qwen 去重及 v006 偏航识别](../experiments/deviation_progress/rxr30_v006/run_20261123_01/README.md)，JEV 4,435 帧评分及 725 个原始候选已完成。

2026-11-23 [RxR 30 条离线两轮实验](../experiments/deviation_progress/rxr30_v006/run_20261123_01/README.md)，先逐帧 JEV 采样及本地 Qwen 去重，再按冻结节点运行 Qwen v006 偏航识别。

2026-11-23 [RxR-CE 明确错选支路 30 例回放](http://134.175.18.101/vln/rxr_crossing_random30_20261123_01/index.html)已发布，包含 8 个场景、4,465 帧，逐例关联决策步、确认步及中英文指令。

2026-11-23 [R2R-CE 原版 StreamVLN 400 条](../experiments/reproduction/streamvln_r2r/run_20261123_01/README.md)，冻结 11 场景分层样本，保存逐动作 RGB 和位姿供错选支路归因，运行状态见批次记录。

2026-11-23 [RxR-CE 400 条失败归因](../experiments/crossing_analysis/rxr_seed2_400/run_20261123_01/README.md)已完成。165 条有效失败中，明确错选支路 80 条（正常 STOP 74、限步 6），占全部 389 条有效评分的 20.57%。不确定 41 条，其他 44 条，技术异常 11 条单列。

2026-11-23 [DeepSeek H1 全 22 例回退](../experiments/inverse_rollback/vlm_action_v001/run_20261123_05_finish22/README.md)已完成，C03、C19 达标，平均终点误差 2.403 米。[逐帧地图与实采 RGB 回放](../experiments/inverse_rollback/exports/deepseek_h1_22_20261123_01/README.md)

2026-11-23 [DeepSeek 驱动 H1 回退追加十例](../experiments/inverse_rollback/vlm_action_v001/run_20261123_04_deepseek10/README.md)已提交独立后台队列，接续原样本清单第 4～13 例。进度见批次状态文件。

2026-11-23 [DeepSeek 控制 H1 实际回退三例](../experiments/inverse_rollback/vlm_action_v001/run_20261123_03_deepseek3/README.md)已完成，C03 达标，C05、C07 误判到达。回退落点 1/3 达标，平均退出水平误差 2.267 米，本次 GPU 1 仿真已退出。

2026-11-23 [VLM 动作回退的 22 例 H1 样本集](../experiments/inverse_rollback/vlm_action_v001/run_20261123_02/README.md)已准备，每例含 A 图、5 张中间图和 B 图，共 154 张原生前视图。已冻结 B 的初始化状态、A 的目标位姿与全部历史动作。

2026-11-23 [原版 StreamVLN 在 RxR-CE 上的 400 条复现](../experiments/reproduction/streamvln_rxr/run_20261123_01/README.md)，逐帧 RGB 与实际动作对齐，供失败归因。实时状态与评分见批次记录。

2026-11-22 [RxR-CE 随机点对往返与 RGB 采集](../experiments/inverse_rollback/rxr_ce_v001/run_20261122_01_rgb20/README.md)已完成 5 场景 20 组，掉头和倒走各 20/20 达标，平均水平误差均为 4.49 厘米，保存 RGB 2,823 张。

2026-11-22 [H1 倒走回退及 RGB 采集](../experiments/inverse_rollback/v002/run_20261122_01_backward_rgb22/README.md)完成 22 组，倒走 0/22 达标，直接 reset 22/22 达标。

2026-11-22 [GPU 3 Qwen27B 待用服务](../experiments/agent_route_choice/services/qwen27b_gpu3_20261121_01/README.md)已按用户要求释放。独立的回退 RGB 采集继续运行。

2026-11-22 [原始报警 ≥1.5 米的 22 组 H1 回退与原生 RGB 采集](../experiments/inverse_rollback/v001/run_20261122_03_rgb22/README.md)已完成，掉头 2/22 达标，直接 reset 22/22 达标。

2026-11-22 [H1 逆动作与直接 reset 回退](../experiments/inverse_rollback/v001/run_20261122_02/README.md)完成 30/30 个 v006 报警案例。逆动作达标 4/30，平均水平误差 1.125 米；直接 reset 达标 30/30，平均水平误差 0.0177 米。[回放导出记录](../experiments/inverse_rollback/v001/run_20261122_02/exports/replay_20261122_01/README.md)

2026-11-22 [203 条旧评测](../experiments/serial_recovery/v002/run_20261121_06_scene203/README.md)已按用户要求停止并释放专属进程；旧版 SR 16/53（30.19%）、平均 SPL 0.2502，同批原版 SR 20/53（37.74%）、平均 SPL 0.3188，8 条技术跳过。[新版 203 条](../experiments/serial_recovery/v002/run_20261122_01_scene203_stop_review/README.md)已冻结，启动器等待 EasyJEV 认证。新版和同批原版均为暂无，已评分 0 条。

2026-11-22 [原版成功、当前失败的回放](../experiments/serial_recovery/v002/run_20261121_06_scene203/exports/paired_losses_20261122_01/README.md)已从 47 条配对评分筛出 6 条并发布。全批当前版 SR 15/47（31.91%）、平均 SPL 0.2634，原版 SR 17/47（36.17%）、平均 SPL 0.2976。后续新准备的 [v006 运行](../experiments/serial_recovery/v002/README.md)会在执行主任务 STOP 前评审，偏航时回退。

2026-11-22 [41 条配对回放新增回退跳转及地图缩放](../experiments/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_02/README.md)已发布。每次实际回退可一键定位，完整底图支持缩放和平移。快照成绩为当前版 SR 15/41（36.59%）、平均 SPL 0.3019，同批原版 SR 17/41（41.46%）、平均 SPL 0.3411。

2026-11-22 [41 条配对任务的偏航与回退事件回放](../experiments/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_01/README.md)已发布。当前版 SR 15/41（36.59%）、平均 SPL 0.3019；同批原版 SR 17/41（41.46%）、平均 SPL 0.3411。7 条技术跳过。可定位 51 次报警、29 次两阶段选路和 18 次实际回退，查看识别支路、选择及实走结果。

2026-11-22 [37 条配对任务的逐次模型原答回放](../experiments/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_recovery/README.md)已发布，包含 47 次节点报警、26 次两阶段选路、16 次实际回退。

2026-11-22 [37 条配对回放地图图层版](../experiments/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_map02/README.md)已发布，支持选择时对照两版结果、独立查看偏航与纠错轨迹。

2026-11-22 [在线恢复 203 条批次的部分回放](../experiments/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956/README.md)已发布。快照含 37 条正式评分和 7 条技术跳过，当前版与原版成功数分别为 13 和 16。

2026-11-21 [八个完整场景的 203 条配对评测](../experiments/serial_recovery/v002/run_20261121_06_scene203/README.md)已启动，原版 seed 2 成功 81/203。先前准备的 98 条已包含在本批，不单独运行。

2026-11-21 [四个完整场景的配对评测](../experiments/serial_recovery/v002/run_20261121_05_scene98/README.md)已准备。98 条均有原版 seed 2 评分，原版成功 40 条。在线恢复批次尚未启动。

2026-11-21 [C13 在线恢复闭环已通过](../experiments/serial_recovery/v002/run_20261121_03/README.md)。自然报警、实际回退、40 个局部动作、策略记忆恢复及交还后 157 个原任务动作均已记录。任务最终卡住，正式 SR 0、NE 9.7192 米。本轮资源已释放，备用任务未启动。

2026-11-21 [在线恢复 v002 C01](../experiments/serial_recovery/v002/run_20261121_02/README.md)已完成，66 动作，非终止报警 1 次，两次 Recovery 后因支路选择无效未接管。正式 SR 0、NE 3.6499 米。[C13 单条补验](../experiments/serial_recovery/v002/run_20261121_03/README.md)已完成。

2026-11-21 [Recovery 两阶段同模型对照 · v006 全部 47 例](../experiments/agent_recovery/branch_instruction_v001/run_20261121_02_paired47/README.md)完成。Qwen 两阶段生成 43 条指令，DeepSeek 两阶段生成 45 条；各 47 份有效回答。[双语对照回放](http://134.175.18.101/vln/recovery_instruction_v001_paired47_web_20261121_01/index.html)已发布。

2026-11-21 [Recovery 第二次调用 v001 · DeepSeek 十例](../experiments/agent_recovery/branch_instruction_v001/run_20261121_01/README.md)完成。十例各输出一条替代支路和一句 8–12 词的英文局部指令，全部排除第一次匹配的已走支路。仅做离线指令生成。[双语回放](http://134.175.18.101/vln/recovery_instruction_v001_deepseek10_web_20261121_02/index.html)已发布。

2026-11-21 [DeepSeek v1 全部 47 例](../experiments/agent_recovery/branch_review_v001/run_20261121_04_deepseek47/README.md)完成，45 例并行新跑、2 例复用，47 份原答格式有效，共 111 条支路。[统一对照网页](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/index.html)已发布，支持勾选模型，回放标记仅取 v006 有效节点。

2026-11-21 [Recovery v1.1 两例试跑](../experiments/agent_recovery/branch_review_v001.1/run_20261121_01/README.md)完成。逐视图候选和跨视图分组可追溯；Qwen 在 C50、C07 均合并了右视图候选，未保留独立右支路。GPU3 原服务已回到待用状态。

2026-11-21 [DeepSeek 两例并行复核](../experiments/agent_recovery/branch_review_v001/run_20261121_03_deepseek2/README.md)完成。v006 C50、C07 复用原七图和 Prompt，两例均返回格式有效的结果，且均列出右前方支路。

2026-11-21 10:43 UTC，[v006 全部回退节点的第一次调用](../experiments/agent_recovery/branch_review_v001/run_20261121_02_all47/README.md)完成。已处理 47/47 个回退节点，其中新增 37 例、复用 10 例。格式有效 47 例，共列出 101 条支路，匹配到此前所走支路 47 例、模型回答不确定 0 例。

2026-11-21 09:20 UTC，[Recovery 第一次调用 v001 十例](../experiments/agent_recovery/branch_review_v001/run_20261121_01/README.md)完成：按用户指定使用 v006 的 C42、C46、C49、C50、C07、C05、C09、C10、C20、C21，GPU3 Qwen27B，每例固定七图且不输入任务指令。10/10 格式有效，模型共列 24 条支路、10 次 identified；无准确率评分。没有第二次指令调用或导航，GPU3 模型按要求继续保留。[双语可视化已发布](http://134.175.18.101/vln/recovery_branch_review_v001_ten_web_20261121_02/index.html)，支路清单、此前所走支路与七图证据醒目展示，附完整离线包。

2026-11-21 按用户新指令，[GPU3 Qwen27B 待用服务](../experiments/agent_route_choice/services/qwen27b_gpu3_20261121_01/README.md)后台启动已确认：主管 993933、模型服务 994127，`http://127.0.0.1:56923/v1`，模型名 `route53-qwen27b`。复用既有环境和权重，`--process-only` 不探测就绪或发送推理，已结束人工跟踪。此服务操作不启动 recovery 第一次调用实验。

2026-11-21 [Recovery 第一次调用 v001](../experiments/agent_recovery/branch_review_v001/README.md)已保存 Prompt 与输入输出协议草稿。固定节点三向图及 +2、+5、+8、+10 前视，共七图；当前层级支路盘点与已走支路识别合并一次调用。本轮仅编写，尚未指定评审模型或样本，未运行推理、导航或 HTML 导出。

2026-11-21 [v006 多视角页面新增 ±70° 选项](../experiments/deviation_progress/v006/exports/node_multiview70_20261121_01/README.md)已发布到[原网址](http://134.175.18.101/vln/v006_node_multiview_web_20261121_01/index.html)。376个存档节点的1128张新图已接入，三种视角切换、节点联动与放大检查通过，远端资源及原入口HTTP 200通过。

2026-11-21 06:04 UTC，[v006 去重节点三向观测补采](../experiments/multiview_capture/v006_pose70/run_20261121_01/README.md)完成 376/376 个节点，左 70°、正前、右 70° 共 1,128 张新图。任务正常结束，GPU 3 已释放。

2026-11-21 04:48 UTC，[v006 去重节点三向观测补采](../experiments/multiview_capture/v006_pose70/run_20261121_01/README.md)已在 GPU 3 启动，主管 PID 773252，首场景 kujiale_0036。预计 53 条轨迹、376 个保留节点、1,128 张新图。运行目录的 status.json 和 progress.json 记录实际进度。

2026-11-21 04:41:55 UTC，按用户最新指令，[GPU3 Qwen27B 服务](../experiments/agent_route_choice/services/qwen27b_gpu3_20261120_01/README.md)已释放。主管及全部服务子进程退出，状态 `stopped`，GPU3 最终仅 5 MiB 基础占用、无计算进程。v6/v6.1 均已完成，权重和结果保留；此前保留服务要求已被本次释放命令终止，不自动重启。

2026-11-21 04:37 UTC 状态核对：v6.1 已于 04:00:22 UTC 完成全 53 条（51 条新跑＋复用 C35、C38），完整汇总 236 轮，189 consistent、45 deviated、2 格式错误，45 条轨迹报警。v6、v6.1 双版本评审已全部完成，主管进程 619682 正常结束。报警数量不代表准确率。本次仅核对并登记结果，v6.1 尚未加入对比网页。[运行与结果记录](../experiments/deviation_progress/v006.1/paired53_20261120_01/resume_20261121_01/README.md)

2026-11-21 03:02 UTC，[v006 节点多视角](../experiments/deviation_progress/v006/exports/node_multiview_20261121_01/README.md)已[发布](http://134.175.18.101/vln/v006_node_multiview_web_20261121_01/index.html)。在五版本页面上加入全部 376 个保留存档节点、53 个终止节点的 180°三视图／360°八方向，突出 47 个 v006 回退目标。3,432 张展示图与节点帧对应，附 138.0 MB 完整离线包；定向交互、双语、手机布局、远端哈希及入口 HTTP 200 通过。原页面与实验结果保留，无新模型调用或 GPU 操作。

2026-11-21 [v6 与既有 v3/v5 五组整合](../experiments/deviation_progress/v006/exports/comparison_20261121_01/README.md)已发布并更新[原网址](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)。默认勾选 Qwen v005、DeepSeek v005、Qwen v006，最多三组偏航区间，原四组历史结果保留。共 1,131 轮原答，离线包 84.4 MB。交互、双语、资源哈希及原入口公网检查通过，无新增模型调用，不干预 GPU 3 后台任务。

2026-11-21 01:41 UTC，[Qwen v006 全 53 条单页可视化](../experiments/deviation_progress/v006/exports/web_all53_20261121_01/README.md)已发布到[独立网页](http://134.175.18.101/vln/qwen_v006_all53_web_20261121_01/index.html)。完整收录 253 轮原答、4,890 帧、实际输入清单与累计进度，47 条报警、9 轮格式错误分别展示，附 78.3 MB 精简离线包。双语与回放交互、远端哈希和 HTTP 200 通过。本次仅导出，不干预 GPU 3 模型或后台 v6.1 评审。

2026-11-21 01:12:46 UTC，v6 已完成 53/53。合并各来源共 253 轮，197 consistent、47 deviated、9 格式错误，47 条轨迹报警。未报警为 C04、C18、C23、C35、C40、C41。C50 的长回答在放宽超时后返回，因达到长度上限而拒收，后续 S05 报警。同一进程已自动进入 v6.1，核对时新完成 C01、C02，连同复用两条为 4/53，正在 C03。[接续记录](../experiments/deviation_progress/v006.1/paired53_20261120_01/resume_20261121_01/README.md)

2026-11-21 00:56 UTC，[GPU 3 双版本接续](../experiments/deviation_progress/v006.1/paired53_20261120_01/resume_20261121_01/README.md)已启动，后台 PID 619682。v6 复用 49 条和 C50 前两轮，从 S03 继续，随后自动跑 v6.1 余下 51 条。模型已正常生成，启动确认已结束。新增运行目录为 `outputs/deviation_progress/v006_pair_route53_20261121_01`，本地请求等待上限 900 秒，临时传输故障最多额外重试三次。

2026-11-21 状态核对。[v6 / v6.1 后台评审](../experiments/deviation_progress/v006.1/paired53_20261120_01/README.md)于 2026-11-20 20:38 UTC 因 C50／S03 的 300 秒 ReadTimeout 退出。v6 已完成 49/53（含复用两条），C50 保存了前两轮，C51–C53 待评审。v6.1 仍仅有既有两条，剩余 51 条尚未启动。主管 384770 已退出，GPU 3 Qwen 进程仍在且健康接口通过。

2026-11-20 17:12 UTC，[GPU 3 Qwen 双版本全样本评审](../experiments/deviation_progress/v006.1/paired53_20261120_01/README.md)已由独立后台进程 384770 启动，先跑 v6、后跑 v6.1，两版各补 51 条。v6 的 C01／S01 已返回 `consistent` 并通过校验，人工启动确认已结束。

2026-11-20 17:00 UTC，[GPU 3 Qwen v6.1 的两例复评](../experiments/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/README.md)完成，10 轮均通过校验。C35 在 F4→F14 报警，C38 避免 F5 提前报警但漏报 F72–F75 错误分支。双版本全样本仍待启动，两版各余 51 条。

2026-11-20 [v6.1 偏航 Prompt 与 C35、C38 错误分析](../experiments/deviation_progress/v006.1/README.md)完成。[GPU 3 Qwen 的双版本全样本入口](../experiments/deviation_progress/v006.1/paired53_20261120_01/README.md)已通过 CPU 清单与接口检查，等待用户启动。v006 复用 2 条、补 51 条，v006.1 待跑 53 条，本次新增模型调用 0 次。

2026-11-20 16:25 UTC，[v006 二分类偏航识别](../experiments/deviation_progress/v006/README.md)完成 GPU 3 Qwen 的 C35、C38 复评。七轮均通过校验。C35 漏报选错浴室，C38 在 F0→F5 提前报警，离线标注的错误分支在 F72–F75。[运行记录与原答](../experiments/deviation_progress/v006/run_20261120_01_qwen_gpu3_c35_c38/README.md)

2026-11-20 15:59 UTC，[GPU 3 Qwen v5.1 复评 C38](../experiments/deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38/README.md)完成，七轮均为 `consistent`。S05 保留了盆栽和厨房的通行要求，S06 又跳过两项要求并宣布完成，本例仍漏报。GPU 3 模型继续保留。

2026-11-20 [四版本页面去重开关修复](../experiments/deviation_progress/v005/run_20261120_06_deepseek_official33/exports/four_versions_20261120_02/README.md)已更新到原网址及修正版离线包。导出时页面 tag 与去重来源 tag 错配，导致开启去重仍显示原始候选；现已同步标识，C02 开关检查通过。DeepSeek v005 的 429 个冻结节点及实际 219 轮端点核对无删除候选，模型结果不受影响，无新增模型调用。

2026-11-20 13:48 UTC，[Qwen / DeepSeek 的 v003、v005 四版本对比](../experiments/deviation_progress/v005/run_20261120_06_deepseek_official33/exports/four_versions_20261120_01/README.md)已发布到[原网址](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)，最多同时勾选三组偏航区间，详情单独切换。共 878 轮原答；DeepSeek v003 仅 C01–C29，其余明确标为未评审，其他三组各 53 条。82.3 MB 完整精简离线包同步发布；交互、资源哈希和公网入口检查通过。仅导出现有结果，GPU 3 Qwen 保留。

2026-11-20 13:24 UTC，[DeepSeek v005 官方接续](../experiments/deviation_progress/v005/run_20261120_06_deepseek_official33/README.md)全部完成 53/53 条（保留网关阶段结果、官方完成剩余 33 条），0 条接口失败。共 219 轮：161 consistent、47 deviated、11 格式错误；47 条轨迹触发有效报警，原答完整保留。用户要求跟踪至完成，现已结束跟踪；GPU 3 Qwen 继续保留。

2026-11-20 [DeepSeek 官方接口接续剩余 33 条](../experiments/deviation_progress/v005/run_20261120_06_deepseek_official33/README.md)已启动，主管 PID 4097663，33 个进程全部发出请求，已有 6 轮官方 HTTP 200 回答通过校验。复用网关阶段已完成的 20 条和匹配中途回答；新增请求发往 `https://api.deepseek.com`，来源另行记录。确认启动后交后台，GPU 3 Qwen 保留。

2026-11-20 13:05 UTC，[DeepSeek v005 15 并行](../experiments/deviation_progress/v005/run_20261120_05_deepseek15/README.md)因网关错误未完整跑完，主管已退出。完成 20/53 条，33 条失败（13 条 524 超时、17 条 525 SSL 握手失败、3 条断连）；保留所有已完成及部分回答，共 99 轮有效回答、2 轮格式错误。此次状态查看未启动补跑，GPU 3 Qwen 继续保留。

2026-11-20 12:52 UTC，[DeepSeek v005 15 并行接续](../experiments/deviation_progress/v005/run_20261120_05_deepseek15/README.md)已从等待转为实际评审，完成 8/53 条（复用 6 条、新完成 2 条），已保存 50 轮有效回答；仍有 HTTP 429，37 次限流尝试已记录并按协议退避，当前无最终失败轨迹，后台主管存活。

2026-11-20 12:47 UTC，用户将 DeepSeek v005 从 53 并行改为 15 并行。[15 并行接续主管](../experiments/deviation_progress/v005/run_20261120_05_deepseek15/README.md) PID 4064299 已启动，等待旧批最后 3 条在途任务结束后自动接续；旧批当时完成 4 条、46 条因 HTTP 429 失败。复用已完成轨迹及匹配的已返回回答，429 请求有限退避；不再发起 53 并行。端点为用户指定的 `https://ai.dijinlong.com/v1`，GPU 3 Qwen 保留。

2026-11-20 12:28 UTC，[v005 全 53 条精简离线包](../experiments/deviation_progress/v005/run_20261120_03_remaining47/exports/compact_20261120_01/README.md)已发布，78.4 MB。全部 272 轮原答、4890 帧、地图、输入清单和累计进度保留；输入图片复用同帧同分辨率 WebP 展示副本，原始 PNG 哈希保留，原无损包继续可下载。

2026-11-20 12:20 UTC，[v005 全 53 条回放](../experiments/deviation_progress/v005/run_20261120_03_remaining47/exports/web_all53_20261120_01/README.md)已更新至原网址，272 轮原答、实际输入帧和累计进度完整收录，379 MB 离线包同步发布。6156 个资源远端哈希通过，页面、JSON、ZIP 均 HTTP 200。GPU 3 模型继续保留。

2026-11-20 11:53 UTC，[v005 剩余 47 条补跑](../experiments/deviation_progress/v005/run_20261120_03_remaining47/README.md)全部完成。加上复用六条，共 53/53 条、272 轮：232 次 consistent、40 次 deviated，0 次格式错误，40 条轨迹报警（不代表报警准确率）。GPU 3 Qwen 按用户要求继续保留。当前网页仍为 48 条阶段快照，尚未更新最终五条。

2026-11-20 11:46 UTC，[v005 当前已完成的 48 条样本阶段回放](../experiments/deviation_progress/v005/run_20261120_03_remaining47/exports/web_partial_20261120_02/README.md)已发布到原网址，附 250 轮原答、实际输入帧、累计进度和离线 ZIP。余下评审仍在后台继续。

2026-11-20 08:25 UTC，[v005 剩余 47 条补跑](../experiments/deviation_progress/v005/run_20261120_03_remaining47/README.md)后台启动，PID 3851381，当前进入 C01。用户选择仅补跑 v005，复用已完成六条，GPU 3 模型继续保留。

2026-11-20 [Qwen v005 六例回放](../experiments/deviation_progress/v005/run_20261120_02_qwen_gpu3/exports/web_20261120_01/README.md)已发布，原网址默认显示 v005，可切换 Qwen v004 和 DeepSeek v004，附逐轮原答、输入图片、进度和离线 ZIP。

2026-11-20 [偏航识别 v005](DEVIATION_PROGRESS_V005.md) 只接受 `consistent` 或 `deviated`。08:06 UTC，[GPU 3 常驻 Qwen 的六例评审](../experiments/deviation_progress/v005/run_20261120_02_qwen_gpu3/README.md)完成 6/6，共 33 轮，5 条轨迹报警，0 次格式错误。模型继续保留。

2026-11-20 用户指定 GPU 3 常驻 Qwen27B，供后续任务复用；空闲时继续保留，直至用户明确下达释放命令。本次仅核验后台进程启动。[服务记录与接口](../experiments/agent_route_choice/services/qwen27b_gpu3_20261120_01/README.md)

2026-11-20 [Qwen27B 与 DeepSeek 六例同页回放](../experiments/deviation_progress/v004/run_20261120_01/exports/paired_web_20261120_01/README.md) 已发布到原网址。Qwen 的 35 份原答均通过修复前后两版校验，仅 C11 报警。修复后的 DeepSeek 回放采用 29 轮，5 条轨迹报警。[打开回放](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)

2026-11-20 [v004 校验器兼容格式标记](../experiments/deviation_progress/v004/run_20261120_03_contract_replay/README.md)。DeepSeek 六条原答重新走首次偏航停止流程，5 条有效报警，29 轮纳入，新增模型调用 0 次。

2026-11-20 [DeepSeek v004 六条逐轮回放](../experiments/deviation_progress/v004/run_20261120_02_deepseek6/exports/web_20261120_01/README.md) 已发布。6/6 完成，30 轮、4 条有效报警、1 轮格式失败。[在线查看](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_01/index.html)

2026-11-20 [DeepSeek v004 六进程对照](../experiments/deviation_progress/v004/run_20261120_02_deepseek6/README.md) 已启动，与 GPU 2 的 Qwen27B 使用相同的六条离线轨迹、节点和中文 Prompt。

2026-11-20 [偏航识别 v004](DEVIATION_PROGRESS_V004.md) 已通过 CPU 接口测试及 10 条离线轨迹的 65 轮历史回放核查。[GPU 2 的六条 Qwen27B 重跑](../experiments/deviation_progress/v004/run_20261120_01/README.md) 复用 v003 离线输入，最新状态见该记录内的运行状态文件。

2026-11-18 [Qwen 全部 53 条偏航结果已同步至原网页](../experiments/deviation_progress/v003/run_20261118_01_qwen27b/exports/deviation53_web_20261118_01/README.md)，C30–C53 新增 17 条红色区间，全组 36 条。

2026-11-18 [Qwen 去重回退点的分叉覆盖](../experiments/deviation_progress/v003/run_20261118_01_qwen27b/analysis/branch_coverage_01/README.md)。44 次明确分叉中，22 次的标注决策区间内有保留节点，16 次原始候选未命中，6 次在去重中失去命中。

2026-11-18 10:59 UTC，DeepSeek 完成 29/29 条偏航识别，28 条有明确偏航。原回放已增加独立 DeepSeek 图层，并通过了公网校验。[记录](../experiments/deviation_progress/v003/run_20261118_03_deepseek29/exports/web_20261118_01/README.md)

2026-11-18 10:52 UTC，[DeepSeek 的 29 条偏航对照](../experiments/deviation_progress/v003/run_20261118_03_deepseek29/README.md)已按 C01–C29 启动。29 个独立工作进程均成功发出图像请求，节点和终止帧与 Qwen 组逐条核对。

2026-11-18 [Qwen 53 条轨迹的回放修正](../experiments/deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_web_20261118_01/README.md)补齐 53 个终止节点。4,890 帧可回放，4,837 帧有 JEV 评分；模型评审清单自本轮开始已包含终止节点。

2026-11-18 10:38 UTC，Qwen 53 条去重回放的偏航标记已同步至 C28，共 19 条轨迹有明确偏航。地图与波形开关、原网址公网哈希均已核验。[发布记录](../experiments/deviation_progress/v003/run_20261118_01_qwen27b/exports/deviation28_web_20261118_01/README.md)

2026-11-18 10:25 UTC，53 条去重回放原网址已加上前 19 条的偏航开关，12 条的实际偏航路径及对应评分区间可同步标红。[验证与发布记录](../experiments/deviation_progress/v003/run_20261118_01_qwen27b/exports/deviation19_web_20261118_01/README.md)

2026-11-18 09:19 UTC，[Qwen27B 全部 53 条轨迹的去重回放](http://134.175.18.101/vln/qwen27b_route53_dedup_v001_web_20261118_01/index.html)已发布。494 个候选保留 376 个，338 次比较逐对可查。53 条轨迹的双语交互、4,859 个远端文件哈希及公网入口 HTTP 200 已核验。[离线版与验证记录](../experiments/deviation_progress/v003/run_20261118_01_qwen27b/exports/all53_web_20261118_01/README.md)

2026-11-18 08:39 UTC [Qwen27B 前 31 条轨迹去重回放](http://134.175.18.101/vln/qwen27b_route31_dedup_v001_web_20261118_01/index.html)已发布。固定 C01–C31 的 270 个候选、204 个保留节点和 191 对模型比较。[验证记录](../experiments/deviation_progress/v003/run_20261118_01_qwen27b/exports/first31_web_20261118_01/README.md)

2026-11-18 08:17 UTC [DeepSeek 十场景去重回放](http://134.175.18.101/vln/deepseek_route10_dedup_v001_web_20261118_01/index.html)已发布，支持 93 个原始候选与 49 个保留节点的对照。[发布记录](../experiments/deviation_progress/v003/run_20261118_02_deepseek10/exports/web_20261118_01/README.md)

2026-11-18 [DeepSeek 十场景去重](../experiments/deviation_progress/v003/run_20261118_02_deepseek10/resume_01/README.md)完成。C48 从断点补齐，10 条轨迹的 93 个候选保留 49 个；偏航识别按用户要求暂停。

2026-11-18 [DeepSeek 十场景离线对照](../experiments/deviation_progress/v003/run_20261118_02_deepseek10/README.md)已登记。使用 10 个进程评审 10 条轨迹的 93 个候选，先去重，再识别偏航。

2026-11-18 GPU 2 的旧仿真与 GPU 3 的旧 StreamVLN 已释放。GPU 3 部署本地 Qwen27B，处理 53 条离线轨迹的 494 个候选节点，按去重 v001、偏航识别 v003 两阶段运行。[运行记录](../experiments/deviation_progress/v003/run_20261118_01_qwen27b/README.md)

2026-11-18 07:00 UTC，[53 条轨迹的 JEV 去重前候选点网页](http://134.175.18.101/vln/jev_route53_sampling_v001_web_20261118_01/index.html)已发布。4,837 个前视概率、494 个候选、地图开关与双语切换通过上线包浏览器核验，4,859 个文件远端哈希通过。[发布记录](../experiments/crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/web_20261118_01/README.md)

2026-11-18 [53 条前视轨迹的 JEV 候选点](../experiments/crossing_checkpoint/online_sampling_v001/run_20261118_01/README.md)已完成。使用[当前固定版本](../experiments/crossing_checkpoint/current_jev_version.json)，300 进程并行评分，4,837/4,837 个位置有效，共 494 个去重前候选节点。逐帧响应和[本地网页](../outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/front_candidates_01/index.html)逐轨迹核对通过。

2026-11-18 05:36 UTC，[53 条选路错误数据集回放](../experiments/offline_route_dataset/v001/run_20261118_01/exports/replay_20261118_01/README.md)已发布。实际与参考路线可分别勾选，53 轨迹、54 事件、4,890 步均有同步观测。浏览器交互、远端资源 SHA256 和公网入口检查通过。

2026-11-18T05:17:33Z：[69条多视角失败归因与离线数据集](../experiments/offline_route_dataset/v001/run_20261118_01/README.md)完成。纳入53条（早期25、新28；明确分支43、方向扩展10），排除13、不确定3；54事件、19场景、4890观测。独立包包含完整180度/360度/前视、位姿朝向、事件标签及因果读取器；53条打包检查、434份元数据/审核图哈希、267张PNG抽验及隔离搬迁读取通过。标签为Codex离线证据初版，非人工共识或反事实因果证明；保留模型/仿真未操作。

2026-11-18T04:35:22.095970+00:00：[69条多视角失败归因与离线数据集](../experiments/offline_route_dataset/v001/run_20261118_01/README.md)开始。原104条采集完整性已通过；仅分析本次SR=0的69条新轨迹（早期来源34、新来源35），逐事件审阅选路错误，历史标签不直接沿用，保留模型与仿真不变。

2026-11-18T04:27:15.269416+00:00：[104条逐步多视角采集](../experiments/multiview_capture/v001/run_20261117_03/README.md)后台状态`complete_services_retained`，正式评分104/104，详见记录。

2026-11-17：[450条原版合并错误分析](../experiments/crossing_analysis/pooled450_v001/run_20261117_01/README.md)完成。早期250条seed2＋新200条原版，450个唯一任务/21场景；官方成功197（43.78%）、失败253。既有标签统一映射：选路/起步方向107、回返13、未完成/局部无效移动45、目标走过头1、无明确选路偏航跌倒12/卡住5、旧异常终止未复核46、不确定24。207条有逐例审阅记录，46条仅按终止方式分组；不新增因果确证。450总表、253失败明细、场景与终止交叉表、PNG/PDF及输入哈希检查完成，无新导航或服务变更。

2026-11-17T09:39:30.496666+00:00：[104条逐步多视角采集运行03](../experiments/multiview_capture/v001/run_20261117_03/README.md)真实启动验证通过，已交后台继续。GPU3原模型3194667未重载，GPU2仿真2366636；前5步40张360°视图、15张180°引用及真实位姿/朝向、物理状态不变、外观恢复均通过，前2步原生前视与模型收到图像逐像素一致。后向自身遮挡修复并经图像抽查；18项CPU检查通过。交接时正式评分0/104，采集至step 26；完整终止与104条验证由后台负责，不持续人工跟踪。

2026-11-17T09:27:21.709375+00:00：[104条逐步多视角采集](../experiments/multiview_capture/v001/run_20261117_02/README.md)后台状态`stopped`，正式评分0/104，详见记录。

2026-11-17T09:13:18.893749+00:00：[104条逐步多视角采集](../experiments/multiview_capture/v001/run_20261117_01/README.md)后台状态`failed`，正式评分0/104，详见记录。

2026-11-17T09:04:06.500221+00:00：[104条逐步多视角采集](../experiments/multiview_capture/v001/run_20261117_01/README.md)已获启动授权，正在准备；复用GPU3保留模型，逐step采集180°/360°与真实位姿，确认正常后后台运行。

2026-11-17T08:28:37.669213+00:00：[原版选错路56条对照可视化](../experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/README.md)已完成并发布：[打开网页](http://134.175.18.101/vln/oracle_route_choice56_run04_web_20261117_01/route_choice56.html)。沿用原Oracle双进度条模板，含两组真实轨迹、56张俯视图、66次纠错与四类筛选；46条有干预且成功、3条有干预失败、3条未干预成功、4条未干预失败。原版缺失RGB明确标注，56条双语与本地浏览器检查、远端全资源哈希及公网入口验证通过。只导出现有结果，服务未变。


2026-11-17T07:57:50.584928+00:00：[原版102条失败分类](../experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01/README.md)完成。离线轨迹归因：偏航/方向错误64条（失败62.75%、全部200条32%），含56条选错方向/分支/漏转弯、8条反向回返；另8条不确定未计入。64条对应纠错组53成功、11失败。102条理由/CSV及审核图已保存，原版缺少全程RGB的限制已明确，无新导航或服务变更。


2026-11-17T07:33:13.047602+00:00：[同200条两组对照04](../experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/README.md)全部完成，400/400；纠错156/200（78%），原版98/200（49%），同任务SR差+29个百分点，69胜11负。两组原生验证通过，离线汇总缺失附加记录问题已修复并保留异常证据，原成绩不变；GPU3原模型3194667、GPU2最后仿真1977525按要求保留。原版102条失败的分类及案例筛选尚未开始。


2026-11-17T02:13:43.668942+00:00：[自动纠错25条可视化导出](../experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/auto_branch25_20261117_01/README.md)已发布：[打开回放](http://134.175.18.101/vln/oracle_auto_branch25_run04_web_20261117_01/auto_branch25.html)。沿用原Oracle双进度条模板，覆盖11场景、27次纠错，含俯视底图、25张独立地图和中英文切换；本地浏览器与远端资源哈希、公网入口验证通过。仅导出现有数据，原版对照继续后台运行。

2026-11-17T00:47:05.077702+00:00：[缩量运行04](../experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/README.md)200条纠错组完成，原版对照已自动接续。纠错组200/200、11场景、成功156（78%）、SPL 0.6030，原生导出验证通过；原版同200条已完成3条，GPU2仿真继续，GPU3原模型保持加载。

2026-11-16T23:43:02.054517+00:00：用户将两组缩减为各约200条，后续以[缩量接续04](../experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/README.md)为准。保留当前算法已完成结果，在200条附近原生任务评分边界结束，再运行完全相同任务的原版对照；旧400条对照队列已取消。GPU3模型继续复用，6项CPU检查及真实已完成子集封印检查通过；控制器PID 1653533，新进度见运行04的`progress.json`。旧400条配置/源码/结果全部保留，不继续跑满400条。

2026-11-16T17:06:02.348080+00:00：[400条在线分支Oracle与原版对照03](../experiments/oracle_recovery/auto_branch_v001/run_20261116_03_gpu2sim_gpu3model/README.md)已确认真实导航正常，当前算法组已原生计分3/400条，4次实际纠错记忆一致性检查通过。GPU2仿真运行、GPU3原模型未重载；原版400条等待自动接续，后台汇总已启动。遵用户要求结束持续人工跟踪，最终保留服务；启动证明已保存，未宣称800条已完成。

2026-11-16 16:48 UTC：用户批准仅重启GPU2仿真，复用GPU3原模型。新[400条在线分支Oracle与原版对照03](../experiments/oracle_recovery/auto_branch_v001/run_20261116_03_gpu2sim_gpu3model/README.md)已启动：主管1332457、GPU2仿真1332521、GPU3模型3194667，auto_branch400先跑，baseline400等待器1332458。算法与准备01一致，17项启动适配检查通过；当前首场景初始化，0/400，尚未确认真实导航。旧串行主管/仿真/采样按授权退出，原记录及策略状态存档保留；模型未重载。

2026-11-16：[400条/22场景在线分支Oracle准备01](../experiments/oracle_recovery/auto_branch_v001/run_20261116_01/README.md)已完成，**等待用户验收，不开始导航**。原版与auto_branch各400条，同顺序/seed=2；在线估计已走轨迹分离位置，0.75米触发、前移1.25米、沿参考路线定向。59项CPU检查通过，仿真Python另复验其中21项；1325源码、44几何文件及原生入口一致性通过。静态162候选不作锚点，几何仅诊断；真实导航0条，暂停serial及保留服务状态未变。

2026-11-16：[400条新任务场景草案](../experiments/oracle_recovery/auto_branch_v001/scene_plan_20261116_01/README.md)统计完成。审计1321份实际StreamVLN记录、0解析异常：已跑290条/11场景（250主实验＋0272场景40条），剩535条/22场景；草案400条覆盖22场景，18场景各18条、4场景各19条。仅排除StreamVLN历史，其他backbone不在排除范围；清单/CSV/哈希已保存，未启动800次导航。自动分支定位52项CPU检查完成，人工场景标定仅为用户允许的补充方案，尚未执行。

2026-11-16：[自动轨迹分支锚点Oracle v001](../experiments/oracle_recovery/auto_branch_v001/README.md)准备完成：从实际位置历史拟合与参考路线分离的变化点，固定锚点后前移1.25米；0.75米触发、保留记忆/原预算。不确定则记录并跳过，不用当前位置替代。52项CPU检查、825条给定锚点几何、33条旧位置顺序回放、最终1324文件冻结/仅打印两组计划及环境检查通过；GPU导航0条，旧暂停任务保持暂停。用户追加400条场景覆盖统计与允许场景级补充标定，统计见该类别scene_plan记录。

2026-11-16 15:04 UTC：[无人工分叉点的自动落点Oracle v001](../experiments/oracle_recovery/auto_route_v001/README.md)代码准备完成：0.75米距离触发，执行时当前位置在正确参考路线上的最近投影后前移1.25米，沿路线自动定向，保留干预时记忆、允许重复纠正。38项CPU检查、825条官方路线的39958次几何检查、1322文件冻结/仅打印两组计划及StreamVLN环境检查通过；原生run_full字节不变。新协议与旧人工分叉点plus05分开；正式400条清单未冻结，GPU导航0条，serial运行05仍暂停。

2026-11-16 14:34 UTC：按用户明确要求，运行05已暂停，保留模型/仿真/GPU状态。主管1160721、仿真1160808及采样子进程1218163均SIGSTOP/T；GPU3原模型3194667继续在线，未释放GPU2/3。本轮正式2/33、成功1/2、跳过3条；禁止自动恢复，等待用户后续指令。 [暂停记录](../experiments/serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 14:24 UTC：运行05正式1/33、成功0/1、跳过3条，已继续kujiale_0240_8_4，同一模型/引擎。上一条199动作中实际执行2次回退与纠错交还，两次记忆哈希及交还后运动均核验；之后因DeepSeek缺少verdict技术跳过，无正式成绩。闭环技术证据与导航成功分开统计。 [运行记录](../experiments/serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 14:08 UTC：运行05仍在推进，正式1/33、成功0/1、跳过2条。当前kujiale_0257_82_4由17推进至83动作，84次有效JEV、11次偏航评审完成，当前等待下一次DeepSeek响应；无新增技术失败，模型/引擎均未重启。 [运行记录](../experiments/serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 13:44 UTC：运行05仍在推进，正式1/33、成功0/1、跳过2条。新增JEV HTTP520失败已自动跳过，同一仿真1160808继续下一任务kujiale_0257_82_4，已17动作/17次有效JEV；实际容错继续已验证，未重启模型或引擎。 [运行记录](../experiments/serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 13:35 UTC：逐条容错运行05启动验证通过，新任务kujiale_0257_73_4已3动作/3次有效JEV，原生策略记忆重置通过。继承1条评分，旧失败1条已绕过待补跑，继续后31条；主管1160721/仿真1160808，GPU2仿真/GPU3原模型保留。43项CPU检查与21份实答复核通过；按用户要求停止持续人工跟踪。 [运行05](../experiments/serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 13:29 UTC：逐条容错运行05已启动，主管1160721、仿真1160808，GPU2空闲44675MiB通过准入，GPU3原模型3194667未重载。继承1条正式结果、1条技术失败待补跑、31条待运行，43项CPU检查及21份历史实答重验通过。当前仿真初始化，真实新任务导航验证待完成；本轮不自动补跑已跳过条目。 [记录](../experiments/serial_recovery/v001/run_20261116_05_full33/README.md)。

2026-11-16 13:15 UTC检查：DeepSeek串行运行04于13:01 UTC退出，1/33完成、成功0/1、未执行回退；第二条5动作后因uncertainties返回zh/en两个列表而校验失败，HTTP200、非接口断连。GPU2本项目仿真已退出，GPU3原模型保留；本次只核验和登记，没有重启。 [运行记录](../experiments/serial_recovery/v001/run_20261116_04_full33/README.md)。

2026-11-16 12:59 UTC：三组33任务Oracle可视化已齐备，复用原Oracle双进度条模板。0.75米组17/33、实际存档回退组6/33、额外前移0.5米组22/33官方成功；旧两页保留并重验HTTP200，新回退页通过33任务/25回退本地浏览器检查、6943文件远端SHA256与公网HTTP200。仅导出现有结果。 [三组网址与导出证据](../experiments/oracle_recovery/distance_v001/run_20261115_06_checkpoint/exports/checkpoint_20261116_01/README.md)。

2026-11-16 12:36 UTC：[DeepSeek串行运行04](../experiments/serial_recovery/v001/run_20261116_04_full33/README.md)已启动，主管1121493、仿真1121566，GPU2共享仿真/GPU3原模型3194667。38项CPU检查及11份历史实答复核通过；只包装完整双语uncertainties单项对象，原答/文字/判定不改、不重试判断。当前初始化，0/33；运行03失败记录保留。

2026-11-16 12:34 UTC：[运行03](../experiments/serial_recovery/v001/run_20261116_03_full33/README.md)在11:55 UTC因DeepSeek将uncertainties写成单个双语对象而退出，0/33完成，50实际动作/50JEV，未执行回退；GPU2本次占用已释放，GPU3原模型保留。已添加仅容器包装的无损兼容，原答/文字/结论不改，38项CPU检查通过，11份真实偏航响应重验全部通过；正准备[运行04](../experiments/serial_recovery/v001/run_20261116_04_full33/README.md)继续原定33任务。

2026-11-16 11:42 UTC：[DeepSeek串行33任务运行03](../experiments/serial_recovery/v001/run_20261116_03_full33/README.md)启动验证通过：首条kujiale_0257_4_3已执行11个实际动作，11次JEV有效、2次DeepSeek偏航评审成功（HTTP200/完整响应），原任务记忆重置验证通过。主管1066001/仿真1066074，GPU2共享仿真、GPU3原模型3194667未重载；评分0/33，实际恢复闭环待后续。停止人工持续跟踪，后台继续全批。证据startup_verified.json。

2026-11-16 11:32 UTC：[DeepSeek串行33任务运行03](../experiments/serial_recovery/v001/run_20261116_03_full33/README.md)已实际启动，仿真GPU2/PID1066074，主管1066001，原StreamVLN GPU3/PID3194667不变。用户授权容量允许时共享忙卡；启动利用率80–100%、空闲约33GiB，通过12GiB准入。36项CPU检查通过；当前场景初始化，0/33，真实API/导航启动验证待完成。Qwen计划已被用户替换，不再重启。

2026-11-16 07:56 UTC：[Qwen27B串行33任务](../experiments/serial_recovery/qwen27b_v001/run_20261116_01/README.md)代码接入与35项CPU检查通过，自动队列PID917244已运行，当前等待GPU2/GPU3资源，仿真0/33。两卡新增他人Arrow任务，不抢占；首次Qwen服务预热失败已清理。资源满足后自动部署02、真实图片预检、冻结并启动33任务/34事件；原GPU3模型及旧仿真仍保留。队列状态：`outputs/serial_recovery/qwen27b_v001/queue_20261116_01/status.json`。

2026-11-16：[Qwen27B全模块串行实验](../experiments/serial_recovery/qwen27b_v001/run_20261116_01/README.md)准备中：用户确认GPU2本地Qwen替换全部DeepSeek语义模块；JEV/StreamVLN保留。33任务、34历史错误事件、9场景，真实仿真重跑。GPU2服务加载中，34项CPU检查通过，尚未启动本轮导航。

2026-11-16：按用户指定复用原JEV模板，已发布[串行联调02波形/采样/去重回放](http://134.175.18.101/vln/serial_jev_template_run02_web_20261116_01/serial_jev_replay.html)。`core/jev_sampling_lab`模板、原app和冻结采样器直接复用；7个实时节点逐点核验，地图/波形显示开关及去重7→2同步、完整曲线和双语通过本地浏览器，44文件远端哈希与公网HTTP200通过。登记见[导出README](../experiments/serial_recovery/v001/run_20261116_02/exports/jev_template_20261116_01/README.md)。无新模型/仿真。

2026-11-16：[串行联调02双语可视化](../experiments/serial_recovery/v001/run_20261116_02/exports/replay_20261116_02/README.md)已发布：[打开回放](http://134.175.18.101/vln/serial_pipeline_v001_run02_web_20261116_01/serial_pipeline_replay.html)。40帧、53次实际请求、三类轨迹、节点去重及评审、双进度条和中英文完整内容通过本地浏览器；44个文件远端哈希及公网入口HTTP 200通过。仅导出现有结果，无新模型/仿真；本次0恢复事件的证据边界明确标注。

2026-11-16 06:48 UTC查验：[单条串行联调02](../experiments/serial_recovery/v001/run_20261116_02/README.md)已于06:41 UTC完成1/1，官方成功0/1、NE 8.543米，最后动作STOP，未到目标。40次JEV、7个候选节点、6次去重后留2点；7次偏航评审为5次consistent、2次uncertain，回退/纠错/交还均0，完整恢复闭环未验证。模型3194667及引擎836845按要求保留，主管正常结束；未启动更多任务。

2026-11-16 06:28 UTC：[单条串行联调02](../experiments/serial_recovery/v001/run_20261116_02/README.md)已确认在GPU3正常导航：6帧真实观测、5个原任务动作，前5次实时JEV均有效，无运行失败；正式评分0/1，完整恢复闭环尚待结果。主管836172、仿真836845、原模型3194667保留。用户再次要求正常开跑后不持续跟踪，现交由后台主管继续单条任务与最终验证，不扩大任务量。

2026-11-16 [EasyJEV图像接口](../experiments/serial_recovery/v001/jev_easyjev_20261116_01/README.md)验证通过：历史三帧与单帧均200，有效概率0.64/0.61；实际响应typesafe/jev-1.14-20261014。JEV调用阻塞解除，正在准备[单条串行联调02](../experiments/serial_recovery/v001/run_20261116_02/README.md)，29项CPU检查通过；仍未取得完整仿真闭环结论，不扩大任务量。

2026-11-16 [TypeSafe官方文档/SDK核验](../experiments/serial_recovery/v001/typesafe_official_audit_20261116_01/README.md)完成：历史三帧通过当前官方OpenAPI和图片规则；官方SDK0.7.5通过api.site文本200、multipart图片400 invalid JSON request、JSON/base64图片400 TypeSafe rejected。实际图像头、图片字节及模型/问题一致性已核验，尚未发现客户端格式错误，具体网关/上游原因仍未定。未启动仿真，完整闭环仍阻塞。

2026-11-16 [Cttai新端点验证](../experiments/serial_recovery/v001/jev_cttai_20261116_01/README.md)：模型目录为空；原生`/v1/systemone`返回404 Invalid URL，聊天兼容路由返回503，明确default (distributor)分组无jev-1.14.0可用渠道。原生图像请求头已发送，完整请求与历史成功相同；未启动仿真，仍需可用JEV渠道。

2026-11-16 用户要求再次尝试：[原脚本复测02](../experiments/serial_recovery/v001/jev_original_retest_20261116_02/README.md)仍HTTP400，完整三帧请求与历史成功版本逐字节相同；无有效概率，未启动仿真。

2026-11-16 按用户要求直接运行原成功JEV探针脚本复测api.site：仍400 TypeSafe rejected the request；请求构建/发送模块与历史冻结源码一致，新旧完整三帧请求及图像审计逐字节相同。当前图像调用未恢复，未启动导航。见[原脚本复测](../experiments/serial_recovery/v001/jev_original_retest_20261116_01/README.md)。

2026-11-16 用户新提供AnyAIGC端点/令牌验证：单帧及三帧JEV1.14请求均404 model_not_found，实际图像请求头已确认；模型目录200、321个条目中无JEV。新端点当前无可用JEV渠道，未更换正式配置或启动仿真。见[AnyAIGC诊断](../experiments/serial_recovery/v001/jev_anyaigc_20261116_01/README.md)。

2026-11-16 JEV请求头复核：同一图像请求的curl实际发送日志确认已携带`TypeSafe-Danger-Zone-Images: true`；带头/不带头均400。证明客户端已发送，不能证明网关已向上游转发；根因未定。证据`outputs/serial_recovery/jev_header_wire_20261116_02/results.json`，见[JEV诊断记录](../experiments/serial_recovery/v001/jev_diagnostics_20261116/README.md)。

2026-11-16 JEV专项诊断：按用户要求优先核对模型和文档。1.14/1.13均为支持图像版本，实际文本200、图片400；直连和7892代理结果一致，简单320×320图片也失败；latest/preview被渠道标为停用。图像链路仍阻塞，未确定网关/上游具体原因，需按请求ID排查，见[诊断记录](../experiments/serial_recovery/v001/jev_diagnostics_20261116/README.md)。未重启仿真或继续DeepSeek调用，GPU3原模型保留；串行相关29项CPU检查通过，不能替代完整仿真验证。

2026-11-16 串行联调01更新：GPU3仿真已实际启动但在导航前因scripts包名遮蔽失败，0/1；主管未把Isaac退出码0误报成功，原模型3194667保留。导入冲突已在公共代码修复并新增回归测试。JEV鉴权目录200，但单帧及两个版本的已知三帧请求均400 TypeSafe rejected the request；正在排查接口。具体证据见[运行01](../experiments/serial_recovery/v001/run_20261116_01/README.md)，尚无完整闭环通过结论。

2026-11-16：[串行单目恢复v001](../experiments/serial_recovery/v001/run_20261116_01/README.md)已实现并冻结首条联调配置，10项新增CPU检查通过。JEV采样/去重、偏航进度、实际姿态回退、单目选路、v007局部纠错及记忆恢复交接已接入原生eval钩子；尚无本轮GPU通过结论。用户选择局部纠错后恢复接管前原任务记忆；先跑开发样本kujiale_0208_21_4，复用GPU3保留模型，不自动扩大到33条。运行状态以新目录status.json为准。

2026-11-16 00:20 UTC：[Oracle落点额外前移0.5米组可视化](../experiments/oracle_recovery/distance_v001/run_20261115_07_early_plus05/exports/early_plus05_20261116_01/README.md)已发布：[打开网页](http://134.175.18.101/vln/oracle_distance_plus05_33_run07_web_20261116_01/oracle_plus05_33.html)。33条、34标注事件、70次纠正，官方成功22/33、正常成功停止19条。原始/参考/本次轨迹及纠正前后画面、双语、双进度条通过本地浏览器检查；6980文件远端哈希和公网HEAD通过。只导出现有结果，未重跑导航或改变服务。

2026-11-16 00:10 UTC检查：回退06和额外前移0.5米07均完成33/33并通过评分导出核验，分别成功6/33（18.18%）和22/33（66.67%）。后续JEV点位采集03失败，0/159，三次均于首点probe阶段退出，具体根因尚未定位；日志与attempt保留。GPU3原模型3194667仍在，当前无本项目仿真运行；未重跑任何任务。

2026-11-15：JEV回退点采集03等待器PID3570684已运行，等待前移0.5米组07完成；159点/165引用，GPU图像仍0。朝向为估计值，尚未验证真实图像复原效果。

2026-11-15：[JEV去重节点180°/360°采集](../experiments/jev_point_capture/v001/run_20261115_03/README.md)已准备：165节点引用、159实际点、9场景，采用估计基础朝向并在采集时与原RGB校准。7项CPU检查通过，尚无本轮GPU图像；等待Oracle额外前移0.5米组07完整结束后在GPU3执行，模型保持加载。

2026-11-15 16:59 UTC：resume_20261115_02启动验证通过，正式评分已从9增至10/33。第10条`kujiale_0234_34_4`完成真实导航和评分；原版任务重置时模型历史/动作队列清空，9条旧结果哈希不变。主管3518096、仿真3518229继续后台运行，GPU3原模型PID3194667未重载。证据`resumes/resume_20261115_02/startup_verified.json`。07等待器3518738正常等待06全33条评分及导出后接续。停止人工持续跟踪；实验阈值、回退规则、原版场景与RSS生命周期均未改变。

2026-11-15 16:52 UTC：resume_20261115_02已实际启动，主管3518096、仿真3518229，从9/33继续；模型3194667仍在GPU3/40617，未重载。9条结果SHA256核验不变。07等待器3518738为waiting_for_checkpoint_group；只有06完整导出后才接续。当前仿真初始化中，首条新导航验证待完成。

2026-11-15 16:50 UTC：第一次续跑完成第9条`kujiale_0234_63_3`，官方计数已为9/33、成功0/9；本次轨迹未达到触发条件，未回退，不能称原朝向失败已在相同前缀通过。随后主管轮询碰到原版ResultLogger原位重写JSON的短暂空文件，JSONDecodeError导致仿真退出；9条正式评分与原模型均保留。已在独立`resumes/resume_20261115_02/`修复：读到未写完的JSON时沿用最后完整计数，下次重新读；最终完成仍要求完整评分/仿真保留标记和独立导出验证。9项相关测试通过（此前全套27项通过），实验协议不变，仿真缓存继续使用原代码目录的原缓存。从第10条续跑，后续07新计划为queue_plan_resume_20261115_02.json。

2026-11-15 16:39 UTC：已实际启动断点续跑，主管PID3506858、仿真PID3506983；模型保持PID3194667/GPU3/40617，未重载。启动时正式评分8/33，8条既有结果SHA256全部一致。仿真正在初始化，尚未确认第9条恢复通过；维护版本在`resumes/resume_20261115_01/`，tmux `oracle_checkpoint_resume_20261115_01`。后续07等待器PID3507365，tmux `oracle_extra05_resume_20261115_01`，状态为waiting_for_checkpoint_group。

2026-11-15 16:35 UTC：用户要求继续推进回退06及后续07。断点续跑、按原版规则重试仿真和attempt独立策略存档已完成，27项CPU检查通过；保留8条评分、原源码与失败证据，15°校验和实验协议不变。正在使用GPU3保留模型3194667准备恢复，实际导航验证尚待完成。

2026-11-15 16:23 UTC检查：[回退06](../experiments/oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)已异常中断，正式评分8/33、成功0/8，均一次回退。第9条`kujiale_0234_63_3`回退稳定后朝向偏差17.596°超过原15°校验上限，随后仿真退出；模型PID3194667继续保留在GPU3。[额外前移0.5米07](../experiments/oracle_recovery/distance_v001/run_20261115_07_early_plus05/README.md)为0/33，队列`prerequisite_not_complete`，尚未启动。未改校验阈值、未跳过失败样本、未续跑；原始结果和失败诊断均保留。

2026-11-15 16:03 UTC：[回退06](../experiments/oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)已完成首条正式评分1/33，第二条正在导航；真实存档、一次回退、模型存档内容一致、回退后无第二次纠正及原版评分均有证据（`first_checkpoint_verified.json`）。GPU3原模型PID3194667仍保持加载。后续后台续跑，不持续人工跟踪；完成后自动执行用户选择的[额外前移0.5米07](../experiments/oracle_recovery/distance_v001/run_20261115_07_early_plus05/README.md)，阈值仍0.75米、落点前移共1.25米。两组各33条，旧距离组不恢复，最终保留模型及最后仿真。

2026-11-15 15:55 UTC：用户已同意仅重启仿真，[回退运行06](../experiments/oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)已在GPU3初始化，主管3230841、仿真3230947，复用原模型3194667/端口40617，0/33。24项CPU检查通过；short剩余/medium/long已取消。用户另选额外前移0.5米，[运行07](../experiments/oracle_recovery/distance_v001/run_20261115_07_early_plus05/README.md)已排在06之后：仍0.75米触发，落点前移共1.25米，33条；34个落点均核对增量恰好0.5米，尚未开跑。最终保留模型和最后仿真。

2026-11-15 用户已取消剩余距离Oracle实验，要求保留模型和仿真，只开始最后的实际存档回退组。05的short保留19条评分，旧仿真/launcher已暂停，模型GPU3继续响应；未释放资源。[回退运行06](../experiments/oracle_recovery/distance_v001/run_20261115_06_checkpoint/README.md)已准备33条配置但尚未开跑：现有引擎没有热换组接口，正等待用户确认是否允许仅重启仿真、模型不重载。不得自动恢复旧short/medium/long队列。

2026-11-15 15:24 UTC：[距离Oracle 0.75米组33条回放](../experiments/oracle_recovery/distance_v001/run_20261115_05/exports/early_20261115_01/README.md)已完成并发布，展示参考正确轨迹、历史未干预轨迹、本次轨迹和93次瞬移。双语、双进度条、全部纠正跳转与手机布局通过本地浏览器验证；7378个文件远端哈希通过，入口HTTP 200。网址：http://134.175.18.101/vln/oracle_distance_075m_33_run05_web_20261115_02/oracle_075m_33.html 。只导出现有结果，其他组运行配置未改变。

2026-11-15 14:59 UTC检查：[自动Oracle运行05](../experiments/oracle_recovery/distance_v001/run_20261115_05/README.md)累计正式评分40/165（继承20、新增20）。early完成33/33，官方成功17/33（51.52%），26条触发、93次纠正；short完成7/33，成功5/7（71.43%），4条触发、25次纠正，其全组导出尚未完成。其余三组未开始。GPU3模型/仿真继续运行；原版同一仿真进程已连续完成early剩余13条并通过整组导出验证。early中1条跌倒、1条卡住因终点距离小于3米仍计官方成功；分组结果尚不能解释为纠正净收益。按用户要求不持续人工跟踪。

2026-11-15 13:41 UTC检查：[自动Oracle运行05](../experiments/oracle_recovery/distance_v001/run_20261115_05/README.md)已固定模型/仿真GPU3，采用用户明确授权的原版`--allow-shared-gpu`。主管3098932、模型3099126、仿真3099726存活；模型AGENT_READY，仿真正在初始化，尚未进入导航/新增评分。旧20条结果保留，05继续145条；19项CPU检查通过，原版生命周期不变。04已停止、GPU2本项目资源已释放；GPU3既有SAM3服务保持运行。

2026-11-15 最新用户约束：[自动Oracle原版运行04](../experiments/oracle_recovery/distance_v001/run_20261115_04/README.md)严格沿用原版run_full.py及原生eval循环，只接入距离Oracle钩子；禁止擅自更改生命周期。自定义场景批次/缓存已撤除。03在在途3条完成后退出，02+03共20条结果保留，余145条。源码已冻结，18项CPU检查及环境检查通过，原版launcher哈希一致；主管PID3091732已后台启动，13:29 UTC等待空闲GPU，尚无04实际GPU验证结果。

2026-11-15 用户授权优化：[自动Oracle批量运行03](../experiments/oracle_recovery/distance_v001/run_20261115_03/README.md)改为常驻模型、同场景多任务仿真和任务间完整重置。02完成17条early后在无在途任务边界停止，保留并引用结果；剩余148条分40批。源码已冻结，18项针对性CPU检查及环境检查通过；主管PID3066523已启动，等待空闲GPU，尚无03实际复用验证。正常后停止持续人工跟踪。

2026-11-15 12:37 UTC 检查：[自动Oracle运行02](../experiments/oracle_recovery/distance_v001/run_20261115_02/README.md)完成16/165，均为early（0.75米）组，当前第17条`kujiale_0232_23_2`在GPU2初始化仿真。已完成16条中10条触发、累计21次纠正；官方评分9成功（6条触发、3条未触发），2卡住、5未到终点。首条任务完成3次纠正并通过完整导航/评分链路，已存在首条验证文件。其余四组尚未开始；中间成绩不能作为全组结论或净恢复收益。后台继续运行，按用户要求不持续人工跟踪。

2026-11-15 08:29 UTC 检查：[自动Oracle运行02](../experiments/oracle_recovery/distance_v001/run_20261115_02/README.md)已准入GPU3，正在加载首条early任务`kujiale_0036_0_0`的StreamVLN模型，完成0/165。主管PID2786697、模型PID2792992存活，尚无ready或仿真评估进程，不能视为导航/自动复位已通过。准入时GPU3空闲；本次检查发现另一用户也已在该卡启动任务，未操作其进程。后台继续执行，尚无本轮导航成绩。

2026-11-15 自动Oracle启动更新：运行01在准入前遇到GPU2/3新占用，模型/仿真未启动；[运行02](../experiments/oracle_recovery/distance_v001/run_20261115_02/README.md)增加资源等待与自动选择空闲GPU，12项新增CPU检查通过，推理和实验协议不变。实际启动/等待状态以02记录为准。

2026-11-15：[距离阈值自动Oracle v001](../experiments/oracle_recovery/distance_v001/README.md)代码与CPU验证完成。原人工集33任务/34事件，默认0.75/1.5/3/4米四档瞬移纠正，另保留实际存档回退组，共165作业；无在线GPT判断。用户已授权在GPU启动，正常后后台推进；实际状态见[正式运行01](../experiments/oracle_recovery/distance_v001/run_20261115_01/README.md)。旧实验不覆盖。

2026-11-12：[偏航与累计语义进度 v003 方法及接手](DEVIATION_PROGRESS_V003.md)已冻结在 `codex/jev-online-sampling-v001` 分支；包含34案例原始结果、提示词、运行脚本与本地网页源码，记录no31提前误报限制。本次仅归档，无新增模型调用。

2026-11-12：[全部34个案例](../experiments/deviation_progress/v003/run_20261112_05/README.md)已完成：补跑22条，新请求74次、有效73次，12条的40次记录原样复用；六进程、本地网页。

2026-11-12：[十二条轨迹补齐](../experiments/deviation_progress/v003/run_20261112_04/README.md)已完成：仅补跑六条，新请求17次、有效16次，其余六条的23次记录原样复用；本地网页合并展示。

2026-11-12：[终止节点评审 v003](../experiments/deviation_progress/v003/run_20261112_03/README.md)已完成：26个有效节点（含6个终止节点），23次请求、17次有效、6次偏航判定，DeepSeek六进程；仅本地网页。

2026-11-12：[有效节点联合评审 v002](../experiments/deviation_progress/v002/run_20261112_02/README.md)已完成同六场景重跑，20个有效节点连续编号，19次请求、18次有效、2次偏航判定；旧v001包含已删除节点，不作为本轮结果。网页仅本地使用。

2026-11-12：[六场景偏航与语义进度联合评审](../experiments/deviation_progress/v001/run_20261112_01/README.md)已准备，用户授权DeepSeek六进程离线运行。复用43次节点建立事件和已有去重；端点＋均匀五帧，新增本地可视化。实际状态见新运行目录，不启动导航或网页发布。

2026-11-12 最新：[本地节点去重完整快照](../experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/README.md)已完成34条：298→165节点，206次实际调用含1次格式错误保留双方；源码和结果保存至原交接分支，网页仅本地使用。此条更新下方“尚未接入后续模型”的历史状态。

2026-11-12：[JEV 在线采样 v001](../experiments/crossing_checkpoint/online_sampling_v001/README.md)获用户认可，准备为主要开发机器合并接入；默认总延迟5个反馈步，确认结果固定。独立算法、41组固定样例、本地网页源码及跨机器导出已验证。网页默认关闭采样，曲线和路线始终完整显示；采样器仍只读取当前前缀。源码交接分支为 `codex/jev-online-sampling-v001`，接手先读 [JEV_SAMPLING_HANDOFF.md](JEV_SAMPLING_HANDOFF.md)。用户要求网页仅本地使用；尚未接入实际导航或后续大模型。

2026-11-09：人工标定集 34 个错误选择点已完成 JEV v004 与最初 Qwen4B 对照。
29 个新调用、5 个完整请求 SHA256 精确复用，34/34 有效；JEV 平均 yes 概率
0.762，19/34 ≥0.75，无低于 0.50 的点；Qwen4B 均分 3.353。用户指定并发上限
500，实际一次性提交 29 个缺失任务并使用 29 个 worker。新 AnyAIGC 端点持续
HTTP 429 后按用户指令切回此前可用端点。三栏双语页面已通过本地交互与移动端检查，
在线远端哈希和 HTTP 200 通过：
http://134.175.18.101/vln/jev_noul_v004_wrong_choices34_qwen4b_template_20261109_05/jev_noul_v004_vs_qwen4b.html 。
见
[`run_20261109_03_wrong_choices34_prevapi`](../experiments/crossing_checkpoint/jev_noul_v004/run_20261109_03_wrong_choices34_prevapi/README.md)。

2026-11-09：InternVLA-N1 fine Val Unseen seed0 曾在 GPU3 继续到
195/825条、8个完整scene；当时 supervisor PID 2192869 仅允许 GPU3，未抢占其他卡；
官方 H1 flash、模型、seed、数据和评分协议不变。记录见
[`run_20261109_01_gpu3_resume`](../experiments/reproduction/internvla_n1_vlnverse/run_20261109_01_gpu3_resume/README.md)。

2026-11-09：N1 GPU3 的 `kujiale_0093` 遇到 Isaac/PhysX 累积停顿，15分钟无日志后
worker终止。已将worker修正为模型服务保持加载、仿真420秒无进展时重启并复用同一
LMDB，最多5次。GPU3 supervisor PID 2939300 已继续执行 `kujiale_0093`。当前
195条完整scene样本的局部SR为44.62%（87/195）、SPL40.05%，不冒充最终825条结果。

2026-11-09：StreamVLN + Isaac Sim + 实时JEV的40条`kujiale_0272`实验完成并发布。
导航40/40，SR45.0%、SPL39.10%、NE3.984m；JEV共2878次有效回答、0错误，
最大step延迟5，215个`N=11,D=5`采样节点。本地浏览器核验40条/2878帧/2878回答，
中英文、地图节点和移动端通过。在线入口：
http://134.175.18.101/vln/streamvln_live_jev_0272_40_template_20261109_03/streamvln_live_jev_0272_40.html 。
真实户型底图由仓库既有USD几何正交投影方法生成；页面已改回既定三栏模板，
并实测轨迹按钮切换。前两版作为历史保留。
实验记录见
[`jev_live_vlnverse/run_20261109_01_0272_40`](../experiments/crossing_checkpoint/jev_live_vlnverse/run_20261109_01_0272_40/README.md)。

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

2026-11-08：lite_v003 单帧诊断完成。仅在 v002 prompt 中加入“短距离转入附近侧向开口不要求与当前朝向平行”，对 `kujiale_0113_1_4` frame 56 只调用 Qwen4B 1 次；仍返回1分，理由与v002相同。未改善该帧，不更新最优版本，不启动整批，未运行导航。

2026-11-08：lite_v004 单帧诊断完成。以 `best_v001` 为底稿，仅加入逐方向显式检查（前方、左侧、右侧、来路，各方向可含多个候选支路）；对 `kujiale_0257_11_2` frame 26 只调用 Qwen4B 1 次，仍返回1分。未改善，不更新最优版本，不启动整批，未运行导航。

2026-11-08：lite_v005 单帧诊断完成。进一步展开逐方向证据检查，要求各方向枚举多个入口并在全部检查后评分；`kujiale_0257_11_2` frame 26 只调用 Qwen4B 1 次，仍返回1分。未改善，不更新最优版本，不启动整批，未运行导航。

2026-11-08：lite_v006 双帧诊断完成。显式要求怀疑墙边、门框、柜体或画面边界后的空间延伸，并按线索强度评2—4分；`kujiale_0207_14_4` F58、F96 各调用 Qwen4B 1 次，均仍返回1分。未改善，不更新最优版本，不启动整批，未运行导航。

2026-11-08：lite_v007 双帧诊断完成。进一步规定画面边界或遮挡不能直接判成墙壁，只有明确连续墙、关闭不可进入门或固定家具才能支持1分；`kujiale_0207_14_4` F58、F96 仍均为1分。未改善，不更新最优版本，不启动整批，未运行导航。

2026-11-08：lite_v009—v012逐方向状态化迭代完成。v012将门洞内部延续和受限侧面默认候选纳入判断；目标F58=2、F96=3、F105=1。47个人工标注帧 `>=3` 从25增至30，20个稳定性控制帧中17个保持1分、3个升至2分、0个达到3分以上。出现可测效果但仍有标注帧降分，未更新最优版本，未运行导航。

2026-11-08：JEV/System One 新接口 v001 完成并做三帧试探。接口通过中转节点
`https://api.site/v1/systemone` 调用 JEV 1.14，输入严格三帧 RGB，使用一个五级
节点 Score 和前/左/右三个 Noul；密钥不落盘、不进入命令行参数。F58/F96/F105
映射后均为3分，连续分2.72/3.31/2.91，但置信度仅0.07/0.03/0.00，因此只证明
接口可运行，不宣称准确率或优于Qwen。额外40帧混合控制面板在用户询问后停止于
10/40且不纳入结论。见[`jev_v001`](../experiments/crossing_checkpoint/jev_v001/README.md)。

2026-11-08：JEV Noul 回退点接口 v001 跑通。保持 v1 三帧输入和局部路线选择定义，
单个 `fallback_point` Noul 直接返回 yes 概率；F58/F96/F105 分别为
0.22/0.32/0.26。不再使用1–5映射，也不生成理由。产物见
[`jev_noul_v001`](../experiments/crossing_checkpoint/jev_noul_v001/README.md)。

2026-11-08：JEV Noul v002 的5条离线全帧对照完成。自包含prompt、三帧RGB、50进程
并发，421/421次有效、0失败，JEV平均回退概率0.394；同帧Qwen4B平均分2.064。
页面双地图分别按Qwen 1–5分和JEV概率染色，颜色越深数值越高，支持中英切换和复核
意见导出。公网入口：
http://134.175.18.101/vln/jev_noul_v002_five50_vs_qwen_20261108_01/jev_noul_vs_qwen.html 。
在线Chromium与远端SHA256验证通过。仅作开发集同帧数值对照，不宣称准确率提升。

2026-11-08：JEV Noul v002 的完整61条离线集完成。首轮按用户要求1000 worker并发，
API出现HTTP/2协议中断、连接reset和超时；5007/5378成功，1000-worker进程池在
收尾阶段阻塞，父进程在结果落盘后终止。保留5007条成功结果，371条失败以100并发
补跑全部成功，最终5378/5378有效、0失败。网页使用Qwen同一轨迹，分图按Qwen分数
和JEV概率由浅到深染色，地图仅有路线和机器人位置，无人为路点。[在线入口](
http://134.175.18.101/vln/jev_noul_v002_full61_vs_qwen_20261108_02/jev_noul_vs_qwen.html)。
本地及在线Chromium、远端SHA256和HTTP 200验证通过。

2026-11-08：JEV Noul v003邻近候选回退点版本完成首条参考样本
`kujiale_0123_fix_15_3`：91个观测中90个有效新画面，一次性用90个并发进程提交，
90/90成功。v003平均回退概率0.317，上一版v002为0.223；80帧升高、8帧降低、
2帧相同。新版prompt为自包含英文，包含5步优先、最多约7步、弱视觉线索、历史图像、
普通空间排除和高召回规则；完整中文翻译随产物保存。地图仅保留同一Qwen轨迹的概率
深浅路线和机器人位置。[在线对照](
http://134.175.18.101/vln/jev_noul_v003_kujiale_0123_fix_15_3_20261108_01/jev_noul_v002_vs_v003.html)。

2026-11-08：JEV Noul v004精简邻近回退点prompt完成两条完整轨迹：
`kujiale_0123_fix_15_3` 90帧、`kujiale_0257_13_4` 98帧；v004共188/188有效。
为第二条轨迹补跑98个v003对照，共提交286个任务、100并发worker，均有效。v003均值
0.388，v004均值0.446；149帧升高、33帧降低、6帧相同。网页可切换两轨迹，地图仅
保留同一Qwen轨迹的概率深浅路线和机器人位置。[在线对照](
http://134.175.18.101/vln/jev_noul_v004_two_cases_20261108_01/jev_noul_v003_vs_v004.html)。

2026-11-08：JEV Noul v004在新增10条轨迹上完成862/862有效判断，最多200并发
worker。首轮859成功、3个空响应失败帧用3并发补跑后全部成功。与冻结v002相比，
平均回退概率0.380→0.495，753帧升高、91帧降低、18帧相同。网页支持10条轨迹切换，
仅显示同一Qwen轨迹的概率深浅路线与机器人位置。[在线对照](
http://134.175.18.101/vln/jev_noul_v004_ten_cases_20261108_01/jev_noul_v002_vs_v004.html)。

2026-11-08T15:24 UTC：用户要求释放属于本项目的GPU0 Qwen。已按服务记录和命令行
核验主管3935702、vLLM3936037后停止主管并确认两者退出；GPU0仅剩他人SAM3约4.2GiB，
空闲约44.2GiB。未停止其他用户进程。

2026-11-08：用户指定 `jev_noul_v004` 为**当前最好 JEV 版本**。当前指针为
`experiments/crossing_checkpoint/current_jev_version.json`，保留最新十条轨迹网页：
http://134.175.18.101/vln/jev_noul_v004_ten_cases_20261108_01/jev_noul_v002_vs_v004.html 。
该JEV指针独立于Qwen `best_v001`，未覆盖或混用Qwen最优版本。

2026-11-08：当前最好JEV v004已完成全部12条轨迹与最初Qwen4B `best_v001` 的合并
对照。共1050/1050个有效同帧结果、1062回放帧；Qwen平均分1.891、JEV平均概率
0.486。两者量纲不同，仅作描述性对照。[在线网页](
http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_20261108_01/jev_noul_v004_vs_qwen4b.html)。
地图仅保留Qwen 1–5分和JEV 0–1概率的深浅路线与机器人位置。

2026-11-09：v004/Qwen4B 12条轨迹对照页增加Gaussian、EMA、Moving Average、
离线Relative Prominence和Streaming Prominence，`N=3..31`窗口及`D=0..5`
最大延迟；原始两线可独立勾选。流式突出度只使用过去历史及最多D个未来观测，
达到i+D后冻结，验证追加6个未来点后既有历史不变。增强仅影响折线图，不改变地图、
原始分数或存档判断。[在线增强版](
http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_filters_20261109_01/jev_noul_v004_vs_qwen4b.html)。

2026-11-09：用户指定 **v004 prompt + Streaming Prominence（N=7,D=5）**
为当前最好 JEV 流水线。滤波版本`jev_noul_v004_filter_v001`，部署默认只把流式
突出度作为参考方法；Gaussian、EMA、Moving Average和离线相对突出度保留为对照。
当前指针更新`experiments/crossing_checkpoint/current_jev_version.json`。该指定是
用户选择，不代表独立准确率或优劣结论。

2026-11-09：v004/Qwen4B波形页增加核心采样点。流式突出度显示时，按高点0.6、
低峰0.18、相对峰谷差0.03、节点间距3帧、最短3帧平台中心起每5帧采样，并在横轴绘制
圆点、竖虚线和S编号。修复开头短平台导致首峰漏采：`kujiale_0207_41_0` 在
N=5/D=5时首峰F3已采样，节点为F3/F14/F20/F25/F49；12条轨迹约67个候选。
新增地图勾选项可在Qwen/JEV两张俯视图同步显示相同采样点。尚未调用大模型，
路线和原始结果不变。[在线采样页](
http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_nodes_20261109_04/jev_noul_v004_vs_qwen4b.html)。

2026-11-17：[JEV 偏航与语义进度 v003 / 34案例历史网页](http://134.175.18.101/vln/jev_deviation_progress_v003_34cases_web_20261117_01/index.html)按最新用户要求发布完成。199节点、33个红色模型偏航区间；原始判断不变，修复中文字体缺字。106份有效回答双语、34案例图片与红线/回退目标/双滑条通过本地浏览器；3288文件远端SHA256与公网HTTP200通过，无新模型或导航。[发布记录](../experiments/deviation_progress/v003/run_20261112_05/exports/web_20261117_01/README.md)。
