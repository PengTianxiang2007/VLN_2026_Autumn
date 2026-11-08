# StreamVLN → VLNVerse 复现审计（2026-11-02）

**结论：当前实现确实复用了官方 StreamVLN，适合作为明确披露协议的 RGB 入口跨环境适配基线；尚不能无条件认定为无缺陷、与 StreamVLN 原论文 Habitat 评测流程完全等价的复现。**

本次检查主仓库提交 `7d8e64564239635dbf1f8287cd9d76ba4cc91775`，并核对正在运行的
`outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/code` 源码快照。
快照基底为 `e93c9d95f30597c116bca681cf106c90f56c7378`，另有 manifest 明示的结果导出和可视化更新。
没有修改正在运行的模型、推理、仿真、评分代码，没有重启实验，也没有下载权重或重新安装环境。

## 1. 实测检查及边界

| 检查 | 结果 |
| --- | --- |
| 对照官方 StreamVLN 提交 `e48f6ff7e9201d93aae003e8f64b04c00cec13bc` 的全部 160 个受版本控制文件 | 主仓库和运行快照均有 159 个逐字节一致；1 个 Habitat evaluator 仅有结果文件读写修正 |
| 实际使用的 `streamvln_agent.py`、`stream_video_vln.py`、视觉塔及 LLaVA 代码 | 与上述官方版本逐字节一致 |
| 运行快照 manifest 的 1,443 个文件哈希 | 全部匹配 |
| 四个模型分片的已有完整 SHA256 记录与作者 Hugging Face 页面 | 四个均一致；本次同时检查全部 15 个模型/视觉资源文件的大小、mtime、inode、device，未变化，未重复读取大权重计算全量哈希 |
| 模型配置与 `config.upstream.json` | 仅 `mm_vision_tower` 从模型名改为本地路径 |
| 现有 CPU 测试 | 21/21 通过 |
| 新增 CPU 控制流探针 | 常规队列、跨 32/64/96 步历史采样、episode reset、对齐边界的变长序列通过；另成功复现一个错位窗口缺陷，见第 2 节 |
| 已完整结束的 seed 0、1 | 各 250 条，唯一 ID、完整 scene 清单匹配；逐条重算 SR/NE/SPL 均匹配 |
| seed 0、1 的 48,758 条动作记录 | 没有队列提前生成、错误出队、步号跳跃或 smoke 强制 STOP；实际模型导入路径均在快照内 |
| 每条任务都有模型动作记录 | 不成立：两个 seed 各有一条预热摔倒任务；详见第 5 节 |

只核查了已完整结束的两个 seed，没有把部分运行当作五 seed 完成，也没有新增 GPU 评测。
新探针使用实际冻结方法体和 CPU 张量，图像预处理器、tokenizer、模型输出受控替代；
它们验证接口和控制流，不证明真实模型输出与 Habitat 入口等价。
旧 `../reproduction_audit/stream_real.json` 的真权重检查比较的是 RGB 入口加队列驱动，
不是与官方 Habitat evaluator 独立进行的等价验证，不能扩大其证明范围。

机器可读证据位于 [outputs/audits/streamvln_20261102](../outputs/audits/streamvln_20261102)：
`artifact_checks.json`、`source_comparison.json`、`control_probes.json`、
`short_sequence_checks.json`、`cpu_tests.log`；两个探针脚本也一并保存。

## 2. 代码缺陷：变长动作序列错过窗口边界时缺少 memory 图像

定位：

- `backbone/streamvln/vlnverse/adapter.py:56`：每完成 32 个动作清空缓存及 `time_ids`。
- `backbone/streamvln/streamvln/streamvln_agent.py:202`：缓存为空且非首步时加入 memory token。
- 同文件 `:224`：只有推理恰好发生在 `step_id % 32 == 0` 时才传入历史图像。
- `backbone/streamvln/streamvln/model/stream_video_vln.py:133`、`:224`：单张图时 memory feature 为 None，但遇到 memory token 时仍进行索引。

**可复现条件**：先生成 3 个非 STOP 动作，此后每次生成 4 个动作。
推理步号为 `0, 3, 7, …, 31, 35`。第 32 个动作后缓存清空，下一次推理发生在第 35 步，
提示词包含 memory token，输入却只有当前一张图。实际多模态拼接方法报
`TypeError: 'NoneType' object is not subscriptable`。

这是继承自上游窗口处理条件的潜在缺陷，并非迁移时重写模型造成。过去的变长队列测试
只覆盖“下一次生成恰好落在 32”这一类情况，不能覆盖此例。

**现有结果影响**：已检查 seed 0、1，没有发现错位窗口生成。
其中 145 / 127 次非四动作输出全部包含 STOP，因而未继续进入这个失败路径。
不能据此宣称当前 500 条结果被该缺陷污染，也不能宣称所有可能输出均安全。

