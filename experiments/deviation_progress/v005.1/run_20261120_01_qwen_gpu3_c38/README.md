# v5.1 Qwen 单例复评 C38

2026-11-20 15:52:46–15:59:19 UTC，GPU 3 上的 Qwen 完成 C38 离线复评（`kujiale_0234_34_4`，seed 2，评审进程 PID 248115）。七轮均通过校验并返回 `consistent`，到终止节点 F112 共零次偏航报警。两个版本逐轮使用相同的指令、端点、图片帧号、图片 SHA256 和采样参数。[v005 原始结果](../../../../outputs/deviation_progress/v005/run_20261120_03_remaining47/run/cases/C38/result.json) · [v5.1 七轮结果](../../../../outputs/deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38/v005.1_results.json)

| 区间 | v005 | v5.1 |
|---|---|---|
| S05，F64→F74 | 认定已沿走廊直行并进入卧室，把盆栽和厨房放入未决 | 只确认接近门洞，当前要求保留左侧高盆栽、右侧开放厨房及门洞通行关系 |
| S06，F74→F98 | 宣布床边停下，走廊地标仍写在未决中 | 请求带入了 S05 的完整要求，原答只引用进卧室和走到床边的指令，宣布“当前：无”，且未决列表为空 |
| S07，F98→F112 | 维持未报警 | 维持全部已完成，仅按床和床头柜评判终段 |

对照既有离线归因，错误分支的决策区间为 F72–F75，模型两版均漏报。v5.1 在 S05 抑制了提前推进，但 S06 又以卧室内的图像确认整段路线。上述结论限于本次单例。[S05 原答](../../../../outputs/deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38/run/cases/C38/S05.response.json) · [S06 输入进度](../../../../outputs/deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38/run/cases/C38/S06.request.json) · [S06 原答](../../../../outputs/deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38/run/cases/C38/S06.response.json) · [离线归因](../../../../outputs/offline_route_dataset/v001/run_20261118_01/dataset/evaluation/episodes/kujiale_0234_34_4.json)

复用 GPU 3 的常驻 `route53-qwen27b` 及 v005 请求参数，temperature 0，top_p 1，seed 2，max_tokens 8192，关闭 thinking。有效节点为 F0、F5、F33、F64、F74、F98、F112（终止）。从首节点独立建立新进度，每轮最多七帧，首次通过校验的偏航即结束。工作树基于 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，本次中英文 Prompt 和入口的实际源码随运行冻结。

在仓库根目录执行。复现时指定新的输出目录。

```bash
PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004.py \
  --version v005.1 --cases 38 \
  --qwen-service outputs/model_services/qwen27b_gpu3_20261120_02/service.json \
  --output outputs/deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38
```

[运行清单与源码哈希](../../../../outputs/deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38/manifest.json) · [运行状态](../../../../outputs/deviation_progress/v005.1/run_20261120_01_qwen_gpu3_c38/status.json)
