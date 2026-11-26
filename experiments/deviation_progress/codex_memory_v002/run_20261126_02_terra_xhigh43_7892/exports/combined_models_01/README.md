# Astra 与 Terra 偏航评审回放

使用既有地图图层模板和同一份 seed 2 冻结轨迹。左侧可切换 GPT-6 Astra medium（43 例）与 GPT-6.1 Terra xhigh（39 例），case 按编号升序排列。同一 case 同时存在时，切换模型保留 case。Terra 的 C02、C15、C31、C39 已取消，未纳入导出。

| 版本 | 展示例数 | 偏航评审轮数（含初始化） | 报警例数 |
|---|---:|---:|---:|
| GPT-6 Astra | 43 | 172 | 38 |
| GPT-6.1 Terra | 39 | 171 | 25 |

Astra 的 C01 使用 [S04 单候选复判](../../../run_20261125_03_c01_s04/README.md)。保留先前 S01–S03 的判断，复判在 F38 建点后结束，默认打开 F38 并展示 F36、F38、F40。此分支没有后续偏航轮。C27 使用[均匀补七张的终止段复判](../../../run_20261125_04_c27_interval7/README.md)，保留分叉前各轮，在 S02（F7）→ END（F42）报警，回退目标为 S02。网页中红线为冻结轨迹上的报警区间。这两次分支均没有执行物理纠错。

其他 Astra 数据来自[此前的 43 例导出](../../../run_20261125_09_gap6_remaining34/exports/combined43_01/README.md)。Terra 逐例取本次运行的完整 result.json 和逐轮实际请求与回答。导航指令沿用已有双语文本，偏航结论沿用模型原答的双语字段。C01 复判英文提示词和英文回答的新增中文译文由 GPT-6.1 Terra 生成，仅用于展示。两版均为离线评审，当前与配对原版的导航 SR、平均 SPL 均暂无，已评分 0 条。

导出使用 [export.py](export.py) 和 [models.js](models.js)，原网址切换使用 [publish.py](publish.py)。离线 HTML 在本运行输出的 `exports/combined_models_01/index.html`，在线资源在 `outputs/visualization_publishing/codex_deviation_v002_astra_terra_web_20261126_01/`。已在本地浏览器抽查版本切换、C01/C27 复判、语言切换及模型图层名称。


2026-11-26T05:38:59.571173+00:00 发布。[在线回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html) · [离线 ZIP](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/replay.zip) · [发布记录](../../../../../../outputs/visualization_publishing/publish_20261126_053858_900338/publication.json)。入口 HTTP 200，服务器已核验入口、ZIP、新字体和复用资源。入口 SHA256 为 8a6ba11521083bc5322e248bd9063f58a3e09b42c2e064e8c5da96d45ab9e4a8，ZIP 为 d0591e398e5d1e95fef0c55c5819ff3c833f05255313115b16ff164bc4bb7afd。
