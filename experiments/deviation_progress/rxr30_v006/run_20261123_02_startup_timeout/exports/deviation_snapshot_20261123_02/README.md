# RxR30 有效节点与已完成偏航识别快照

状态：已发布，2026-11-23。用户授权更新网页，偏航区间提供独立勾选，并将实际 A→B 轨迹染红。

## 范围与协议

只读冻结当前已完成的第二轮结果，不调用模型、不重跑导航、不改后台进程。第一轮全部30条最终有效节点进入本页；已删除候选不显示为节点。第二轮仅收录有正式 case result 的完成案例，格式错误单列，不当作报警。偏航层按实际评审记录的 from_frame/to_frame 遍历原轨迹，不能直接连两端，也不能假定 A/B 编号连续。

继承前版首4条的完整双语逐次去重详情，其余26条本页增加最终节点和汇总，原始去重结果可下载。全部已完成偏航案例提供逐轮原答、实际输入帧、累计进度、双语理由和证据。默认中文，红色偏航层默认关闭，由用户勾选显示。

样本与原导航、推理设置沿用父运行：RxR随机30条，导航清单seed2，本地Qwen27B seed2/temperature0，v006，首次有效报警后停止该条离线评审。本轮无新导航评分：当前版和配对原版SR/平均SPL均暂无，已评分0条；来源原版30条SR 0/30（0%）、平均SPL 0，属于预选失败样本。

## 生成与交付

```bash
python3 -B scripts/export_rxr_deviation_snapshot.py prepare
python3 -B scripts/export_rxr_deviation_snapshot.py build
```

使用新的导出目录和发布版本，不覆盖旧网页。输出目录与本记录同构，位于outputs/；冻结数据与来源哈希、源码保存在该目录。按docs/VISUALIZATION_PUBLISHING.md的已有online_manifest标准流程发布。

冻结时间：2026-11-23 15:20:06 UTC。去重30/30，725原始候选→517有效节点（另加30终止节点），208删除；656次比较，29次uncertain含4次校验错误。逐次去重双语详情仍覆盖原首4条134次模型比较，其余26条的完整去重结果提供原始JSON下载。

偏航4/30条，共51轮：42 consistent、2 deviated、7 format_error。C01/ep837在S08 F40→S09 F50报警，C02/ep1825在S10 F67→S12 F82报警；C03/ep1504、C04/ep6858完成评审未报警。其他26条是冻结时无完整结果，不当作未偏航，也不纳入统计。未重跑或重解释任何模型回答。

本地验证通过：两个报警的全部实际位姿边与画布绘制逐一对应；独立开关开启后出现红色像素、关闭后恢复；另两条无报警结果切换不产生红线。51轮原答在中文/English切换后与原始回答、任务帧对应，原始JSON保持不变；A/B跳帧、全部有效节点、待完成状态、390px移动端正常，页面JS错误0。证据见validation.json及输出validation/截图。未执行公网浏览器或全量公网下载。

实际Git基线7ce5f9fee30686bae304425bc84c36b3fbedc39c；工作区含此前未提交修改，本次实际导出和页面源码副本在输出source/，哈希见build.json，输入文件哈希见source_hashes.json。离线包227842657字节。

```bash
node scripts/check_rxr_deviation_snapshot.cjs outputs/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/deviation_snapshot_20261123_02
python3 -B experiments/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/deviation_snapshot_20261123_02/publish.py
```

后台推理继续独立运行，本页是冻结快照，不自动刷新。


## 发布结果

[打开新版网页](http://134.175.18.101/vln/rxr30_deviation_snapshot_web_20261123_02/index.html) · [下载完整离线包](http://134.175.18.101/vln/rxr30_deviation_snapshot_web_20261123_02/rxr30_deviation_snapshot_offline.zip)

入口HTML：`outputs/deviation_progress/rxr30_v006/run_20261123_02_startup_timeout/exports/deviation_snapshot_20261123_02/index.html`。HTML SHA256：`9fa33f4da63cab5bb34f967d8fa76217ff53e27a90991954de75c88f8600ffaa`。ZIP SHA256：`52567187a3dc5493fb6211628f2a72540bca33c1e2c5b14c7cf297efbfe90a43`。全部579个文件远端SHA256通过，入口公网HEAD为HTTP 200、text/html；标准发布退出0。发布记录：`outputs/visualization_publishing/publish_20261123_152545_118957/publication.json`。冻结和发布为同日，精确发布时间见publication.json。

旧版首4条去重网页保留。本次已完成用户要求的偏航红色图层与网站更新；后续等用户询问时再查询后台，不持续追踪。
