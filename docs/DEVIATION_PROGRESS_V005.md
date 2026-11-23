# v005 二分类偏航识别

每轮只输出 `consistent`（未偏航）或 `deviated`（偏航）。模型根据 A→B 的前视图判断是否发生与当前子任务明确冲突的通行选择。完整提示词见[中文原文](../experiments/deviation_progress/v005/prompt_zh.txt)和[英文对照](../experiments/deviation_progress/v005/prompt_en.txt)。

| 判定 | 状态更新 |
| --- | --- |
| `consistent` | B 成为下一轮的 A。只有证据充分的子任务进入 Completed，没有新里程碑时保留 Current。 |
| `deviated` | 记录 A 为回退目标，结束该条离线评审，本轮 `semantic_progress` 为 `null`。 |

模型仍可在 `uncertainties` 记录看不清的细节。如果原答在 `verdict` 中写了 `uncertain`，系统保存原答，登记格式错误，保留上一轮的 A 和进度。单帧初始化、端点与最多五张中间前视图、每节点一次调用及九字段接口均沿用 [v004](DEVIATION_PROGRESS_V004.md)。

## 运行

Qwen 与 DeepSeek 的原评审命令加上 `--version v005`，并指定新的输出目录，即使用本版 Prompt 和校验器。原命令默认选择 v004。

```bash
.runtime/crossing_vllm27/bin/python -B -m unittest discover -s tests -p 'test_deviation_progress_v00*.py' -v
.runtime/crossing_vllm27/bin/python -B scripts/run_deviation_progress_v004.py --version v005 --check-only --cases 7 11 19 30 47 50 --output outputs/deviation_progress/v005/reproduce_cpu_01
```

两条命令均在仓库根目录运行。六例的 CPU 检查和验证范围见[运行记录](../experiments/deviation_progress/v005/run_20261120_01/README.md)。
