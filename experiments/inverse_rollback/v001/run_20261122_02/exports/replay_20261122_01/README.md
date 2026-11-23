# 30 例物理回退的地图与第一人称回放

采用[运行 02](../../README.md)已完成的 30 组配对记录。逆动作达标 4/30（13.33%），平均水平误差 1.125 米，平均朝向误差 47.08°。直接 reset 达标 30/30（100%），平均水平误差 0.0177 米，平均朝向误差 0.46°。整条导航的 SR 与平均 SPL，两组均为暂无，已评分 0 条。

第一人称观测只展示历史去程 A→B 已保存的原生 RGB，包括报警点 B。逆动作阶段显示实测逐动作轨迹、当前位置和朝向。直接 reset 显示从 B 到实际落点的虚线。两组回退均未保存 RGB，页面在对应步显示缺失提示。已按用户要求停止补绘，发布内容仅包含实测记录。地图支持缩放、平移、线宽调节和机器人朝向开关。

从仓库根目录导出：

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_inverse_rollback_replay.py outputs/inverse_rollback/v001/run_20261122_02/exports/replay_20261122_01
```

2026-11-22T15:43:32+00:00 UTC 已发布[实测回放](http://134.175.18.101/vln/inverse_rollback30_measured_20261122_01/index.html)。30 例、16 个场景、552 张历史前视、1,038 个实测逆动作。线宽、缩放、朝向开关、双语和缺图提示通过本地浏览器检查。远端 SHA256 与公网 HTTP 200 通过。[离线源页面](../../../../../../outputs/inverse_rollback/v001/run_20261122_02/exports/replay_20261122_01/index.html)，SHA256 为 `65b89083d91da31b9e82faba0051f3f1c9b5338dda2715ef717f87590e1e50a3`。[发布记录](../../../../../../outputs/visualization_publishing/publish_20261122_154303_635072/publication.json)。
