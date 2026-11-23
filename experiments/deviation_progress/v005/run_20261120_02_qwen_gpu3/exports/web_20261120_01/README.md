# Qwen v005 六例回放与 v004 对照

2026-11-20 UTC。沿用用户指定的双进度条网页，在原入口加入 Qwen27B v005，并默认选中 v005。页面包含 Qwen v005 的 33 轮、Qwen v004 的 35 轮及校验修复后 DeepSeek v004 的 29 轮。每组可查看实际输入前视图、逐字模型原答、指令证据、视觉证据、调用前后进度、回退目标及对应版本 Prompt。默认中文，支持英文切换。

本地导出位于 `outputs/deviation_progress/v005/run_20261120_02_qwen_gpu3/exports/web_20261120_01`，在线包位于 `outputs/visualization_publishing/qwen_v005_v004_six_web_20261120_01`。原答来自三组已完成结果，导出所用源码哈希记录在 `export.json`。

按用户要求更新 [原入口](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)，发布脚本先上传独立版本，再备份原 HTML 并切换入口。

08:14 UTC 发布完成。新增 v005 的本地浏览器检查通过 6 条轨迹、33 轮、180 个实际输入帧引用，核对了逐字原答、双语内容、版本切换和双进度条。发布核对 588 个资源哈希，原入口新增 30 个资源，入口、v005 逐轮 JSON 和 ZIP 均返回 HTTP 200。原入口 SHA256 为 `4f5eabbaa93b152c4ac071329cc5d511b9e93568cda497e99cd3cee6885d905a`。旧 HTML 备份为 `index_before_v005_20261120.html`。[发布记录](publication.json)

- [完整离线 ZIP](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_v005_comparison_six_offline.zip)
- [v005 逐轮模型回答 JSON](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_v005_model_returns.json)

ZIP 包含三组回放数据、输入图片、逐轮原始回答 TXT、JSONL 和各版本中英文 Prompt。浏览器记录和源码哈希分别位于本地导出目录的 `browser.json` 与 `export.json`。
