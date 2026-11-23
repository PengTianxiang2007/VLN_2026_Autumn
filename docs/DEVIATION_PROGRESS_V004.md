# v004 基于当前子任务约束的偏航识别

[完整中文系统 Prompt](../experiments/deviation_progress/v004/prompt_zh.txt) 是实际发送的文本。[完整英文对照](../experiments/deviation_progress/v004/prompt_en.txt) 用于阅读。每个有效节点触发一次联合评审。模型从完整原指令和 A 处可信进度识别当前适用的子任务，在同一份回答中判断实际通行是否冲突，并在可以确认时更新累计进度。

## 如何判定

1. 从可信进度找出首个尚未确认完成的要求，保留限定它的地标、方向、侧别、入口及顺序。已完成的地标可帮助定位。未来要求在相应阶段才生效。若新证据与历史矛盾，保留疑点并重新判断受影响的阶段。
2. 独立描述输入帧中发生的事件。把看见空间、朝向入口、从指定侧经过、穿过入口、进入和停止分别判断。图像左右会随转头改变，单帧可见物体也可能属于相邻空间。
3. 将实际行为与当时生效的要求对照。地标有助于确认选择发生在指定位置。进入目标空间的里程碑还需要实际进入的证据。进入未在原指令中提到的空间，要结合当前指令才能解释其是否冲突。目标缺失、节点数量、经过时间均不能单独证明走错。片段内有足够证据完成一项时，按顺序继续检查随后已经发生的行为。
4. 已定位的明确通行冲突给出 `deviated`。后续遮挡或尚未到达终点不能抹去早先的明确冲突。若阶段、路口身份、是否真正穿门等关键疑点足以改变本段结论，给出 `uncertain`。有正面观测支持与当前约束相容、且没有关键选择待解时，给出 `consistent`。这包括仍在按要求沿通路前进且尚未到达下一地标的情形。

| 与 v003 对照 | v004 的具体变化 |
| --- | --- |
| v003 已区分看见与进入，也允许无新增完成项时给出 consistent | 先确定阶段，再独立描述行为，再检查适用约束。把运动证据、约束适用位置和判定理由逐项联系起来 |
| v003 从整段经历、已有进度和完整任务综合判断 | 对发生时生效的要求逐段比对。检查明确冲突后，再看其余不确定性是否会改变冲突的成立 |
| v003 使用自由格式的累计摘要 | 中英文累计文本分为已完成、当前、待执行，按需追加未决事项。跨节点保留限定词，允许 A 前移而当前子任务继续 |
| v003 已校验英文摘录在原指令内逐字连续 | 提示先选最短充分引文，逐条回查。分散证据分条摘录，继续保留原始回答及校验结果 |

## 每轮输入、时间与进度

输入来自与 [v003](DEVIATION_PROGRESS_V003.md) 相同的离线轨迹与去重节点。去重前的原始候选只可能以普通观测被抽样。保留节点重新编号，按 v003 协议追加终止观测。模型仅收到完整英文指令、A 的可信中文进度、区间模式、端点编号与帧号、取图说明和带时间/角色的原生前视 RGB。地图、位姿、参考路线、结果标签、JEV 分数和推理时刻之后的图像均不进入消息。

首次有效节点 A=B，仅提供单帧，可能晚于 F0。以 `consistent` 建立当前环境，并明确此前路线进度未知。常规节点在 `emittedAt` 确认可用，这批轨迹为 B+5。终止节点在终止帧立即可用。取图始终截止 B，端点必取，开区间中最多均匀取五帧，不重复补帧。若有 n>5 张中间帧，使用 Python 的 `round(i*(n-1)/4)` 选索引，i=0…4。以新版本自己的 A 取图，两版本在相同 B 上可能具有不同的起点和中间帧。

| 本轮结果 | 可信 A 与累计语义进度 |
| --- | --- |
| consistent，有新里程碑 | 提交截至 B 的双语进度，A 更新到 B。已完成的要求移入 Completed，Current 接续下一项 |
| consistent，无新里程碑 | A 同样更新到 B，Current 保留原要求和限定条件，可补充有证据的局部状态 |
| uncertain 或回答格式错误 | 保留 A 和原可信进度，下一节点重新取 A 到新 B 的观测。格式错误单列并保存原答 |
| deviated | 记录 A、其帧号和原可信进度作为回退目标，本条离线评审结束。该轮不提交任何中途完成的子任务 |

