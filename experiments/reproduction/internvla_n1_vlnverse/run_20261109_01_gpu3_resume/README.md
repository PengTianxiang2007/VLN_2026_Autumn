# InternVLA-N1 fine Val Unseen：GPU3 续跑

更新时间：2026-11-09（UTC）
状态：运行中；分块重启修正后继续 `kujiale_0093`

## 目的与范围

继续既有 seed 0 正式复现，不改变 825 条 fine Val Unseen、33 个 scene、
官方 H1 flash 协议、模型权重、提示词、动作队列或评分。当前只允许物理 GPU3，
模型与仿真均使用该卡。

已完成的历史有效部分保留：

- `kujiale_0020`：25 条完成
- `kujiale_0031`：25 条完成
- 合计 50/825；
- `kujiale_0030` 历史运行在 23 条完整视频后停止写日志，15 分钟无进展后由
  worker 超时终止；该 scene 未记完成，必须整 scene 重跑并重新验证。

## 本次变化

- `INTERNVLA_N1_ALLOWED_GPUS=3`，禁止调度到其他 GPU；
- 历史阻塞 supervisor `3154663`先停止；
- GPU锁和临时目录移入项目输出目录；
- 保持 `checkpoint`, seed, dataset, smoke gate 和 worker 超时逻辑不变。

## 启动方式

```bash
INTERNVLA_N1_ALLOWED_GPUS=3 \
python3 scripts/reproduce_internvla_n1_vlnverse.py run
```

## 结果与限制

恢复后优先重跑 `kujiale_0030`。只有官方结果验证通过才写入
`completed/<scene>.json`。GPU3 若被其他用户占用，队列等待，不抢占、不停止他人进程。
Flash 结果与 StreamVLN physical 结果分开报告。

2026-11-09 中断修正：`kujiale_0093` 在一次运行中遇到 Isaac/PhysX 累积场景停顿，
仿真日志 15 分钟无更新后 worker 被终止。修正为模型服务保持加载，仿真在420秒无
日志更新时终止，并在同一 run 目录重启；已写入 LMDB 的 episode 会跳过，最多重启
5次。新的 GPU3 supervisor PID `2939300`，当前 active scene `kujiale_0093`。

截至修正前，8个完整 scene、195条已核验结果的局部 SR 为 **44.62%（87/195）**，
SPL 40.05%。这不是最终825条成绩，也不包含失败中断的局部 episode。

本次启动：

- tmux：`internvla_n1_gpu3_20261109`
- supervisor PID：`2192869`
- worker PID：`2193972`
- 模型服务 PID：`2193985`
- 当前 scene：`kujiale_0030`
- 模型和仿真 GPU：`3`
- 恢复前完成：`50/825`，来自 `kujiale_0020`、`kujiale_0031`

## 产物

- campaign：`outputs/reproduction/internvla_n1_fine825_seed0_20261102`
- 实时状态：campaign 的 `status.json`
- 新 worker 日志：campaign 的 `worker_logs/<scene>.log`
- 监督器日志：本次 tmux 会话与 `supervisor_gpu3_20261109.log`
- 启动记录：campaign 的 `gpu3_resume_launch_20261109.json`
- 重启修正记录：campaign 的 `gpu3_restart_fix_20261109.json`
