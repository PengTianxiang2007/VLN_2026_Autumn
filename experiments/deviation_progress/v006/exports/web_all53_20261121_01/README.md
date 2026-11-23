# Qwen v006 全 53 条单页回放

状态：2026-11-21 01:41 UTC 已发布。用户要求将 v6 放在一个网页中展示。

[打开 v6 全 53 条回放](http://134.175.18.101/vln/qwen_v006_all53_web_20261121_01/index.html) · [下载完整精简离线包（78.3 MB）](http://134.175.18.101/vln/qwen_v006_all53_web_20261121_01/qwen_v006_all_53_offline.zip)

范围为全部 53 条既有离线结果，共 253 轮、197 consistent、47 deviated、9 轮格式错误，47 条轨迹报警。沿用双进度条、地图/RGB 回放、去重后有效节点、双语原答、实际输入帧与调用前后累计进度。首次有效报警后的节点标为未评审。地图与参考路线只用于离线展示。

来源为 `outputs/deviation_progress/v006_pair_route53_20261121_01/v006_all53.json` 的逐条 `source_run`，合并两例预跑、第一批完整结果和 C50–C53 接续结果。三组 Qwen3.8-27B-FP8 使用相同 v006 中文 Prompt、seed 2、temperature 0、top_p 1、max_tokens 8192、关闭 thinking、相同冻结节点与采样协议。无新增模型调用，不改变模型结果或状态更新。GPU 3 后台评审与模型服务保持运行。

九轮失败原答全部保留。C50/S03 达到长度上限且 JSON 截断，`answer` 保持 null；仅为展示提取已有完整字段，并逐句翻译附加英文文字，重复也完整保留。展示提取不修复或重新采纳原答。`uncertainties` 误返回对象的原答也可双语查看。

为沿用此前精简下载方式，输入图片复用同帧同分辨率 WebP 展示副本。保留原始 PNG SHA256 与展示文件 SHA256，页面说明二者区别。所有轨迹帧、地图、模型原文、输入清单、进度和 Prompt 完整保留。

执行命令：

```bash
backbone/streamvln/.venv/bin/python -B experiments/deviation_progress/v006/exports/web_all53_20261121_01/build_export.py
```

汇总快照：`outputs/deviation_progress/v006/all53_20261121_01/`。导出源码哈希、实际 HEAD 与来源清单保存于该目录。在线目录：`outputs/visualization_publishing/qwen_v006_all53_web_20261121_01/`。

实际完成过程：导出器生成媒体后发现输入清单的旧 `front/` 路径与拆分后的 `assets/` 路径不同。已修正公共导出器，并用本目录 `finish_export.py` 单次更新未发布页面的路径、完成打包，复用已生成媒体。没有重新推理或改变判定。

本地页面检查记录为 `outputs/deviation_progress/v006/all53_20261121_01/exports/web_all53_20261121_01/browser_check.json`。检查首尾样本及全部九轮格式失败，覆盖中英文正文、逐字原答、640 像素宽输入图、双进度条同步、有效节点数和去重数据标识，浏览器无脚本错误。输入图路径元数据后续仅做上述修正，媒体内容与交互不变。

发布回执为 `outputs/visualization_publishing/publish_20261121_014015_146211/publication.json`，`phase=published`、`remote_sha256_verified=true`，全部 4,913 个文件远端哈希通过，入口 HTTP 200。公网采用 HEAD 快速检查，未执行额外的全量下载或在线浏览器检查。

- 在线 HTML SHA256：`5890ee68d51d623ffd6c433c5e61afd1085a70dc4e7e7e9c237a955c5a723134`
- 离线 ZIP SHA256：`2e04921bcb25affb434d8dd787a07d41689e0f2ea578a7199481c66a92a49859`
- ZIP 大小：78,302,489 bytes。
- 导出统计与最终源码哈希：`outputs/deviation_progress/v006/all53_20261121_01/exports/web_all53_20261121_01/export.json`。

47 条报警仅是模型输出统计，不是偏航识别准确率。九轮格式错误没有被计为有效判定。离线包使用展示用 WebP，保留实际输入 PNG 的哈希；不包含另存一份的无损 PNG。
