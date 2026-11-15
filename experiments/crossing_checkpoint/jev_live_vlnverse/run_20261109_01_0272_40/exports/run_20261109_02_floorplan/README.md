# StreamVLN + 实时 JEV 40 条：真实俯视户型图修订版

更新时间：2026-11-09（UTC）
状态：本地浏览器验证通过，已发布

## 修订原因

首发页面只有坐标网格和轨迹，没有场景户型底图，不能称为完整俯视地图。
本版复用仓库既有 `scripts/build_checkpoint_review.py extract` 方法，从
`kujiale_0272/start_result_navigation.usd` 的 USD 世界空间网格中裁剪墙高带、
正交投影并栅格化，生成真实 `floorplan.png` 与 `geometry.json`，没有运行导航或模型。

## 地图与页面

- floorplan：`outputs/crossing_checkpoint/jev_noul_v004/vlnverse_live_0272_40/maps_cpu/run_20261109_01/scenes/kujiale_0272/floorplan.png`
- floorplan SHA256：`713793157a47d23655860564f2363cd820a71773da723172379e5ee3f7dd3247`
- geometry SHA256：`2d9edeeb1d6f95def3802a455099dd611e750f879f86154ec5e96a7dc046c88b`
- geometry尺寸：`365×345`，分辨率`0.035m/pixel`
- 坐标变换沿用旧方法：`u=(x-low_x)/resolution`、`v=(high_y-y)/resolution`
- 40条实际轨迹、参考路线、215个采样节点均绘制在该户型图上；
- 页面仍含2878帧RGB、2878次JEV概率、API延迟、中英文任务和prompt。

## 文件与验证

- HTML：`streamvln_live_jev_0272_40.html`
- HTML SHA256：`a258a992c9e2d37b5ea58ac2f96ae28579ee11e4086260c12790a2aa8c68c1ee`
- 浏览器证据：`browser_verification.json`
- Chromium核验：40条、2878帧、2878回答、215节点、户型图非空像素50871、
  节点开关、双语、复核导出和移动端通过；页面错误0、外部请求0。

## 发布

在线入口：

http://134.175.18.101/vln/streamvln_live_jev_0272_40_floorplan_20261109_02/streamvln_live_jev_0272_40.html

- 在线目录：`outputs/visualization_publishing/streamvln_live_jev_0272_40_floorplan_20261109_02`
- 在线HTML：1,756,305字节
- 在线HTML SHA256：`4b34ecbc2ec769d2018ca4460402a597e1a825fa4f8bd8553140d854511dc6d8`
- 发布记录：`outputs/visualization_publishing/publish_20261109_104010_530135/publication.json`
- 全部2880个文件远端SHA256通过，入口HTTP 200、`text/html`
