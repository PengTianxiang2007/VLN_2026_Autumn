# 七例独立 R2R 纠错：指令生成与部署检查

状态：准备后台启动。2026-11-07；用户要求安排进程，启动后不持续跟踪。

目的：复用昨晚已选分支，用已确认的简短 prompt 生成七条独立指令。样本17/18/19/20/28/29/34，原C不变，选择原答见samples.json。

协议：Qwen3.8-27B-FP8、本地既有环境、temperature0、seed20261107、关闭思考，每例一次纯文本请求。只改写方向与描述，不重新选路。GPU0三次资源准入，共享他人4.2GiB服务，不停止他人。Qwen完成释放后，重新准入并加载StreamVLN和Isaac，检查reset接口及0232场景/H1资产加载。此阶段不执行七例物理恢复、不计算成功率。结束或异常清理自己的子进程。

启动命令：`python3 -B scripts/deploy_r2r_recovery.py`。

产物：outputs/agent_recovery/r2r_v001/run_20261107_01；status.json为实际状态，instructions.json及qwen/保留请求和原答；source/、registration.json、workspace.patch保存当前Git与源码。既有未提交修改不覆盖。仅AST检查通过，GPU结果由后台落盘。

下一步：依据部署结果接入七例标定姿态、清空记忆后的独立导航；原任务最终成功与局部执行成功分开。尚无局部终点标注或恢复成绩。


后台部署结果：{"phase": "failed", "pid": 1855535, "started_at": "2026-11-07T09:24:00.232022+00:00", "gpu": 0, "qwen_pid": 1855958, "base_url": "http://127.0.0.1:43351/v1", "updated_at": "2026-11-07T09:48:57.696716+00:00", "sample": "sample_34", "instructions": 7, "streamvln_pid": 1866191, "error": "KeyboardInterrupt: Termination requested", "finished_at": "2026-11-07T09:48:57.696700+00:00", "gpu_released": true}。仅指令生成和环境加载检查；七例物理恢复尚未执行。

2026-11-07：用户明确停止七例v001部署队列，原因是指令过长并延伸至房间/后续路线；向已核验主管1855535发送SIGTERM。旧七条结果保留且不执行。新最小局部纠正prompt见 experiments/agent_recovery/r2r_v002/，仅方向输入，未调用模型或导航，不自动重启。

停止核验：本轮GPU进程已全部退出，GPU0仅剩他人4234MiB服务，空闲44277MiB；status.json明确标为cancelled。未执行仿真恢复。
