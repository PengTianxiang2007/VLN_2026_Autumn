# 节点触发的偏航判定与累计语义进度：v003

2026-11-12 冻结当前实际方法与 34 个案例结果，交接分支为
`codex/jev-online-sampling-v001`。本次提交仅归档和提供本地重建工具，
不修改已运行的提示词、节点、模型答案，不启动新的导航或模型实验。

## 当前方法

1. 沿用 [JEV 在线采样 v001](JEV_SAMPLING_V001.md)，默认 N=7、D=5。
   去重规则见 [节点去重快照](../experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/README.md)。
2. 本轮直接使用最终去重后的有效节点，按轨迹重新编号为 S01、S02……。
   被删除的节点不参与判断链、进度维护或节点展示；原有 RGB 录像仍然存在，
   区间均匀取图可能取到同一时刻的普通观测，这不等于恢复该节点。
3. 把录像终止帧追加为最后一个节点；若已存在则不重复。终止节点立即可用，
   没有额外五帧等待，不伪造 JEV 概率。
4. 首个有效节点单图初始化，A=B；它可能晚于 F0。
   只描述当前语义状态，不能从单帧补认此前已经完成的导航步骤。
5. 后续每个新有效节点 B 触发一次联合评审，从上一个可信语义锚点 A 到 B。
   同一轨迹串行，不同轨迹最多六个进程并行。

当前实验基于已完成去重的冻结列表，是离线方法验证。尚未把去重替换、节点确认、
模型耗时与导航动作协调接入机器人实时循环；不能据此声称已完成在线部署。

## 一次调用输入什么

- 完整英文任务指令 `instruction_en`，不截断为局部子指令。
- A 处上一份可信的累计中文语义进度 `prior_semantic_progress`。
- A、B 的 ID 和实际帧号，初始化/普通区间模式，以及抽样覆盖说明。
- A、B 各一张 RGB，严格在二者之间均匀采最多五张 RGB，总计最多七张。
  观测带角色与真实帧号，按时间排列。

中间帧候选为 `A+1 ... B-1`；不足或等于五张时全取，不重复补帧。
超过五张时，候选长度为 n，取索引 `round(i*(n-1)/4)`，i=0..4，
实际 Python `round` 规则以冻结脚本为准。

判断截止 B 的中心帧，不使用 B 之后的图像。常规节点在其 `emittedAt`
才可用于判断；例如 F23 节点在 F28 确认，判断图像仍截止 F23。

实际调用的 system prompt 是中文
[prompt_zh.txt](../experiments/deviation_progress/v003/run_20261112_05/snapshot/run/prompt_zh.txt)，
[prompt_en.txt](../experiments/deviation_progress/v003/run_20261112_05/snapshot/run/prompt_en.txt)
是对应英文版本。中文 prompt 的 SHA256 为
`129ef91051dcb6cc1be8e2e276cb102166bff322a36fdd10661e644de2162cad`。

模型不接收地图、坐标、参考路线、人工 crossing/错误选择标注、任务成败、
JEV 分数、去重理由或未来图像。它们可存在于离线回放数据中，
但 API 消息通过字段白名单单独构建。

## 判断和进度怎么更新

提示词先要求概括已经经历的区间，再结合指令、已有进度判断空间、参照物、
空间关系和经历顺序。实际经历与累计进度是两个独立输出字段。

| 返回结果 | 语义进度与锚点 | 下一步 |
| --- | --- | --- |
| `consistent` | 提交截至 B 的累计 `semantic_progress`，锚点移到 B | 等待下一个有效节点 |
| `uncertain` | 保留原进度和 A，返回进度为 null | 下次判断 A 到新节点的合并区间 |
| 请求/格式错误 | 保留原进度和 A，不擅自修补答案或重试 | 普通错误继续下一节点；鉴权/额度错误停止该 case |
| `deviated` | 不提交新进度，记录 A 及其可信进度作为回退目标 | 标红 A→B 的实际路径，停止该 case 后续评审 |

语义进度回答“截至这里，总任务已经完成了哪些，正在执行什么，哪些还不能确认”。
它是累计自然语言摘要，不是本段动作复述，不输出百分比或固定子任务编号清单。
通常限制在约 200 个汉字，但这只是提示词约束，代码不进行字数截断。

完整输出包含 `previous_id`、`current_id`、`verdict`、`segment_summary`、`reason`、
`instruction_evidence`、`visual_evidence`、`semantic_progress` 和 `uncertainties`。
自然语言输出含中文及忠实英文翻译；格式校验检查端点、枚举、引用帧、原指令摘录等，
不能验证物体识别或运动推断在语义上是否正确。

