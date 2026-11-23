# DeepSeek H1 选路位置约束 · 四例配对回放

2026-11-23 17:07 UTC [在线回放](http://134.175.18.101/vln/deepseek_h1_choice_position4_20261123_01/index.html)已发布。新版回程 452 帧、旧版回程 96 帧、共用历史去程 118 帧。入口及依赖共 677 个文件，远端 SHA256 均匹配，公网入口直连 HEAD 为 HTTP 200。入口 SHA256 为 `799e4d5e96debb87493f9eec812b25936c59a9b97889e026b73d99c59cf5d17e`。

[本地浏览器检查](../../../../outputs/inverse_rollback/exports/choice_position4_20261123_01/browser.json)覆盖四例两版末帧、同步进度条、图层与线宽、双语切换及移动端宽度。[发布回执](../../../../outputs/visualization_publishing/publish_20261123_170736_064943/publication.json)

本页对照[选路位置版四例重跑](../../vlm_action_v001/run_20261123_06_choice_position4/README.md)与[旧版 22 例](../../vlm_action_v001/run_20261123_05_finish22/README.md)中的同一批 C15、C21、C31、C34。两版使用 seed 2、相同的 B 起始状态及同一份历史去程描述。局部达标要求模型主动退出且终点距 A 不超过 0.35 米。新版、旧版均为 0/4（0%），平均终点误差分别为 4.179 米和 3.590 米。整条导航的 SR 与平均 SPL，两版均为“暂无，已评分 0 条”。

地图、原生前视、回程动作和每轮模型判断按所选版本的帧号同步。回程从初始掉头完成后的 R0 起播。历史 A→B 去程共用一份实拍记录。同图可独立显示新旧回退、历史去程、原任务标注参考路线及 B 至下一有效节点的历史偏航段。C34 的 B 后无下一有效节点，该图层在该例禁用。

[本地入口](../../../../outputs/inverse_rollback/exports/choice_position4_20261123_01/index.html) · [导出计数与源结果哈希](../../../../outputs/inverse_rollback/exports/choice_position4_20261123_01/export.json)

```bash
backbone/streamvln/.venv/bin/python -Bu scripts/export_vlm_rollback_replay.py outputs/inverse_rollback/exports/choice_position4_20261123_01 --compare-run outputs/inverse_rollback/vlm_action_v001/run_20261123_06_choice_position4
```
