# 在线恢复 v002 · 偏航与回退事件回放

冻结于 2026-11-22 07:32:48 UTC。203 条批次中纳入当时全部 41 条唯一正式评分任务，7 条技术跳过单列。两组按 episode ID 与派生 seed 配对，run seed 为 2。

| 版本 | 成功 / 已评分 | SR | 平均 SPL，含失败 |
| --- | ---: | ---: | ---: |
| 在线恢复 v002 | 15/41 | 36.59% | 0.3019 |
| 原版 StreamVLN | 17/41 | 41.46% | 0.3411 |

298 次节点判断，27 次接管前复核。51 次节点报警中，18 次实际回退，8 次选路为空，3 次选路校验失败，6 次复核改判一致，1 次复核无效，15 次随任务终止。回退涉及 14 条任务，其中 17 次交还原策略。

## 地图和模型证据

任务选择器显示配对结果。地图使用帧和导航段关联每次事件，A 为上次可信节点，B 为被评审的节点，R 为给出判断的位置，G 为接管前复核，P 为实际回退前，T 为目标存档位置，L 为回退后实测落点，H 为交还位置。末次局部观测可在未交还的事件中查看。相同位置的事件标记使用引线。事件附近和全程可切换，点击标记可查看该帧。节点清单只使用去重后的有效节点及协议终止节点，区分可信存档与实际回退目标。

橙色区间来自实际评审输入首末帧。红色区间从模型判为偏航的节点起，到同段下一节点、回退前或结束。跳转和局部纠错按真实事件分别绘制。评审区间提供实测动作数和距起点最大水平偏移。目标距离字段按当前回放 XY 和参考终点计算；几何信息用于复核。模型的“已走”“选中”及其图像证据属于当轮输出，物理轨迹、交还和最终评分单列。返回空支路、复核撤销和被拒的选择均可逐条查看。

Recovery 的第一次选路使用存档点三向图与 +2/+5/+8/+10 前视，第二次使用同一存档点三向图。模型完成选路且通过校验之后才执行物理回退。页面在同一事件内展示模型列出的全部入口、对已走支路的判断、所选支路、原指令和之后的实际动作。英文与中文展示逐次关联。点击支路证据可放大对应输入图。两次运行各用自身时间轴。

## 来源与导出

[本地页面](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_01/index.html) · [冻结清单](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_01/snapshot.json) · [配对实验](../../README.md) · [支路译文](branch_translations.json) · [任务与指令译文](translations.json)。

基于 Git `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 与当时工作区的导出源码。已有 37 条的 RGB 图集复用，新增 4 条由媒体导出器在 CPU 上编码。新目录中执行配对与事件导出。冻结清单 SHA256 为 `dd36b266a0b33fe54f41c2fd88a1562bf5cb87600257a5a933f8796b7528921a`。

```bash
OUT=outputs/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_01
REC=experiments/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_01
backbone/streamvln/.venv/bin/python -B scripts/export_serial_paired_media.py "$OUT/snapshot.json"
backbone/streamvln/.venv/bin/python -B scripts/export_serial_paired_snapshot.py "$OUT/snapshot.json" "$REC"
backbone/streamvln/.venv/bin/python -B scripts/export_online_recovery_answers.py "$OUT" "$REC" "$REC"
```

本地浏览器已核对回退前后帧、地图/RGB 同步、分支证据图放大、语言切换、独立图层、有效节点跳转、两次不同的选路结果、校验拒绝、无报警任务与手机页面宽度。

| 工作区源码 | SHA256 |
| --- | --- |
| core/serial_recovery_answers.html | `627fd35a2c9142fce7ddbe1999407dc50dc726aab3836ca751a6dc4682fd3569` |
| core/serial_recovery_answers.css | `21f019b7697ad4287055e029e0b5589c1e61d22fad35140e917c119ce7867d1b` |
| core/serial_recovery_answers.js | `c2283f7d893b04426e962e7a84ba79bf48589814f605b7c7c408e7e8eaefe367` |
| scripts/export_online_recovery_answers.py | `cf234cf2e6d933d714036d989a2d8709cdfd1318b139edf803fa9a87f008b648` |

## 发布

2026-11-22 07:44:48 UTC，[打开事件回放](http://134.175.18.101/vln/serial_recovery_v002_scene203_events41_20261122_01/index.html) · [完整离线包](http://134.175.18.101/vln/serial_recovery_v002_scene203_events41_20261122_01/replay_offline.zip) · [发布记录](../../../../../../outputs/visualization_publishing/publish_20261122_074353_370942/publication.json)。807 个文件通过远端 SHA256 校验，公网入口 HEAD 返回 200。入口 SHA256 为 `2fd2c347017de907fc2e79385b31e6f230cba138603a29ccca8d59f7227b0f10`。
