# v004：智谱 GLM-5.3-Flash 十条并发离线评测

准备启动。用户授权10条、10个并发进程；每条内部严格按动作顺序逐步调用。沿用第3稿prompt、8图/32动作历史、2/3确认与1m时间窗匹配。样本为既有dev5_val15输入顺序前十条，计划588次；不是全新盲测。上一批本地六条继续原授权任务，不占用新GPU。

模型官方接口支持多图，但只能启用思考（https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash）。适配器将既有内部请求转换为官方JSON输出请求，移除本地seed/chat_template_kwargs/json_schema，改thinking.enabled及json_object；实际远端payload哈希随reply保存，JSON继续本地严格校验。内部请求哈希供因果回放审计，不能冒充远端原始请求哈希。temperature=0、max_tokens=8192（含思考）保留，原导航seed2。服务端采样不承诺本地seed复现。

产物：`/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/v004/run_20261105_01`。源码冻结于versions/；Git及工作区差异已登记。失败即停止本批次，最多8小时，每请求600秒、重试最多一次。密钥仅从stdin输入内存并在进程退出时释放，不写入仓库、输出或日志；无法删除用户聊天中的密钥或替用户撤销平台密钥。全部完成后自动评分、诊断、模板HTML导出到exports/final/visualization/crossing_review_offline.html。最终状态见status.json。

最终状态：{"phase": "failed", "error": "RuntimeError: An episode worker failed; aborting fixed batch", "finished_at": "2026-11-05T09:19:50.597956+00:00", "credential_on_disk": false, "workers_exited": true}


2026-11-05状态核验：智谱v004批次于09:19:50 UTC失败退出，累计26/588次有效回答、0/10条完成。一条请求首次输出达到长度上限，重试时遇到连接重置，随后触发整批停止。全部worker和主管已退出，密钥没有落盘，未生成最终分数或HTML。病例旧running状态只代表中断前状态；以批次status.json为准。未自动重启。

智谱十条已授权重试并跑完：run_20261105_02，复用26条有效回答，流式请求/输出预算/退避修复已登记于experiments/crossing_checkpoint/v004/run_20261105_02/README.md。

最终状态：{"phase": "failed", "error": "RuntimeError: Termination requested", "finished_at": "2026-11-05T09:49:24.434617+00:00", "credential_on_disk": false, "workers_exited": true}

智谱run_02默认max持续长思考，已结束自己的进程；切换run_03统一low重新评测10条、10并发、588次，不混用旧结果。详细记录 experiments/crossing_checkpoint/v004/run_20261105_03/README.md。

最终状态：{"phase": "failed", "error": "RuntimeError: Termination requested", "finished_at": "2026-11-05T10:06:33.405403+00:00", "credential_on_disk": false, "workers_exited": true}

智谱low续跑run_04：保留82次成功回答，将实测600秒空等的网络读超时缩至60秒；方法不变。见experiments/crossing_checkpoint/v004/run_20261105_04/README.md。

最终状态：{"phase": "complete", "error": null, "finished_at": "2026-11-05T10:40:48.502818+00:00", "credential_on_disk": false, "workers_exited": true}


## 最终结果（2026-11-05）

run_20261105_04 已完成，10/10条、588/588个逐步判定。GLM-5.3-Flash，统一low思考强度，初始10进程；高强度失败尝试不混入成绩。1m口径：TP8/FP11/FN12，P42.11%、R40.00%、F1 41.03%，包含2次重复预测惩罚。该10条来自已使用的开发/验证样本，不能当作全新盲测，也不能直接与不同三条或六条的总分比较。

588条内部因果请求与实际远端请求hash复核全部通过，HTML图像池往返校验及源码/成绩审计通过。主管和全部API worker已退出；密钥只经stdin进入内存，没有落盘，产物格式扫描无凭据匹配。该清理不表示删除聊天内容或撤销平台密钥。

HTML：outputs/crossing_checkpoint/v004/run_20261105_04/exports/final/visualization/crossing_review_offline.html（27,177,542字节，约25.9 MiB）。摘要final_summary.json，详细审计remote_request_audit.json，清理证据credential_cleanup_check.json。没有启动额外推理或下一轮。
