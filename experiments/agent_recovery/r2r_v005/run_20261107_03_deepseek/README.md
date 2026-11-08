# DeepSeek多模态七进程局部纠正指令

2026-11-07 UTC；状态：准备启动。用户提供DeepSeek凭据，明确要求多模态模型和并行进程。原27B资源等待主管2524971已核验身份并停止，避免重复运行。

模型：官方api.deepseek.com，deepseek-flash（官方文档当前对应DeepSeek-V4.1-Flash-1017，实际返回model字段另存），支持image_url。temperature0、thinking disabled、max_tokens512，7个独立进程并行，每例一次无自动重试；seed未发送（官方未列此参数）。先GET /models核验鉴权及模型名，再同时放行七例。

输入：v005最终确认prompt英文原文，七例17/18/19/20/28/29/34的原C画面＋已选方向＋第一轮选中分支landmark。完全复用run_01输入和哈希，不使用Qwen4B文字替代版，不含原任务/旧route_description。只生成指令，无导航/仿真，无本地GPU。

密钥：无回显终端输入，经匿名stdin管道进入后台主管，再由fork继承到七worker内存；不写配置、环境、命令行或原始请求，不使用其他项目凭据。关闭core dump，限制官方HTTPS端点并禁用重定向/环境代理；响应/错误在落盘前剔除意外回显密钥。结束扫描本运行目录并清理自己的worker，不触碰他人服务。

启动：`python3 -B scripts/run_deepseek_correction_commands.py --prepared experiments/agent_recovery/r2r_v005/run_20261107_03_deepseek --output outputs/agent_recovery/r2r_v005/run_20261107_03_deepseek`，提示后仅通过无回显输入提供密钥。

验证：七例实际请求构造、图片哈希、prompt精确一致、无凭据payload及AST通过。source/与manifest.json保存实际Git/源码/输入哈希，workspace.patch及workspace_status.txt保留差异；历史不覆盖。

产物：outputs/agent_recovery/r2r_v005/run_20261107_03_deepseek/status.json、workers.json、cases/完整请求/响应及审计、instructions.json。语义有效性待复核，不生成HTML。按照用户既有要求，启动核验后后台运行，不持续跟踪。


DeepSeek v005七例图文并行收尾：{"phase": "complete", "supervisor_pid": 2542551, "started_at": "2026-11-07T16:26:11.859144+00:00", "model": "deepseek-flash", "concurrency": 7, "expected_calls": 7, "completed": 7, "credential_on_disk": false, "navigation_executed": false, "simulation_started": false, "updated_at": "2026-11-07T16:26:19.457060+00:00", "worker_pids": [2542581, 2542582, 2542583, 2542584, 2542585, 2542586, 2542587], "semantic_review": "pending", "workers_exited": true, "finished_at": "2026-11-07T16:26:19.457044+00:00"}；产物 outputs/agent_recovery/r2r_v005/run_20261107_03_deepseek。无导航或仿真。
