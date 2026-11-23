# 69条本轮导航失败：归因、事件标定与离线数据集

53 条入选任务的[逐步回放](http://134.175.18.101/vln/offline_route53_replay_web_20261118_01/index.html)已发布，支持分别勾选实际路线、参考路线及同步多视角观测。详见[可视化导出记录](exports/replay_20261118_01/README.md)。

状态：已完成。用户2026-11-18授权开始；2026-11-18T05:17:33Z完成独立数据包验收。

## 目的与输入

分析`outputs/multiview_capture/v001/run_20261117_03`的69条原生SR=0任务：older48来源34条，newer56来源35条。35条本轮成功不进入失败筛选。原生104条评分及全9891观测/79128多方向图完整性校验均已通过；seed=2，原采集21场景，本次失败及入选任务覆盖19场景。来源采集含辅助渲染且未证明与无辅助渲染运行行为一致。

早期48条来源为`outputs/checkpoint_review/seed2_crossing_attribution_20261103/attribution_reviews.json`的归因候选；新56条来源为`experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/selection.json`。两批无重叠；不使用人工33条集缩减，不将旧标签当作新轨迹的答案。

## 筛选结果

| 来源 | 本轮总任务 | 成功 | 失败 | 纳入 | 排除 | 不确定 |
|---|---:|---:|---:|---:|---:|---:|
| 早期48（older48） | 48 | 14 | 34 | 25 | 8 | 1 |
| 新56（newer56） | 56 | 21 | 35 | 28 | 5 | 2 |
| 合计 | 104 | 35 | 69 | 53 | 13 | 3 |

53条分为明确分支核心集43条（早期21、新22）和方向扩展集10条（早期4、新6）。不是将所有偏离参考线的轨迹自动归为错误分支。

| 入选类别 | 数量 | 子集 |
|---|---:|---|
| 漏掉应有转弯 | 24 | branch_core |
| 选错房门 | 12 | branch_core |
| 选择错误通路分支 | 7 | branch_core |
| 开放区域方向错误 | 6 | direction_extension |
| 初始行进方向错误 | 4 | direction_extension |

入选任务最终终止方式为未到目标46条、跌倒6条、卡住1条；选路错误与最终终止原因分开记录。50条标为高置信度、3条中等置信度（`kujiale_0147_57_1`、`kujiale_0226_14_2`、`kujiale_0258_35_1`）；置信度是审核等级，不是校准概率。

共标定54个入选事件。`kujiale_0036_3_2`有两次不同方向选择：先走向客厅错误方向，回到门口后再进错误卧室。`kujiale_0294_43_3`一直未离开初始卧室，反复穿越几何阈值按一次持续错误方向事件处理，不虚增独立路口次数。

排除13条：局部无效动作6条、接近评分阈值但未完成路线的停止3条、无确认选路错误的跌倒2条、正确通路卡住1条、沿原路线回返1条。完整逐例解释见[审核笔记](review_notes.tsv)与[小体积清单](selection.json)。

不确定3条不进入主集：

- `kujiale_0036_43_0`：门口约0.8米内转回初始卧室，局部无效动作和错误方向选择难以区分。
- `kujiale_0159_50_0`：曾进入错误卧室，后已面向正确走廊再卡住，失败与早期错误的关联不清楚。
- `kujiale_0285_2_3`：末段偏离与身体失稳交织，step78俯仰已22.3度，不能确认独立选路错误先于跌倒。

## 方法与版本

结合官方指令/参考路线、完整真实逐步位置/朝向、原生前视及多方向关键帧逐条审阅。69张轨迹图和69组默认关键帧均已查看，另对12条生成并查看补充帧；不是逐帧人工审核全部RGB。几何偏离只生成候选时刻，不能自动充当失败原因。主类别与最终终止方式分开；保留多次错误及恢复情况的说明。单纯反向沿原路回返、未走完停止、局部无效移动、无路线错误证据的跌倒/卡住、目标越过和不确定单列，不能全部纳入选路错误。

入选要求：实际错误方向/支路或漏转弯有轨迹和视觉证据，发生在任务失败之前，且与未完成指令有可解释关联。事件提供决策时刻/确认时刻及不确定区间、真实位姿/朝向、沿参考路线的正确方向与实际离开方向。标注者为Codex，性质为事后离线归因，不是人工共识或反事实因果证明；无法确认的样本不强行纳入。

审核轨迹图的`D`只表示首次超过0.75米几何偏离阈值，`M`表示最接近目标的位置，`G`表示目标；`D`不是最终错误决策标注。最终事件以`evaluation/episodes/`中的事件字段为准，不能从候选几何标记直接生成真值。

事件字段包含代表性决策step、选择区间、确认错误step、两个时刻的完整位姿/朝向与仿真时间。决策step和确认step均检查为实际查看过的关键帧。例如`kujiale_0207_69_4`早期26步只是卧室内横向偏移，实际事件使用32–48区间、代表step40，避免误用首个0.75米阈值触发帧。

正确方向字段是从实际位置指向“参考路径最近投影弧长前移1.25米点”的几何方位，带相对当前朝向角度；实际离开方向按决策到确认帧的水平位移计算。此标定不含执行可达性/碰撞验证，不是已验证Oracle落点。

公共分析/打包代码为`scripts/prepare_multiview_failure_review.py`、`scripts/build_offline_route_dataset.py`，读取器为`core/offline_route_dataset.py`，独立验收脚本为`scripts/validate_offline_route_dataset.py`。实际Git提交`7ce5f9fee30686bae304425bc84c36b3fbedc39c`，工作区有既有未提交修改，本次没有覆盖其他工作；源码与SHA256在输出`source_audit.json`及数据包`code/`、`SHA256SUMS`冻结，独立验收脚本另存输出`code/`。输入历史记录只读，保留模型/仿真不操作。

## 启动方式

使用仓库现有`benchmarks/vlnverse/.venv/bin/python -B`，离线CPU分析，无新增GPU任务/API请求。

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_multiview_failure_review.py --output outputs/offline_route_dataset/v001/run_20261118_01
benchmarks/vlnverse/.venv/bin/python -B scripts/build_offline_route_dataset.py --analysis outputs/offline_route_dataset/v001/run_20261118_01 --notes experiments/offline_route_dataset/v001/run_20261118_01/review_notes.tsv
benchmarks/vlnverse/.venv/bin/python -B -m unittest discover -s tests -p test_offline_route_dataset.py -v
benchmarks/vlnverse/.venv/bin/python -B scripts/validate_offline_route_dataset.py outputs/offline_route_dataset/v001/run_20261118_01/dataset --report outputs/offline_route_dataset/v001/run_20261118_01/delivery_validation.json
```

首次打包在公共NAS上受串行文件元数据操作限制，仅终止了已核验命令行/工作目录/UID的本次CPU打包PID3472117；源图、部分打包内容、日志均保留。随后以8个有界文件线程、`--resume`继续同一未完成包，文件存在时核对inode、清单签名必须相同。没有停止导航模型或仿真。

定向5项CPU测试已通过：历史截断且不读取未来记录、180度排序/原生前视区分、越界与路径逃逸检查、跨参考折角的lookahead、角度环绕与终点截断。

## 离线产物

输出：`outputs/offline_route_dataset/v001/run_20261118_01/`。独立数据目录为其下`dataset/`，已通过检查并从临时目录转为正式目录；没有遗留`dataset.building/`。

- `cases.json`、`source_audit.json`：69条新轨迹、原始数据来源与哈希核验。
- `maps/`、`visual/`、`refine_evidence.json`：全部轨迹图及关键帧证据。
- `dataset/manifest.json`：53任务、54事件、19场景、4890观测时刻和协议。
- `dataset/inputs/`：原始任务指令、每个step的180度/360度/前视索引、完整机器人和相机位姿/朝向、时间、过去动作。
- `dataset/evaluation/`：69条分类、排除理由、选中任务参考路线/轨迹/当前动作/事件答案。
- `dataset/subsets/`：53条全集、43条明确分支核心集、10条方向扩展集。
- `dataset/provenance/`、`dataset/code/`：原始采集元数据、来源审计、冻结源码。
- `dataset/validation.json`、`dataset/SHA256SUMS`：检查结果与迁移校验清单。

图片复用已验证原PNG，不依赖外部软链接；180度三图是360度八图中的+45/0/-45度硬链接别名。全部观测含初始和终止，4890观测对应4837个实际导航动作。原生前视4890张、多方向39120张，独立PNG共44010张，另14670个180度路径别名。JSON和标准库读取器即可离线使用，不需要模型或仿真。原图硬链接不可原位修改，加工先复制新文件。本次没有新HTML或对外发布。

## 验收与体积

打包检查53/53通过，完整校验所有入选step的位姿/朝向、物理冻结、180度/360度对应、图片来源及因果读取边界。辅助PNG复用原采集已通过的全量SHA256证明，并检查修改时间和源/目标inode一致；4890张原生前视及新元数据重新计算SHA256。

独立验收再次读取全部53条输入和事件记录，核对58680个PNG路径索引，重新计算434份元数据/审核图文件与267张PNG抽样的哈希，检查159对180度别名。复制真实任务前两步、图片及标准库读取器到独立临时目录，前视/180度/360度三种读取均通过；该目录没有evaluation/provenance或仓库依赖。不是本轮再次全量读回所有辅助图。验收明细见输出`delivery_validation.json`及本目录[验证摘要](validation.json)。

PNG独立文件字节数为10,384,196,699（9.671 GiB）；全部数据包保留硬链接关系时文件内容合计约9.801 GiB，普通逐路径复制而不保留别名硬链接时约13.033 GiB（不含文件系统目录/块开销）。本地图片硬链接复用原图，以上是搬迁数据量，不是新增图片磁盘占用或运行内存。

数据包`manifest.json` SHA256：`bcf64509c87b55cabc667964253509595e1983f188f737d59c907b0f19cdf3c5`；`SHA256SUMS` SHA256：`8a9c03d18a9169c213250d26e32b08b8d41123e4cd62b440ef83e61295bdc189`。

## 限制与下一步

离线数据集初版已可使用。标定以step为单位并提供事件区间；正确参考方向不等于验证过的可执行纠正动作。尚未经人工共识复核，3条不确定保留在全69条审核清单中、没有纳入53条主集。未预设训练/验证划分；同场景多条指令共享几何，后续划分需要单独记录。仅准备数据，不启动模型评测或干预实验，不与既有人工33条标签混报。
