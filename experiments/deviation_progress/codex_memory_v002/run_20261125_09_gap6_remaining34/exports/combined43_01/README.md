# 43 例偏航评审回放

本次将已发布的 9 例与本批完成的 34 例合并，左栏按 C 编号升序排列。共展示 3,945 个轨迹帧、173 轮偏航评审，37 例报警。新增 34 例的 143 轮评审共补入 124 张前视图。每轮可引用的观测均可点击跳帧，画面分别标记历史观测、本轮补图及模型实际引用的证据。地图红线为首次报警区间。

网页沿用原地图图层模板，导航指令采用 Route53 已有的英中对照。模型判断、理由和进度展示 Astra 在原评审请求中生成的双语字段。提示词保留实际发送的英文，中文以仓库已有译文加上对应的附件引用生成。

离线源文件为 `outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_09_gap6_remaining34/exports/combined43_01/index.html`。在线拆分版与离线下载包保存在 `outputs/visualization_publishing/codex_deviation_v002_combined43_gap6_web_20261125_01/`。导出入口为 [export.py](../../../run_20261125_01_terminal4/exports/map_layers_01/export.py)，原网址更新使用 [publish.py](publish.py)。

[在线回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html) · [离线 ZIP](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/replay.zip) · [原网址发布记录](../../../../../../outputs/visualization_publishing/publish_20261125_194531_594009/publication.json)。

2026-11-25T19:45:31.567392+00:00 发布。服务器已校验 3966 个文件，原网址入口 HTTP 200。入口 SHA256 为 `6fa8e1ece5e1763eda4368c1c9e46cb57408a4bbd9f0cfddddbeb59258ae2fd7`，ZIP 为 `622f31f78326412b4caf4e19eb104bebea236347f36e05d21bc8da40a9e15405`，离线单文件为 `557cfd690e6db6435604c796efc2b7ad8dd5c7ae5f65439f7e243c5cb128da31`。
