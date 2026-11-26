# 早期 48 条 seed 2 Crossing 错选轨迹的三版采样

固定原始 seed 2 导航录像，按 2026-11-03 attribution_reviews.json 的 crossing 清单与原始顺序取 48 条。全 48 条只回放既有 v001、v003 coverage、v002 active；采用各自冻结的配置、五步确认延迟。共 4506 个非终止评分位置。按图像窗口匹配复用历史 JEV v004 分数，缺失部分使用相同问题和模型的 EasyJEV 前视评分。原归因每例一个错选位置，±3 步一对一统计错选帧覆盖；该参考集不提供完整 Astra 回退点标注。无导航重跑、采样器训练或调参。基线提交 e40d9a821ee72516261ee819284e36be7be2eff1，采样器及本轮入口的实际源码快照保存至输出 source/。

从仓库根目录用 benchmarks/vlnverse/.venv/bin/python -B 运行同目录 run.py，执行 prepare 和 cache 阶段；缺分补评及导出命令见下文。

## 缓存阶段

完整对齐原 48 条、10 个场景。与上一轮 42 条有 18 个 episode ID 重合，与 53 条有 25 个 ID 重合；本轮逐帧使用早期原录像。33 条可完整复用 3,006 帧 JEV v004 分数，另 15 条尚缺 1,500 帧。按三帧图片哈希或完整请求 SHA256 复用。参考点来自 2026-11-03 原始错选归因，每条一个，区别于完整的回退点参考集。±3 步在每条轨迹上最多命中一次。

| 采样版本 | 候选数 | 错选位置覆盖 |
| --- | ---: | ---: |
| v001 原版 | 284 | 20/33（60.61%） |
| v003 覆盖优先 | 140 | 16/33（48.48%） |
| v002 精简 | 187 | 17/33（51.52%） |

[本地回放](../../../../outputs/crossing_checkpoint/online_sampling_v003/run_20261125_01_early48/cached/index.html) · [离线 ZIP](../../../../outputs/crossing_checkpoint/online_sampling_v003/run_20261125_01_early48/cached/early48.zip) · [实际匹配帧与缺分清单](../../../../outputs/crossing_checkpoint/online_sampling_v003/run_20261125_01_early48/cached/summary.json)。本地浏览器核对 RGB/地图、四个图层、全组及单例统计和中英文切换。采纳率无完整 Astra 标签，暂无。导航当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

实际入口：使用 run.py prepare 生成图像及轨迹；run.py cache 为纯本地核对，run.py score 才补评；export.py cached 导出现成的完整流，export.py full 要求全部完成。早期 48 条缺分补评的自动审批要求用户对发送缺失前视窗口到 EasyJEV 明确授权。

## 缓存阶段公网回放

[打开已完成的 33/48 条三版采样回放](http://134.175.18.101/vln/early48_seed2_three_samplers_33of48_web_20261125_01/index.html)。源为本轮 cached/index.html，缺分 15 条在页面列出。2026-11-25T07:36:04.340377+00:00 发布，在线目录 outputs/visualization_publishing/early48_seed2_three_samplers_33of48_web_20261125_01/。入口 SHA256 为 `c3fbd1063831336dc61b4151af1e38a9d1247b42a26e57c05321071992cfd56f`，共 3018 个文件远端哈希核验通过，公网入口 HTTP 200。[发布记录](../../../../outputs/visualization_publishing/publish_20261125_073550_184750/publication.json)。
