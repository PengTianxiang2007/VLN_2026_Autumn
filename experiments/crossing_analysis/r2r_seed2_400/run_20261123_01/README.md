# R2R-CE 原版失败任务的错选支路审阅

2026-11-23 UTC。输入为[原版 StreamVLN 的 400 条 R2R-CE 评测](../../../reproduction/streamvln_r2r/run_20261123_01/README.md)，抽样 seed 2，Habitat 配置 seed 100。等评测成功结束后，以 CPU 读取各次正式评分所对应的轨迹和原始 RGB，为每条有效失败任务生成全局和局部 navmesh 路线对照图、关键帧及原指令。保留逐动作原图供调整审阅窗口。

复用 [RxR 的逐例审阅口径](../../rxr_seed2_400/run_20261123_01/README.md)。R2R 的参考轨迹为官方标注的路径点，图中相邻点连线仅用来寻找待看的时段。明确错选需要指认实际通路、预期通路并有证据支持它导致失败。逐个 episode 计数，分别汇报正常 STOP、限步终止和合计，以及占有效失败和全部有效评分的比例。保留不确定、其他失败及技术异常。当前排队的是审阅材料生成，错选支路数量待逐例审阅。

导航主管进程退出后，运行以下命令；入口先核实整批已完整结束、有效失败数与正式评分相符。

```bash
CUDA_VISIBLE_DEVICES='' backbone/streamvln/.venv/bin/python -B scripts/prepare_r2r_crossing_evidence.py outputs/reproduction/streamvln_r2r/run_20261123_01 outputs/crossing_analysis/r2r_seed2_400/run_20261123_01
```

基线提交 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。[生成日志](../../../../outputs/reproduction/streamvln_r2r/run_20261123_01/evidence.log) · [审阅材料](../../../../outputs/crossing_analysis/r2r_seed2_400/run_20261123_01/)。
