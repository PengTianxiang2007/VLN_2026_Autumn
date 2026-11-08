# Qwen27B GPU0 常驻待用服务

2026-11-06 用户明确要求“把Qwen27B挂起来，随时可能用，用GPU0”。状态：已就绪，保持待用。属于用户明确保留的在途待用服务，不因空闲自动关闭。停止或异常时清理本主管拥有的服务进程，不影响他人。

目的：提供本地OpenAI兼容图文接口，供后续交互使用；不执行34条实验或导航。模型沿用本地 Qwen3.8-27B-FP8、现有 .runtime/crossing_vllm27 环境，GPU0共享、显存预算0.75、上下文32768、并发1、最多8图。三次资源准入后启动，只绑定127.0.0.1动态空闲端口，离线加载。

本次唯一启动检查为一张既有RGB的简短物体描述，不用于语义评分。无新实验seed；服务seed沿用20261106。

启动：
```sh
.runtime/crossing_vllm27/bin/python -B scripts/serve_qwen27b_standby.py --config experiments/agent_route_choice/services/qwen27b_gpu0_20261106_01/model.json --output outputs/model_services/qwen27b_gpu0_20261106_01 --gpu 0 --allow-shared-gpu
```

命令由独立会话后台启动，启动日志见 outputs/model_services/qwen27b_gpu0_20261106_01.supervisor.log。实际PID、端口、状态见同名目录 service.json。模型原件和其他实验服务不改写。关闭前必须核验该主管PID和进程身份，再向它发送SIGTERM，使其完成自身清理。

版本：本次启动器及复用源码的SHA256见 registration.json，实际源码快照见 source/。历史模型实验的运行版本不由当前HEAD替代。下一步：就绪后保留，等待用户后续使用。


就绪时间：2026-11-06T16:09:23.977981+00:00。接口 `http://127.0.0.1:37007/v1`，model=`route-choice-qwen27b-standby`；主管PID197411，API服务PID198361。GET /v1/models 与单张图文请求均HTTP200，响应保存在 smoke.json；这是服务检查，不计入实验。
