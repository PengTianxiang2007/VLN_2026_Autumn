# 四例终止节点偏航回放

[在线回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html) · [离线 ZIP](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/replay.zip)。直接派生自用户指定的[JEV 42 例地图图层模板](http://134.175.18.101/vln/jev_sampling_astra_map_layers42_web_20261125_01/)。以本轮四例替换模板数据，补入四张原生终止帧，保留地图、JEV 波形、前视 RGB、双进度条及双语切换。独立图层包括 v002 原始候选、最终有效节点、报警轨迹、记录的回退目标、END 和事后归因区间。C23 的 END 只在轨迹回放中展示，明确标示未发出终止轮。页面收录 232 帧与 17 轮偏航原答。

离线源 `outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_01_terminal4/exports/map_layers_01/release/index.html`，SHA256 `64c45530eec98cc675dfbce2d8757552a949714bac05e8fefae3b120112a116f`。在线目录 `outputs/visualization_publishing/codex_deviation_v002_terminal4_map_layers_web_20261125_01`，入口 SHA256 `0d496376bfbfad440dfc9cd87bc7ae993e4543b4e0754b1bb85f6e3ca98a231d`。首次本地导出发现模板已有嵌入字体，移除旧字体后生成 release/ 成品。2026-11-25T15:47:36.982321+00:00 发布，238 文件全部通过远端 SHA256 校验，公网入口直连 HEAD 返回 200。[发布记录](../../../../../../outputs/visualization_publishing/publish_20261125_154732_218681/publication.json)。

[本地交互检查](browser_check.json)覆盖四例、有效节点、终止帧、各自报警区间、原答中英文、同步进度条及证据跳转。离线判定不产生导航评分；当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。
