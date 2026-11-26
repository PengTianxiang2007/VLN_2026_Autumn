# GPT-6 Astra / Qwen / DeepSeek 去重对照导出

状态：已完成并发布；2026-11-23T22:05:56.769411+00:00。

[打开在线回放](http://134.175.18.101/vln/codex_astra_route10_dedup_compare_web_20261123_03/index.html) · [下载完整离线包](http://134.175.18.101/vln/codex_astra_route10_dedup_compare_web_20261123_03/compare_20261123_03_offline.zip)（约 13.70 MiB）。

## 输入与结果

VLNVerse C01–C10，原顺序前十条错误轨迹，seed=2。只展示第一轮去重，模型均使用同一批原始候选和五帧前视证据。

| 模型 | 覆盖 | 原始候选 | 有效节点 | 删除 | 比较 |
|---|---:|---:|---:|---:|---:|
| GPT-6 Astra / Codex | 10/10 | 89 | 56 | 33 | 63 |
| Qwen27B | 10/10 | 89 | 63 | 26 | 63 |
| DeepSeek | 2/10，C04、C08 | 26 | 9 | 17 | 19 |

GPT-6 Astra 有 4 次 uncertain，0 格式错误、0 调用失败。所有输入、模型原答、历史会话与正式结果保持原样。
DeepSeek 其他轨迹明确标为未评审，不把缺失结果视为保留结论，不补跑模型。
当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

## 页面与操作

沿用原 Qwen53 / DeepSeek10 去重回放模板，保留地图、前视、JEV 波形、双进度条、逐比较 A/B 证据、分支对应及理由。
默认勾选 GPT-6 Astra；可独立勾选三种模型隐藏其判为重复的候选，全部取消显示原始候选。
多选隐藏删除集合的并集，页面明确标为组合显示，不冒充任一模型输出。
逐模型实际结果与原答通过独立下拉框查看，逐候选表可比较保留/删除/未评审并跳转到该帧。
地图、波形及当前帧提示同步读取所选过滤结果；被删除项只作为原始候选供对照。
默认中文，可切换 English。原始 JSON 原样保留，说明、分支、任务指令和提示词提供对应译文。
211 条 GPT-6 Astra 展示译文由当前助手在本地整理；复用已有模型展示译文，无额外模型翻译调用。

## 产物及复现

- 离线目录：`outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_02/exports/compare_20261123_03`。
- 在线目录：`outputs/visualization_publishing/codex_astra_route10_dedup_compare_web_20261123_03`。
- 离线 ZIP：`outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_02/exports/compare_20261123_03_offline.zip`，SHA256 `367a743358a92c65a3eeaa31353c325c8c4284eb67b7554b2d92feae20fe43be`。
- 离线 HTML SHA256：`4efaf7b2b0b44785ee4446efa121620ea311e408bd1ac81f15ddede291265f44`。
- 在线 HTML SHA256：`ee10f378586c64a1605518dca95a364822724b96bdd8eb1894f618e4563b6c84`。
- 导出入口：`scripts/export_codex_dedup_comparison.py`；界面扩展：`core/codex_dedup_comparison.js`。
- 冻结来源及逐模型统计：[snapshot.json](snapshot.json)；译文：[review_en.txt](review_en.txt)、[translation_source.json](translation_source.json)。
- 浏览器验收：[browser_check.json](browser_check.json)；发布摘要：[publication_summary.json](publication_summary.json)。

```bash
.runtime/crossing_vllm27/bin/python scripts/export_codex_dedup_comparison.py \
  --run outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_02 \
  --record experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_02/exports/compare_20261123_03 \
  --offline outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_02/exports/NEW_EXPORT \
  --online outputs/visualization_publishing/NEW_RELEASE
```

## 验证与发布范围

十条各五种勾选组合与保存节点清单一致；双语、原始 JSON、证据图片、同步进度条、DeepSeek 未评审标注及手机宽度通过，浏览器错误 0。
最终版与已通过交互检查的构建02仅内嵌字库不同；字库覆盖本页全部中文，重新截图核对通过，复用原交互验收。
929 个远端文件 SHA256 全部通过；公网入口直连 HEAD 返回 HTTP 200。没有执行公网全量下载或额外在线浏览器检查。
字体许可证已包含于 font_license.zip；发布器拒绝重复的独立 TXT 项后，仅修正资产清单，未修改页面或许可证内容。
构建01/02为未发布历史，分别保留布局/旧统计修正和字体补齐前的产物。最终发布为新目录，未覆盖旧页面。

已交付，无待执行模型或导航任务。
