# Qwen4B 三帧五级评分：完整人工标注集

目的：在已有61条人工标注轨迹（失败34、成功27）上重新独立判断局部多分支位置。
版本：lite_full_v001/run_20261108_01；seed 20261107。5378次评分；不重跑导航/仿真。
模型：已有GPU0 Qwen3.5-4B BF16服务 qwen35-4b-standby，服务seed20261108；每请求seed沿用旧版派生方式。
协议：与lite_v001原prompt逐字相同，当前及过去两帧，初始不足三帧时只用已有帧；末尾复用帧不推理；1–5分、中文理由；temperature0、thinking关闭、max_tokens256、结构化JSON。
所有61条均重算，不复用旧评分。并行4个请求worker，复用的vLLM服务max_num_seqs=1（与旧版服务4不同）；结果是否完全一致不作保证。没有原指令、人工标签、地图、参考路径或历史回答进入判断输入。
可视化：路径按原始分数染色，无C/P点、文字、当前位置或原地转向圆点；仅失败轨迹可开关参考路线；当前图及三帧历史图显示各自帧的评分，明确不把当前分数套用历史图。参考路线默认关闭。
中英切换：原任务使用数据集已有中英文本，评分理由及提示词单独翻译，仅用于显示，保留原始请求/回答。无人标注帧不算负类，不报告PR/F1。
流程：等待用户已保留模型服务就绪→4 worker评分→翻译→审计导出→本地浏览器验证→标准发布→记录delivery.json。失败立即记录，不冒充完整结果。模型待命服务按用户既有保留授权继续运行；本批worker退出清理。
启动：`python3 -B scripts/run_crossing_lite_full.py --output outputs/crossing_checkpoint/lite_full_v001/run_20261108_01`
准备：同一命令追加`--prepare experiments/crossing_checkpoint/lite_full_v001/run_20261108_01`。
产物：outputs/crossing_checkpoint/lite_full_v001/run_20261108_01；status.json记录状态、worker_i.status.json记录进度、delivery.json记录验证后的网址。
实际Git/未提交差异及源码快照：运行目录manifest.json、tracked_worktree.diff、workspace_status.txt、source/。
部署后不持续跟踪；后台自动收尾，未完成前不报告评分成绩或已发布网址。

2026-11-08T07:42:49.132117+00:00 full61后台流程状态：{"phase": "failed", "pid": 3955960, "started_at": "2026-11-08T06:07:30.349439+00:00", "expected_calls": 5378, "updated_at": "2026-11-08T07:42:48.945430+00:00", "service": "http://127.0.0.1:58317/v1", "service_reused": true, "server_max_num_seqs": 1, "error": "CalledProcessError: Command '['/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/backbone/streamvln/.venv/bin/python', '-B', '/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/scripts/crossing_lite_full_finish.py', '/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/lite_full_v001/run_20261108_01']' died with <Signals.SIGTERM: 15>.", "finished_at": "2026-11-08T07:42:48.945408+00:00"}

用户要求改用DeepSeek：剩余展示翻译切换deepseek-flash，32个并行进程，保留已完成译文。入口scripts/crossing_lite_full_finish_deepseek.py；评分原始结果不变，后续继续导出、验证和发布。API凭据仅通过匿名stdin管道传入，不落盘。

DeepSeek批量翻译reason_02710返回校验失败，首次流程停止；追加失败批次拆分单条重试，复用已完成缓存，后台重启收尾，日志deepseek_finish_retry01.log。

机器人位置点修正版已发布：http://134.175.18.101/vln/crossing_lite_full61_run_20261108_01_web_02/crossing_lite_review.html 。48组双时间轴/参考路径开关/完整轨迹开关位置及可见像素检查通过，远端资源SHA256和公网HTTP验证通过。发布记录：outputs/visualization_publishing/publish_20261108_081302_517506/publication.json。

2026-11-08：用户将当前三帧五级评分版本标记为“最优版本1”（best_v001），冻结登记 experiments/crossing_checkpoint/best_v001/；当前指针 experiments/crossing_checkpoint/current_best.json，网页为web_02机器人位置点修正版。
