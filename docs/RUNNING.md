# 推理与验证

从 `/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn` 执行命令。
模型均使用既有权重和原生推理策略；入口没有 TTA、PRM 或在线更新参数。

先运行 `nvidia-smi` 查看分配与实时占用。下面 GPU 0 仅是示例。
统一入口默认拒绝已有计算进程的 GPU；只有协调后允许共享时才加 --allow-shared-gpu。

## R2R-CE 与 RxR-CE

```bash
python3 scripts/evaluate.py --backbone streamvln --benchmark r2r --gpu 0 --episodes 1
python3 scripts/evaluate.py --backbone streamvln --benchmark rxr --gpu 0 --episodes 1
python3 scripts/evaluate.py --backbone janusvln --benchmark r2r --gpu 0 --episodes 1
python3 scripts/evaluate.py --backbone janusvln --benchmark rxr --gpu 0 --episodes 1
```

每条命令完整运行一条任务，保留原最大步数、传感器、提示词、历史、精度和动作队列。
成功退出与单条导航 success=1 是不同概念；验证不要求这一条导航一定成功。
去掉 --episodes 或指定 0 才是完整 val_unseen，不要在仅验证迁移时启动全集。

--dry-run 仅打印命令，不加载模型；--preflight-only 检查环境位置、数据链接与 GPU 条件。
--output 可指定新的空目录，默认结果在 outputs/<backbone>/<benchmark>/<UTC时间>/。
目录保存 launch.json、run.log、result.json、summary.json 和 validation.json。
出错时读取 run.log，不会自动重试或覆盖旧结果。

## VLNVerse

```bash
python3 scripts/evaluate.py --backbone streamvln --benchmark vlnverse --gpu 0 --episodes 1 --preflight-only
python3 scripts/evaluate.py --backbone streamvln --benchmark vlnverse --gpu 0 --episodes 1
python3 scripts/evaluate.py --backbone janusvln --benchmark vlnverse --gpu 0 --episodes 1
```

默认 H1 physical 模式，25,000 physics ticks、500 warm-up ticks、640×480 RGB。
模型动作不额外截断，采用官方终止与评分规则。--mode flash 使用 500 ticks 的 flash
协议；两种模式的成绩分别记录，不能合并。可加 --sim-gpu 指定另一张已协调的 GPU。
JanusVLN 同卡要求 45,000 MiB 空闲显存，分卡要求模型 39,000 MiB、仿真 12,000 MiB；
StreamVLN 对应为 32,000 MiB 或模型 25,000 MiB、仿真 12,000 MiB。

结果在 outputs/vlnverse/<backbone>/results/<run_id>/，包含 run.json、分段日志、
progress.json、result.json、storage 中的 LMDB。子集任务清单也保存在该次输出内，
不会向共享数据目录写入新的验证数据。终端打印 RUN_ID；可加 --resume RUN_ID 续跑。
runner 只清理自己启动的子进程，完整恢复仍须检查原输出状态。

## CPU 检查

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_environment.py --backbone streamvln --output outputs/checks/streamvln.json
python3 scripts/check_environment.py --backbone janusvln --output outputs/checks/janusvln.json
```

CPU 检查覆盖六路入口、真实源码导入位置、数据加载、场景/navmesh、权重分片与 metadata，
不加载完整权重或运行仿真。GPU 验证覆盖范围以 docs/VALIDATION.md 为准。
