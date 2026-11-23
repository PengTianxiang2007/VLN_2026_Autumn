# VLNVerse H1 动作回退样本集 · 每例 7 张历史前视图

2026-11-23 UTC。沿用[昨晚冻结的 22 例](../../v001/run_20261122_03_rgb22/cases.csv)，seed 为 2。为每个案例准备 A 的目标图、去程中间均匀采样的 5 张图和 B 的报警图。仿真复现方法见[第一版说明](../run_20261123_01/README.md)。

已完成 22 例，覆盖 13 个场景，共 154 张原生前视图、538 个历史动作。逐例核对了端点、5 个不同的中间帧及对应图片。C03 的端点为 F25 和 F45，中间帧为 F26、F30、F35、F40、F44。本次仅构建离线输入。

[22 例帧号索引](cases.csv) · [数据包总清单](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_02/manifest.json) · [C03 模型参考输入](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_02/cases/C03/reference.json)

5 张中间图按 v006 的 `uniform_between` 规则，在 F(A+1) 至 F(B−1) 的动作边界中均匀取样。每张图均取自原始前视 RGB。A、B 两张端点图单独加入。模型参考输入同时包含从 A 到 B 的全部去程动作，后续实走时采集的掉头后当前图独立于这 7 张历史图。

## 离线构建

Git 基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，数据包的 `source/` 随附实际构建脚本及仿真配置，清单记录其来源。下列为本次构建命令，重建时使用新目录。

```bash
python3 -B scripts/prepare_vlm_rollback_dataset.py outputs/inverse_rollback/vlm_action_v001/run_20261123_02
```
