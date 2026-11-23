# v004 DeepSeek 六进程离线评审

2026-11-20 UTC，用户授权立即启动与 GPU 2 Qwen 组相同的六条轨迹，每条一个独立进程。固定 C07、C11、C19、C30、C47、C50 的 seed 2 离线前视、去重节点及终止节点，39 个节点为两组各自的调用上限。每条内部串行，从单帧初始化到首次有效偏航或终止节点。各版本分别维护自己的 A 和进度。

使用 v004 中文 Prompt，沿用 [v003 DeepSeek 模型配置](../../v003/run_20261118_03_deepseek29/README.md)中的 deepseek-flash、thinking enabled、reasoning_effort high、max_tokens 32768、JSON object、非流式。模型请求未设置推理 seed。进度、调用原答、错误和实际发出的图像清单分别保存。当一次真实回答格式错误时，保留原答和旧锚点，继续到下一有效节点。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004_deepseek.py \
  --workers 6 --cases 7 11 19 30 47 50 \
  --output outputs/deviation_progress/v004/run_20261120_02_deepseek6
```

凭据经终端隐藏输入交给独立主管。复现时另取新的输出目录。运行中读取 `outputs/deviation_progress/v004/run_20261120_02_deepseek6/status.json`，主管结尾将状态同步为本目录 `completion.json`。各轨迹方法预测的语言内容与帧序列可从 `run/cases/Cxx/Sxx.request.json`、`Sxx.response.json`、`state.json` 核对。首次偏航区间的两模型差异不直接代表准确率。[v004 方法与局限](../../../../docs/DEVIATION_PROGRESS_V004.md)

05:53 UTC 主管 PID 3696863 启动，凭据验证通过，六个工作进程已进入评审。[当前状态](../../../../outputs/deviation_progress/v004/run_20261120_02_deepseek6/status.json) · [模型、节点及源码哈希](../../../../outputs/deviation_progress/v004/run_20261120_02_deepseek6/manifest.json) · [逐轮日志](../../../../outputs/deviation_progress/v004/run_20261120_02_deepseek6/supervisor.log)

六个不同 PID 的真实首帧请求全部返回 HTTP 200 并通过 v004 校验，六条轨迹均把各自的已提交中文进度逐字传入了 S02。C07 的 S02 七帧返回 uncertain，C11 的 S02 六帧返回 deviated。交后台时已核对两组模型的全部 39 个节点、数据集哈希和中文 Prompt 哈希一致。[启动核验](../../../../outputs/deviation_progress/v004/run_20261120_02_deepseek6/startup_validation.json)

06:01:58 UTC，6/6 条完成。30 轮含 17 次 consistent（其中 6 次初始化）、8 次 uncertain、4 次有效 deviated 和 1 次格式失败。C07 在 F2→75、C11 在 F0→5、C30 在 F42→47、C50 在 F15→33 首次有效报警。C19、C47 均未触发有效报警。C47 S04 虽在原答中写 deviated，多返回顶层字段 `type` 导致校验失败，本轮保留原锚点。六个工作进程已退出。[运行收尾](completion.json) · [逐轮结果](../../../../outputs/deviation_progress/v004/run_20261120_02_deepseek6/v004_results.json) · [可视化导出记录](exports/web_20261120_01/README.md)
