# DeepSeek 十场景节点去重回放

[打开在线回放](http://134.175.18.101/vln/deepseek_route10_dedup_v001_web_20261118_01/index.html)。2026-11-18 08:17:06 UTC 发布。用户要求沿用之前的模板，并确认保留离线版。默认中文、开启节点去重，切换去重开关可对照 93 个原始候选与 49 个保留节点。逐候选记录给出去重理由、分支对应、证据图、序列事件与实际提示词。偏航识别处于暂停状态。

沿用 53 轨迹版本的地图、原生前视、波形、同步进度条，以及历史分支的去重面板。10 条轨迹、10 个地图、901 个前视帧、67 对模型判断。C48 使用断点续跑后的结果，保留 S02、S04、S05。[结果索引](../../resume_01/completion.json)

离线入口为 `outputs/deviation_progress/v003/run_20261118_02_deepseek10/exports/dedup_01/index.html`，SHA256 为 `43b1ae111de51adcc4c6c78fe89a5717252ff6e54ebdb7151b22961624f9cfdc`。同级打包文件 `deepseek_route10_dedup_offline_01.zip` 包含全部离线依赖，SHA256 为 `e94b60c35c24c540531a325a7d1cfa0bec041136797146487fb7532c4c9020e8`。生成脚本为 `scripts/export_route53_deepseek_dedup.py`，展示译文保存在 `review_en.txt` 并按源文本摘要校验。

在线目录为 `outputs/visualization_publishing/deepseek_route10_dedup_v001_web_20261118_01/`，入口 SHA256 为 `173ff9046eb812e0cd83cc114bd2eedd9b04c9c006a308178f7c8ddc6b2bba7b`。914 个文件通过远端 SHA256 校验，公网入口 HTTP 200。实际发布记录为 `outputs/visualization_publishing/publish_20261118_081652_411629/publication.json`。[离线浏览器验收](browser_offline.json)与[上线包本地浏览器验收](browser_online_package.json)覆盖去重开关、双进度条、逐决策双语显示和图像对应。
