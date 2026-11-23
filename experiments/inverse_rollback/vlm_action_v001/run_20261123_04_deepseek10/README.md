# DeepSeek 驱动 H1 实际回退 · 追加十例

2026-11-23 UTC。按[七帧样本集](../run_20261123_02/README.md)顺序取第 4～13 个不同 episode，seed 2。[案例顺序](cases.json)为 C12、C15、C19、C20、C21、C22、C24、C25、C27、C28。

复用[首批三例](../run_20261123_03_deepseek3/README.md)的模型、两份英文 prompt、图片顺序与动作协议。使用官方 `deepseek-flash`，temperature 0，关闭 thinking。去程七帧生成一次描述，原生 H1 在 B 掉头后，每轮输入四张固定参考图和最多四张回程图。模型自主退出时按水平距离 ≤0.35 米判断达标，单列朝向误差。主导航 SR 与平均 SPL，当前版和配对原版均为“暂无，已评分 0 条”。

Git 基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，实际运行代码与 prompt 随批次冻结。后台启动命令如下，凭据在隐藏终端输入。

```bash
tmux -L peng_h1_ds10_20261123 -f /dev/null new-session -s rollback10 'env VLN_ROLLBACK_RUN_ID=run_20261123_04_deepseek10 .runtime/crossing_vllm27/bin/python -Bu scripts/run_vlm_rollback.py start'
```

[实时状态](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_04_deepseek10/status.json) · [冻结清单](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_04_deepseek10/manifest.json)。任务结束后由主管汇总各例的 `result.json` 至 `summary.json` 并关闭仿真。按用户要求仅确认正常启动。

已通过[一次性启动确认](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_04_deepseek10/startup_verified.json)。十份七图去程描述均已生成。GPU 1 上的 C12 完成初始掉头，随后执行 DeepSeek 首轮四个 LEFT，各 50 个物理步；下一轮请求已带入四张固定图和 R0、R2、R4。确认程序已退出，已分离的 tmux 队列继续运行。
