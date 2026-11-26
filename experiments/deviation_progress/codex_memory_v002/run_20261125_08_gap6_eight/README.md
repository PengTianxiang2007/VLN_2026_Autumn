# 八例偏航重跑 · 最大间隔六帧

2026-11-25，冻结 seed 2 的 C47、C16、C37、C25、C41、C08、C40、C50。沿用 JEV v002 active、v006.1 候选筛选及原 v002 英文偏航规则。每例新建一个 Codex 会话，8 个进程并行，GPT-6 Astra 常规档、medium、代理 17982。使用离线轨迹和远端模型，首次报警即停，其余评审到真实 END。

每段将已提交且处于段内的前视帧作为锚点，包括被删除候选的窗口及同一会话前次补图。相邻锚点间每隔 6 个动作帧号补入一张原生前视图，恰好落在已有锚点时不重复提交。补图路径及 SHA256 在对应请求中留存，附图顺序、帧号与可引用图见每轮 request.json。最大允许间隔为 6。

准备命令为 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v002/run_20261125_08_gap6_eight/prepare.py`。启动命令如下。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_codex_node_dedup.py --input experiments/deviation_progress/codex_memory_v002/run_20261125_08_gap6_eight/input.json --output outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_08_gap6_eight --workers 8 --model gpt-6-astra --reasoning-effort medium --timeout 1800 --proxy-url http://127.0.0.1:17982
```

[冻结输入](input.json) · [实时状态与源码哈希](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_08_gap6_eight/status.json)。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25T18:31:03.279621+00:00 已启动，主管 PID `1547296`。已核对八个独立工作进程各自发起了实际 Codex 调用，当前交后台运行。

## 完成结果

2026-11-25T18:49:12.576165+00:00，8/8 完成，技术失败 0。7 例由模型判定偏航（4 例在终止段，3 例在终止前），C40 仅初始化。实际补图 30 张。

| Case | 结果 | 末轮区间 | 末轮补图 | 全例补图 |
|---|---|---|---:|---:|
| C08 | 终止段报警 | F130→F162 | 4 | 4 |
| C16 | 终止段报警 | F55→F84 | 4 | 5 |
| C25 | 终止段报警 | F46→F90 | 5 | 6 |
| C37 | 终止前报警 | F38→F80 | 6 | 6 |
| C40 | 仅终止帧初始化 | F62→F62 | 0 | 0 |
| C41 | 终止前报警 | F37→F86 | 5 | 5 |
| C47 | 终止前报警 | F33→F52 | 2 | 2 |
| C50 | 终止段报警 | F7→F33 | 2 | 2 |

[原始结果](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_08_gap6_eight/results.json)。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。
