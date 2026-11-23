# 在线恢复与原版 · 37 条配对回放

2026-11-22 06:24:16 UTC 发布。[在线回放](http://134.175.18.101/vln/serial_recovery_v002_scene203_paired37_20261122_060956/index.html) · [下载离线回放](http://134.175.18.101/vln/serial_recovery_v002_scene203_paired37_20261122_060956/replay_offline.zip) · [下载配对成绩](http://134.175.18.101/vln/serial_recovery_v002_scene203_paired37_20261122_060956/paired_results.zip)。537 个文件均通过远端 SHA256 核对，公网入口 HEAD 返回 HTTP 200。[发布记录](../../../../../../outputs/visualization_publishing/publish_20261122_062325_745709/publication.json)。

北京时间 2026-11-22 14:09:56（06:09:56 UTC）固定输入。本批计划 203 条，本次快照包含当时已正式评分的 37 条，另列 7 条技术跳过。按实际完成顺序纳入，覆盖 kujiale_0240 和 kujiale_0234。导出读取现有运行文件，后台导航继续独立推进。

| 同一批 37 条 | 成功数 | SR | 平均 SPL |
| --- | ---: | ---: | ---: |
| 在线恢复 v002 | 13 | 35.14% | 0.2850 |
| 原版 StreamVLN | 16 | 43.24% | 0.3533 |

原版失败转成功 3 条，成功转失败 6 条。12 条发生实际回退，共 16 次回退和 15 次交还。7 条技术跳过中，5 条为 JEV HTTP 520，2 条为回退位姿朝向偏差超限。

## 回放口径

当前版本读取每次观测保存的 RGB PNG，共 3,669 帧，含局部纠错与交还观测。原版按同一 episode ID 和派生 seed 配对，从历史视频提取原生前视区域并逐帧匹配当时的位置记录，共 3,425 帧。用于网页回放的图像分辨率为 480×360。两条时间轴独立可调，各自驱动地图上的当前位置。地图与波形标注实际有效节点，在有回退的轨迹上单独画出回退跳跃。事件按钮中的 A 是全程动作序号，F 是本次导出观测序号。复核回答引用的 F 编号沿用当轮导航段原始记录，交还后导航段内编号重新计数。

任务筛选覆盖两组结局及发生回退的任务。事件可定位自然报警、接管前复核、实际回退及交还，回退卡展示存档点三视图、已走和改选支路 ID、局部指令。页面默认中文，支持英文。[补充的展示译文](translations.json)仅用于回放。已在本地浏览器验证 37 组、7 个跳过项、成功转失败筛选、独立帧步进、回退前后跳转、三视图解码和语言切换后任务与帧保持一致。

## 导出记录

运行源码和协议见[父实验](../../README.md)，原始逐条评分见[同批基线](../../baseline203.csv)。导出基于 Git `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 及当前工作区的两个导出脚本与双语页面模板。使用仓库 StreamVLN 环境在 CPU 上执行：

```bash
SNAP=outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956/snapshot.json
REC=experiments/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956
backbone/streamvln/.venv/bin/python -B scripts/export_serial_paired_media.py "$SNAP"
backbone/streamvln/.venv/bin/python -B scripts/export_serial_paired_snapshot.py "$SNAP" "$REC"
```

[本地入口](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956/index.html)及同目录资源已整理为[离线压缩包](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956/replay_offline.zip)，解压后打开 `index.html`。在线版沿用同一入口和静态文件清单。入口 SHA256 为 `9b8bbdff38bef5bc60624038f6d64690239a2af559974bbc8b739029d5c661eb`。
