# 智谱low十条续跑：60秒网络读取超时

继承run_03相同low设置、10个并发进程和82条成功回答，实际API payload不变。定位证据：成功请求中位12秒、最大25秒；10次左右请求卡在600秒网络读超时。仅将读取超时改为60秒以提前退避重试，最多8次，失败不终止其他轨迹。原始结果保留。prompt、图像历史、存档和匹配规则不变。总588次观测。

密钥经stdin只存进程内存；终止清理已验证。代码/注册/协议已冻结。状态status.json；完成后自动评分及默认模板HTML，路径exports/final/visualization/crossing_review_offline.html。

命令：benchmarks/vlnverse/.venv/bin/python -B scripts/run_crossing_remote.py outputs/crossing_checkpoint/v004/run_20261105_04


## 最终结果（2026-11-05）

run_20261105_04 已完成，10/10条、588/588个逐步判定。GLM-5.3-Flash，统一low思考强度，初始10进程；高强度失败尝试不混入成绩。1m口径：TP8/FP11/FN12，P42.11%、R40.00%、F1 41.03%，包含2次重复预测惩罚。该10条来自已使用的开发/验证样本，不能当作全新盲测，也不能直接与不同三条或六条的总分比较。

588条内部因果请求与实际远端请求hash复核全部通过，HTML图像池往返校验及源码/成绩审计通过。主管和全部API worker已退出；密钥只经stdin进入内存，没有落盘，产物格式扫描无凭据匹配。该清理不表示删除聊天内容或撤销平台密钥。

HTML：outputs/crossing_checkpoint/v004/run_20261105_04/exports/final/visualization/crossing_review_offline.html（27,177,542字节，约25.9 MiB）。摘要final_summary.json，详细审计remote_request_audit.json，清理证据credential_cleanup_check.json。没有启动额外推理或下一轮。
