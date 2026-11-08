# v006 DeepSeek七例多模态并行对比

2026-11-07 UTC；状态：准备启动。用户要求按刚确认的prompt并行调用一次，查看本版结果。

目的：避免把眼前所选分支解释为先沿未选路线前进再找远处侧门；入口描述仅辅助，不能引入额外绕行。中文为已确认全文，英文为逐段对应翻译。

协议：精确复用v005/run_20261107_03_deepseek七例输入（17/18/19/20/28/29/34）、C帧原图、已选方向及landmark原文。仅用户prompt变化；deepseek-flash、官方API、thinking disabled、temperature0、max_tokens512、七进程同时放行，每例一次、无重试，seed未发送。原入口识别错误不人工修正，以保留本轮对比条件。无导航/仿真。

版本：source/、manifest.json、workspace.patch和workspace_status.txt保存Git与源码。公共worker只修正完成通知的版本名，推理逻辑不变；七例请求逐项核验除prompt文本外完全相同，图像及配置哈希一致，AST通过。

启动：`python3 -B scripts/run_deepseek_correction_commands.py --prepared experiments/agent_recovery/r2r_v006/run_20261107_01 --output outputs/agent_recovery/r2r_v006/run_20261107_01`。沿用用户本会话提供的DeepSeek密钥，经无回显stdin和匿名管道传递，不写文件/环境/命令行。

产物：outputs/agent_recovery/r2r_v006/run_20261107_01，含status.json、workers.json、原始请求/回答、instructions.json；自动收尾清理worker、扫描密钥未落盘。只生成命令，无HTML，无本地GPU，不恢复已取消队列。模型语义与实际执行效果分别判断。


DeepSeek r2r_v006七例图文并行收尾：{"phase": "complete", "supervisor_pid": 2570826, "started_at": "2026-11-07T16:41:56.622603+00:00", "model": "deepseek-flash", "concurrency": 7, "expected_calls": 7, "completed": 7, "credential_on_disk": false, "navigation_executed": false, "simulation_started": false, "updated_at": "2026-11-07T16:42:04.566564+00:00", "worker_pids": [2570830, 2570831, 2570832, 2570833, 2570834, 2570835, 2570837], "semantic_review": "pending", "workers_exited": true, "finished_at": "2026-11-07T16:42:04.566548+00:00"}；产物 outputs/agent_recovery/r2r_v006/run_20261107_01。无导航或仿真。
