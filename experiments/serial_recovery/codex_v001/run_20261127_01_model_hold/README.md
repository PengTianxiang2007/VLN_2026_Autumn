# StreamVLN 双 GPU 后台常驻模型

2026-11-27T04:33:37.848218+00:00。按用户要求仅提交 GPU0/1 模型服务启动，不跟踪加载、不启动导航或 JEV/Codex 评审；旧仿真保留。沿用 StreamVLN_R2R_v1_3、seed 2 和原服务入口，端口自动分配，加载完成由各 gpu*/ready.json 记录。

本次无导航任务，当前版与原版 SR、平均 SPL 均暂无，已评分 0 条。PID、命令、日志、源码快照见同名 outputs 的 launch.json、gpu*/agent.log 和 source/。用户已要求挂起保留模型，等待后续使用或停止指令。
