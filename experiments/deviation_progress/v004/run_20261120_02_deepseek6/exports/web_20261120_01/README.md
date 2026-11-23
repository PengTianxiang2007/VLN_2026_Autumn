# DeepSeek v004 六条轨迹的逐轮偏航回放

2026-11-20 UTC，基于已完成的 6 条轨迹、30 轮原始响应和此前的 Route53 双进度条模板导出。本次只读取实际模型结果。展示原始输入 PNG、A/B 与可用时刻、判定与证据、累计进度、回退目标和逐字模型回答。格式失败与首次偏航后未审阅的节点独立标记。

版本基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 及当前导出脚本。输入为 `outputs/deviation_progress/v004/run_20261120_02_deepseek6/`，源模板为 `outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_01/index.html`。

2026-11-20 06:16:59 UTC 发布完成。[在线回放](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_01/index.html) · [完整离线 ZIP](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_01/deepseek_v004_six_offline.zip) · [逐轮回答 JSON](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_01/model_returns.json)

6 个场景、394 个回放帧、39 个有效节点。30 轮实际调用有 162 个输入帧引用，对应 128 张不同的原始 PNG。9 个后续节点在首次有效报警后未调用模型。离线 ZIP 含可直接打开的页面、地图、前视图、模型实际输入 PNG、30 份逐字原答 TXT、全轮 JSON/JSONL 与中英文 Prompt。C47 S04 同时展示模型的 deviated 与系统的格式失败，未计入 4 条有效报警。[该轮接口复验](../../c47_contract_check.json)

本地浏览器逐轮验证了双语正文与原答、节点选择、双滑块、图片解码、真实输入 SHA256 和进度对应，零页面错误。全部 532 个发布文件的远端 SHA256 已核对。公网入口 HTTP 200，ZIP 为 application/zip、37,838,107 字节，JSON 为 application/json、456,830 字节。源离线 HTML SHA256 为 `42b1137eebbc99ebd3c2afd7f498e039975cf625c018fad36b2bc2827cee5b63`，在线 HTML 为 `5d69545bc6d16454c6b6cd9fcbfbca22b1029e3759ae50224a20c4dca23e1279`，ZIP 为 `54a0bfca2ec03db9d346cd0aaf1f30a9bdd68a8f3f175eea52c02df0e5f20550`。[本地源 HTML](../../../../../../outputs/deviation_progress/v004/run_20261120_02_deepseek6/exports/replay_01/index.html) · [浏览器核验](../../../../../../outputs/deviation_progress/v004/run_20261120_02_deepseek6/exports/replay_01/browser_check.json) · [发布记录](../../../../../../outputs/visualization_publishing/publish_20261120_061641_407899/publication.json)

生成入口为 `scripts/export_deviation_progress_v004_replay.py`，逐轮排版在 `core/deviation_progress_v004_review.js`。从仓库根目录重建时为两个目标各选一个新目录。

```bash
backbone/streamvln/.venv/bin/python -Bu scripts/export_deviation_progress_v004_replay.py \
  --run outputs/deviation_progress/v004/run_20261120_02_deepseek6 \
  --template outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_01/index.html \
  --output outputs/deviation_progress/v004/run_20261120_02_deepseek6/exports/reproduce_01 \
  --online outputs/visualization_publishing/deepseek_v004_six_reproduce_01
```
