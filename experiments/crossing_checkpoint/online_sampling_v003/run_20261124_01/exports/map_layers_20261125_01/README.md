# JEV 采样点与 Astra 参考点的地图图层

来源为 v003 的 42 条轨迹本地双语回放，含 20 条设计轨迹和 22 条验证轨迹。沿用上次冻结结果和原有位置坐标。图层包括 v001 原版、v002 保守 / 均衡 / 精简、v003 覆盖优先 / p60 / p70 / 严格，以及 GPT-6 Astra v006.1 最终保留的参考点。

地图上方的图层可单独或组合开关。相同显示位置的不同版本分扇区绘制，Astra 使用独立紫色菱形描边；指针悬停可读出版本、编号和帧。红圈标记当前回放位置。打开时选中 p60 和 Astra，支持中文 / English。同一版本在同一投影位置的多次到访保留全部帧号。候选轨迹间 ±3 步的匹配口径不参与地图合并。浏览器用 C42 核对了全部九层的绘制帧、重叠显示、单独关闭参考、全部关闭、仅开参考和语言切换。

导出命令：`python3 -B experiments/crossing_checkpoint/online_sampling_v003/run_20261124_01/exports/map_layers_20261125_01/export.py`。新目录保留历史回放，本地 ZIP 包含网页、前视图、地图和字体许可证，解压后打开 index.html。

[本地网页](../../../../../../outputs/crossing_checkpoint/online_sampling_v003/run_20261124_01/exports/map_layers_20261125_01/index.html) · [完整离线 ZIP](../../../../../../outputs/crossing_checkpoint/online_sampling_v003/run_20261124_01/exports/map_layers_20261125_01/jev_sampling_map_layers.zip)。42 条轨迹引用的 3309 项图像资源均可在包内找到。ZIP 大小 53,496,610 字节。网页 SHA256 为 `0e7e50eceb7096a1a4aff189228546935fd03098897c63b2eb7fe636046771a9`。

## 公网发布

2026-11-25T05:43:39.711854+00:00 按用户要求发布[九图层回放](http://134.175.18.101/vln/jev_sampling_astra_map_layers42_web_20261125_01/index.html)，版本 jev_sampling_astra_map_layers42_web_20261125_01。在线源由上述离线 ZIP 中的 index.html 拆分，在线入口 SHA256 为 `c1020fe6c27fd62abf769b09a43d2c9f82e10d201fc36511b5f3dfc02b9711ee`。3312 个文件远端 SHA256 核验通过，公网入口 HEAD 返回 HTTP 200、text/html，大小 1428428 字节。九层交互沿用已记录的本地浏览器核对。

[发布记录](../../../../../../outputs/visualization_publishing/publish_20261125_054253_219111/publication.json) · [在线包清单](../../../../../../outputs/visualization_publishing/jev_sampling_astra_map_layers42_web_20261125_01/online_manifest.json)
