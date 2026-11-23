# 回退快捷定位与可缩放俯视图

沿用[事件回放 01 的冻结输入和译文](../event_diagnosis_20261122_01/README.md)。2026-11-22 07:32:48 UTC 快照，seed 2，正式评分 41 条。当前版 SR 15/41（36.59%）、平均 SPL 0.3019。同 ID、同派生 seed 的原版 SR 17/41（41.46%）、平均 SPL 0.3411。7 条技术跳过另计。复用已导出的逐帧数据、配对成绩、模型原答及媒体。

地图进度条下按任务内实际回退顺序列出每一次回退。点击后切换至当前版本和对应评审，并将地图、RGB 同步定位到回退后的实测落点。若回退期间结束且缺少落点观测，按钮会标注并定位存档帧。未执行回退的任务显示“本任务无实际回退”。

每次打开新任务时默认适配完整底图。可用滚轮、加减按钮或双指缩放，单指或鼠标拖动平移。“完整底图”“适配全程”“定位当前事件”可以随时重新定位，逐帧播放和语言切换保留手动视角。

沿用上版 Git 基线 `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 与当前工作区的 `core/serial_recovery_answers.html`、`.css`、`.js`。在新目录复用冻结数据及图集，使用下列命令重建页面和离线包。

```bash
OUT=outputs/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_02
PREV=experiments/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_01
backbone/streamvln/.venv/bin/python -B scripts/export_online_recovery_answers.py "$OUT" "$PREV" "$PREV" --reuse-answers
```

本地浏览器验证了 `kujiale_0234_27_4` 三次回退分别跳至 F81、F153 和 F236，同步进度条及评审事件。另核对了无回退任务、整幅底图边界、滚轮缩放、鼠标拖动、加减控制、手机触控缩放，以及帧步进和切换语言后视角的保持。

## 发布

2026-11-22T07:58:28.561856+00:00，[新版网页](http://134.175.18.101/vln/serial_recovery_v002_scene203_events41_20261122_02/index.html) · [三次回退示例](http://134.175.18.101/vln/serial_recovery_v002_scene203_events41_20261122_02/index.html?case=kujiale_0234_27_4) · [本地源页面](../../../../../../outputs/serial_recovery/v002/run_20261121_06_scene203/exports/event_diagnosis_20261122_02/index.html) · [发布记录](../../../../../../outputs/visualization_publishing/publish_20261122_075732_735739/publication.json)。807 个文件远端 SHA256 通过，公网入口 HEAD 返回 200，入口 SHA256 为 `f47e45fb0c90e7114afb0a8a9ed6bb4b72c9666b15941acff2e25241d5d5a240`。

- core/serial_recovery_answers.html SHA256 `38bcd7487f3bb48ca2537d3bcfbfdc4ae255a9d9a407fe82178613893644910c`
- core/serial_recovery_answers.css SHA256 `a64cef3dd61055caefcb6546250ab1eeec051ae1718015fe7ebe95f7e7320099`
- core/serial_recovery_answers.js SHA256 `44b7d5b0caed3d7a438413a92fbf00b8d2ba6c0bdfe743366c04a6952472927d`
