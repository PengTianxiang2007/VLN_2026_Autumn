# Route53 未做过整例 Codex 偏航评审的 34 例

按同一 seed 2 的 episode ID 从 53 例扣除四个既有整例批次已完成的 19 个唯一 ID。保留 JEV v002 active、v006.1 候选筛选、原 v002 英文偏航规则和最大间隔 6 帧补图。每例独立 Codex 会话，首次报警即停，否则评审至真实 END。GPT-6 Astra 常规档、medium，代理 17982。仅使用冻结轨迹和原生前视图，计算在远端模型进行。34 个本地 worker，每例内部各轮串行。

启动前检查：服务器 CPU 亲和性 128 核，1 分钟负载约 22.3，系统可用内存约 335 GiB，用户代理 17982 可连接。限制各进程本地计算库的线程数，避免在共享服务器上叠加与评审无关的本地线程。候选清单可用 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v002/run_20261125_09_gap6_remaining34/prepare.py` 生成。运行命令如下。

```bash
TOKIO_WORKER_THREADS=2 RAYON_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .runtime/crossing_vllm27/bin/python -Bu scripts/run_codex_node_dedup.py --input experiments/deviation_progress/codex_memory_v002/run_20261125_09_gap6_remaining34/input.json --output outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_09_gap6_remaining34 --workers 34 --model gpt-6-astra --reasoning-effort medium --timeout 1800 --proxy-url http://127.0.0.1:17982
```

[冻结输入](input.json) · [实时状态及源码快照](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_09_gap6_remaining34/status.json)。为离线偏航评审，当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

2026-11-25T19:03:43.025757+00:00 启动，主管 PID `1600865`。34 个 case 已分别发出首次 Codex 请求。

34/34 例评审完成，无技术失败。共 143 轮偏航评审，实际补图 124 张。16 例在终止节点前首次报警，15 例在终止轮首次报警（其中 C39 为 F102 → END F125）。C38 至终点未报警。C13 和 C28 只有终止节点，分别在 F130 和 F63 初始化。

[43 例合并可视化与发布记录](exports/combined43_01/README.md)。
