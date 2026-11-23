# v005 二分类离线接口验证

2026-11-20 UTC 登记。基线工作树 HEAD 为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。本次新增 v005 中英文 Prompt 和二分类校验，在 v004 的两个评审入口中接入版本选择。

验证使用原 seed 2 离线轨迹 C07、C11、C19、C30、C47、C50 的冻结输入。检查首节点单帧、每段最多七帧、进度提交、首次偏航停止，以及对第三种判定的拒收。CPU 用例通过模拟模型响应核对两种模型入口。归档中的历史回答只用于接口核查。

在仓库根目录运行以下命令。复验时使用新的输出目录。

```bash
.runtime/crossing_vllm27/bin/python -B -m unittest discover -s tests -p 'test_deviation_progress_v00*.py' -v
.runtime/crossing_vllm27/bin/python -B scripts/run_deviation_progress_v004.py --version v005 --check-only --cases 7 11 19 30 47 50 --output outputs/deviation_progress/v005/run_20261120_01
```

六例 CPU 回放核对了 34 轮 v003 历史请求，新增模型调用 0 次。[CPU 状态](../../../../outputs/deviation_progress/v005/run_20261120_01/status.json)。版本测试共 12 项通过，包括两种模型入口的状态转移，以及 35 份 Qwen、29 份 DeepSeek 的 v004 归档回答。该组归档中的 27 份 uncertain 均被 v005 判为格式错误，37 份二分类原答通过。另有 27 项串联流程回归通过。修正 Qwen 测试用的模型名后，最终测试源码随[六例运行清单](../../../../outputs/deviation_progress/v005/run_20261120_02_qwen_gpu3/manifest.json)冻结。
