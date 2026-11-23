# GPU 3 Qwen27B：53 条离线轨迹的节点去重与偏航识别

2026-11-18 [Qwen 全部 53 条偏航结果已同步至原网页](exports/deviation53_web_20261118_01/README.md)，C30–C53 新增 17 条红色区间，全组 36 条。

2026-11-18 [Qwen 去重回退点的分叉覆盖](analysis/branch_coverage_01/README.md)。44 次明确分叉中，22 次的标注决策区间内有保留节点，16 次原始候选未命中，6 次在去重中失去命中。

[固定终止节点回放](exports/terminal53_web_20261118_01/README.md)已逐条核对。376 个保留候选和 53 个终止节点合计 429 个有效节点，网页可直接跳到各条真实终止前视。

[完整 53 条去重回放与离线版](exports/all53_web_20261118_01/README.md)包含 19 个场景的 494 个候选、376 个保留节点。338 次比较中有 1 次证据引用校验失败，页面单列模型原答和实际保留决定。

[前 31 条去重回放](http://134.175.18.101/vln/qwen27b_route31_dedup_v001_web_20261118_01/index.html)已发布，270 个候选保留 204 个。[快照与导出记录](exports/first31_web_20261118_01/README.md)

2026-11-18 用户批准释放之前的本项目仿真与 StreamVLN，部署本地 Qwen27B 并执行本批离线评审。上游为[53 条轨迹的 494 个候选](../../../crossing_checkpoint/online_sampling_v001/run_20261118_01/README.md)，VLNVerse seed 2。前视图来自同批离线数据，独立输出 `outputs/deviation_progress/v003/run_20261118_01_qwen27b/`。[当前阶段和已完成轨迹数](../../../../outputs/deviation_progress/v003/run_20261118_01_qwen27b/status.json)

方法沿用固定分支的节点去重 v001 和偏航/累计语义进度 v003，语义模型统一改用 GPU 3 的 Qwen27B FP8。先对全部候选做相邻节点去重，再对各轨迹最终保留的节点重新编号，追加真实终止观测，按进度锚点评审至首次偏航或轨迹结束。候选、原始前视、模型原答、技术失败及两阶段结果分开记录。评分依据不含地图、参考路线或离线归因标签。仅执行语义识别。

使用已有 `.runtime/crossing_vllm27`，仓库提交 `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 及工作区现有 27B 服务入口；模型参数见 [service_config.json](service_config.json)。部署主管 `scripts/serve_qwen27b_standby.py --gpu 3 --config experiments/deviation_progress/v003/run_20261118_01_qwen27b/service_config.json --output outputs/model_services/qwen27b_gpu3_route53_20261118_01`。使用回环接口及动态端口。

07:11 UTC 已核实 GPU 2 旧仿真 3187906 和 GPU 3 旧模型 3194667 退出。[释放前后占用记录](../../../../outputs/deviation_progress/v003/run_20261118_01_qwen27b/old_gpu_release.json)

首次输入检查将最后一帧错误地按动作前视文件名校验，在发起模型请求前退出。失败日志及源码保存在输出目录的 `attempt_01_input_check/`。修正后逐条核验了 4,837 张动作前视与 53 张终止前视的索引、候选位置和终止节点衔接；338 对满足模型比较条件。07:23 UTC 以 `.runtime/crossing_vllm27/bin/python -u -B scripts/run_route53_qwen_review.py` 启动独立后台进程，PID 3641266。该环境支持按进程身份释放本次 Qwen 服务。[数据与代码哈希](../../../../outputs/deviation_progress/v003/run_20261118_01_qwen27b/manifest.json)

07:29 UTC，GPU 3 单图推理自检通过。第一条轨迹的 S01、S02 通过正式接口返回 HTTP 200，结果通过冻结的校验器，判定为 different，两点均保留。07:29:53 UTC 交后台时完成 1/338 对模型比较，处于首条轨迹，偏航阶段等待全部去重完成。用户要求正常启动后交后台。[首对正式结果](../../../../outputs/deviation_progress/v003/run_20261118_01_qwen27b/dedup/cases/C01/requests/S02.response.json)
