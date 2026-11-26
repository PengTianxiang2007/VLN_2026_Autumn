# VLNVerse 前十条错误轨迹：Codex 候选去重

状态：完成；2026-11-23 21:47 UTC。用户确认五帧前视输入，并明确要求十条并行。

## 目的与方法

在已采集多视角的 53 条错误轨迹集上运行 C01–C10 全部原始候选的第一轮去重。
复用既有 JEV 候选，模型为 Codex CLI 的 `gpt-6-astra / medium`，每轮超时 600 秒。
每条轨迹一个独立工作进程、独立会话；轨迹内按时间顺序显式 exec/resume。
十条同时运行，不把同一轨迹的候选比较并行。

只使用 A/B 各自 -2…+2 的原生前视图，初始缺图如实标记；不加入 180°/360°辅助图。
同前版 8 步比较限制和 same 删旧留新协议。输出只含第一轮有效节点，不追加终止节点，
不启动偏航识别、回退导航或新 JEV 采样。格式错误保留双方；传输失败停止该轨迹，其余独立轨迹继续，失败单列。

输入轨迹 seed=2；Codex 无固定采样 seed。本批没有导航评分，也不将候选减少量当作去重准确率。
实际代码、原提示词、Git 提交、工作区差异及哈希由运行入口保存在输出 status.json 与 source/。
并发入口新增 --workers，其余模型/去重协议沿用已通过真实两轮测试的 v001。

## 冻结样本

按原 `dataset/subsets/all_selected.txt` 前十条，合计 89 原始候选、63 次模型比较。

| Case | Episode | 原始候选 | 模型比较 |
|---|---|---:|---:|
| C01 | kujiale_0036_0_0 | 5 | 3 |
| C02 | kujiale_0036_3_2 | 15 | 12 |
| C03 | kujiale_0036_52_4 | 6 | 5 |
| C04 | kujiale_0113_18_1 | 15 | 13 |
| C05 | kujiale_0113_1_4 | 10 | 8 |
| C06 | kujiale_0123_fix_13_3 | 10 | 4 |
| C07 | kujiale_0123_fix_19_3 | 4 | 2 |
| C08 | kujiale_0123_fix_43_3 | 11 | 6 |
| C09 | kujiale_0128_fix_12_4 | 6 | 5 |
| C10 | kujiale_0128_fix_18_1 | 7 | 5 |

输入与来源哈希：[input.json](input.json)。上游原始候选为
`outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/candidates.json`。
数据集为 `outputs/offline_route_dataset/v001/run_20261118_01/dataset/`。

## 启动命令

```bash
.runtime/crossing_vllm27/bin/python -u scripts/run_codex_node_dedup.py \
  --input experiments/crossing_checkpoint/codex_dedup_v001/run_20261123_02/input.json \
  --output outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_02 \
  --workers 10
```

复用用户指定 Codex 二进制及 CODEX_HOME /mnt/nas/gezuhao/PengTianxiang/.codex。
只调用远程 Codex，不占本地 GPU，不修改共享环境或服务。
每轮原始输入/输出、图片及会话映射在独立运行目录保存。

## 产物与状态

- 输出：`outputs/codex_tasks/checkpoint_dedup/v001/run_20261123_02/`。
- 启动及主管日志：`outputs/codex_tasks/checkpoint_dedup/v001/launches/run_20261123_02/`。
- 总进度 status.json；逐例 cases/Cxx_ep<episode>/state.json；逐轮 codex/turns/。
- 成功结果 results.json，失败列 failures，不将失败任务计为完成。
- 当前版 SR / 平均 SPL：暂无，已评分 0 条；配对原版 SR / 平均 SPL：暂无，已评分 0 条。

## 验证与下一步

新增并发调度的定向检查通过：三个假 CLI 工作进程实际并行、三个独立会话、有序汇总；未重跑无关测试。
运行后记录十条实际状态、去重数量、调用错误与历史路径。

## 实际启动记录

启动时间：2026-11-23T21:37:28.067781+00:00；主管 PID `2417949`。
十个工作进程已进入 C01–C10，各建一个独立 Codex 会话，独立 thread ID 共 10 个。
核对时间：2026-11-23T21:38:24.038450+00:00；证据为输出 `startup_check.json`。
后台进程独立于当前终端，完成/失败自动更新状态及汇总，原始记录持续落盘。

## 最终结果

21:47:38 UTC 完成，运行约 10 分 8 秒。十条共 89 原始候选，保留 56 有效节点、删除 33 个；63 次比较，4 次 uncertain，0 格式错误、0 传输失败。
独立会话共 10 个，主管及其工作进程已正常退出；完整原答及历史保留。[逐例摘要](summary.json)。
用户随后授权制作多模型去重对照可视化，记录见 [导出](exports/compare_20261123_03/README.md)。

三模型去重对照已[发布](http://134.175.18.101/vln/codex_astra_route10_dedup_compare_web_20261123_03/index.html)，提供模型独立勾选和完整离线包。
