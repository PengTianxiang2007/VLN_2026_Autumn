# v005七例局部入口指令生成

2026-11-07 UTC；状态：准备后台资源等待。用户要求按最后确认的prompt跑一遍，沿用本地Qwen27B，不启动导航或仿真。

目的与输入：样本17/18/19/20/28/29/34，C分别66/15/117/6/34/39/0。v005中英文prompt均冻结；实际请求用英文对应翻译。每例一张原C画面＋昨晚选定方向＋第一阶段对应branch的landmark原文。入口描述由分支ID精确关联，不传第二阶段route_description、原任务全文、destination_hypothesis或未来图像。原视觉描述仍可能错误，未人工修改，需独立语义复核。相对v003同时改变prompt与文本输入来源，不将差异全部归因于prompt。

模型与协议：Qwen3.8-27B-FP8，既有.runtime/crossing_vllm27，temperature0，seed20261107，thinking=false，max_tokens512，单并发、每例一次，共7次，无自动重试。图像最大像素沿用307200。原答不裁剪、不人工修改。

资源：目前GPU0新增他人41936MiB模型（已通过cwd/父进程核验），其他卡忙；不调用或停止他人服务。后台每60秒检查全部GPU，保留原显存预算0.75及4GiB余量、负载<=10%、主存>=64GiB准入，再经原start_local三次检查与项目锁才启动。最多等待24小时；超时失败退出，不占GPU等待。加载/推理后或异常时仅清理自身进程，不长期空载占卡。

启动：`python3 -B scripts/run_entrance_correction_commands.py --prepared experiments/agent_recovery/r2r_v005/run_20261107_01 --output outputs/agent_recovery/r2r_v005/run_20261107_01 --gpu -1 --allow-shared-gpu --resource-wait-seconds 86400`。

版本与验证：manifest.json记录当前Git、实际源码哈希、输入哈希；source/保存源码，workspace.patch与workspace_status.txt记录未提交差异。7例图像哈希、精确prompt请求构造、来源字段一致、GPU准入边界检查及AST通过，无推理成绩。独立脚本不改变v003旧运行器。

产物：outputs/agent_recovery/r2r_v005/run_20261107_01，status.json、resource_wait.json、instructions.json、cases/原始请求/响应、server.log与cleanup.json。完成/失败自动追加结果，语义正确性待复核，不生成HTML。

按用户要求仅启动检查后交给后台，不持续跟踪。不会恢复已取消导航队列。

已启动后台主管PID 2524971；一次启动核验后停止持续跟踪，实际状态见输出status.json。


2026-11-07 v005七例局部纠正命令后台收尾：状态`cancelled`，完成0/7，GPU释放True；原答语义待复核，无导航或仿真。产物 `outputs/agent_recovery/r2r_v005/run_20261107_01`。
