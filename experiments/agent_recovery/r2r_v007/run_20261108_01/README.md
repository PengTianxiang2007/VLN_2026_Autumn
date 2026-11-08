# v007 DeepSeek七例图文并行

2026-11-08 UTC；状态：已完成7/7，用户指定为当前最优prompt并保留。用户授权最新简短prompt并行调用七例各一次。

目的：只完成眼前岔路选择，能直接转向则直接转向，仅必要时接近岔路；不额外要求进入房间或沿支路继续走。中文为确认全文，英文为对应翻译。

输入/模型：精确复用v006七例17/18/19/20/28/29/34的C帧图片、选择方向与局部描述。除prompt文本外实际请求逐项一致。deepseek-flash多模态、thinking disabled、temperature0、max_tokens512、七独立进程同时放行、每例一次无重试；seed未发送。入口描述潜在错误不人工修正。无导航/仿真。

版本/检查：source/与manifest.json保存实际Git、worker和输入哈希；workspace.patch及workspace_status.txt保存差异。七例只更换prompt验证、图像哈希与AST通过。

启动：`python3 -B scripts/run_deepseek_correction_commands.py --prepared experiments/agent_recovery/r2r_v007/run_20261108_01 --output outputs/agent_recovery/r2r_v007/run_20261108_01`。密钥沿用用户本会话已提供凭据，通过无回显stdin/匿名管道传递，不写入文件、环境或命令行。

产物：outputs/agent_recovery/r2r_v007/run_20261108_01中的status.json、workers.json、cases/原始请求/响应、instructions.json；完成后自动清理worker并扫描凭据未落盘。语义有效性待复核，未运行导航，不生成HTML。v006保留不覆盖。


DeepSeek r2r_v007七例图文并行收尾：{"phase": "complete", "supervisor_pid": 3885224, "started_at": "2026-11-08T05:20:06.223152+00:00", "model": "deepseek-flash", "concurrency": 7, "expected_calls": 7, "completed": 7, "credential_on_disk": false, "navigation_executed": false, "simulation_started": false, "updated_at": "2026-11-08T05:20:12.214645+00:00", "worker_pids": [3885259, 3885260, 3885261, 3885262, 3885263, 3885264, 3885265], "semantic_review": "pending", "workers_exited": true, "finished_at": "2026-11-08T05:20:12.214630+00:00"}；产物 outputs/agent_recovery/r2r_v007/run_20261108_01。无导航或仿真。

2026-11-08 用户审阅决定：保留本版七例原始结果，并将v007标记为当前最优prompt；统一指针为 [current_best.json](../../current_best.json)。该标记是当前指令生成版本选择，不代表已验证导航恢复效果；第34条移动范围问题仍保留。此次仅登记，不修改prompt/输入/原答，不启动新模型或导航。