这次离线评审记录回退目标。物理回退与后续导航属于原有的恢复系统。

## 输出及校验边界

v004 校验器接受模型在顶层原样回显的格式标记 `"type": "json_object"`。原答完整存档，九个任务字段仍逐项校验。DeepSeek C47 S04 经修复后正常触发偏航与回退目标记录。[修复回放](../experiments/deviation_progress/v004/run_20261120_03_contract_replay/README.md)

九个顶层字段沿用原接口。`previous_id`、`current_id` 对齐输入端点。`verdict` 使用三类枚举。`segment_summary` 写实际观察，`reason` 说明当前适用要求、观察、冲突是否成立及判定依据。`instruction_evidence` 最多三段英文原文及各自中文翻译，偏航至少一段。`visual_evidence` 提供一至三项事实及本轮实际整数帧号。`uncertainties` 始终为双语条目数组。

`semantic_progress` 在 consistent 时为 `{"zh": "...", "en": "..."}`，两个语言各自依次包含 `已完成 / 当前 / 待执行` 和 `Completed / Current / Pending`，每段有内容，空集可明确写“无”。影响后续判断的未决问题追加至双语进度中。每轮只向下一轮传递已提交的中文文本。uncertain 和 deviated 都要求返回 JSON 的 `null`。静态校验检查 JSON、字段类型、枚举、逐字引文、端点、帧号以及进度标题与非空内容。两种语言描述是否忠实、地标识别和运动推断是否正确，仍需要审阅原答和实际图像。

## 实现与复现

- [v004 入口、进度校验及回放核查](../scripts/run_deviation_progress_v004.py) 从历史去重结果装入节点，运行时冻结代码、Prompt、配置、输入清单哈希及实际提交。
- [共用区间评审器](../scripts/run_deviation_progress_review.py) 执行原有抽帧、存档、状态推进与首次偏航停止。v004 显式传入本地服务和自己的回答校验器。
- [CPU 回归用例](../tests/test_deviation_progress_v004.py) 覆盖模型请求白名单、两种 Prompt、连续引文、假帧号、初始化、进度结构和多轮状态转移。
- [本次运行、六条轨迹和逐轮数据](../experiments/deviation_progress/v004/run_20261120_01/README.md) 登记实际 GPU 配置、进度及已验证范围。
- [DeepSeek 并行入口](../scripts/run_deviation_progress_v004_deepseek.py) 使用同一 Prompt、节点、图像采样和回答校验，各进程仅处理自己的轨迹。[六条离线对照与启动命令](../experiments/deviation_progress/v004/run_20261120_02_deepseek6/README.md)

在仓库根目录执行下列 CPU 命令。输出目录取一个新路径。

```bash
.runtime/crossing_vllm27/bin/python -B -m unittest discover -s tests -p 'test_deviation_progress_v004.py' -v
.runtime/crossing_vllm27/bin/python -B -m unittest discover -s tests -p 'test_serial_pipeline.py' -v
.runtime/crossing_vllm27/bin/python -B scripts/run_deviation_progress_v004.py \
  --check-only --cases 1 2 6 7 11 14 23 30 47 50 \
  --output outputs/deviation_progress/v004/reproduce_cpu_01
```

六条离线轨迹的本地模型复现命令如下。模型使用同一份 Qwen3.8-27B-FP8 权重，temperature=0，top_p=1，seed=2，max_tokens=8192，关闭 thinking，输出 JSON object。每条轨迹在自身的首次有效偏航处停止，实际调用上限为 39 次。入口在 GPU 2 可用时启动，结束后清理本次服务。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004.py \
  --local-qwen --cases 7 11 19 30 47 50 --gpu 2 --allow-shared-gpu \
  --gpu-memory-utilization 0.70 --max-model-len 16384 \
  --output outputs/deviation_progress/v004/reproduce_qwen6_01
```

## 局限

最多七张稀疏前视图可能遗漏真正的分支选择。连续 uncertain 会让可信锚点停留在较早位置，区间增长后仍最多七帧。首次初始化可能错过此前的真实路线，已提交的错误进度也可能影响后续阶段。报警只能定位到 A→B。历史归因标签和模型报警数量都不能单独给出偏航准确率，六例诊断也不能估计全样本误报率或导航恢复收益。
