# 37 条配对回放 · 地图图层版

2026-11-22 06:40:53 UTC 发布。[在线回放](http://134.175.18.101/vln/serial_recovery_v002_scene203_paired37_maps02_20261122/index.html) · [下载离线包](http://134.175.18.101/vln/serial_recovery_v002_scene203_paired37_maps02_20261122/replay_offline.zip)。[本地入口](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_map02/index.html)与同目录资源组成在线版。537 个文件通过远端哈希核对，公网入口 HEAD 返回 200，入口 SHA256 为 `78d7b17ef17387b6f3065abfd35d4fa87477e5ad391b552ce41ee60ecc0093f8`。[发布记录](../../../../../../outputs/visualization_publishing/publish_20261122_064006_586866/publication.json)。

本地浏览器核对了 37 个选择项的双版本标记、筛选及双语切换，验证独立图层、点击区间定位、地图和当前 RGB 进度同步。实际节点偏航标记中，17 个区间有同段下一节点，16 个在下一节点前回退，14 个在下一节点前结束（含终止节点自身）；16 个实际局部纠错段均使用局部控制下的观测。

使用[第一版冻结的 37 条及译文](../paired_snapshot_20261122_060956/README.md)。北京时间 2026-11-22 14:09:56 快照，seed 2。当前版本 SR 13/37（35.14%），平均 SPL 0.2850；同一批原版 SR 16/37（43.24%），平均 SPL 0.3533。7 条技术跳过另列。

任务选择器逐条显示原版和当前版本各自的结果。参考仓库串行模板的图层勾选和双进度条，以及偏航多版本回放对判定区间的标色。两版轨迹、参考路线、有效节点与回退点、回退跳转和局部纠错轨迹均可独立开关。地图进度条与当前版本 RGB 逐帧同步。

偏航图层从判为偏航的有效节点的原始观测帧开始，到同一导航段的下一有效节点结束。中途发生回退就截在回退前；任务先结束就截在最后的主导航观测。节点延迟确认不移动区间起点，接管前复核不额外建立节点。另有图层显示模型作出偏航判断所依据的区间（上一个可信节点到本次节点）。局部纠错只绘制回退后由局部策略控制的连续实测位姿。点击高亮段可定位帧及其事件；空心圆为有效节点、菱形为实际回退点、方框为终止节点。

复用冻结的 `snapshot.json`、`media_index.json` 与 RGB 图集，将它们放在独立输出目录 `outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_map02`。使用当前工作区的 `core/serial_paired_snapshot.html`、`core/serial_paired_snapshot.js` 与原导出入口，Git 基于 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_serial_paired_snapshot.py \
  outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_map02/snapshot.json \
  experiments/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956
```
