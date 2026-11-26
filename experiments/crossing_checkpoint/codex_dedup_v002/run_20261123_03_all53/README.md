# VLNVerse 全 53 条 · GPT-6 Astra 三帧去重

状态：53条全部完成并已发布全集可视化。用户明确将原计划的十路队列改为剩余任务全部同时运行。

## 样本与协议

完整数据集 route_choice_multiview53_seed2_20261118_v001，53 条、494 原始候选、338 次比较。直接复用 [run_20261123_02](../run_20261123_02/README.md) 已完成的 C01–C10（89 候选、63 比较、57 有效节点）；本次只运行 C11–C53，共 43 条、405 候选、275 次比较。复用来源与哈希见 reuse.json。

沿用已验证 GPT-6 Astra / medium、每端 -2/0/+2 原生前视三帧、不超过 8 步才比较、same 删旧留新协议。每例独立新会话、例内按时间顺序 exec/resume；43 个独立进程同时调度，无十路并发上限。每轮 600 秒超时，技术失败单列，格式错误按原规则保留双方。轨迹 seed=2，Codex 无固定采样 seed。原始候选及图像不重新采样，不运行导航。

复用现有入口与已通过的三帧定向验证，仅新增输入清单和并发数量；未重复测试已通过逻辑。输入从冻结 candidates.json 与 dataset/inputs 元数据生成；不向模型提供任务指令、真值、参考路线或全景辅助图。实际源码、Git 提交和差异由入口归档。

## 启动

```bash
.runtime/crossing_vllm27/bin/python -u scripts/run_codex_node_dedup.py --input experiments/crossing_checkpoint/codex_dedup_v002/run_20261123_03_all53/input.json --output outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_03_all53 --workers 43 --model gpt-6-astra --reasoning-effort medium
```

启动前确认无重复去重进程，MemAvailable 约 339 GiB；只使用本项目 CPU 进程及远程 Codex，不占本地 GPU，不更改共享环境。

输出：`outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_03_all53/`。status.json 的 target_cases=43；全量完成数为 10 + completed_cases。新会话在 cases/Cxx_ep<episode>/codex/turns/，已完成十条历史保留原位。

## 完整交付

新结果与复用十条按 episode ID 合并为 aggregate_all53/，逐例标明源运行；成功凑齐 53 条后导出完整网页。沿用既有模板和默认三帧选项，保留旧 Astra 五帧 10/53、Qwen 53/53、DeepSeek 10/53（C04/C08/C12/C34/C40/C41/C44/C48/C49/C51）。未覆盖项标为未评审；独立去重勾选、原始候选、三帧证据、中英文原答及同步进度条保留。按标准流程另存发布版与离线包。

当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条；本轮没有导航评测。

## 推理完成

2026-11-23T22:59:23.389512+00:00 开始，2026-11-23T23:13:07.774614+00:00 完成，主管 PID 2554729。新增 43 条：405 候选→251有效节点，275次比较、22 uncertain、0格式/调用错误。C28 的候选间隔均超过8步，按协议无模型比较；其余42条各有独立新thread。

合并已完成十条后：53条、494原始候选→308有效节点，删除186；338次比较、26 uncertain、0格式/调用错误。完整结果在输出 aggregate_all53/，逐例 source_run 及源文件 SHA256 保留。已按用户指定模板完成与 Qwen 全集对照的双语可视化。

## 可视化交付

[完整53条在线对照](http://134.175.18.101/vln/codex_astra_three_frame_route53_compare_web_20261123_01/index.html) · [完整离线ZIP](http://134.175.18.101/vln/codex_astra_three_frame_route53_compare_web_20261123_01/all53_20261123_01_offline.zip) · [导出记录](exports/all53_20261123_01/README.md)。默认Astra三帧，独立去重勾选、模型原答、中文/English及双进度条同步；保留旧Astra五帧和DeepSeek的真实覆盖范围。

同批494原始候选：Astra三帧保留308，Qwen五帧保留376；保留数量不等于准确率。本次Astra 0调用失败、0格式错误，所有推理进程已退出。53例页面交互检查通过；2026-11-23T23:32:42.323357+00:00 标准发布完成，4860文件远端SHA256通过，公网入口HTTP 200。

当前版及配对原版SR、平均SPL均暂无，已评分0条；未运行导航评测。
