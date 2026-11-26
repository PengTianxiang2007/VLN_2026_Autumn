# 全53条回退点去重对照导出

状态：已完成导出、53条页面交互检查与正式发布。

## 内容与来源

沿用用户刚确认的十条三帧对照模板，扩大到同一冻结数据集全部53条；不重新采样，不运行导航。默认 GPT-6 Astra 三帧，可独立勾选应用各模型删除结果；多选显示删除集合的并集，全部取消显示原始候选。原答下拉框独立切换，地图、RGB、双进度条与逐候选跳转保持同步。默认中文，完整中英文切换，原始JSON原样保留。

| 版本 | 覆盖 | 原始候选 | 保留有效节点 | 删除 | 比较 | 不确定 |
|---|---:|---:|---:|---:|---:|---:|
| GPT-6 Astra 三帧 | 53/53 | 494 | 308 | 186 | 338 | 26 |
| Qwen27B 五帧 | 53/53 | 494 | 376 | 118 | 338 | 10 |
| 历史 GPT-6 Astra 五帧 | 10/53 | 89 | 56 | 33 | 63 | 4 |
| 历史 DeepSeek 五帧 | 10/53 | 93 | 49 | 44 | 67 | 9 |

不同模型的保留数量不是准确率。旧Astra五帧为C01–C10，DeepSeek为C04/C08/C12/C34/C40/C41/C44/C48/C49/C51；无历史结果的样本明确标记未评审，不视为保留结论。

本次只增加全集动态数量/覆盖说明及历史来源映射。首次生成在写出HTML前发现DeepSeek C48不在常规目录；改为按其正式dedup_resume_01/summary.json索引读取已完成补跑结果，核对保留ID与历史页面一致，不改动历史产物、不重跑模型。

原答展示翻译为本地人工逐条翻译，共1123条不同文本；不修改中文原答、模型输入或评分依据。源码、翻译、各模型结果与模板SHA256见snapshot.json。

## 生成命令

```bash
python3 -B scripts/export_codex_dedup_comparison.py --run outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_03_all53/aggregate_all53 --record experiments/crossing_checkpoint/codex_dedup_v002/run_20261123_03_all53/exports/all53_20261123_01 --previous-run outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_02 --previous-record experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_02/exports/compare_20261123_03 --offline outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_03_all53/exports/all53_20261123_01 --online outputs/visualization_publishing/codex_astra_three_frame_route53_compare_web_20261123_01
```

离线HTML：`outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_03_all53/exports/all53_20261123_01/index.html`；SHA256：`00580850c72a85d93539f6974c3422bf80f5e315b919a1a44d3e0923dcb20c6f`。

完整离线包：`outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_03_all53/exports/all53_20261123_01_offline.zip`；SHA256：`6eac3bb29f9ed919c7779616d83dcd9a64533b7a5b773ddd3d16af95860e7bef`。

发布版：`outputs/visualization_publishing/codex_astra_three_frame_route53_compare_web_20261123_01`，4856张原生观测/地图资源及完整字体、许可和离线包；在线资源按需加载。

当前版及配对原版SR、平均SPL均暂无，已评分0条。本次没有导航评分。

## 针对性验证

2026-11-23T23:31:19.224Z，已有Playwright检查入口通过全部53例、每例6种筛选组合，以及可用模型的中英文原答/原始JSON、三帧与五帧证据数量、同步进度条、图像加载、缺失版本提示和移动端宽度；页面错误0。详见browser_check.json。Qwen C51历史回答缺失证据引用的校验失败状态保持原样，检查脚本已适配这一既有展示分支。未修改历史回答，未重复导航或模型实验。

发布包4860个文件，148.81 MiB，含完整离线ZIP；在线HTML 6.18 MiB，图片及字体外置。采用标准远端SHA256与公网快速检查，不额外下载完整在线资源。

## 发布完成

网页：[http://134.175.18.101/vln/codex_astra_three_frame_route53_compare_web_20261123_01/index.html](http://134.175.18.101/vln/codex_astra_three_frame_route53_compare_web_20261123_01/index.html)

完整离线包：[http://134.175.18.101/vln/codex_astra_three_frame_route53_compare_web_20261123_01/all53_20261123_01_offline.zip](http://134.175.18.101/vln/codex_astra_three_frame_route53_compare_web_20261123_01/all53_20261123_01_offline.zip)

发布时间：2026-11-23T23:32:42.323357+00:00。发布记录：`outputs/visualization_publishing/publish_20261123_233158_740149/publication.json`。4860个文件远端SHA256全部通过，公网入口直连HTTP 200；ZIP远端哈希通过，未额外进行全量公网下载。
