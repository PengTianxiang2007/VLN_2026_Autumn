# v003 / v005 四版本偏航区间对比

用户确认提供 Qwen v003、DeepSeek v003、Qwen v005、DeepSeek v005 四组，通过勾选最多同时显示三组偏航区间，沿用原网页入口。Qwen v003、Qwen v005、DeepSeek v005 各有 53 条；DeepSeek v003 仅有 C01–C29，其他任务明确标注未评审，不补跑模型。

保留原地图与 RGB 双进度条、完整轨迹、节点与原答详情。不同版本以独立颜色和分行区间条显示，支持零到三组勾选；详细回答单独选择版本。默认显示 Qwen v003、Qwen v005、DeepSeek v005，详情默认 DeepSeek v005。格式错误仍使用历史系统采纳状态，不重新校验或补收报警；原答完整保留。所有界面、正文及校验错误说明支持中文/English。

来源：v003 两组原始 `deviation/run/cases`；Qwen v005 的 `all53_20261120_01` 合并来源；DeepSeek v005 官方接续 `run_20261120_06_deepseek_official33`（包含旧网关回答，保留来源）。图片使用同帧、同分辨率 WebP 展示副本，共用既有 4,890 帧与 19 张地图，原始 PNG 输入身份和 SHA256 保留。下载包包含四组逐轮 JSON、逐字原答、实际输入清单、累计进度和中英文 Prompt。

实现：`scripts/export_deviation_four_versions.py`、`core/deviation_four_versions.js`。仅运行一次覆盖本次新增行为的本地浏览器检查，再按标准发布器上传新版本并备份、切换用户原网址入口，不重跑导航或模型。

状态：2026-11-20 13:48:24 UTC 已发布并切换原入口。

- [四版本在线对比](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)
- [完整精简离线包，82.3 MB](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/vln_v003_v005_four_versions_offline.zip)
- [独立保留的本次版本](http://134.175.18.101/vln/deviation_four_versions_web_20261120_01/index.html)

| 版本 | 已评审 case | 逐轮原答 | 有效报警轨迹 | 格式错误轮次 |
| --- | ---: | ---: | ---: | ---: |
| Qwen v003 | 53 | 288 | 36 | 5 |
| DeepSeek v003 | 29 | 99 | 28 | 5 |
| Qwen v005 | 53 | 272 | 40 | 0 |
| DeepSeek v005 | 53 | 219 | 47 | 11 |

共收录 878 份逐轮原答。报警数量不代表准确率。DeepSeek v003 的 C30–C53 显示未评审；格式错误保留原答结论与历史未采纳状态。未新增模型调用。

本地产物：`outputs/visualization_publishing/deviation_four_versions_web_20261120_01/`。该目录包含 HTML、四组 `compare4_*_model_returns.json`、离线 ZIP、资源清单与 `export.json` 来源哈希。ZIP 保留全部回放帧、地图、原答、输入清单、累计进度和中英文 Prompt；图片为同帧同分辨率的 WebP 展示副本，原始 PNG 路径和哈希另存。

验证：本地浏览器检查覆盖四选项、最多三组限制、全部取消、53 条切换、缺失版本、原答与中英文内容、异常 JSON 展示和双滑块同步，结果见 `browser_check.json`；补齐中文字体后单次截图确认，见 `preview.png`。标准发布器与原入口切换共核对 4915 个资源哈希，原入口新增 6 个资源；页面及四组 JSON 公网 HTTP 200 且哈希一致，ZIP HEAD 为 HTTP 200、82,297,930 字节。未做完整公网 ZIP 下载。发布记录见 `publication.json`。

HTML SHA256：`6970177a5078d47159d9381bc689600a95b7c8ce696184eb5ce6f4a428900a1d`。
ZIP SHA256：`c8bad38f58742e14b195c1b71752b191695b69aae44ca9a01aab41ec1e646d51`。
原入口已备份为 `index_before_four_versions_20261120.html`；旧下载文件继续保留。
