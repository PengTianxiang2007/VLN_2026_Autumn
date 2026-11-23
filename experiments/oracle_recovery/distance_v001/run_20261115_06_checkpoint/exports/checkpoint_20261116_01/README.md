# 三组Oracle结果交付：实际存档回退组补齐

状态：已完成并发布，2026-11-16T12:59:04.470573+00:00（北京时间11月16日20:59）。用户要求复用之前模板发布三组；0.75米组与额外前移0.5米组沿用已发布原网页，本次补齐运行06的回退组。

| 实验 | 官方成功 | 正常成功停止 | 触发任务 / 干预次数 | 网页 |
| --- | --- | --- | --- | --- |
| 偏移0.75米、正确参考路线落点前移0.75米 | 17/33（51.52%） | 15 | 26 / 93 | [原0.75米组](http://134.175.18.101/vln/oracle_distance_075m_33_run05_web_20261115_02/oracle_075m_33.html) |
| 实际存档回退，随后自主续走 | 6/33（18.18%） | 5 | 25 / 25 | [回退组](http://134.175.18.101/vln/oracle_checkpoint_33_run06_web_20261116_01/oracle_checkpoint_33.html) |
| 偏移0.75米、正确参考路线落点前移1.25米 | 22/33（66.67%） | 19 | 26 / 70 | [额外前移0.5米组](http://134.175.18.101/vln/oracle_distance_plus05_33_run07_web_20261116_01/oracle_plus05_33.html) |

三组均为seed2、同33任务/34历史错误事件；官方成功与正常成功停止分别展示，不将独立运行间的成绩差异视为相同前缀的因果证据。回退组SPL16.06%、NE6.0655米；33个实际存档点（32条任务），1条无存档，8条未执行回退。以上是距离脚本Oracle实验，不是JEV/DeepSeek串行pipeline成绩。

## 原模板复用与数据适配

复用`core/oracle_distance_replay.html`与`scripts/export_oracle_distance_replay.py`。页面CSS与此前plus05冻结模板逐字节一致（证据`template_reuse.json`）；布局、地图/RGB双进度条、原始/参考/本次轨迹、图层/筛选、结果CSV、完整中文/English切换均沿用，默认中文。

T显示真实存档位置，未捕获不伪造落点；回退前后策略动作编号可回绕，以实际观测sequence定位事件。25次实际恢复的位置、记忆和预算证据全部核验；页面比较原存档与恢复记忆哈希，不误称回退前后记忆不变。只读正式完成attempt和原评分；没有新设计或重跑导航。

## 导出与验证

- 命令：`backbone/streamvln/.venv/bin/python -B scripts/export_oracle_distance_replay.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint --arm checkpoint --output outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint/exports/checkpoint_20261116_01/oracle_checkpoint_33.html`。
- 实际导出版本：Git `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，含未提交修改；本次源码冻结在`outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint/exports/checkpoint_20261116_01/source/`。历史实验版本仍以运行06原manifest与续跑快照为准，不用当前Git追填历史版本。
- 离线HTML：`outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint/exports/checkpoint_20261116_01/oracle_checkpoint_33.html`，81,674,743字节，SHA256 `3cfe36c1b94c492ae2c4b4441c6540cb4275e11c2292b916c0fb5debeae7fc09`；输入/观测/源代码审计见同目录`oracle_checkpoint_33.build.json`。
- 在线目录：`/tmp/oracle_checkpoint_33_run06_web_20261116_01/`；完整`online_bundle.tar.gz`与`online_manifest.json`保存在上述产物目录，逐项产物哈希见`artifact_sha256.json`。在线HTML 2,121,001字节，SHA256 `f2e23ff0b6776deaf4b4a29893f349c68c953555063867cb091e27ccfc486667`。
- 本地Chromium通过：33任务双语指令与原始回放、25次真实回退前后画面/节点/轨迹段切换、8条未回退任务、双进度条、播放/缩放/图层/筛选、33行CSV、手机布局；零页面错误和外部请求。证据与截图在`outputs/oracle_crossing/distance_v001/run_20261115_06_checkpoint/exports/checkpoint_20261116_01/validation/`。
- 标准发布脚本上传6943个文件（HTML、图片、字体及字体许可ZIP），全部远端SHA256核验通过；公网直连入口HEAD返回HTTP200，类型与大小通过。未进行公网全量下载或在线浏览器检查。
- 发布记录：`outputs/visualization_publishing/publish_20261116_125846_172323/publication.json`，`phase=published`、`remote_sha256_verified=true`；发布时间`2026-11-16T12:59:04.470573+00:00`。
- 已有两页本次仅重新核验公网HEAD200/类型/大小，结果在本登记目录`existing_pages_http.json`。复用原完整发布证据：`outputs/visualization_publishing/publish_20261115_152407_011385/publication.json`与`outputs/visualization_publishing/publish_20261116_002025_195726/publication.json`；未覆盖历史版本。

本轮只导出与发布已有结果，没有启动/停止模型或仿真，没有恢复已取消的其他距离组。
