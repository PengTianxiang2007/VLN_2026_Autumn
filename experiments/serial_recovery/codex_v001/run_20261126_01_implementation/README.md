# 在线串行 Codex 接管：实施与 CPU 验证

日期：2026-11-26 UTC。状态：实现完成；真实闭环导航待验证。

## 目的与版本

按用户“现在把这个版本做出来”的指令，实现在线串行 JEV → 回退点 → 偏航 → GPT 接管至终点。特别保留 StreamVLN 请求 STOP 后等待末段偏航判定的屏障。

基于 Git `68f16df4d822b0a3ced83d606c320378da2ed729` 的当前工作区开发，未覆盖此前恢复实验的未提交修改。核心实现为 `core/codex_serial_{config,review,runtime}.py`、`core/codex_live_takeover.py` 和 CPU worker；通过原生 evaluator 与 `run_full.py --codex-serial-output` 接入。共享机器人桥仅添加可选生命周期回调与终止观测返回，原调用方式继续有效。

沿用 JEV v004 / v002 active / Codex v006.1 / 偏航 v002 / 最大六帧补图 / Astra medium / 7892。恢复提示词保留 goal180 英文原文。当前没有选择或启动新评测任务；原双 GPU 恢复队列不由本实施任务操作。

## 验证

使用替身模型、假环境与临时图片执行 CPU 测试，不调用远端模型、不启动 Isaac、不占 GPU。

```bash
.runtime/crossing_vllm27/bin/python -B -m unittest \
  tests.test_codex_serial_pipeline tests.test_codex_node_dedup -q
```

新增 11 项测试通过，覆盖：真实 `run_case` 的候选/去重/终止评审顺序、STOP 屏障、末段与中途偏航交接、无回退点的终止初始化、模型/原生评分分离、物理终止不重复 STOP、传输失败不推进、不评分、180 步限制和最终会话 fork。既有 Codex 会话/去重接口共 12 项一并回归。

首轮新增 11 项全部通过；既有 12 项中 1 项并发日志测试因同一行拼接多个 JSON 失败，其余通过。该项单独复核通过（1/1）；没有修改无关并发代码。另检查新入口 `--help`、相关 Python 语法及 `git diff --check`。

## 产物与限制

本地证据目录：`outputs/serial_recovery/codex_v001/run_20261126_01_implementation/`，保存测试输出、源码快照及验证摘要。任务启动方法、协议、逐帧产物和指标口径见 [版本说明](../README.md)。

这是代码与 CPU 合同验证，不代表已验证网络请求、真实会话 fork、当前服务器仿真及导航端到端效果。本版尚未运行导航：当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

下一步是在指定任务和可用 GPU 上进行小规模真实闭环联调，重点观察自然报警与末段 STOP 报警。当前保留的实验与仿真没有切换到本版。
