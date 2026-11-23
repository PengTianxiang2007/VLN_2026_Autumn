# Qwen27B 前 31 条轨迹去重回放

[打开在线回放](http://134.175.18.101/vln/qwen27b_route31_dedup_v001_web_20261118_01/index.html)。2026-11-18 08:39:14 UTC 发布，2,616 个远端文件哈希通过，公网入口 HTTP 200。[本地浏览器验收](browser_online_package.json)逐轨迹核对了全部比较的理由、证据与节点显示。发布记录为 `outputs/visualization_publishing/publish_20261118_083846_681204/publication.json`。离线 HTML 的 SHA256 为 `25912d6c6f3d1372f32aeafc875ba83f0ec9c7e490875bcbe2dd1ccab40371c0`，相邻离线压缩包 `qwen27b_first31_dedup_offline_01.zip` 的 SHA256 为 `3e5829a66836cfbd85bd299443e23827166979bcd57cd66d16b6fc431b2ce54d`。

选取 2026-11-18 08:24 UTC 进度检查时已完整结束去重的 C01–C31，共 11 个场景、2,602 个已评分原生前视帧。每条结果的路径、SHA256、保留节点和本批计数已写入[快照](snapshot.json)。270 个候选经 191 对比较后保留 204 个、删除 66 个；3 对不确定均保留。采用十场景 DeepSeek 回放的模板，本页展示 Qwen 原答。

主开关默认显示去重后节点，关闭后恢复原始候选。逐候选查看判定、理由、分支对应和两组前视证据。中文保留模型原答，英文译文按固定文本序列及其摘要校验。[展示译文](review_en.txt)

离线目录为 `outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/first31_dedup_01/`。线上包目录为 `outputs/visualization_publishing/qwen27b_route31_dedup_v001_web_20261118_01/`，入口 SHA256 为 `bc377215c7bb29a4fae1970a4e4a43d3f70bf65fc9673610e244e1833f1bc628`。导出入口为 `scripts/export_route53_deepseek_dedup.py --snapshot <本目录>/snapshot.json --offline <离线目录> --online <线上包目录>`。
