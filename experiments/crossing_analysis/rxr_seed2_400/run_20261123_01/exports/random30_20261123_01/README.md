# RxR-CE 错选支路随机 30 例回放

2026-11-23 UTC，从[逐例归因](../../attribution.csv)中选取明确错选的三类，含正常 STOP 和限步终止。按 episode ID 的数值排序，以 Python Random(2) 无放回抽取 30/80 条，顺序沿用抽取顺序。只读取已评分的原始采集与既有审阅结论。页面按动作边界回放 RGB 与轨迹，默认定位在原归因的决策步，可跳至确认步。

[打开回放](http://134.175.18.101/vln/rxr_crossing_random30_20261123_01/index.html) · [抽样清单](sample.json) · [逐条译文](translations.tsv)

8 个场景，30 条轨迹，共 4,465 帧，含初始和终止观测。走错通道分支 11 条、进错门或房间 10 条、漏掉转弯或楼梯入口 9 条。28 条执行 STOP、2 条耗尽步数。公开回放采用 640×480 JPEG 预览，原始 PNG 保留于采集目录。地图显示决策步高度的可行走网格，其他高度的路径以虚线显示。当前版即原版，完整原始批次双方 SR 均为 224/389（57.58%），平均 SPL 均为 0.4915，技术异常 11 条；本次抽样的 30 条均来自正式评分失败。

使用 StreamVLN 环境先后运行 `scripts/export_rxr_branch_replay.py media` 和 `scripts/export_rxr_branch_replay.py build`。基线提交 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。[源码快照及哈希](../../../../../../outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/exports/random30_20261123_01/source/versions.json) · [本地 HTML](../../../../../../outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/exports/random30_20261123_01/index.html) · [在线静态资源清单](../../../../../../outputs/crossing_analysis/rxr_seed2_400/run_20261123_01/exports/random30_20261123_01/online_manifest.json)。

2026-11-23 07:26:36 UTC 发布完成。HTML SHA256 为 `ab34cb638fd683bc8ec4ec5c5fc5dc2c7eab4e1a3dc58bda4f480f5c877650f4`。本地浏览器核对 30/30 个案例的决策与确认帧，双语切换、地图与 RGB 进度、播放及图层通过检查。远端 544 个文件通过 SHA256 校验，公网入口直连 HEAD 返回 HTTP 200。[发布回执](../../../../../../outputs/visualization_publishing/publish_20261123_072529_466512/publication.json)
