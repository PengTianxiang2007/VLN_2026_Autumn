# v005：第四稿宽松提示词，智谱十条并发离线评测

更新时间：2026-11-05T11:10:10.335510+00:00。状态：运行中，首批有效回答验证通过，后台继续。

目的：针对Qwen两处实际遗漏，小幅放宽不同区域与局部侧向开口的证据门槛。只改提示词；不加入额外复杂规则。中英文及diff见experiments/crossing_checkpoint/v005/。

方法：GLM-5.3-Flash官方API，reasoning_effort=max（按用户明确选择），10个episode进程并发，每条内部每步顺序调用；原10条共588观测，全新调用，不复用第三稿输出。导航seed2；远端不发送本地seed。8图/32动作历史、schema、2/3存档确认、位置判定及1m匹配均不变。样本来自既有开发/验证集合，不是独立盲测。上次完成的智谱第三稿为low，因此两次成绩不能作为仅prompt变化的因果对照。

实际Git：0a805dfcf4457f80300822abb4eff7cabba43aae；工作区有未提交改动。versions/冻结core与replay，orchestration_source/保存主管及导出审计源码，source_hashes.json、workspace_diff.patch、workspace_status.txt记录来源。

命令：`benchmarks/vlnverse/.venv/bin/python -B scripts/run_crossing_remote.py outputs/crossing_checkpoint/v005/run_20261105_01`，密钥由关闭终端回显的stdin输入，仅在进程内存中。使用云API，不启动本地GPU模型或仿真。

退出机制：固定一版10条，无自动下一轮；总计最多8小时；流式读取超时60秒，每次最多8个网络尝试并退避，截断时输出预算32768逐次增至131072；外层最多一次格式重试。单条失败不终止其他条，全部退出后整批标记失败或完成；保留成功结果，不伪造缺失分数。子进程退出清理自己的内存凭据，不写密钥文件。

完成后自动评分、远端payload审计、诊断、默认双进度条模板HTML导出。产物：outputs/crossing_checkpoint/v005/run_20261105_01；状态status.json；HTML exports/final/visualization/crossing_review_offline.html。确认有效回答及并行worker正常后停止人工持续跟踪。

下一步：启动此批并验证首批有效回答；不启动额外旧版重跑。

启动记录：{"pid": 1373822, "started_at": "2026-11-05T11:11:40.250158+00:00", "output": "outputs/crossing_checkpoint/v005/run_20261105_01", "key_on_disk": false}；10个独立episode worker均已进入回放。

启动验证通过：10个独立worker存活，已验证6个有效回答及实际远端max请求哈希；提示词与第4稿一致。个别网络读取超时由既有退避自动重试。后台继续，停止人工持续跟踪；完成后自动评分、完整审计、模板导出和进程清理。

最终状态：{"tag": "glm53flash_draft04_max_10", "output": "/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/v005/run_20261105_01", "phase": "failed", "error": "RuntimeError: Worker failure", "finished_at": "2026-11-05T13:25:22.234308+00:00", "credential_on_disk": false, "workers_exited": true}

智谱第四稿max：178/588次，0/10条；超时和HTTP429耗尽重试，worker已退出。未完成片段预览已导出，178条因果请求重建校验通过，不计算最终分数，不启动推理。HTML：outputs/crossing_checkpoint/v005/run_20261105_01/exports/partial_20261105_01/glm_draft04_max_partial178.html。
