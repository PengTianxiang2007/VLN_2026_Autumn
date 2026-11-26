# GPT-6 Astra 三帧 / 五帧及历史模型对照

状态：已导出、验证并发布。

使用现有回退点去重模板，默认 GPT-6 Astra 三帧；保留旧 Astra 五帧、Qwen 五帧及 DeepSeek 五帧。新版与旧版为同 C01–C10、相同原始候选、相同 seed=2 图像；仅每端观测窗口由 -2/-1/0/+1/+2 改为 -2/0/+2，缺失前起点帧如实标注。DeepSeek 历史只覆盖本页 C04/C08。

勾选模型后隐藏其判为重复的原始候选；多选取删除并集，组合显示不代表单一模型结果。取消全部显示原始候选。模型原答选择独立于勾选；地图、波形、当前帧标志与双进度条同步。

`translation_source.json` 与 `review_en.txt` 按编号逐条对应，由本地助手翻译展示文本。中文原答、JSON 和实际推理输入不改。未向外部服务另发翻译请求。

```bash
python3 -B scripts/export_codex_dedup_comparison.py \
  --run outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_02 \
  --record experiments/crossing_checkpoint/codex_dedup_v002/run_20261123_02/exports/compare_20261123_01 \
  --previous-run outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_02 \
  --previous-record experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_02/exports/compare_20261123_03 \
  --offline outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_02/exports/compare_20261123_01 \
  --online outputs/visualization_publishing/codex_astra_three_frame_route10_compare_web_20261123_01
```

运行无新导航评分：当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

## 发布与验证

- 在线页面：http://134.175.18.101/vln/codex_astra_three_frame_route10_compare_web_20261123_01/index.html
- 完整离线包：http://134.175.18.101/vln/codex_astra_three_frame_route10_compare_web_20261123_01/compare_20261123_01_offline.zip
- 发布时间：2026-11-23T22:45:09.554641+00:00
- 标准发布记录：`outputs/visualization_publishing/publish_20261123_224459_132188/publication.json`。
- 929 个发布文件远端 SHA256 全部一致，HTML 公网 HEAD 200；未追加全量公网下载。
- 离线 HTML SHA256：`ff1f68d9ba41e3224fbe25f8b6011ebff9e6194bec1e62922fbf0a2e6d220414`。
- 离线 ZIP SHA256：`ee593754cd108733668ce28d7a94ee45218f5aa717bcda794704ebb76e66535a`。
- 原始页面、字体、图片及完整离线包位于 snapshot.json 所列 offline/online/zip 路径。

浏览器直接验证十条、每条六种勾选组合，三/五帧证据数量与各自 prompt 相符；四版本中英文原答、原始 JSON、任务/帧及双滑块一致；C04/C08 之外 DeepSeek 明确未评审；移动端无横向溢出，页面异常 0。字体覆盖全部展示汉字。219 条新展示文本逐条对应原中文，原始实验内容不改。证据：[浏览器检查](browser_check.json)、[来源与哈希](snapshot.json)。

| 版本 | 覆盖任务 | 原始候选 | 有效节点 | 删除 | 比较 |
|---|---:|---:|---:|---:|---:|
| GPT-6 Astra 三帧 | 10 | 89 | 57 | 32 | 63 |
| GPT-6 Astra 旧五帧 | 10 | 89 | 56 | 33 | 63 |
| Qwen 五帧 | 10 | 89 | 63 | 26 | 63 |
| DeepSeek 五帧 | 2（C04/C08） | 26 | 9 | 17 | 19 |
