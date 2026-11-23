# DeepSeek H1 实际回退 · 接续至全部 22 例

2026-11-23 UTC。接续[首批三例](../run_20261123_03_deepseek3/README.md)和[在途十例](../run_20261123_04_deepseek10/README.md)。已登记的最后九例为 C31、C32、C34、C37、C42、C46、C47、C49、C50，使用[同一份七帧数据集](../run_20261123_02/README.md)，seed 2。

等待十例主管退出后，在冻结的 22 个 episode 中逐条检查已有物理结果，按原顺序提交剩余案例。每轮重新做 GPU 准入。沿用 `deepseek-flash`、首批实际英文 prompt、7 帧去程、4 张固定图和最多 4 张回程图，按模型自主退出且误差 ≤0.35 米判定回退达标。已经有落点评分的案例均保留，包括未达标案例。整条导航的 SR 和平均 SPL，当前版与同批原版均为“暂无，已评分 0 条”。

主管先在 CPU 等待；在途十例如果技术中断，缺失结果纳入后续任务。每次物理运行写入新 attempt 目录。程序定期汇总唯一 episode，完成后保存 22 例逐条结果及平均误差。Git 基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，本批启动时冻结实际代码、prompt 和清单哈希。

```bash
tmux -L peng_rollback22_20261123 -f /dev/null new-session -s finish22 '.runtime/crossing_vllm27/bin/python -Bu scripts/finish_vlm_rollback.py'
```

[全批进度](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_05_finish22/progress.json) · [调度记录](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_05_finish22/manifest.json)

01:54 UTC 已确认独立后台会话 finish22，主管 PID 668399，状态为 `waiting_for_previous`。当时全清单已完成 8/22，位置达标 2/8，平均退出水平误差 2.631 米。后续由队列自动衔接。

全部 22 例已完成，位置达标 2/22，平均退出水平误差 2.403 米。[逐例结果](summary.json)

[22 例逐帧地图与 RGB 回放](../../exports/deepseek_h1_22_20261123_01/README.md)
