# 原版成功、当前失败的配对回放

2026-11-22 09:35:33 UTC 冻结运行中的 203 条批次，以唯一 episode ID 和派生 seed 匹配 seed 2 原版。47 条取得正式评分，8 条技术跳过，1 条在途。与上版相比多评分 6 条，均为两版失败。此次筛出 6 条原版成功、当前失败的任务。回放使用这批任务实际运行时冻结的代码。主策略 STOP 前评审属于后续运行协议。

| 范围 | 当前版 SR | 当前版平均 SPL | 原版 SR | 原版平均 SPL |
| --- | ---: | ---: | ---: | ---: |
| 全部配对评分 | 15/47（31.91%） | 0.2634 | 17/47（36.17%） | 0.2976 |
| 本页筛选结果 | 0/6（0%） | 0.0000 | 6/6（100%） | 0.8398 |

6 条任务共 45 次节点评审、8 次偏航报警、5 次两阶段选路、3 次实际回退及 3 次交还。任务菜单、顶部指标、配对 CSV、模型原答和离线包均以这 6 条为范围。保留上一版的中英切换、地图缩放、逐次回退跳转、两版轨迹和支路证据。

从项目根目录执行下列命令可在新的导出目录生成这一类回放。源代码基于 Git `7ce5f9f` 与工作区新增的筛选导出器，任务、纠错指令和支路译文沿用上一版。

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_serial_paired_losses.py \
  outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_losses_20261122_01 \
  experiments/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_01
```

[冻结清单](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_losses_20261122_01/snapshot.json) · [本地回放](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/paired_losses_20261122_01/index.html)

2026-11-22 09:41:19 UTC 发布。130 个静态文件的远端 SHA256 校验通过，入口公网 HEAD 为 200，入口 SHA256 为 `f47e45fb0c90e7114afb0a8a9ed6bb4b72c9666b15941acff2e25241d5d5a240`。本地浏览器核对了 6 条的筛选条件、指标和双语任务内容，以及点击回退后切换语言时的事件和帧。[公开页面](http://134.175.18.101/vln/serial_recovery_v002_scene203_paired_losses_20261122_01/index.html) · [发布记录](../../../../../../outputs/visualization_publishing/publish_20261122_094109_882083/publication.json)
