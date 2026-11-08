# Qwen27B GPU0待用服务：11图容量

为用户授权的七帧+四帧第二轮将max_images从8改为11，其余模型参数保持。核验旧服务主管命令行/工作目录后正常停止，再经共享GPU准入启动新服务。旧记录不覆盖。

状态文件：outputs/model_services/qwen27b_gpu0_20261106_02/service.json；地址 http://127.0.0.1:58549/v1；按用户明确要求保留待用。旧01服务已停止，其地址失效。新服务主管395599，API396074，实际存活以状态和进程核验为准。

启动命令：`.runtime/crossing_vllm27/bin/python -B scripts/serve_qwen27b_standby.py --output outputs/model_services/qwen27b_gpu0_20261106_02 --config experiments/agent_route_choice/human_v002/run_20261106_06/service_config.json --gpu 0 --allow-shared-gpu`