后续应在独立版本中让“缓存重建”和“历史图像装配”使用同一窗口状态，验证 memory token
与历史特征成对出现，并测试窗口中途耗尽队列。不要在当前五 seed 实验中途改变算法。

## 3. 原版忠实度：官方 RGB 入口不等于官方 Habitat evaluator

适配器直接调用官方 `streamvln_agent.py`，不是自行重写一个近似 StreamVLN。
BF16、FlashAttention2、贪心解码、单 beam、32 步窗口、8 个历史帧、原动作解析和完整动作队列均保留。
`num_future_steps=4` 是原配置，不是把所有输出硬截成四个动作；这一点与官方驱动相符。

但官方仓库的两个入口本来就不同：

| 行为 | 当前采用的官方 RGB agent | 官方 Habitat evaluator |
| --- | --- | --- |
| 图像提示连接语 | 固定列表第一个 | `random.choice` |
| 重新打开窗口时的历史提示语 | `You have visited these areas` | `These are your historical observations` |
| 队列仍有动作、不生成新输出的步骤 | 复用上一次预处理图像加入历史 | 每步预处理并记录当步 RGB |
| 32 步缓存重置 | adapter 补齐生成当步的重置分支 | 主循环每 32 个动作重置 |

对应代码：`streamvln_agent.py:126,177,206`；`streamvln_eval.py:274,300,351,429`。

图像缓存差异不是在每条轨迹上都影响模型输入。若非终止输出一直为四动作，历史采样位置
也落在每四步的生成位置，CPU 探针验证了 32/64/96 步的对应关系。
但在允许的变长队列中，差异能传入 memory：受控输出长度 `6,25,1,3` 时，第 32 步的历史
实际为 `[0,0,6,6,6,6,6,6]`，逐步新图的对应位置应为 `[0,4,8,12,16,20,24,28]`。
这说明两入口并非一般意义上的等价实现；本次不声称该差异已经改变现有成绩。

RGB-only 本身不是丢掉有效深度模态：当前官方 `encode_rgbd()` 的实际视觉计算使用图像，
没有使用传入的 depth、pose、intrinsic 值。服务仅把 RGB 和指令传给 `agent.step()`，
未发现目标位置、参考路径或成功标签进入模型推理。

**论文命名建议**：保留当前实现时明确写“StreamVLN official RGB-agent adaptation”，
同时说明使用 v1_3 benchmark checkpoint。若目标是最大程度对齐原论文的 benchmark 推理流程，
应以官方 Habitat evaluator 的提示词、观测历史和生成循环为参照，建立单独的忠实适配版本，
并在固定 RGB 序列上比较 token、历史帧索引、生成参数及真实权重动作输出。不能仅凭代码来源一致跳过这一步。

## 4. 评分口径：当前官方代码的成功不要求 STOP

