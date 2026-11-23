# v005 全 53 条精简离线包

用户要求缩小下载体积并保留完整内容。复用已发布的 53 条、272 轮完整包，不重跑模型，不重新生成轨迹或改模型原答。1,244 张实际输入 PNG 与回放已有同帧 640×480 WebP 重复；精简包将输入图和回放图指向同一份已有 WebP，保留 4,890 帧、地图、所有轮次、原始回答 TXT、JSON/JSONL、中英文 Prompt、累计进度、输入帧清单及实际输入的原始 SHA256。

WebP 是有损展示副本，PNG 原始字节不放入精简包；完整无损包仍保留。JSON 中 `images[].file` 指向包内展示副本，`original_file` 和原 `sha256` 保留实际输入身份，`display_sha256` 标识展示文件；这些展示元数据不修改模型原答。`image_manifest.json` 保存全部对应关系及原包下载地址。

构建命令：

```bash
.runtime/crossing_vllm27/bin/python -Bu experiments/deviation_progress/v005/run_20261120_03_remaining47/exports/compact_20261120_01/build.py
```

直接读取现有 ZIP，仅处理页面和展示元数据；压缩包先写入 `/tmp` 再复制到 `outputs/`，避免重新写数千个 NAS 图片文件。一次页面检查复用原检查脚本，核对 53 条/272 轮、双语原答和输入帧。发布使用既有标准发布器，仅上传下载说明页与新 ZIP。

状态：2026-11-20 12:28 UTC 已发布。新包 78,367,381 字节（78.4 MB），原包 379,231,091 字节，缩小约 79.3%。一次本地页面检查通过 53 条、272 轮、中文/英文、原答、实际输入帧和同步进度条；标准发布远端 SHA256 通过，下载地址 HEAD 返回 HTTP 200、application/zip、正确大小。没有重新调用模型。

- [直接下载 78.4 MB 精简完整包](http://134.175.18.101/vln/qwen_v005_all53_compact_download_20261120_01/qwen_v005_all_53_compact_offline.zip)
- [双语下载说明](http://134.175.18.101/vln/qwen_v005_all53_compact_download_20261120_01/index.html)
- [发布记录](publication.json) · [页面检查](browser_check.json)

产物：`outputs/visualization_publishing/qwen_v005_all53_compact_download_20261120_01/`。SHA256：`bdf82f772480dfcbdef9c865f4514b84985db3604e4a84c9a478dd150d936b5c`。标准发布记录：`outputs/visualization_publishing/publish_20261120_122730_228143/publication.json`。

发布命令：

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/publish_visualization.py --html outputs/visualization_publishing/qwen_v005_all53_compact_download_20261120_01/index.html --name qwen_v005_all53_compact_download_20261120_01 --asset qwen_v005_all_53_compact_offline.zip
```
