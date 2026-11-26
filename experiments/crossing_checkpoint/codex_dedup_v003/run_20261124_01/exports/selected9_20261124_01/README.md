# 九例会话历史回退点筛选可视化

状态为完成并发布，发布时间 2026-11-24T10:57:08.850947+00:00。模型运行于 2026-11-24 10:49:14 UTC 全部完成。

在线入口 [http://134.175.18.101/vln/codex_memory_selected9_web_20261124_01/index.html](http://134.175.18.101/vln/codex_memory_selected9_web_20261124_01/index.html)；离线包 [http://134.175.18.101/vln/codex_memory_selected9_web_20261124_01/selected9_offline.zip](http://134.175.18.101/vln/codex_memory_selected9_web_20261124_01/selected9_offline.zip)。

## 数据与协议

C01、C03、C04、C05、C11、C17、C19、C32、C34 共 77 个原始候选。新版 gpt-6-astra / medium，每例独立会话，先发送英文初始化，随后每轮仅发送当前候选的 −2/0/+2 前视图像，明确引用上一保留回退点的历史图像。先判断回退点资格，再判断支路重复。模型返回结构化结果，程序维护有效节点序列。

新版保留 24 个有效节点，删除 53 个，其中不符合定义 21、重复 32。不确定 4 次按实现中的保守规则保留，最终接受记录格式错误 0。有效逻辑轮次为 77 次候选判断及 9 次初始化，不包括历史中断与重试。最终来源见 source_results.json 及汇总 status.json 中的 SHA256。

同九例旧 Astra v002 保留 47，Qwen 保留 54。DeepSeek 仅 C04、C34 有结果，20 个原始候选保留 7，页面明确标注其余不可用。新版加入资格筛选且评审全部候选，旧版去重协议不同，保留数量不是准确率。

当前版 SR、平均 SPL 均暂无，已评分 0 条；配对原版 SR、平均 SPL 均暂无，已评分 0 条。

## 可视化与验证

沿用原去重模板，提供新版、旧 Astra、Qwen、已有 DeepSeek 的独立去除勾选及并集组合，原始候选开关、同步地图/RGB进度条、逐轮历史参照与当前图像、初始化与每轮提示词、资格判断和分支依据。默认中文，可切换 English，原始英文响应完整保留。315 条独立模型自然语言文本逐条翻译；实际输入、原始模型输出及筛选结果未因翻译改变。

browser_check.json 记录九例逐一验证，双语、模型筛选组合、原答、证据图像、进度条和移动端布局通过，页面错误 0。字体覆盖检查通过。发布完成 615 个文件的远端 SHA256 校验及公网 HEAD 检查，发布工具未执行公网浏览器检查。

## 产物

- 汇总 outputs/codex_tasks/checkpoint_dedup/v003/selected9_20261124_01/results.json
- 离线 HTML outputs/codex_tasks/checkpoint_dedup/v003/selected9_20261124_01/exports/selected9/index.html
- 在线目录 outputs/visualization_publishing/codex_memory_selected9_web_20261124_01
- 离线 HTML SHA256 `260dc7f578622e5c1729bc83b0998673e4096f5a255aff50646c562cf1a895ed`
- 离线包 outputs/codex_tasks/checkpoint_dedup/v003/selected9_20261124_01/exports/selected9_offline.zip
- 离线包 SHA256 `d75c8a8c717e3fc1079e77b8ef9019901a6c04cb59d9756a3e907f8cf129fa7a`
- 发布证据 outputs/visualization_publishing/publish_20261124_105659_936913/publication.json
- 导出脚本 scripts/export_codex_dedup_comparison.py，页面脚本 core/codex_dedup_comparison.js

保留之前 C01/C03 的独立导出和全部历史运行，不覆盖旧结果。后续为人工复核与协议比较，本次未启动新的推理或导航实验。
