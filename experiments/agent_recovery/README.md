# 外部 Agent 独立 R2R 纠错

**当前最优 prompt：v007（用户于2026-11-08指定）。** [英文](r2r_v007/prompt_en.txt) · [中文](r2r_v007/prompt_zh.txt) · [七例运行结果](r2r_v007/run_20261108_01/README.md) · [版本索引](current_best.json)。此标记针对指令生成审阅，未验证实际恢复导航；后续以此版为当前参考，不自动重跑。

[首版七例部署](r2r_v001/run_20261107_01/README.md)：复用选路，清空StreamVLN记忆，局部任务。

2026-11-07：用户明确停止七例v001部署队列，原因是指令过长并延伸至房间/后续路线；向已核验主管1855535发送SIGTERM。旧七条结果保留且不执行。新最小局部纠正prompt见 experiments/agent_recovery/r2r_v002/，仅方向输入，未调用模型或导航，不自动重启。

2026-11-07：局部纠正prompt v003已保存于 experiments/agent_recovery/r2r_v003/，限制关键分支纠正的移动范围，允许必要的靠近＋转向＋少量前进；取代v002机械方向映射，仅文本修改，无模型或导航运行，v001保持取消。

2026-11-07：用户授权v003七例局部纠正prompt生成，准备后台运行；记录 experiments/agent_recovery/r2r_v003/run_20261107_01/README.md。Qwen27B、原选路＋C帧画面，7次请求，无导航/仿真。

2026-11-07：v004局部导航prompt已保存于 experiments/agent_recovery/r2r_v004/，仅当前画面＋已选方向＋局部入口描述，删除原任务路线字段、实验背景与固定动作示例。仅供审阅，无模型/仿真调用；旧运行器未接入新版。

2026-11-07：v005七例新prompt生成已准备后台资源等待；见 experiments/agent_recovery/r2r_v005/run_20261107_01/README.md。使用C画面＋原选择方向＋分支视觉landmark，不传任务或旧route_description；当前无可准入GPU，等待24小时以内，未运行模型/导航。

2026-11-07：按用户要求准备v005 Qwen3-4B现有服务文字版七例；接口HTTP401，自动审批拒绝读取他人凭据，推理0/7。见 experiments/agent_recovery/r2r_v005/run_20261107_02_qwen4b_text/README.md。原27B资源等待队列保留。

2026-11-07：用户切换DeepSeek多模态，v005/run_20261107_03_deepseek准备七进程并行，复用原图文输入。原Qwen27B资源等待队列已停止；Qwen4B未调用。密钥仅内存传递，无导航或仿真。

2026-11-07：v006 DeepSeek七例多模态新prompt对比已准备，除prompt外请求逐项一致；见 experiments/agent_recovery/r2r_v006/run_20261107_01/README.md。七进程各一次，无导航/仿真。

2026-11-08：v007最新简短prompt七例DeepSeek图文并行准备完成，仅更换prompt；见 experiments/agent_recovery/r2r_v007/run_20261108_01/README.md。无导航/仿真，v006保留。

2026-11-08：v007全量34点/33轨迹重新生成已准备，34独立进程，全部新调用（含旧七例），DeepSeek多模态；见 experiments/agent_recovery/r2r_v007/run_20261108_02_all34/README.md。上游11/31格式问题保留，不重新选路；未启动导航/仿真。

2026-11-08：全量run_20261108_02_all34已完成34/34，实际请求重建/原答核验通过，34请求区间并行、worker全部退出。原七例重跑7/7一致；15方向表述与34移动终点待复核，无导航结果。
