# v004 子任务进度与地标约束偏航评审

- [六例 Qwen 原答兼容性核查与双模型回放](run_20261120_01/exports/paired_web_20261120_01/README.md)

- [校验兼容修复与 DeepSeek 六条原答回放](run_20261120_03_contract_replay/README.md)

每个有效检查节点使用一次 VLM 调用，对照当前子任务的通行约束判断偏航，并在 `consistent` 时维护累计进度。

- [方法、接口与复现命令](../../../docs/DEVIATION_PROGRESS_V004.md)
- [实际发送的中文 Prompt](prompt_zh.txt) · [英文对照](prompt_en.txt)
- [离线诊断与 GPU 2 的六条 Qwen27B 重跑](run_20261120_01/README.md)
- [同六条 DeepSeek 对照，每条轨迹一个独立进程](run_20261120_02_deepseek6/README.md)
