# RxR30 DeepSeek 两轮完整可视化

状态：已发布，2026-11-23 18:16 UTC。用户要求将DeepSeek版导出可视化。

使用本次Mistral DeepSeek/high的全部30条结果：725原始候选、295有效节点及30终止节点、656次去重比较、137轮偏航评审；23条有效模型报警、7条未报警，7轮无效回答单列。节点及偏航均来自本次DeepSeek，原版轨迹与4,465帧RGB复用既有采集。删除候选不显示为节点。

沿用RxR双进度条回放，提供JEV、最终节点、逐次去重的A/B输入和完整理由、逐轮偏航的输入/语义进度/原答、复核意见与离线ZIP。独立勾选偏航后，按实际from_frame/to_frame遍历原轨迹并染红，未通过校验的原答不产生红线。原始服务端响应随raw/归档，页面读取最终回答文本。

默认中文，支持English。去重中文理由补译英文仅用于展示，偏航沿用原答已有双语，不改实验输入、提示词、原答或校验结论；截断回答明确标注未形成最终答案，不补写模型结论。翻译任务使用同一供应商模型，独立保存于display_translation_202/，不计作实验推理。

```bash
.runtime/crossing_vllm27/bin/python -B scripts/export_rxr_deepseek_snapshot.py prepare
.runtime/crossing_vllm27/bin/python -Bu scripts/export_rxr_deepseek_snapshot.py translate
.runtime/crossing_vllm27/bin/python -B scripts/export_rxr_deepseek_snapshot.py build
```

输出目录与本记录同构，位于outputs/；来源哈希、实际导出源码、翻译原答和浏览器检查留存。新版本发布至用户指定服务器，保留历史网站与实验原件。发布按docs/VISUALIZATION_PUBLISHING.md的已有online_manifest流程执行。

本轮无新导航评分：当前版及配对原版SR、平均SPL均暂无，已评分0条。原版来源30条SR 0/30（0%）、平均SPL 0，是已筛选失败样本。模型报警数量不等于准确率。


## 准备与授权记录

全部30条数据、325个节点（295有效＋30终止）、793份原始模型响应已冻结，页面独立偏航红线、原答下载、截断回答提示与浏览器校验脚本已准备，JS语法通过。当时完整导出与浏览器验收待英文译文齐备，后续已完成，见下文。

2013段待译内容均逐字来自本次已授权Mistral原答；本地证据见translation_authorization_evidence.json。45批具体请求及哈希见translation_request_plan.json。当时翻译网络请求尚未发送。自动审批两次拒绝翻译调用，理由是既有实验及可视化授权不明确覆盖这批文本再次发送Mistral用于翻译，已向用户请求明确确认。未绕过审批、未改用其他外部服务；未发布不完整双语网页。


用户最新确认：“允许。并行几百个进程一口气做”。翻译保持同一2013段文本、同一Mistral端点与模型，改为202个进程、每批最多10段同时执行。原45批本地请求计划保留，未发送；新翻译日志独立存display_translation_202/。


## 已完成导出与验证

202个工作进程的翻译已全部完成并退出，2013段新增展示译文，加上24段复用或固定程序说明，共2037条双语文本。没有记录到HTTP限流或服务端重试。所有译文只影响页面展示，原始实验793份响应逐份保存，未重跑实验。

浏览器验证通过：30条实际节点清单合计295有效＋30终止，全部23个有效报警区间逐边匹配原位姿轨迹；独立红色开关可显示/隐藏，A/B跳帧正常。代表性6例检查中文/English、same/different/uncertain去重详情及7轮无效回答相关状态，包含无最终回答的输出截断。全部793份最终回答文本与原始响应一致；390px移动端无横向溢出，JS错误0。证据见validation.json及输出validation/截图。

本地入口index.html，快照数据snapshot_public.json，完整离线包rxr30_deepseek_full_offline.zip（239769472字节）。实际源码及哈希见build.json与输出source/。

## 发布完成

2026-11-23 18:16:03 UTC 发布完成：[在线回放](http://134.175.18.101/vln/rxr30_deepseek_full_web_20261123_01/index.html)；[完整离线 ZIP](http://134.175.18.101/vln/rxr30_deepseek_full_web_20261123_01/rxr30_deepseek_full_offline.zip)。旧版网站保留。

标准发布脚本核对全部 2225 个远端文件的 SHA256，公网入口 HEAD 返回 HTTP 200；未重复全量公网下载。本地浏览器验收结果见 validation.json，发布清单见 publication.json，完整发布记录为 `outputs/visualization_publishing/publish_20261123_181416_448999/publication.json`。

入口 HTML SHA256：`3b044b3f6bdd93afcadef84b6f865a281b9c9a9d805613d8f8e21f678022148c`。

离线 ZIP SHA256：`f20d9624b65d04e9788d22683a471dac3653d08da6ceee7892c21cdbe5cf1e89`。
