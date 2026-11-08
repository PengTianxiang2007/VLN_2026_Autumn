# Qwen3.5-4B GPU0 常驻服务准备

2026-11-08 UTC；状态：部署准备完成，尚未启动。用户明确要求释放GPU0原模型并挂起自己的Qwen4B，常驻待用授权适用于本服务。

模型：复用本项目此前验证的Qwen3.5-4B BF16、Resource_Peng权重与.runtime/crossing_vllm27环境。GPU0、显存预算0.50、8192上下文、最多3图、单并发、seed20261108，动态localhost端口。使用既有启动/资源准入/清理实现，常驻保留；启动后/models及一次图文响应检查通过才标ready，不运行实验或仿真。

阻塞：GPU0目前他人ljh Qwen3-4B占41936MiB、huangyinuo SAM3占4686MiB。用户要求释放前者，但自动审批以缺少所有者或管理员授权、存在公共服务器服务中断风险拒绝SIGTERM操作。命令未执行，没有停止任何进程。不得通过引擎PID、进程组或其他路径绕过拒绝。需要服务所有者/管理员授权确认，或对方自行释放。当前其他GPU忙，不抢占。

已完成：检查本地权重config和解释器存在、脚本AST通过；source/保存源码，registration.json记录实际Git/哈希。部署配置已准备，可在GPU0资源满足准入后使用以下命令；本次没有启动等待进程。

启动：`python3 -B scripts/serve_qwen4b_standby.py --config experiments/agent_route_choice/services/qwen4b_gpu0_20261108_01/model.json --output outputs/model_services/qwen4b_gpu0_20261108_01 --gpu 0 --allow-shared-gpu`。

进程/产物：启动后位于outputs/model_services/qwen4b_gpu0_20261108_01/service.json；目前无API地址或PID，不冒称部署成功。正常停止或异常只清理自己创建的服务；不停止SAM3或其他项目。

授权更新：用户明确确认具备管理员或所有者授权后，自动审批允许仅停止已核验的API PID2294080；SIGTERM已发送，随后验证退出与GPU释放，再启动本项目Qwen3.5-4B。SAM3不变。

2026-11-08：用户确认管理员/所有者授权后，GPU0原Qwen3-4B API2294080及引擎2294951已正常退出，释放约41GiB，SAM3保留。本项目Qwen3.5-4B常驻主管3935702已启动，后台自动就绪检查；实际状态outputs/model_services/qwen4b_gpu0_20261108_01/service.json。用户明确要求挂起待用，不因空闲清理。
