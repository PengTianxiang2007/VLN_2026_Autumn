# 0.75米组33条任务回放与发布

2026-11-15，状态：已完成并发布。用户要求将已完成的0.75米组制作可视化并发布，标注原始轨迹、参考正确轨迹及纠正过程。

网址：http://134.175.18.101/vln/oracle_distance_075m_33_run05_web_20261115_02/oracle_075m_33.html

发布时间：2026-11-15 15:24:26 UTC（北京时间23:24）。在线HTML为2,270,517字节，SHA256为`2a368dad3794ceb55e09c769043be90ce8161cfb05a6a4f10b11515e54f8317d`；全部7378个发布文件的远端SHA256通过，入口直连HEAD为HTTP 200。没有进行公网全量下载或在线浏览器检查。

只读取已完成early结果：运行02的17条、03的3条、05的13条，共33任务/34标注事件，seed 2，93次纠正，官方成功17条。复用原人工样本集的历史未干预轨迹、中文指令、RGB及场景底图，不重跑导航，不更改在途其他组。

地图分别显示参考正确路线、历史seed 2未干预轨迹、本次Oracle轨迹、瞬移虚线、人工分叉点、计划落点、起点及目标。两次独立运行通过回放来源切换查看，各自地图与RGB使用同步进度条，不将相同帧号视为同一时刻。纠正前后使用实际记录，逐次核对记忆哈希。

公共代码：`scripts/export_oracle_distance_replay.py`、`core/oracle_distance_replay.html`。实际源码哈希、输入结果哈希与媒体计数写入导出manifest；实验实际运行版本以各来源run的冻结源码为准。

输出目录：`outputs/oracle_crossing/distance_v001/run_20261115_05/exports/early_20261115_01/`。离线原件为`oracle_075m_33.html`，元数据为`oracle_075m_33.build.json`，最终在线完整归档为`online_bundle.tar.gz`，源码快照在`source/`。使用既有中文字体子集，许可证随ZIP静态附件发布。

验证：33条任务全部核对指令中文/英文切换、历史/本次回放切换；93次纠正逐次检查前后帧、动作号、轨迹分段、实际图像和记忆哈希。4352个本次观测节点、3039帧历史轨迹；24条缺少独立终止RGB的任务明确标注复用，不伪造终止图像。双进度条、播放暂停、缩放、图层开关、7条未触发任务、2条非正常终止但官方成功任务、CSV33行和手机布局均通过，零JS错误。本地证据：`validation/validation.json`及四张截图。

构建命令：

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_oracle_distance_replay.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_05 --output outputs/oracle_crossing/distance_v001/run_20261115_05/exports/early_20261115_01/oracle_075m_33.html
node scripts/check_oracle_distance_replay.cjs outputs/oracle_crossing/distance_v001/run_20261115_05/exports/early_20261115_01/oracle_075m_33.html outputs/oracle_crossing/distance_v001/run_20261115_05/exports/early_20261115_01/validation
```

发布沿用`prepare_online_visualization.py`和`publish_visualization.py`。初始NAS拆分过慢，仅停止已核验属于本次导出的CPU拆分进程，部分文件保留在`outputs/visualization_publishing/oracle_distance_075m_33_run05_web_20261115_01/`，未发布该版本。最终使用本机临时盘`/tmp/oracle_distance_075m_33_run05_web_20261115_02/`执行同一标准流程并归档到项目outputs；字体许可证使用发布器支持的ZIP附件。

发布记录：`outputs/visualization_publishing/publish_20261115_152407_011385/publication.json`，`phase=published`、`remote_sha256_verified=true`。下一步：用户通过网页审阅；未因可视化重跑导航或改变其他实验组。
