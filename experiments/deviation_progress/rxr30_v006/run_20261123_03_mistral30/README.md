# RxR30 · Mistral DeepSeek 两轮各30进程

2026-11-23 18:16 UTC，全部30条的[DeepSeek双语可视化](http://134.175.18.101/vln/rxr30_deepseek_full_web_20261123_01/index.html)已发布；[导出与验证记录](exports/full_20261123_01/README.md)。支持逐帧RGB、有效节点、完整两轮评审及独立偏航红线。

状态：已完成，2026-11-23 17:42:12 UTC。用户明确要求用Mistral供应商的deepseek-v4-1-flash-1017并发几十个进程，随后补充第一轮去重也重新跑。

## 方法与范围

复用既有RxR随机30条、4,465帧、JEV的4,435个分数和725个原始候选。第一轮用DeepSeek重跑v001双位置分支去重，最多30个独立案例进程，各例内部顺序处理。全部30条成功产出后，冻结本次有效节点与追加终止节点，再用30个进程运行v006偏航识别。第二轮只读本次DeepSeek节点；不混入Qwen节点或原答。首次有效偏航停止该例，格式错误按原协议处理，不重试语义结论。

去重沿用最多8步比较、每处中心与±2帧、same删旧留新、uncertain保留两处。偏航沿用实际原始英文指令、中文累计进度、A/B端点和最多5张均匀中间观测、九字段双语回答。输入原图哈希、实际请求、完整原始响应、进度与事件逐例保存。

模型：`deepseek-v4-1-flash-1017`。端点：`https://api.mistral.ai/v1`。两轮显式`reasoning_effort=high`、`max_tokens=32768`、JSON object、非流式，其他采样参数沿用供应商默认，未指定模型seed。任务清单seed2，原导航Habitat seed100。Mistral官方目录实际确认vision与reasoning能力。供应商内容数组只取text块供现有JSON校验器解析，thinking块及原始响应完整存档；不修改模型结论或现有状态机。

服务器直连Mistral不可达，通过用户指定且已验证连通的`http://127.0.0.1:7892`代理发送。凭据仅存Git忽略的本地0600文件，通过stdin交后台主管；不进入命令行参数、实验记录、日志或网页。HTTP 408/429/5xx或连接错误最多六次有限退避；认证/权限/请求格式错误停止后续调用。所有尝试另存，禁止无限重试。

本批仅CPU工作进程调用远端API，`CUDA_VISIBLE_DEVICES`为空，不占本地GPU。已有Qwen运行和结果保持独立。去重预检使用第一例第一个真实比较；通过后原答直接复用到正式批次，不重复计费。

## 启动

```bash
.runtime/crossing_vllm27/bin/python -B scripts/run_rxr_mistral_semantics.py prepare
.runtime/crossing_vllm27/bin/python -B scripts/run_rxr_mistral_semantics.py preflight
.runtime/crossing_vllm27/bin/python -B scripts/run_rxr_mistral_semantics.py launch
```

输出：`outputs/deviation_progress/rxr30_v006/run_20261123_03_mistral30/`。Git基线与实际未提交源码副本见manifest.json和source/。status.json统计两轮完成案例数；dedup/cases/Cxx/state.json及deviation/run/cases/Cxx/state.json记录在途进度。supervisor.log保留并行日志。确认批次正常进入任务后交后台，不持续追踪。

无新导航评分：当前版及配对原版SR、平均SPL均暂无，已评分0条。30条来源原版SR 0/30（0%）、平均SPL 0，属于预选失败样本。偏航报警数量不是准确率。

供应商参考：[模型说明](https://docs.mistral.ai/models/deepseek-v4-flash-1017)、[reasoning_effort与内容数组](https://docs.mistral.ai/inference/conversations/reasoning)。实际兼容性以本次真实输入原答为准。

准备记录：实际Git基线`7ce5f9fee30686bae304425bc84c36b3fbedc39c`，30条/725原始候选已冻结。内容数组适配的针对性CPU检查通过，未改动原去重、偏航状态机及校验规则。供应商模型目录HTTP 200；首个正式可复用去重请求已HTTP 200、格式有效，耗时103.464秒，原答直接复用于C01/S02。

启动确认：主管PID 2081596，实际30个子进程、30个案例均已进入去重，31份请求元数据已落盘（含复用预检）。当前阶段dedup，整例完成0/30，偏航尚未开始；确认到此交后台，不等待所有模型回答或任何整例完成。两轮仅用远端API，新进程不使用本地GPU，未停止或重启Qwen任务。后续查看status.json和各例state.json。


## 最终结果（2026-11-23 17:53 UTC 查询确认）

16:55:14 UTC启动，17:42:12 UTC完成，两轮合计46分58秒（不含103.464秒预检）。去重30/30：725原始候选→295有效节点，删除430个，另加30终止节点；656次比较，71次uncertain，0格式错误。

偏航30/30：23条有效模型报警（76.67%）、7条未报警。共137轮，107 consistent、23 deviated、7 format_error。报警比例不等于准确率。对已有离线归因的时间比较为11条报警可用时刻在参考决策步前、3条位于决策至确认区间、9条在确认之后、7条无报警；这只是时序比较，不是自动真伪判定。

状态complete、failed_cases为空、workers_exited=true，主管2081596已退出。仅使用远端API，无本批本地GPU服务需要释放。原Qwen独立任务继续。全部原始请求、原答和有效节点保留；本次进度查询未重跑模型或重新发布网页。

轻量结果见final_summary.json，逐例偏航汇总见输出deviation/v006_results.json，时序对照见timing_comparison.json。当前版及配对原版SR、平均SPL均暂无，已评分0条。
