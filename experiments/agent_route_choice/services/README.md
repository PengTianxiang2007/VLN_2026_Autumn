# 外部Agent本地模型待用服务

- [GPU3 Qwen27B 待用服务，2026-11-21](qwen27b_gpu3_20261121_01/README.md)。用户新授权启动；主管 993933、服务 994127 已确认存活，地址 `http://127.0.0.1:56923/v1`。仅确认进程启动，未探测就绪或调用模型，已交后台待用。

- [GPU 3 的 Qwen27B 常驻服务，2026-11-20](qwen27b_gpu3_20261120_01/README.md)。用户要求持续保留，后续任务复用本实例，释放须用户明确下令。

- [Qwen27B GPU0，2026-11-06，用户明确保留待用](qwen27b_gpu0_20261106_01/README.md)。实际存活状态以service.json和进程核验为准。

2026-11-08：用户要求GPU0挂起本项目Qwen3.5-4B；配置与启动器已准备，尚未启动。停止GPU0他人ljh服务的SIGTERM操作被自动审批拒绝（缺少所有者/管理员授权），未执行；待授权或对方释放。记录 experiments/agent_route_choice/services/qwen4b_gpu0_20261108_01/README.md。

2026-11-08：用户确认管理员/所有者授权后，GPU0原Qwen3-4B API2294080及引擎2294951已正常退出，释放约41GiB，SAM3保留。本项目Qwen3.5-4B常驻主管3935702已启动，后台自动就绪检查；实际状态outputs/model_services/qwen4b_gpu0_20261108_01/service.json。用户明确要求挂起待用，不因空闲清理。
