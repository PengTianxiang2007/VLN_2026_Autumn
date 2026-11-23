# RxR-CE 原版 StreamVLN，400 条逐帧 RGB

2026-11-23 UTC。运行状态及结束摘要见 [status.json](../../../../outputs/reproduction/streamvln_rxr/run_20261123_01/status.json)，原生评测逐条写入 [result.json](../../../../outputs/reproduction/streamvln_rxr/run_20261123_01/result.json)。

## 目的与协议

获得原版 StreamVLN 的 RxR-CE 子集成绩，为随后逐条分析选错分支、门口或转弯等失败保留证据。本批全部任务由原版自主导航。

从 val_unseen 的 3,669 条英语 Guide 指令（en-US、en-IN）中，按 11 个 MP3D 场景的任务数比例以最大余数法分配 400 条。每个场景按 episode ID 整数排序，用同一个 Python Random(2) 随机源按场景名顺序无放回抽取。以指令 episode 为单位；同一路线可能有多条不同指令。[冻结任务清单及各场景配额](episodes.json)。

沿用 v1.3 权重和仓库 RxR evaluator、Habitat 配置 seed 100、贪心生成、原始历史和动作队列、每条最多 500 步、3 米成功阈值。seed 2 仅用于抽取任务。记录初始状态和每次原生动作后的 640×480 前视 PNG，包括原地转向和终止观测。每条 trace 记录动作、机器人与 RGB 相机位置、xyzw 四元数、朝向和终止标记。episode.json 附原指令和 Guide 参考轨迹。所有记录直接来自同一次导航。

原生逐条指标保留 SR、SPL、OS、NE、nDTW。报告有效评分中的 SR 和全体有效评分的平均 SPL，含失败；非有限指标保留原值并另列 ID，不作为选路失败归因。历史 oLBMNvg9in8 场景存在起终点不连通的已知异常，本批仍按冻结清单运行。

## 启动与产物

从项目根目录执行，空闲 GPU 3 同时运行模型和 Habitat。

2026-11-23 00:12:08 UTC 后台启动，tmux 会话 rxr400，主管 PID 544027，评测进程 PID 544245。启动时 GPU 3 可用显存 48,511 MiB，无其他计算进程。

00:28:14 UTC 已确认正常导航与采集，转交后台。当前版与原版为同一次原版运行，双方 SR 均为 1/1（100%），平均 SPL 均为 0.9183。episode 298 执行 157 个动作，以 STOP 结束，共 158 帧，步号及图像路径完整，首帧与终止帧均为 640×480 原始 RGB。episode 311 进行中，技术异常 0 条。[启动确认](../../../../outputs/reproduction/streamvln_rxr/run_20261123_01/startup.json)

```bash
python3 -B scripts/run_rxr_rgb_subset.py prepare run_20261123_01 --count 400 --sample-seed 2
tmux -L peng_rxr400_20261123 new-session -d -s rxr400 'exec python3 -Bu scripts/run_rxr_rgb_subset.py run run_20261123_01 --gpu 3 >> outputs/reproduction/streamvln_rxr/run_20261123_01/launcher.log 2>&1'
```

Git 基线 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。本轮新增样本过滤与观测记录，评测子进程使用冻结的 evaluator。采集器、启动器、数据读取和指标代码、原生配置与文件哈希存于 [source/](../../../../outputs/reproduction/streamvln_rxr/run_20261123_01/source/)。[运行目录](../../../../outputs/reproduction/streamvln_rxr/run_20261123_01/) 内的 run.log、status.json 和 result.json 可用于接手；逐条结果的 capture 字段指向该次已评分轨迹。

2026-11-23T05:33:40+00:00 · 224/389 成功，平均 SPL 0.49146400566375814，技术异常 11 条，共保存 52675 帧。
