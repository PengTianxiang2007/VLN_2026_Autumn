# 自动纠错组25条回放与俯视地图

2026-11-17，状态：已完成并发布。用户要求导出20–30条自动纠错可视化、沿用既有模板并绘制俯视地图。本次选25条，覆盖已完成200条中的11个场景；使用原`core/oracle_distance_replay.html`双进度条模板，仅增加自动分离点数据与无历史对照的显示兼容，不建立新模板。

仅读取运行04导出的200条原生成绩和运行03原始轨迹/RGB/干预证据。seed=2，触发阈值0.75米，分离点沿参考路线前移1.25米，记忆保留。地图复用本批场景USD的已有几何投影，并按真实世界坐标叠加参考路线、实际行走段、瞬移、估计分离点及落点。静态几何候选点不作为运行时节点。

选择规则与ID见`selection.json`：每场景两条，优先取未截断到终点的纠错成功例和失败例，再补充已解释的实例、未纠错例及反复终点截断例；同类按固定SHA256排序。用于行为检查，不是随机抽样，页面样本成绩不能替代200条总体成绩。无完整Oracle回放的暖机跌倒任务不纳入本页；完整200条原生成绩不变。

输出目录：`outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/exports/auto_branch25_20261117_01/`。默认中文，完整英文原指令与对应中文逐条保留。完成后记录浏览器验证、哈希、发布证据与公开网址。现有原版对照后台继续，导出不启动模型或仿真。

网页：http://134.175.18.101/vln/oracle_auto_branch25_run04_web_20261117_01/auto_branch25.html

25张俯视图下载：http://134.175.18.101/vln/oracle_auto_branch25_run04_web_20261117_01/topdown_maps_25.zip

导出结果：25条、11场景、2035个回放节点、27次实际纠错（逐次记忆证明与跳变核验），18条触发、7条未纠错，5次落点截断到终点。展示样本15/25成功（60%）、14条正常成功停止；完整200条仍为156/200（78%），页面已明确区分。

导出命令：`backbone/streamvln/.venv/bin/python -B scripts/export_oracle_auto_branch_replay.py --campaign outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200 --selection outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/exports/auto_branch25_20261117_01/selection.json --translations experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/auto_branch25_20261117_01/instructions_zh.json --output outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/exports/auto_branch25_20261117_01/auto_branch25.html`。

离线HTML：25294181字节，SHA256 `916abf308225ff708a1e6c7f5eec8097d7f104a184fce79fba1adec53268a622`。在线入口：724846字节，SHA256 `7cba903334b3e3a58dceadeec293488cfe686628c211b46e7da353182f0e1ab3`。复用模板 `core/oracle_distance_replay.html`，适配后SHA256 `695b8d6c0219f0e5b256abd9a31f13babaeaf73eadec93af9be9cc7339147aa6`；前后源码分别保存于输出`source_before/`和`source/`。Git `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，包含未提交修改，实际来源见build和artifact哈希清单。

验证：本地Chromium通过25条双语指令/帧对应、27次纠错前后跳转、地图/RGB双进度条、播放、缩放、图层、筛选、25行CSV及手机布局，零页面脚本错误、零外部请求。数据审计确认11场景坐标变换、25张静态地图和原生评分一致，全部回放坐标均在相应底图范围内。原版轨迹未提供，界面未伪造原版数据。

发布使用 `docs/VISUALIZATION_PUBLISHING.md` 标准流程：拆分内嵌媒体，上传入口及2025个资源（含地图ZIP、字体许可ZIP），远端全部SHA256通过，公网入口快速检查通过；地图ZIP另做HEAD检查HTTP200、大小匹配。未宣称在线浏览器测试。发布证据：`outputs/visualization_publishing/publish_20261117_021231_186498/publication.json`；完成时间：2026-11-17T02:13:43.668942+00:00。
