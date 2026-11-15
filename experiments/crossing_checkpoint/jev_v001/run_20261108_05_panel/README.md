# JEV v001 / run_20261108_05_panel

状态：失败；顺序执行到第 8 帧时遇到一次 curl 传输状态 0，已完成的前 7 条保留在
`partial.json`，不纳入最终汇总。接口随后增加最多 3 次指数退避并另起
`run_20261108_06_panel` 完整重跑。

目的：检查三帧目标改善是否只是 JEV 普遍抬分。面板沿用
`lite_v012/run_20261108_02_panel/panel.json` 中已经审计的角色和帧，不查看 JEV
结果后重选样本。

- 人工标注帧：从 47 帧中按 episode 均衡、固定 seed 选取 20 帧；
- 稳定性控制：从 20 个远离人工标注、`best_v001` 与 `lite_v002` 都为 1 分的帧中
  选取 20 帧；
- 目标三帧已由 `run_20261108_04` 单独记录，不在本面板中重复。

模型输入仍只有三帧 RGB 和固定的 Score/Noul 问题；role、标注、baseline 分数和任务
均不进入请求。面板属于开发诊断，不是独立验证，未标帧不作为真正负类。

入口：

```bash
.runtime/crossing_vllm27/bin/python -B scripts/run_jev_node_panel.py \
  --output outputs/crossing_checkpoint/jev_v001/run_20261108_05_panel \
  --panel-source outputs/crossing_checkpoint/lite_v012/run_20261108_02_panel/panel.json \
  --baseline-run outputs/crossing_checkpoint/lite_v002/run_20261108_01
```
