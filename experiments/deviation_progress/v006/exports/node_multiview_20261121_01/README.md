# v006 存档节点 180° / 360° 多视角

状态：2026-11-21 03:02:31 UTC 已发布。用户已确认：在现有五版本页面上，为全部去重后保留的存档节点增加历史多视角，突出 v006 指定的回退目标，终止节点单独标注。

[打开多视角页面](http://134.175.18.101/vln/v006_node_multiview_web_20261121_01/index.html) · [完整离线包（138.0 MB）](http://134.175.18.101/vln/v006_node_multiview_web_20261121_01/v006_node_multiview_offline.zip)

## 范围与来源

- 基础页面：`outputs/visualization_publishing/deviation_five_versions_web_20261121_01/index.html`。
- 保留五组原结果、53 条轨迹、4,890 帧、1,131 轮原答及原有双语、地图、波形、双进度条。
- 增加 376 个保留存档节点和 53 个终止节点的观测；v006 的 47 个回退目标按冻结结果标记。
- 多视角来源：`outputs/offline_route_dataset/v001/run_20261118_01/dataset/inputs/<episode_id>/observations.jsonl` 和对应原始 PNG。
- 按 episode_id 和节点 index 对应采集 step，核对原生前视哈希和机器人位置。取节点自身帧，不使用 emittedAt 或报警帧代替。
- 180° 按左前 +45°、正前 0°、右前 −45°排列；360°使用八方向，朝向相对当步真实机器人。显示为图组，提供单图放大。
- 仅导出既有数据，不改变 seed 2、Prompt、节点、模型原答、评分或实际输入，不调用模型、不启动仿真、不操作 GPU 服务。

## 实现与命令

导出器：`scripts/export_deviation_node_multiview.py`；交互：`core/deviation_node_multiview.js`、`core/deviation_node_multiview.css`。

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_deviation_node_multiview.py media
backbone/streamvln/.venv/bin/python -B scripts/export_deviation_node_multiview.py page
node experiments/deviation_progress/v006/exports/node_multiview_20261121_01/browser_check.cjs
backbone/streamvln/.venv/bin/python -B scripts/export_deviation_node_multiview.py package
```

新导出目录：`outputs/visualization_publishing/v006_node_multiview_web_20261121_01/`。保留原页面与历史下载，不覆盖既有发布。实际 Git 提交、工作区状态、来源及实现哈希、源码快照、导出统计与必要验证保存于新目录及本记录。

## 交付状态

429 个节点全部通过任务/节点帧/原生前视哈希/机器人位置对应核对，3,432 张原 PNG 在生成展示副本时核对 SHA256。180° 三图的方向及原图哈希与360°对应，复用同一展示图片。展示副本为 640×480 WebP，quality=85，原图保留不变。

定向浏览器检查已通过，记录见 [browser_check.json](browser_check.json)：C01 的方向顺序、3/8图切换、放大和普通帧清空；C04 无回退目标；C50 在 F33 报警而正确展示 F15 回退目标、双语、原答及截断错误保留；C53 终止节点。两进度条、切换历史版本及390像素手机布局均通过，无脚本或加载错误。桌面与手机截图已人工查看；不重复执行历史全量评审回放或导航实验。

发布使用仓库标准流程：

```bash
python3 -B experiments/deviation_progress/v006/exports/node_multiview_20261121_01/publish.py
```

标准发布已完成，8,349 个文件远端 SHA256 全部通过，入口公网直连 HEAD 为 HTTP 200。仅执行快速公网检查，未下载全量公网资源或另做在线浏览器回归。原多版本入口与历史页面保留。

- 发布摘要：[publication.json](publication.json)。完整回执：`outputs/visualization_publishing/publish_20261121_030057_593413/publication.json`。
- 本地页面：`outputs/visualization_publishing/v006_node_multiview_web_20261121_01/index.html`。
- HTML SHA256：`012c134b84639538f206dda739fb294b4c772dc016b51d6eb99553429e9eead2`。
- 离线 ZIP：138,031,101 bytes，SHA256 `cb6289ac82a77e5e61371cf301157cac4d2fd333939a75247c699503c6f0413f`。
- 实际 Git 提交：`7ce5f9fee30686bae304425bc84c36b3fbedc39c`；工作区已有修改保留。实际生成源码和哈希在 `source_snapshot/`、`export.json`；发布及检查助手另有快照，发布清单调整记于 `publication_preparation.json`。

首次发布在本地清单准备阶段发现字体许可证 `.txt` 不属于上传器支持的静态类型，核验 PID、命令行、工作目录和 UID 后仅停止本轮发布准备进程，尚未写远端。许可证保留在离线 ZIP，网页资源清单排除该文本；页面与 ZIP 均未改动，随后按标准流程发布成功。本次没有新模型调用或仿真，未操作 GPU 服务。

限制：多视角为当时采集的辅助环境观测（排除机器人自身遮挡），保持当时真实姿态；没有拼接为单幅全景。模型输入仍为原生前视。47 个目标来自 v006 离线报警，不代表实际执行过回退或回退成功。