因此标红区间可能跳过中间一次证据不足/技术失败的节点；这与节点被去重删除不同。
标红整个 A→B 是区间判定，不表示其中每一帧都已偏航，也不是精确的错误起始定位。
本轮只记录回退请求，没有执行真实回退、重新选路或续跑导航。

## 实际模型与结果

本轮使用 `https://api.deepseek.com`、`deepseek-flash`、thinking enabled、
reasoning_effort high、JSON object、max_tokens 32768、非流式；未指定 seed。
配置记录在 [manifest.json](../experiments/deviation_progress/v003/run_20261112_05/snapshot/run/manifest.json)。
这些是本轮实际配置，不保证模型服务未来仍使用相同模型实现。

- 34 个案例，33 条独立轨迹，9 个场景；case32/33 是同一轨迹的不同事件。
- 199 个有效节点，含 34 个终止节点。
- 复用 12 条既有案例的 40 次记录，包括 7 次失败；只补跑剩余 22 条。
- 新请求 74 次，有效 73 次；合计 114 次，有效 106 次、错误 8 次。
- 34 次初始化；40 次区间 consistent，33 次 deviated，5 次 uncertain。
- 85 个节点未评审，终止节点实际评审 7 个。首次偏航后保留录像，但不继续调用。

`valid` 指输出通过协议检查，`deviations` 指模型的判断数量，两者都不是准确率。
历史汇总中的 worker_processes=18 来自多批次不同 PID，并非同时运行 18 个进程；
本次补跑实际六个 worker。完整记录见
[run05 README](../experiments/deviation_progress/v003/run_20261112_05/README.md)。

## 已知问题：no31 提前误报

case31 在 S02(F13)→S03(F23) 返回 deviated。模型依据床、窗、电视柜居中或变大，
把门口朝卧室的观察推断成“已经深入卧室窗前”，并辅以未出现客厅参照物的判断。
事后对照位置，S02→S03 平面净位移约 0.46 米；S02、S03 到参考路径的最近平面距离
分别约 0.08、0.09 米。后续画面显示折叠门重新入镜，支持视角变化的解释。

S04(F43)→S05(F62) 则持续走进另一间卧室，距参考路线由约 0.11 米扩大至 2.79 米，
偏航证据明显。但 S03 的首次误报已停止后续评审，因此 S04→S05 没有模型判定。
人工 wrong_choice 标注在 F36，属于 S03→S04；它与后续明显偏离区间不是同一个概念。
以上坐标和人工标注仅供事后归因，没有进入模型输入。

现有中文提示词第 3、4、6、7 条已经要求区分看见/进入、转头/转入通路、
尚未到达目标/实际偏航，并在证据不足时 uncertain。因此问题包括视觉运动推断失误、
任务阶段对齐和过度确定性，不只是漏写一句提示词。未来收紧实际通行证据、
降低首次误报影响属于待研究方向；本次未实现、未重跑，不覆盖原答案。

## 分支接手与本地网页重建

在另一台机器先保留其未提交/未推送工作，再合并：

```bash
git fetch origin
git merge origin/codex/jev-online-sampling-v001
```

[snapshot/](../experiments/deviation_progress/v003/run_20261112_05/snapshot/)
保存原始网页源码、逐请求元数据/响应、结果、节点输入、prompt、配置与运行源码。
其中不包含 RGB/地图/字体资产；这些复用原 ZIP
`wrong_choices34_fullwave_site_20261109_05.zip`，无需重新推理。

从仓库根目录，用 Python 3.10+ 标准库即可恢复当前完整网页：

```bash
python scripts/export_deviation_progress_snapshot.py --source /path/to/wrong_choices34_fullwave_site_20261109_05.zip --destination outputs/deviation_progress_v003_review_01
```

也可将 `--source` 指向已有带 assets/ 的本地站点目录，或其中的 HTML。
直接打开新目录的 `index.html`；原始 JSON 查看同样离线可用。
导出拒绝覆盖既有目录，不调用模型、不发布网站，不修改历史结果。

`scripts/run_deviation_progress_review.py` 是实际 run05 runner 的逐字节副本，
模型调用依赖 `httpx`，API key 仅从 `DEEPSEEK_API_KEY` 或隐藏标准输入读取。
不要为查看结果运行它。新的模型实验需另建输入、manifest 和输出目录，保留历史记录；
归档内 prepare/derive/finalize 脚本包含当时 Windows 路径，仅作历史源码证据，
跨机恢复网页使用上述独立导出入口。

本轮在基线提交 `ccda30c25002f7b690313162cb573a51e3acca72` 上使用未提交脚本运行。
源码及其历史哈希随本次提交冻结，不能把本次提交写成历史模型运行时已使用的 Git 版本。
保留所有既有失败和复用记录，密钥不进入 Git。网页继续只在本地打开。
