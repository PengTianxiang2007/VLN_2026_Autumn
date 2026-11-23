# 额外前移0.5米组：33条任务回放

状态：已完成并发布，2026-11-16 00:20:43 UTC（北京时间08:20）。

网页：http://134.175.18.101/vln/oracle_distance_plus05_33_run07_web_20261116_01/oracle_plus05_33.html

用户要求将已完成的early_plus05组制作可视化网页。只读取运行07已有结果，不重跑导航。33条任务、34个标注事件；偏航触发阈值0.75米，分叉点投影后沿正确参考路线前移共1.25米，较原组多0.5米。结果为22/33官方成功、19条正常成功停止、26条触发、70次纠正，SPL44.30%、NE2.7629m。

沿用上一组双进度条模板：正确参考路线、历史seed2未干预路线、本次路线、分叉点与计划落点、瞬移前后RGB、策略记忆一致性证据；中英文正文完整对应，默认中文。不同独立运行不按帧号硬同步，不把成功率差异当同前缀因果证据。

导出器新增arm参数，支持已完成且官方导出通过的单组目录；文案、落点和计数均从本组实际配置/结果生成。旧离线HTML及远端网页保留。

本地产物：outputs/oracle_crossing/distance_v001/run_20261115_07_early_plus05/exports/early_plus05_20261116_01/oracle_plus05_33.html。

## 导出、验证与发布证据

- 命令：`backbone/streamvln/.venv/bin/python -B scripts/export_oracle_distance_replay.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_07_early_plus05 --arm early_plus05 --output outputs/oracle_crossing/distance_v001/run_20261115_07_early_plus05/exports/early_plus05_20261116_01/oracle_plus05_33.html`。
- 导出版本：Git `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，工作区含未提交修改；实际导出器、模板、检查器保存于同产物目录的`source/`，逐文件哈希见`artifact_sha256.json`，源实验与媒体审计见`oracle_plus05_33.build.json`。
- 离线HTML：83,056,390字节，SHA256 `460b78d81e98c01dfa3a5ab07e1e387339d603484c3c048f9ad666df8d9d6034`。本次3957个观测节点、历史3039个节点；复用的终止画面在页面明确标识。
- 在线目录：`/tmp/oracle_distance_plus05_33_run07_web_20261116_01/`；完整备份`online_bundle.tar.gz`及`online_manifest.json`保存于上述产物目录。按需加载6978个图片/字体资源，另附字体许可ZIP。在线HTML 2,148,417字节，SHA256 `f7e526d2eb2679152039d9480120dea2c449a020ba90a3307efcad0e77cf660e`。
- 本地Chromium检查通过：33条任务的双语指令与历史回放、全部70次纠正前后画面/节点/轨迹段跳转、7条未触发任务、地图/RGB双进度条、播放/缩放/图层、结果筛选、33行CSV、手机布局；零页面错误和外部请求。证据与截图在`validation/`。另核对两种语言的落点共1.25米、额外0.5米及本组70次计数。
- 使用标准拆分与发布脚本，6980个文件全部远端SHA256通过，公网直连入口HEAD返回HTTP 200，类型与大小核验通过；未进行公网全量下载或在线浏览器检查。本地浏览器检查不能与公网HEAD混称。
- 发布记录：`outputs/visualization_publishing/publish_20261116_002025_195726/publication.json`，状态`published`，`remote_sha256_verified=true`。

本页明确区分官方成功22条与正常成功停止19条；3条官方成功但异常终止独立标识。落点已处目标3米半径内时显示提示，不将瞬移后的成功全部归因于自主导航。只导出已有结果，未启动模型、仿真或已取消组。
