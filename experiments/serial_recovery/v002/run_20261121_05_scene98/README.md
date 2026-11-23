# 四个完整场景的在线恢复与原版配对评测

2026-11-21，已准备，导航尚未启动。目标是看现有在线恢复管线在一批完整场景上能否改善原版 StreamVLN 的任务结果。

## 样本与原版对照

从[已有原版 250 条实验](../../../../docs/STREAMVLN_VLNVERSE_SCENE250.md)的 10 个场景按 scene ID 排序取前四个，纳入这些场景在 VLNVerse fine val_unseen 的全部 98 条。选择只依赖场景名，不按成功、失败或报警记录筛选。已逐条核对 split 与历史 seed 2 的 episode ID、场景和派生 seed。C01 位于 kujiale_0036，随整场重新运行，先前单条验收结果不计入本批。

| 场景 | 全部 case | 原版成功 | 原版 SR |
| --- | ---: | ---: | ---: |
| kujiale_0036 | 25 | 12 | 48.00% |
| kujiale_0113 | 25 | 14 | 56.00% |
| kujiale_0123_fix | 25 | 8 | 32.00% |
| kujiale_0207 | 23 | 6 | 26.09% |
| 合计 | 98 | 40 | 40.82% |

[逐条原版结果及本批清单](baseline98.csv)沿用[原版评测评分表](../../../../outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/episodes.csv)中的原值，每行含历史 run ID。98 条平均 SPL 为 0.33376，NE 为 4.34871 米，TL 为 9.21475 米。原始评分表 SHA256 为 `489a8b59f12106572c4a78f509bcdf96d130cbb9ea72c826362f926457babfaf`。

## 运行与交付

新组从各任务起点开始运行 StreamVLN 和现有在线管线。沿用 [C13 闭环](../run_20261121_03/README.md)的建点和去重、v006 偏航识别、两阶段 Recovery、实际回退及交还机制。继续使用同一导航权重、seed 2、每条派生 seed、原生停止和评分规则，25,000 个物理 tick 预算包含纠错。原版逐条评分仅供事后对照。当前工作区基于 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，实际使用的源码与提示词哈希见[冻结清单](../../../../outputs/serial_recovery/v002/run_20261121_05_scene98/manifest.json)。

批次沿用原生评测循环和 [split 顺序](../../../../outputs/serial_recovery/v002/run_20261121_05_scene98/config.json)。首条真实闭环后继续，无报警、无接管、跌倒、卡住等有原生评分的任务全部计入。技术跳过单列，排查后只补缺失 ID；98 条各有一份正式评分后完成配对。

以下为正式开跑时使用的命令。`MODEL_GPU` 和 `SIM_GPU` 按届时空闲资源设置，沿用已登记的本地 Qwen 服务及 EasyJEV 鉴权。

```bash
VLN_MODEL_READY_TIMEOUT=3600 benchmarks/vlnverse/.venv/bin/python -Bu scripts/run_serial_v006.py \
  --campaign outputs/serial_recovery/v002/run_20261121_05_scene98 \
  --model-gpu "${MODEL_GPU:?}" --sim-gpu "${SIM_GPU:?}"
```

按 episode ID 配对报告两组 SR、SPL、NE、TL，以及原版失败变成功和原版成功变失败各多少条。另列自然报警、实际接管和交还各覆盖多少条，方便对照导航结果。
