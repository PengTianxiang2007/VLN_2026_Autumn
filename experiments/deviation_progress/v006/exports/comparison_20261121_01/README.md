# v6 接入既有多版本对比网页

用户要求将 v6 与以前 v5 整合到同一个网站，交互沿用原页面。本次复用已发布的四组 v003/v005 和 Qwen v006 全部结果，新增模型调用 0 次。

五组为 Qwen v003、DeepSeek v003、Qwen v005、DeepSeek v005、Qwen v006。默认勾选两组 v005 与 Qwen v006，默认详情为 Qwen v006，最多同时显示三组偏航区间。原四组结果保留。DeepSeek v003 仍只覆盖 C01–C29，其余版本各覆盖 53 条。共 1,131 轮原答，既有格式失败及 v6 截断回答的中英文展示完整保留。

只导出既有结果，不改变 seed、模型参数、节点、采样、进度或偏航结论。使用相同的 4,890 帧和冻结有效节点、双进度条及中英文切换。新增 Q6 地图标签，避免沿用 Q5 标签。

构建命令：

```bash
backbone/streamvln/.venv/bin/python -B scripts/extend_deviation_comparison_v006.py
```

来源：`outputs/visualization_publishing/deviation_four_versions_web_20261120_02/` 与 `outputs/visualization_publishing/qwen_v006_all53_web_20261121_01/`。

新目录：`outputs/visualization_publishing/deviation_five_versions_web_20261121_01/`。发布至独立版本目录后，备份旧入口并更新用户原网址 `http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html`。旧发布与下载保留。

状态：已发布并切换原入口。最终源码哈希、结果来源哈希及实际 HEAD 记录于导出目录的 `export.json`。

[原网址：五版本同页对比](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html) · [独立发布快照](http://134.175.18.101/vln/deviation_five_versions_web_20261121_01/index.html) · [完整精简离线包（84.4 MB）](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/vln_v003_v005_v006_five_versions_offline.zip)

本次相关检查已通过，记录见 `browser_check.json`：五组切换、默认三组选取、三组上限、中英文正文及原答、C50 截断原答、输入帧与双进度条同步、DeepSeek v003 缺失覆盖。无浏览器脚本错误。

标准发布通过远端资源 SHA256 和入口 HTTP 200。记录：`outputs/visualization_publishing/publish_20261121_020056_957717/publication.json`。原入口切换及公网检查见本目录 `publication.json`，入口及 v6 JSON 内容哈希一致，ZIP HEAD 大小一致。旧入口备份名为 `index_before_v006_comparison_20261121.html`。

- HTML SHA256：`0d5b9a3ebeb10c734571c3eefc4002e4ac96a36ce63c678faa750941a2225f30`。
- 离线 ZIP 大小：84,379,224 bytes。
- ZIP SHA256：`d0d5bf9d2f66b9dddc9c7659f1bacdaa4f6c6e23a718b97e72841e22a7d2ff3e`。

发布命令：`python3 -B experiments/deviation_progress/v006/exports/comparison_20261121_01/publish.py`。复用此前原入口发布脚本，保留历史文件，新版资源就绪后才原子替换入口。GPU 3 模型和后台任务未作修改。
