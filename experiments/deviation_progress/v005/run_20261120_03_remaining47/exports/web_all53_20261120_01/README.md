# v005 全 53 条离线回放

用户要求将阶段版剩余五条上传到原网址。本次复用六条首轮结果和补跑的 47 条结果，共 53 条、272 轮（232 次 consistent、40 次 deviated），不新增模型调用。冻结输入、seed 2、Prompt 和推理参数均来自实际运行清单。

通过 `build_export.py` 汇总实际来源并调用已有导出器，生成双语页面、逐轮模型原答、实际输入图像、累计进度和离线 ZIP。使用独立快照 `outputs/deviation_progress/v005/all53_20261120_01`；旧阶段版及原始运行结果保留。页面模板仅将固定六条字样和下载文件名改为实际样本数。

运行命令（仓库根目录）：

```bash
PYTHONPATH=.:scripts backbone/streamvln/.venv/bin/python -B experiments/deviation_progress/v005/run_20261120_03_remaining47/exports/web_all53_20261120_01/build_export.py
node experiments/deviation_progress/v005/run_20261120_03_remaining47/exports/web_all53_20261120_01/browser_check.cjs outputs/visualization_publishing/qwen_v005_all53_web_20261120_01/index.html outputs/deviation_progress/v005/all53_20261120_01/v005_results.json
.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/v005/run_20261120_03_remaining47/exports/web_all53_20261120_01/publish.py
```

发布状态：2026-11-20 12:20:55 UTC 已完成。使用标准发布器上传新版本，再备份并切换用户指定的原网址入口。53 条、272 轮、429 个有效节点、4890 帧回放、1244 张独立实际输入 PNG 已纳入。仅执行导出器原有完整性检查、一次本地页面检查（含新增 C53 的双语、原答和同步输入帧）及标准公网快速验证。

- [原网址完整回放](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)
- [完整离线 ZIP，379,231,091 字节](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_v005_all_53_offline.zip)
- [全部 272 轮模型返回 JSON](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/qwen_v005_all_53_model_returns.json)
- [独立版本入口](http://134.175.18.101/vln/qwen_v005_all53_web_20261120_01/index.html)

6156 个资源远端哈希通过，原入口新增 729 个资源，旧 HTML 备份为 `index_before_v005_all53_20261120.html`。页面、JSON、ZIP 均 HTTP 200；页面与 JSON 的公网内容哈希通过，ZIP 只做 HEAD 大小检查。原入口 SHA256：`e190bb235dee75f39cd2910770aa6277c0ad9da0ff6329b2e8c9439143b6af16`；ZIP SHA256：`544e2fb8782196ffa1e4a4ed054d51f9bcab48795ad3e16b34b2ef2fabd08ca8`。证据见 [publication.json](publication.json)、[browser_check.json](browser_check.json)，标准发布记录位于 `outputs/visualization_publishing/publish_20261120_121727_147167/publication.json`。未重新运行模型，GPU 3 常驻服务未改动。

首次误用 Qwen 环境，导出在字体处理阶段因缺少 `fontTools` 退出，未进行上传。复用已生成的 53 条快照，改用历史导出的 StreamVLN 环境，实际离线 HTML 与导出记录存入 `outputs/deviation_progress/v005/all53_20261120_01/exports/web_all53_20261120_02`。环境未修改。重建时须选择新的输出目录，避免覆盖现有产物。
