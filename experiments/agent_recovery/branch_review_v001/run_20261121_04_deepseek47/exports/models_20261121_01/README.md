# v006 的 47 个回退节点 · Qwen / DeepSeek 模型对照

同一组 47 个回退节点、每例七图，默认勾选 Qwen27B v1 和 DeepSeek Flash v1。每个模型可以单独勾选，C50 和 C07 还支持 Qwen v1.1 候选与去重对照。地图、RGB 和证据图片共享案例和帧；每个模型保留自己的支路编号和原答。Qwen v1、DeepSeek v1 分别给出 101、111 个支路项，两者均有 47 次此前支路匹配。它们是模型输出计数。

网页沿用 v006 地图/RGB 模板。数据取自 Qwen v1 全集 run_20261121_02_all47、DeepSeek v1 全集 run_20261121_04_deepseek47 和 Qwen v1.1 两例 run_20261121_01。部分英文展示译文使用本机 Qwen 处理，其余本地逐项整理；原始评审消息与图片未随翻译改变。

本地导出（重导出请使用新的输出目录）：

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_recovery_branch_review.py \
  --run outputs/agent_recovery/branch_review_v001/run_20261121_02_all47 \
  --translations experiments/agent_recovery/branch_review_v001/run_20261121_02_all47/display_translations_en.json \
  --comparison-run outputs/agent_recovery/branch_review_v001.1/run_20261121_01 \
  --comparison-translations experiments/agent_recovery/branch_review_v001.1/run_20261121_01/display_v11_en.json \
  --deepseek-run outputs/agent_recovery/branch_review_v001/run_20261121_04_deepseek47 \
  --deepseek-translations experiments/agent_recovery/branch_review_v001/run_20261121_04_deepseek47/display_translations_en.json \
  --output outputs/visualization_publishing/recovery_branch_models_v006_47_web_20261121_01
```

浏览器检查核对所有 47 对 v1 原答，以及 C50、C07 的 v1.1 结果。抽查 C50、C07、C01 的勾选、取消勾选、默认中文、英文切换、同一帧定位和七图放大，零 JS 错误。检查入口为 check_page.cjs，导出目录包含 browser_check.json。

发布于 2026-11-21T11:17:22.008791+00:00。[在线页面](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_01/index.html) · [离线包](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_01/recovery_qwen_deepseek_v006_47_offline.zip)。4586 个文件通过远端 SHA256 校验，公网入口 HEAD HTTP 200。入口 SHA256 为 `6637bc5018059306f9a501d3f38de601cb06b412db1102d7f58c7cde59bef50a`。发布记录为 `outputs/visualization_publishing/publish_20261121_111620_553862/publication.json`。
