# R2R-CE 原版 StreamVLN，400 条逐帧 RGB

2026-11-23 09:18:59 UTC 按用户要求暂停并释放 GPU 3，转给 RxR30 的本地 Qwen。当前版即原版，双方 SR 均为 123/217（56.68%），平均 SPL 均为 0.4933，技术异常 0 条，已评分部分共 20,070 帧。episode 618 的未评分采集保留。恢复时原入口会跳过已有正式评分，为未完成任务新建 attempt。证据整理等待器一并暂停，后续恢复由用户指令决定。[暂停摘要](../../../../outputs/reproduction/streamvln_r2r/run_20261123_01/pause_summary.json)

2026-11-23 UTC，从 val_unseen 的 1,839 条英文指令中，按 11 个场景的 episode 数比例以最大余数法分配 400 条。按场景名、episode ID 整数排序，用同一 Random(2) 在各场景内无放回抽样。抽样单位为指令 episode。见[冻结清单](episodes.json)。

沿用原生 R2R evaluator、StreamVLN R2R v1.3 权重、Habitat 配置 seed 100、贪心生成、原始历史与动作队列、500 步上限及 3 米成功判定。模型与仿真共用 GPU 3。仅记录初始及每个动作后（含终止）的前视 640×480 PNG、机器人和 RGB 相机位姿、动作、碰撞与终止标记。每条 episode.json 保存原指令、R2R 标注的参考路径点和目标。重试另建轨迹目录，以正式评分行的 capture 字段对应实际采集。

正式指标为原生 SR、SPL、OS 和 NE。SR 和平均 SPL 基于所有指标有限的唯一 episode，平均 SPL 包含失败；技术异常另列。当前版即原版。完成后的错选支路分析沿用 [RxR 逐例判据](../../../crossing_analysis/rxr_seed2_400/run_20261123_01/README.md)，对照指令、RGB、实走和参考轨迹确认具体的分支选择及其与失败的关系，按正常 STOP 和步数耗尽分别计数，保留其他失败与不确定。

```bash
python3 -B scripts/run_rxr_rgb_subset.py prepare run_20261123_01 --benchmark r2r --count 400 --sample-seed 2
tmux -L peng_r2r400_20261123 new-session -d -s r2r400 'exec python3 -Bu scripts/run_rxr_rgb_subset.py run run_20261123_01 --benchmark r2r --gpu 3 >> outputs/reproduction/streamvln_r2r/run_20261123_01/launcher.log 2>&1'
```

[源码快照及 Git 基线](../../../../outputs/reproduction/streamvln_r2r/run_20261123_01/source/versions.json) · [运行状态](../../../../outputs/reproduction/streamvln_r2r/run_20261123_01/status.json) · [逐条评分](../../../../outputs/reproduction/streamvln_r2r/run_20261123_01/result.json) · [推理日志](../../../../outputs/reproduction/streamvln_r2r/run_20261123_01/run.log)

06:52:05 UTC 后台启动，主管 PID 1092140。06:55:05 UTC 确认后交后台。当前版与原版为同一次运行，两者 SR 均为 1/2（50.00%），平均 SPL 均为 0.5000，技术异常 0 条。首条 episode 43 执行 69 个动作并 STOP，已采集起始至终止共 70 帧 RGB，对齐步号、动作和位姿；episode 61 正在进行。[启动确认](../../../../outputs/reproduction/streamvln_r2r/run_20261123_01/startup.json)。后台会话 `r2r_evidence` 等待该评测退出，随后在 CPU 上生成[失败审阅材料](../../../crossing_analysis/r2r_seed2_400/run_20261123_01/README.md)。

2026-11-23T09:18:59+00:00 · 运行中断，原因见 status.json 和 run.log（）。
