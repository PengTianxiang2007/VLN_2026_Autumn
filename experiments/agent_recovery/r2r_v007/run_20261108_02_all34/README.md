# v007 全部34个标定点重新生成局部纠正指令

2026-11-08 UTC；状态：已完成34/34，全部worker已退出。用户要求“并行把这三十几个全部再重新跑一遍”。沿用当前最优v007，不重做分支选择，不执行导航或仿真。

范围：原human_v002/run_20261107_01的sample_01—34，34个标定点/33条轨迹；原七例也重新调用，不复用生成答案，不覆盖七例已接受结果。每例输入原C帧图片、已选方向和分支landmark原文；不传原任务、route_description或destination_hypothesis。方向包含back/front_left/front_right，原样保留，不人为简化。sample_11历史properties包装按既有规则读取；sample_31旧引用问题保留说明，不改原选择。

模型：deepseek-flash多模态，官方API；thinking disabled、temperature0、max_tokens512、seed未发送。34个独立进程同时放行，每例一次，无自动重试；失败保留，模型响应原文不改写。GET /models鉴权和模型可用检查通过后才启动推理。

版本：manifest.json记录真实Git与worker/输入/源数据哈希，source/保存源码，workspace.patch和workspace_status.txt记录差异。worker仅将固定七例的计数/完成通知推广到实际样本数，wire生成不变。全部34例图片哈希、编号/选择/入口对应、prompt原文一致验证通过；原七例实际请求与已接受批次完全相同。未重跑导航/模型验证测试。

启动：`python3 -B scripts/run_deepseek_correction_commands.py --prepared experiments/agent_recovery/r2r_v007/run_20261108_02_all34 --output outputs/agent_recovery/r2r_v007/run_20261108_02_all34`。沿用用户本会话提供的DeepSeek密钥，凭据经无回显终端和匿名管道进入内存，不落盘或进入命令行/环境；不使用他人服务，无本地GPU。

产物：outputs/agent_recovery/r2r_v007/run_20261108_02_all34 的status.json、workers.json、cases/原始请求/响应、instructions.json；完成后清理自身worker，检查凭据未落盘并更新索引。预计34次请求，语义质量待复核，不将生成完成率称为恢复成功率。未制作HTML。当前最优prompt标记保持v007，七例已接受结果保留。

遵循用户要求，启动核验后交由后台，不持续跟踪。


DeepSeek r2r_v00734例图文并行收尾：{"phase": "complete", "supervisor_pid": 3897400, "started_at": "2026-11-08T05:29:33.811152+00:00", "model": "deepseek-flash", "concurrency": 34, "expected_calls": 34, "completed": 34, "credential_on_disk": false, "navigation_executed": false, "simulation_started": false, "updated_at": "2026-11-08T05:29:41.709800+00:00", "worker_pids": [3897401, 3897402, 3897403, 3897404, 3897405, 3897406, 3897407, 3897408, 3897409, 3897410, 3897411, 3897412, 3897413, 3897414, 3897415, 3897416, 3897417, 3897418, 3897419, 3897420, 3897421, 3897422, 3897423, 3897424, 3897425, 3897426, 3897427, 3897428, 3897429, 3897430, 3897431, 3897432, 3897433, 3897434], "semantic_review": "pending", "workers_exited": true, "finished_at": "2026-11-08T05:29:41.709785+00:00"}；产物 outputs/agent_recovery/r2r_v007/run_20261108_02_all34。无导航或仿真。

结果核验：34/34响应完成且finish_reason=stop，34个实际请求与冻结输入重建一致，34个唯一响应ID，原指令未改写。worker请求区间最大并行数34，进程均退出；不含导航结果。详细审计见result_audit.json。

初步文字复核：原七例重新生成的结果7/7与此前完全一致。sample_15输出“Turn front-right toward the doorway on the left wall.”，同时出现右前方与左墙门口，需结合画面复核方向表述；sample_34仍缺少明确短程终点。原答保留，不将34/34完成率视为语义正确率。
