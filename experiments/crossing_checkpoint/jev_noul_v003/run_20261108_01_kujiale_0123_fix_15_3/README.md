# kujiale_0123_fix_15_3 全观测运行

状态：完成。90/90个有效观测返回概率，0失败；网页已发布。

样本共91个观测，其中90个有有效新RGB；最后1帧终止/复用画面不重复推理。
90个观测一次性提交为90个并发进程，每个观测使用严格 `t-2,t-1,t` 窗口和同一
自包含 v003 Noul prompt。

对照：同一轨迹的JEV Noul v002概率与Qwen4B `best_v001` 分数。请求模型输入不包含
任务、动作、位置、地图、标签、参考路线或任何旧模型回答。

## 结果

- v002平均 `P(yes)=0.223`；
- v003平均 `P(yes)=0.317`；
- v003较高80帧、较低8帧、相同2帧；
- 90个观测以90个进程同时请求，最终90/90有效、0失败；
- 最后1个终止/复用画面不重复调用，因此回放共91帧。

## 网页

[打开 v002/v003 在线对照](http://134.175.18.101/vln/jev_noul_v003_kujiale_0123_fix_15_3_20261108_01/jev_noul_v002_vs_v003.html)

- 本地HTML：`outputs/crossing_checkpoint/jev_noul_v003/run_20261108_01_kujiale_0123_fix_15_3/exports/run_20261108_01/jev_noul_v002_vs_v003.html`
- SHA256：`19fa533800c444f9c79a9fa7ed03e85a16521f3f132d2355ee749f27d7be025e`
- 发布记录：`outputs/visualization_publishing/publish_20261108_144830_254631/publication.json`
- 在线浏览器证据：`outputs/visualization_publishing/online_check_jev_noul_v003_20261108_01/browser_verification.json`

地图使用Qwen轨迹几何；上一版v002为蓝色调，新版v003为红色调，颜色越深概率越高。
地图只绘制路线和当前机器人位置，没有人工点、JEV高分方块或其他路点。

实际英文prompt、完整中文翻译和请求条件见运行目录的 `prompt_en.json`、
`prompt_zh.json`；网页中也完整展示两版文本。
