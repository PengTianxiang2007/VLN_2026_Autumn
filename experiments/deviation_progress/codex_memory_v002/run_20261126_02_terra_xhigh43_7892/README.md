# Terra xhigh 43 例 · 7892 代理

复用[前次运行](../run_20261126_01_terra_xhigh43/README.md)的完整冻结输入，seed 2、v002 active、对应的两版建点提示词、原 9 例与后 34 例各自的区间观测规则。模型为 GPT-6.1 Terra 常规档、xhigh，22 进程并行，沿用同一轮次自动退避重试。代理为 127.0.0.1:7892。前次未完成任何 case，本次使用新会话和独立输出目录。

[输入](input.json) · [运行状态](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261126_02_terra_xhigh43_7892/status.json)。实际源码及 Git 状态由主管保存。离线评审，当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_codex_node_dedup.py --input experiments/deviation_progress/codex_memory_v002/run_20261126_02_terra_xhigh43_7892/input.json --output outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261126_02_terra_xhigh43_7892 --workers 22 --model gpt-6.1-terra --reasoning-effort xhigh --timeout 1800 --proxy-url http://127.0.0.1:7892 --retry-calls
```

2026-11-26T04:26:28.642685+00:00 启动，主管 PID 2378314。

启动确认时，22 例已进入初始化，2 例收到有效回答。其中 C14 用时 65.843 秒。已交后台。

2026-11-26T05:23:27.912592+00:00 依用户指令停止剩余评审和自动重试，完成 39/43，取消 C02, C15, C31, C39。已完成逐例结果保留。

39 例已作为可选模型加入同一网页，Astra C01、C27 已换用后续复判。[双模型导出记录](exports/combined_models_01/README.md) · [在线回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html)。
