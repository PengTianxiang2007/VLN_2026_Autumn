# 53 条选路错误离线回放

状态已发布，完成时间为 2026-11-18 05:36:48 UTC。[打开回放](http://134.175.18.101/vln/offline_route53_replay_web_20261118_01/index.html)

发布版本 `offline_route53_replay_web_20261118_01` 直接复用本地已按步拆分的静态文件及 `online_manifest.json`。4,915 个文件全部通过远端 SHA256 核验，入口公网直连返回 HTTP 200。本地入口 SHA256 为 `d642bc216840f24a49d5538e00485cda1cc4dd1cb96132b34f6ae8e8062addd6`。发布记录位于 `outputs/visualization_publishing/publish_20261118_053549_090839/publication.json`。

2026-11-18 开始导出。使用 seed 2 的已封存 53 条入选轨迹、54 个标定事件和 4,890 个观测时刻。按世界 XY 投影到原场景底图，分别控制实际路线与参考路线，记录位姿、方向与图像的同帧关系。源码基线为 7ce5f9fee30686bae304425bc84c36b3fbedc39c，导出代码及模板为本次工作区新增内容。

从仓库根目录执行：

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/export_offline_route_replay.py media
backbone/streamvln/.venv/bin/python -B scripts/export_offline_route_replay.py page
```

本地入口为 `outputs/offline_route_dataset/v001/run_20261118_01/exports/replay_20261118_01/index.html`。离线使用时完整保留同目录的资源，可直接在浏览器打开。地图以场景几何的分辨率、左边界及上边界将世界 XY 映射到同一张底图，显示蓝色实线实际轨迹和绿色虚线参考轨迹。两个图层默认勾选，各自包含相应终点标记。橙色箭头按该步机器人真实位置和朝向绘制。两个进度条联动，支持播放、逐步前进后退和跳至决策或确认步。界面、53 条任务指令和 53 份标定理由均可切换中英文。

网页为每个观测时刻保存一个 3×3 WebP 图集。每个视图为 320×240，第一格是原生前视，接下来的八格按原始 360° 视图 ID 排列。180° 选择相对当步朝向的 +45°、0°、−45°。可点击缩略图放大当前方向。数据集中的 640×480 原始 PNG 和标签在封存目录保留。

验证覆盖 53 条任务、54 个事件和 4,890 个观测时刻。4,890 张图集全部解码通过。浏览器逐例检查双语指令和理由、事件定位、地图与观测步数、一键播放和窄屏布局，并验证图层开关的四种组合。实际与参考路线的开关在切换任务后延续已有选择。详见[本地验收及版本哈希](validation.json)。独立导出源快照、桌面截图及检查结果位于输出目录同级的 `replay_20261118_01_checks/`。
