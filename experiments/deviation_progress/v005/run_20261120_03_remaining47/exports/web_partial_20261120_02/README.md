# v005 当前已完成样本阶段版

本阶段版使用快照时已完整落盘的 48 条样本，来自首次六条运行和剩余样本补跑，包含 250 轮模型回答及 381 个有效节点。仍在评审中的样本没有纳入。每轮展示原始回答、实际输入帧、指令及视觉证据、前后累计进度、报警区间和 v005 Prompt。页面默认中文并支持英文。

- [打开沿用的原网址](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)
- [下载 48 条样本完整离线包](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_v005_completed_48_offline.zip)
- [下载 v005 逐轮回答 JSON](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_v005_partial_48_model_returns.json)

11:46 UTC 发布及公网检查通过。入口文件 5,762,122 字节，5428 个静态资源远端哈希核验通过。旧入口已备份为 `index_before_v005_partial48_20261120.html`。网页、逐轮 JSON 和 350,269,313 字节离线 ZIP 均返回 HTTP 200。

阶段快照、导出数据和 SHA256 见 `outputs/deviation_progress/v005/partial_20261120_01/` 及 `outputs/visualization_publishing/qwen_v005_partial_48_web_20261120_02/`。本地页面检查见 `browser_check.json`，发布记录见 `publication.json`。此页面覆盖原入口，发布脚本在入口切换前备份原 HTML。
