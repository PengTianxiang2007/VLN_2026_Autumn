# 无全景版：完整录像、地图同步进度条与Crossing跳转

2026-11-06，已完成导出与浏览器验证。用户要求将上一版无全景选路可视化改为v002的直观布局，并提供可拖动的地图/观测同步进度条，以及一键跳转当前Crossing的按钮。

固定复用v001原十条Qwen32B的20份响应和既有中文译文，不运行模型、仿真或导航。第7条同时排除和选择B1的矛盾保留。GLM原批无有效回答，不补造结果。原两版HTML及v002全景版均保留。

数据来自preparation_20261106_04/provenance.json绑定的十份原始seed2录像与steps.jsonl，共737帧。显示完整原始导航历史，地图路线截至当前帧，区分Crossing前、已标注错误尝试和原录像后续；后续画面不代表外部Agent建议执行后的结果。原80张模型输入PNG按哈希及解码像素复核，其余回放帧压缩为JPEG用于展示。

Crossing按钮严格跳到每条dataset.json的checkpoint_frame，即两次请求共同使用的当前观测帧P。地图保留人工标定C与原存档P，不把略有偏差的C位置当作录像存在另一帧。旧录像未记录相机姿态，地图不凭位移推测真实相机朝向，支路方向仍相对于固定判断帧。

新代码：scripts/export_agent_route_timeline.py、core/agent_route_timeline_page.html、core/agent_route_timeline_review.js；复用v002页面CSS并保留来源哈希。计划输出outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_03/crossing_v001_timeline_zh.html。

```bash
backbone/streamvln/.venv/bin/python scripts/export_agent_route_timeline.py --output outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_03
```

验证重点：十条全部逐帧拖动更新真实画面/地图位置/已走路线；地图和RGB下的进度条双向同步；任意位置按按钮精确回到对应Crossing帧及原始PNG；播放暂停、证据跳转、语言切换、样本切换、复核导出和移动端布局。保存实际Git提交、未提交源码快照、源录像/轨迹及模型响应哈希。


## 交付与验证

- [新版单文件HTML](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_03/crossing_v001_timeline_zh.html)，55.37 MiB，断网可用。
- [Crossing首屏截图](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_03/preview_crossing.png)。
- [回放其他帧截图](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_03/preview_replay.png)。
- [第7条原始矛盾截图](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_03/preview_case07.png)。
- [逐帧浏览器验证](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_03/browser_check.json)。
- [轻量摘要](summary.json)。

默认打开每条Crossing原始判断帧，首屏地图和画面下方各有同步进度条。拖动任意一条会暂停播放、更新对应原始帧、地图实际位置和截至该帧的路线；按钮“回到Crossing”从任意位置精确跳回对应checkpoint_frame并暂停。另提供逐帧前后、播放速度、错误片段末帧和模型关键帧跳转。

实际浏览器逐帧检查全部737帧：左右滑条值一致，观测图像逐帧匹配，轨迹前缀长度及当前位置匹配，并按地图世界坐标投影逐帧读取紫色位置标记的真实画布像素。十条Crossing跳转均与原模型输入PNG完全一致；语言切换保持进度，返回按钮暂停播放，31条支路、10个实际选择和第7条矛盾均保留。桌面与手机布局、图片放大、复核意见导出通过，外部网络请求0、JS错误0。已查看真实首屏和第7条截图。

原80张模型输入与对应录像解码帧逐像素一致；20份中文译文与原响应哈希绑定且不改结构。旧两版v001 HTML和v002全景HTML的前后哈希均一致。源码、实际Git提交、未提交差异、视频/steps来源哈希保存在输出审计中。本次仅CPU导出，无模型、仿真或导航调用。

下一步仅等待用户审阅；不因展示更新重启任何实验。
