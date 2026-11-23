# 串行联调02双语回放：发布版

更新时间：2026-11-16T07:09:00.988120+00:00。状态：已发布。

## 目的与范围

用户要求导出当前单条联调。仅CPU读取现有结果，无新模型调用或仿真，不改变保留的GPU服务。包含40帧实际观测、40次JEV、7次建点、6次去重、7次偏航评审，以及历史原始/正确参考/本次实际轨迹和历史人工C点。地图、参考路线和人工点仅为事后展示。

任务失败、NE 8.543米；5次consistent均为A=B初始化，2次非零路段评审为uncertain。0次回退、0次纠错、0次记忆交还，完整恢复闭环未验证。终止后独立RGB未采集，末帧明确标为STOP前画面。

## 版本与来源

Git基线：7ce5f9fee30686bae304425bc84c36b3fbedc39c，有未提交改动。入口`scripts/export_serial_replay.py`，模板`core/serial_replay.html`，展示翻译`core/serial_replay_translations.json`、`core/serial_replay_dedup_prompt_en.txt`。源码副本、逐源文件哈希、原请求和RGB哈希核验在导出目录`build.json`。本地准备版01保留；截图复核修正语言控件对比度和地图标签后另建02，不覆盖旧HTML。

## 生成与验证

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_serial_replay.py --campaign outputs/serial_recovery/v001/run_20261116_02 --output outputs/serial_recovery/v001/run_20261116_02/exports/replay_20261116_02
node scripts/check_serial_replay.cjs outputs/serial_recovery/v001/run_20261116_02/exports/replay_20261116_02/serial_pipeline_replay.html outputs/serial_recovery/v001/run_20261116_02/exports/replay_20261116_02/browser
```

本地浏览器通过40帧、53次请求、106个双语视图、7次节点跳转、双进度条、因果状态、完整提示词、原始记录、输入图片解码、放大/播放/地图图层、复核意见/40行CSV导出及390像素移动端检查；无JS错误、无外部请求。截图在`browser/`，验证`browser/validation.json`。

## 发布

网址：[http://134.175.18.101/vln/serial_pipeline_v001_run02_web_20261116_01/serial_pipeline_replay.html](http://134.175.18.101/vln/serial_pipeline_v001_run02_web_20261116_01/serial_pipeline_replay.html)

离线HTML：`outputs/serial_recovery/v001/run_20261116_02/exports/replay_20261116_02/serial_pipeline_replay.html`，SHA256：`5eb0b7deeb978c20305857e1ef302f2272e22640bb27b02da2dc134dff5d3fe8`。

在线目录：`outputs/visualization_publishing/serial_pipeline_v001_run02_web_20261116_01/`。按标准流程拆分图片/字体，共42个资源，另附`FONT_LICENSE.zip`，连同入口共44个文件。前两次发布准备分别因资源字典与列表拼接、TXT后缀不被发布器支持而在上传前停止；修正为遍历字典键及许可证ZIP后，标准发布成功。

发布记录：`outputs/visualization_publishing/publish_20261116_070753_146427/publication.json`。全部远端SHA256通过、公网入口HTTP 200；未声称在线浏览器验证，交互验证为本地浏览器。无需重跑实验。
