# GPT-6.1 Terra xhigh · 43 例离线偏航评审

使用原 43 例的三个 Astra 批次冻结输入，导航 seed 2。每个 case 独立新建 Codex 会话，JEV v002 active 原候选、候选观测、去重和首次报警/真实 END 协议沿用对应原批次。原 9 例不额外补图并沿用旧建点提示词；其余 34 例最大帧距 6 并使用当时的有限视野提示。偏航判断沿用 v002 英文规则。

22 个进程，常规服务档，Terra xhigh。失败调用在同一轮次按 2 至 60 秒退避重试。每次请求有开始和结束时间、elapsed_seconds；整批墙钟可由 status.json 的启动和完成时间计算。离线评审不产生导航评分，当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

[冻结输入与源哈希](input.json) · [实时状态](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261126_01_terra_xhigh43/status.json)。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_codex_node_dedup.py --input experiments/deviation_progress/codex_memory_v002/run_20261126_01_terra_xhigh43/input.json --output outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261126_01_terra_xhigh43 --workers 22 --model gpt-6.1-terra --reasoning-effort xhigh --timeout 1800 --proxy-url http://127.0.0.1:17982 --retry-calls
```

2026-11-26T03:13:54.458051+00:00 UTC 启动，主管 PID 2234455。

2026-11-26T03:17:21.501872+00:00 启动核对：22 个 worker 均发出初始化请求，已核实模型和 xhigh 参数。检查时有效返回 0。17982 接受 CONNECT，但上游 TLS 握手失败，CLI 记录 workspace routing discovery failed。主管保留队列并自动重试。

2026-11-26T04:21:46.578741+00:00 用户要求停止。主管、评审 worker 和在途子进程已退出，自动重试结束。已完成 0/43，原始调用记录保留。