当前 `vln_pe_metrics.py:116` 使用最终 XY 距离 `<3m` 判断成功，未联合检查 STOP、fall 或 stuck。
这一逻辑与本次查询到的 [VLNVerse 上游指标实现](https://github.com/sihaoevery/vlnverse_emr/blob/vlnverse/vlnverse/projects/internutopia_vln_extension/metrics/vln_pe_metrics.py) 一致。
但 [VLNVerse 论文附录 B](https://arxiv.org/html/2512.19021v1#A2) 的 SR 定义要求发出 STOP。
因此不能把两种口径直接混称。

| 已完成 seed | 当前代码 SR | 正常 STOP 且成功的比例（诊断） | 被代码计成功的 fall / stuck |
| --- | --- | --- | --- |
| 0 | 98/250 = 39.2% | 87/250 = 34.8% | 11 条 |
| 1 | 99/250 = 39.6% | 92/250 = 36.8% | 7 条 |

右侧比例按 `fail_reason == 'success'` 重算，现有 task 代码仅在正常 STOP 且到达阈值时赋该值。
它是附加诊断，不能覆盖原始官方代码评分，也不是与 Habitat 测地距离 SR 完全相同的指标。
这些任务已经发生，故这不是纯理论差异。

建议保留原始评分，论文明确标注“VLNVerse released-code SR”，附正常 STOP 成功率、FR、StR，
并对所有对比方法使用同样的规则。如要改用论文文字中的 SR，所有方法都需统一重算并说明。

另外，上游 `_calc_ndtw()` 实际实现为到参考点集合的最近距离高斯分数均值，没有 DTW 的顺序对齐；
当前导出不包含 nDTW。将来不能直接把该字段当标准 nDTW 报告。

## 5. 真实发生的预热失败与验收缺口

`kujiale_0259_12_3` 在 seed 0、1 中均于 500 次预热物理更新后以 `fall` 结束。
两次都有 episode seed/reset 记录，但没有任何模型动作记录。
最终高度分别约 0.235m / 0.255m，保存的轨迹只有初始点与结束点；仿真日志支持预热终止的判断。

这两条按当前环境协议被保留为失败，符合完整 scene 不挑任务的要求。
**不可将它们描述成模型完成导航后失败，也不能为了提高成绩删除它们。**
对比实验需要采用统一的起始状态有效性规则；若要修复初始化，应独立冻结协议并重评所有方法。

`scripts/export_vlnverse_results.py:47` 只检查存在的 trace 内容，没有要求每个结果都有 trace 或
明确的预热失败证明；这两个 scene 的 `validation.json` 仍是 `passed=true`。
因此这个标志目前只能证明导出规则通过，不能证明每条任务都运行过模型。
后续验收应分别统计 `model_evaluated` 和 `pre_action_environment_failure`，并验证后者的终止证据。

这也解释了两条 OS 重算差异：保存轨迹的初始点已在阈值内，但官方 OS 只在 `finish_action`
时更新最近距离，预热末端已经离开阈值；把所有保存点（含初始点）取最小距离会得到不同结果。
其余 498 条的保存路径 OS 重算匹配，500 条的 SR/NE/SPL 全部匹配。

## 6. 可以支持的论文结论与仍需补齐的条件

当前 250 条覆盖所选 10 个 scene 在 fine val_unseen 的全部任务，抽样清单与 825 条原始标注核对通过。
它是一个预先冻结的场景子集，不等于 825 条全集，更不是 test split。
五个 seed 是固定 checkpoint 的五次带种子评测，不是五次独立训练；贪心输出不变时差异主要来自环境执行。
当前规则固定种子但不保证 GPU 物理/渲染逐位确定性。

H1 physical 模式、640×480 原有 RGB、目标 0.25m/15° 的离散控制器、每动作 50 个物理 tick、
200Hz 物理、25,000 tick 限制和 500 tick 预热均应在方法/附录中记录。
这是具备物理执行误差的控制，不能宣称每步实际恰好移动 0.25m 或转 15°。
上游部分 fine baseline 配置使用 flash 与 256×256 观测，不能将其成绩直接当作相同设置的对照。
此次确认了相机 USD 路径与分辨率，未单独读取运行中相机的 FOV/外参，不能声称与 Habitat 79° 视场相同。

当前结果可保留，用途是**已有官方 RGB 适配协议下的真实跨环境结果**。成为论文中的正式表格前，应：

1. 明确选择 RGB 适配还是 Habitat 推理忠实版本，写清与原始入口的差异；变更版本不能与旧结果混算。
2. 固定并披露 SR/OS/SPL 口径、物理/flash 模式、传感器和初始化失败处理；全部比较方法一致。
3. 对潜在窗口缺陷加入独立回归验证，并记录任何修复；当前冻结实验不要中途替换算法。
4. 五 seed 全部完成后验收 1,250 个唯一 `(seed, episode_id)`，报告每 seed 和跨 seed 均值、样本标准差。
   对同一批 scene 的反复评测不能当成 1,250 个独立场景样本；比较方法使用相同 scene 和 seed。
5. 归档源码/权重/数据哈希、依赖版本、配置、每条结果、重试/预热失败记录与可视化版本。
   当前运行快照已有文件级哈希；VLNVerse 上游 revision 和相机具体参数宜另补为明确的版本证据。

截至本次审计，查阅的 [VLNVerse v1 论文](https://arxiv.org/html/2512.19021v1) 没有 StreamVLN 成绩行。
所以应表述为“我们将 StreamVLN 适配到 VLNVerse 并评测”，不能写成复现了论文已报告的 StreamVLN-on-VLNVerse 数字。

## 7. 上游出处与复查命令

- [固定 StreamVLN 源码版本](https://github.com/InternRobotics/StreamVLN/tree/e48f6ff7e9201d93aae003e8f64b04c00cec13bc)
- [官方 RGB agent](https://github.com/InternRobotics/StreamVLN/blob/e48f6ff7e9201d93aae003e8f64b04c00cec13bc/streamvln/streamvln_agent.py)
- [官方 Habitat evaluator](https://github.com/InternRobotics/StreamVLN/blob/e48f6ff7e9201d93aae003e8f64b04c00cec13bc/streamvln/streamvln_eval.py)
- [作者 v1_3 checkpoint](https://huggingface.co/mengwei0427/StreamVLN_Video_qwen_1_5_r2r_rxr_envdrop_scalevln_v1_3/tree/main)

在仓库根目录使用已有环境；命令只读既有实验，输出写入审计目录：

```bash
python3 outputs/audits/streamvln_20261102/audit_artifacts.py
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  backbone/streamvln/.venv/bin/python outputs/audits/streamvln_20261102/probe_streamvln.py
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 \
  benchmarks/vlnverse/.venv/bin/python -m unittest discover -s tests -v
```
