# v002 统一离线 HTML 导出

状态：2026-11-05已完成。用户要求导出本轮可视化HTML并将进度条放到地图和画面旁；当前推荐版本为run_20261105_03。

只读取已完成的run_20261104_01：五条开发的baseline、r01、r02，以及冻结baseline的十五条验证。使用原报告中已审计的RGB、地图、逐帧输出和评分；不重新推理，不启动仿真，不改变预测或标注。

最终文件：[crossing_v002_dev5_val15_offline.html](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_03/crossing_v002_dev5_val15_offline.html)。大小52,917,753字节（约50.5MiB），复制这一份文件即可离线打开，无需图片目录或服务器。

统一页面默认展示十五条验证，支持切换开发版本、保留同一轨迹和帧位置、地图/RGB联动、误报漏检跳转、七个典型问题入口、RGB大图及本地复核笔记导出。蓝色C为原地图标定，红色P为模型确认当时的机器人位置。所有图像内嵌，重复图像去重；四份历史报告保留。开发三版与独立验证分开展示，不把不同样本的分数差解释为方法变化。

## 数据与检查

四份原报告的SHA256均与原审计记录一致。去重后的1217幅图像覆盖20条独立轨迹、30个轨迹/版本视图、1791个观测；数据展开后逐版哈希与原始报告完全一致，预测、记忆、事件和评分未改。继承原始seed和协议，没有重新采样。

02版实际Chromium133完整检查通过：4个版本、30个轨迹/版本视图、1791条因果数据、76次事件跳转、196次标注点跳转；版本切换保持同帧、笔记隔离与导出、播放/暂停/拖动/键盘、标注层切换、大图、移动端布局均通过。页面错误0、外部网络请求0。03版只调整进度条位置并增加同步控件，数据哈希与02版一致；本次定向浏览器检查见文末，不将02版完整检查冒充03版重测。

- [导出清单与源码哈希](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_02/export_manifest.json)
- [浏览器检查](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_02/browser_validation/browser_verification.json)
- [桌面截图](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_02/browser_validation/01_overview.png)
- [标定与存档对照截图](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_02/browser_validation/02_checkpoint_comparison.png)
- [移动端截图](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_02/browser_validation/04_mobile.png)

首版run_20261105_01功能检查通过，但截图发现现有Noto Sans JP字体缺少“发、验、证、线、检”等简体字，因此保留首版并新建02。最终HTML内嵌文泉驿微米黑子集，覆盖报告中的全部809个汉字；字体与Apache-2.0许可说明一同内嵌。字体包仅从上海交大镜像下载并提取到`Resource_Peng/assets/fonts/wqy_microhei_20261105/`，没有安装系统包或修改共享环境。来源、SHA256、许可和子集源码均有记录。

## 实际构建命令

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_crossing_campaign.py \
  --campaign outputs/crossing_checkpoint/dev5_val15/run_20261104_01 \
  --destination outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_03 \
  --annotations experiments/crossing_checkpoint/v002/visualization_export/annotations.json \
  --font /mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/fonts/wqy_microhei_20261105/wqy-microhei.ttc \
  --font-license /mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/fonts/wqy_microhei_20261105/copyright
```

该目标目录现已存在；重导出应使用新编号。构建入口为`scripts/export_crossing_campaign.py`，新增页面组件为`core/crossing_campaign_panel.html`与`core/crossing_campaign.js`，在原冻结模板上扩展。Git HEAD为`0a805dfcf4457f80300822abb4eff7cabba43aae`；未提交源码的实际快照保存在最终导出目录source中。浏览器检查入口为`scripts/check_crossing_campaign.cjs`，使用已有Chromium/Playwright、显式禁用GPU，完成后正常关闭。

## 2026-11-05 进度条位置调整

状态：已完成，当前推荐03版。将原进度条及播放按钮移至地图正下方，在RGB正下方增加同步进度条；拖动任一进度条、播放、逐步查看、事件跳转和切换版本均使用同一帧状态。样本、seed、预测和评分沿用原导出，旧文件保留。

本次使用上述构建命令，未运行模型或仿真。Chromium133定向检查通过：四个版本的30个轨迹/版本视图均确认帧号、两条进度条、RGB与原始回答一致；实际鼠标拖动两条进度条、播放/暂停、拖动暂停、上下步、事件跳转和同帧版本切换均通过。1600、1366、390像素宽度下，进度条容器分别距地图/RGB下边缘10像素，无水平溢出。页面错误和外部请求均为0；桌面和移动端截图已查看。未重复执行与布局无关的笔记导出等02版检查。

- [03版导出清单与源码哈希](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_03/export_manifest.json)
- [03版进度条检查](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_03/browser_validation/playback_verification.json)
- [桌面地图与画面同步进度条](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_03/browser_validation/playback_1366_map.png)
- [移动端画面进度条](../../../../outputs/crossing_checkpoint/dev5_val15/run_20261104_01/exports/run_20261105_03/browser_validation/playback_390_image.png)

后续修改继续使用新导出编号；本次无待运行任务。

2026-11-05用户进一步指定03版为以后每轮迭代的默认模板，已独立保存到core并接入统一导出入口，见[模板规范](../../../../docs/CROSSING_VISUALIZATION_TEMPLATE.md)与[固化记录](../../visualization_template/README.md)。历史03版HTML保持原样；当前通用合并入口默认文件名为 `crossing_review_offline.html`，若需沿用上述历史文件名，可显式传入 `--filename crossing_v002_dev5_val15_offline.html`，仍须使用新目录。
