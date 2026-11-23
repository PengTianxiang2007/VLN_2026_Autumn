# Qwen27B 与 DeepSeek v004 同轨迹回放

2026-11-20 UTC。复用 seed 2 的 C07、C11、C19、C30、C47、C50，逐份比较 Qwen 运行时校验器和修复后的校验器，再将两组原答接到 DeepSeek 修复版回放的原入口。本次只读取归档结果，新增模型调用为零。

Qwen 来源为 `outputs/deviation_progress/v004/run_20261120_01/qwen_gpu2_01`，DeepSeek 来源为 `outputs/deviation_progress/v004/run_20261120_03_contract_replay`。模板为 `outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_01/index.html`。基线提交为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。各自按首次有效偏航停止，回放共享原始轨迹和去重后保留的节点。

## 核查结果

Qwen 的 35 份原答逐份送入运行时和修复后的校验器，两者均采纳全部回答，返回值与当时保存的结果逐项一致。没有一份含顶层 `type`。14 轮为 `consistent`（含六次初始化），20 轮为 `uncertain`，1 轮为 `deviated`。C47 S04 的 Qwen 原答为 `uncertain`。每轮的原答哈希、节点、区间和校验器源码哈希见[核查记录](qwen_validator_audit.json)。

| 案例 | Qwen27B 首次报警 | DeepSeek 首次报警（修复版） |
| --- | --- | --- |
| C07 | 无 | F2→F75 |
| C11 | F0→F5 | F0→F5 |
| C19 | 无 | 无 |
| C30 | 无 | F42→F47 |
| C47 | 无 | F0→F52 |
| C50 | 无 | F15→F33 |

两组的 394 个回放帧、39 个有效节点均已核对。浏览器检查覆盖 Qwen 的 35 轮、198 个实际输入帧引用，以及 DeepSeek 修复版的 29 轮、155 个引用。两组共用 156 张不同的实际输入 PNG。按模型核对双语内容、逐字原答、输入帧、提交前后进度、报警区间和首次偏航后的未评审节点。切换模型可保留轨迹、帧与选中的轮次。结果为这六条轨迹的模型报警记录，未进行人工正确率评估。[Qwen 浏览器检查](browser_qwen.json) · [DeepSeek 浏览器检查](browser_deepseek.json)

## 页面与下载

2026-11-20 06:49:02 UTC，双模型入口在原地址上线。默认显示 DeepSeek，页面顶部可选 Qwen27B。离线包内分别存放两组逐轮 JSONL 及原始回答 TXT，网页中的模型原答、每次实际输入图像和累计进度也可以离线查看。只需要交给 GPT 阅读 Qwen 答案时，可直接取 Qwen JSON。[原网址](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html) · [直达 Qwen](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html?model=qwen) · [Qwen 逐轮 JSON](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_model_returns.json) · [两组完整 ZIP](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_deepseek_v004_six_offline.zip)

发布核验了 561 个文件。原入口新增 37 个静态资源，原 HTML 已备份。公网入口和两份 JSON 逐字节核对，各下载包通过 HTTP 200 和大小检查。入口 SHA256 为 `5a38d8dc746b2d94fd11993a10b6824d664c86d7aa1240aca74221199171b08c`，ZIP SHA256 为 `3bb451c47a7e67abe6add65c2b35e96de83d56338db3211b86f5d7048a872570`。[导出和源码哈希](../../../../../../outputs/deviation_progress/v004/run_20261120_01/qwen_gpu2_01/exports/paired_web_20261120_01/export.json) · [原入口发布记录](publication.json) · [新版本发布清单](../../../../../../outputs/visualization_publishing/publish_20261120_064833_993191/publication.json)

## 复现命令

从仓库根目录运行，选择尚不存在的导出和检查文件名。

```bash
QWEN_RUN=outputs/deviation_progress/v004/run_20261120_01/qwen_gpu2_01
DS_RUN=outputs/deviation_progress/v004/run_20261120_03_contract_replay
PAIR_OUT="$QWEN_RUN/exports/paired_rebuild_01"
PAIR_WEB=outputs/visualization_publishing/paired_rebuild_01
PAIR_REC=experiments/deviation_progress/v004/run_20261120_01/exports/paired_web_20261120_01
.runtime/crossing_vllm27/bin/python -B "$PAIR_REC/audit_qwen.py" /tmp/v004_qwen_audit_rebuild_01.json
PYTHONPATH=.:scripts backbone/streamvln/.venv/bin/python -Bu scripts/export_deviation_progress_v004_replay.py \
  --run "$DS_RUN" --compare-run "$QWEN_RUN" \
  --template outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/terminal53_01/index.html \
  --output "$PAIR_OUT" --online "$PAIR_WEB"
node scripts/check_deviation_progress_v004_replay.cjs "$QWEN_RUN" "$PAIR_WEB/index.html" "$PAIR_OUT/browser_qwen.json" qwen
node scripts/check_deviation_progress_v004_replay.cjs "$DS_RUN" "$PAIR_WEB/index.html" "$PAIR_OUT/browser_deepseek.json" deepseek
```
