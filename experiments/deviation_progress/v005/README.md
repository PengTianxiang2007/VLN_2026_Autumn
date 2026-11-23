# v005 二分类偏航评审

- [四版本页面去重显示修复](run_20261120_06_deepseek_official33/exports/four_versions_20261120_02/README.md)：原入口与离线包已修复。DeepSeek 实际仅使用去重后节点及终止节点，评审结果不变。

- [Qwen / DeepSeek v003、v005 四版本同页对比](run_20261120_06_deepseek_official33/exports/four_versions_20261120_01/README.md)：已发布到原网址，四选最多三组，保留 878 轮原答、输入清单与进度，附 82.3 MB 离线包。DeepSeek v003 覆盖 29 条，其他三组各 53 条。

- [DeepSeek 官方接口接续剩余 33 条](run_20261120_06_deepseek_official33/README.md)：已完成全 53 条汇总，219 轮、47 条有效报警、11 轮格式错误；复用此前完成的 20 条及匹配回答，0 条接口失败。

- [DeepSeek 全 53 条、15 并行接续](run_20261120_05_deepseek15/README.md)：用户指定网关；原 53 并行触发限流，现由后台主管等待在途任务结束后自动接续，复用已有回答。

- [78.4 MB 精简完整离线包](run_20261120_03_remaining47/exports/compact_20261120_01/README.md)：全部 53 条、272 轮原答和 4890 帧保留；图片复用同帧 WebP 压缩副本。

- [全 53 条完整回放](run_20261120_03_remaining47/exports/web_all53_20261120_01/README.md)：272 轮，40 条轨迹触发报警，完整页面、原答及离线包已更新到原网址。

- [当前已完成 48 条样本阶段回放](run_20261120_03_remaining47/exports/web_partial_20261120_02/README.md)：250 轮，36 条轨迹触发报警，已发布到原网址。

- [完整 53 条样本的剩余 47 条补跑](run_20261120_03_remaining47/README.md)，复用已完成六条。

每轮由模型直接给出 `consistent`（未偏航）或 `deviated`（偏航）。初始化、取帧、子任务进度和回退目标沿用 v004。

- [完整中文 Prompt](prompt_zh.txt) · [完整英文对照](prompt_en.txt)
- [方法与运行命令](../../../docs/DEVIATION_PROGRESS_V005.md)
- [离线接口验证](run_20261120_01/README.md)
- [GPU 3 常驻 Qwen27B 六例重跑](run_20261120_02_qwen_gpu3/README.md)
