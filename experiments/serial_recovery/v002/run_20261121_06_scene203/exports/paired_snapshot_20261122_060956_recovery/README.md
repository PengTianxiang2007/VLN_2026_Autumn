# 37 条配对回放与逐次模型原答

2026-11-22 07:12:07 UTC 发布。[打开在线回放](http://134.175.18.101/vln/serial_recovery_v002_paired37_model_answers_20261122_01/index.html) · [逐次模型原答 JSON](http://134.175.18.101/vln/serial_recovery_v002_paired37_model_answers_20261122_01/answers.json) · [完整离线包](http://134.175.18.101/vln/serial_recovery_v002_paired37_model_answers_20261122_01/replay_offline.zip)。721 个文件通过远端 SHA256 校验，公网入口 HTTP 200，入口 SHA256 为 `d08a489084981370ccd2e499acb4b851f636925f01ed889cd55d36355fa9c36b`。[发布记录](../../../../../../outputs/visualization_publishing/publish_20261122_071115_681111/publication.json)。

沿用 11 月 21 日北京时间 20:28 发布的[两阶段 Recovery 回放模板](http://134.175.18.101/vln/recovery_instruction_v001_paired47_web_20261121_01/index.html)。左侧选任务，中栏按动作顺序选报警、复核和两阶段回答，右侧可切换原版或当前版的 RGB，并与俯视图同步定位。每个任务选项同时标记原版、当前版是否成功。

## 快照与成绩

使用[已冻结的 37 条配对任务](../paired_snapshot_20261122_060956/README.md)，seed 2，快照时间为 2026-11-22 06:09:56 UTC。两组分别为当前在线恢复和相同任务、相同 seed 的原版 StreamVLN。7 条技术跳过另列。当前版 SR 为 13/37（35.14%）、平均 SPL 为 0.2850；同批原版 SR 为 16/37（43.24%）、平均 SPL 为 0.3533。3 条失败转成功、6 条成功转失败。

## 逐次输出与执行

共 348 条模型回答，来自 271 次节点判断、25 次接管前复核和 26 组两阶段调用。每项保留该次 `response.json` 中完整的 `choices[0].message.content`，逐次关联校验状态、任务 ID、导航段、动作计数以及本次的输入图像。中英文均能查看支路入口描述、判断依据、已走支路、备选指令和不确定性。[支路译文](branch_translations.json)用于网页显示。

| 47 次有效节点报警的去向 | 次数 |
| --- | ---: |
| 执行回退并启动局部导航 | 16 |
| 第二次调用返回空支路及空指令 | 7 |
| 第二次调用所选支路未通过校验 | 3 |
| 接管前复核改判一致 | 6 |
| 接管前复核回答无效 | 1 |
| 任务终止时结束 | 14 |

每次选路可查看第一次调用的七张实际输入、全部候选支路及依据，再查看第二次调用的所选 ID 和模型返回的完整局部英文指令。局部策略的执行单独按日志展示动作和 STOP 或终止情况。16 次实际回退出现在 12 个任务中，其中 15 次交还原策略，1 次在局部导航期间任务终止。展开原答可看到无效回答，以及唯一一条在生成中断时已经返回的文字。原答中的 F 编号遵循模型当轮使用的导航段，网页跳转按钮中的 F 是整条回放的观测序号。

示例 `kujiale_0240_28_4` 的第一次调用识别出 B1 为正前走廊、B2 为左侧卧室，模型判定已经走进 B2。第二次调用改选 B1，输出 “Turn right to face the hallway with the framed picture on the left wall.”。实际回退目标为 F73，局部策略执行 33 个动作后发出 STOP 并交还原任务。两版最终均未到达目标。

## 导出与验证

Git 基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，本次使用工作区中的 `scripts/export_online_recovery_answers.py`、`core/serial_recovery_answers.html`、`core/serial_recovery_answers.js` 以及归档模板样式。新输出目录保留源快照的 `snapshot.json`、`media_index.json`、`data.js`、配对成绩和 RGB 图集、地图。命令读取快照列明的在线导航 attempt 和本次展示译文，仅做离线导出。

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_online_recovery_answers.py \
  outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_recovery \
  experiments/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_recovery \
  experiments/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956
```

本地浏览器核对了 37 个任务选项、有实际回退的两次模型回答、七张图的解码、原版切换和地图帧定位、中英文在同一帧切换，以及空选择、被拒绝的选路和不完整原答的展示。[本地网页](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_snapshot_20261122_060956_recovery/index.html)。
