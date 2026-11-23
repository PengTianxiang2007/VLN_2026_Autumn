# v006 Recovery 对照网页 · 有效节点修订

本次仅重新导出 Qwen 和 DeepSeek 的 47 例原答。旧模板按导出标签及轨迹在页面中的序号匹配去重记录。Recovery 导出改了标签并筛选了轨迹，匹配失败后，地图和波形使用了原始候选。修订后两图与当前帧提示共同读取 v006 有效节点序列，沿用评审时的节点 ID 和观测帧，终止节点单独标记。页面移除了节点去重开关和原始候选的采样面板。

按 [v006 全量记录](../../../../../../outputs/deviation_progress/v006_pair_route53_20261121_01/v006_all53.json) 逐例读取实际 source_run 中的 retained_nodes_and_terminals.json，以原始候选的 source_id 和帧对照 final_active_ids。53 条轨迹共 494 个原始候选，保留 376 个，删除 118 个，另有 53 个终止节点。253 轮的区间端点全部属于有效节点。47 例回退目标的节点编号及帧与实际 v006 首次报警记录逐一一致，两模型的输入清单逐例相同。四张后续前视图中共有 12 个图像位置命中被删候选所在帧，均作为普通 RGB 观测参与判断。

本地网页目录为 `outputs/visualization_publishing/recovery_branch_models_v006_47_web_20261121_02/`，入口为 `index.html`。[上一版导出记录](../models_20261121_01/README.md)中的命令更换输出目录后可复现本次导出。

浏览器抽查 C07 的 F36、F41 及终止帧，中英文的地图和波形标记均与有效清单一致。

[修订版网页](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/index.html) · [离线包](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/recovery_qwen_deepseek_v006_47_offline.zip)。入口 SHA256 为 `22585b9e79ee7199855e10d8be070f090f191f0c63ee59926689cc821189d1a6`，2026-11-21T11:33:03.203617+00:00 发布，远端 SHA256 及公网入口 HTTP 200 通过。发布记录为 `outputs/visualization_publishing/publish_20261121_113206_453581/publication.json`。
