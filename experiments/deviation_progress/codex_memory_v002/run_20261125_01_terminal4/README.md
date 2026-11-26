# 终止节点评审与 JEV v002 精简候选，四例

2026-11-25 准备。目标是核对最后有效节点到真实终止观测的偏航。仅处理 VLNVerse 冻结 seed 2 的 C17、C43、C23、C20。选路资格及去重为 v006.1。GPT-6 Astra 常规档、medium，每例独立会话，4 个并发工作进程；使用已确认的 17982 代理，CPU 调用远端 Codex。首次有效报警停止该例。评审输出为离线模型判定。

已有非终止帧 JEV 分数使用官方采样回放入口 `--version v002 --mode active` 逐条生成候选。END 使用数据集中该轨迹的最后一张原生前视图，独立于采样、资格与去重，不增加额外区间抽帧。偏航轮均只发送文本。若此前已报警，记录为提前停审，不再请求终止帧。输入与来源哈希见 [input.json](input.json)。基线 `e40d9a821ee72516261ee819284e36be7be2eff1`，实际筛选、偏航、客户端源码及工作区差异由运行入口冻结到输出 source/。

首次冻结清单：`.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v002/run_20261125_01_terminal4/prepare.py`。使用冻结清单启动：

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_codex_node_dedup.py \
  --input experiments/deviation_progress/codex_memory_v002/run_20261125_01_terminal4/input.json \
  --output outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_01_terminal4 \
  --model gpt-6-astra --reasoning-effort medium --workers 4 --timeout 1800 \
  --proxy-url http://127.0.0.1:17982
```

运行状态与逐例原答位于 `outputs/codex_tasks/deviation_progress/codex_memory_v002/run_20261125_01_terminal4`。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。

15:30:56 UTC 已启动，主管 PID 1357286，4 个独立 case 均已进入初始化。C17/C43/C23/C20 的 v002 原始候选数依次为 10/6/3/3，真实终止帧为 F91/F58/F32/F47。终止图像哈希、最后节点到 END 的传入进度、零图片偏航轮和报警回退目标的本地定向检查通过。

## 完成结果

15:45:06 UTC 完成 4/4，技术跳过 0 条。处理全部 22 个原始候选，17 轮纯文本评审（6 轮初始化、11 轮区间判断）。4 条轨迹均报警，3 条在 END 首次报警。随后已导出并发布[指定模板回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html)与[离线 ZIP](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/replay.zip)。[导出记录](exports/map_layers_01/README.md)。

| 案例 | 首次报警与回退目标 | 模型依据 | 已有事后错选区间 |
| --- | --- | --- | --- |
| C17 | F68→END/F91，S09/F68 | 直行穿过门槛进入卧室，指令要求在走廊尽头右转入室。 | F70–F76 |
| C43 | F30→END/F58，S04/F30 | 最后停在卧室床头柜旁，与客厅大窗前的停靠要求冲突。 | F24–F29 |
| C23 | F7→F17，S02/F7 | 实际沿电视柜位于左侧的路线前进，指令要求保持电视柜在右侧；首次报警后停审。 | F8–F14 |
| C20 | F41→END/F47，S03/F41 | 继续深入客厅并停在座位区，与在卧室书桌和六边形置物架旁停下的要求冲突。 | F21–F25 |

归因区间仅在模型调用结束后用于对照。回退目标是报警区间起点，未执行物理回退。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。
