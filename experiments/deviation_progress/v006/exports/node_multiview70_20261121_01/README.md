# v006 多视角页面新增 ±70° 选项

状态：已发布并更新原网址。用户要求在现有180°／360°视角下拉框加入±70°三视图，沿用节点联动和图片放大。

来源页面为 `outputs/visualization_publishing/v006_node_multiview_web_20261121_01/`。新增图像来自 `outputs/multiview_capture/v006_pose70/run_20261121_01/points/`，376个存档节点、1,128张图，依次显示左70°、正前0°、右70°。角度相对记录的原生相机朝向。终止节点显示该视角未采集提示。

新版本目录为 `outputs/visualization_publishing/v006_node_multiview70_web_20261121_01/`。导出和发布记录在此登记。先发布独立快照，再备份并更新用户当前多视角网址。

[当前网址](http://134.175.18.101/vln/v006_node_multiview_web_20261121_01/index.html) · [独立版本](http://134.175.18.101/vln/v006_node_multiview70_web_20261121_01/index.html) · [离线包（157.9 MB）](http://134.175.18.101/vln/v006_node_multiview_web_20261121_01/v006_node_multiview70_offline.zip)

导出命令为 `backbone/streamvln/.venv/bin/python -B scripts/export_deviation_node_multiview70.py`。新增三图逐节点按 episode_id、节点编号、帧号、原生前视哈希和机器人位置对应，转换时核对1128张原PNG哈希。

定向浏览器检查 `check.cjs` 已通过三种视角切换、双语、同图放大、C50回退目标F15联动以及终止节点缺图提示，记录在导出目录的 `browser_check.json`。发布使用本目录 `publish.py`，复用标准发布器和既有原子入口更新脚本。旧入口备份为 `index_before_pose70_20261121.html`。

发布回执为 `outputs/visualization_publishing/publish_20261121_072447_055469/publication.json`，原入口回执为本目录 `publication.json`。9477个资源校验通过，原入口新增1130个资源，HTTP 200。HTML SHA256为 `13be0d93cebe58b650dbf4abd36e60c4cdace7a87ba9d4665d970278a0943412`，ZIP大小157930752字节。实际Git版本、工作区状态、来源和源码哈希记录于导出目录的 `export.json` 和 `source_snapshot/`。
