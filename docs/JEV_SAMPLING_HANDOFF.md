# 后续联合评审更新（2026-11-12）

同一分支已追加节点触发的偏航判断与累计语义进度 v003，完整34案例已归档。
当前方法、实际提示词、首次偏航停止规则、已知误报以及独立本地网页恢复命令，见 [DEVIATION_PROGRESS_V003.md](DEVIATION_PROGRESS_V003.md)。
下文节点采样/去重网页保留原用途；联合评审网页直接显示最终有效节点和终止节点，无去重开关。

# 当前版本更新（2026-11-12）

已保存全部34条节点去重结果及五条节点消除v001/v002历史。详细协议、结果与限制见 [版本快照](../experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/README.md)。原合并和导出命令不变；导出自动包含两项审核开关、提示词、结果及运行脚本，无需重新调用模型。图片仍从原ZIP取得。

去重共298候选保留165，删除133；每次删除旧节点、保留新节点。同case顺序执行，case之间并行。已完成结果只是语义待复核的候选子集，不代表导航收益。完整节点展示取代下文旧版按进度显示的历史描述。

# JEV 在线采样 v001：另一台机器接手入口

更新：2026-11-12。用户已认可当前采样方法，并要求将其提交到 GitHub 分支 `codex/jev-online-sampling-v001`，供主要开发机器合并。

## 当前状态与用户要求

目标流程是 **连续 JEV 反馈 → 在线采样 → 潜在回退点 → 后续大模型审阅**。本分支完成滤波/采样参考实现、固定样例、命令行回放和本地网页导出；已完成本地记录数据的大模型节点消除与去重审核；尚未修改机器人实时运行循环。

另一台机器存在尚未同步到 GitHub 的开发内容。请以那台机器的实际工作区为准寻找接入点，保留未提交、未推送的工作。本分支基线为 `df32de50a5981b3d2175ae927ed2ca7ab50888f7`，不代表那台机器完整的最新状态。

用户对本轮工作明确要求：**后续离线在本地迭代，通过网页查看；不要发布到外部网页服务器。** 本次 GitHub 源码分支提交已获授权。该本地要求是根 AGENTS.md 发布规则中的用户后续例外，不需要为本轮网页运行发布脚本。

网页的当前确定行为：

- 保留 JEV 地图、RGB、同步双进度条、波形和复核意见；移除 Qwen4B 展示和多种旧滤波选项。
- 曲线区只有「JEV 原始概率」「滤波结果」，默认开启；勾选滤波不会开启采样。
- 采样版本有独立勾选项，默认关闭。勾选 v001 才在波形和地图上同步显示 S 编号；取消后同时隐藏。
- **波形与地图路线始终完整显示**。进度条移动当前帧标记、切换 RGB；已确认采样点及审核结果也始终完整显示，不受回放进度影响。

## 文件与职责

| 文件 | 用途 |
| --- | --- |
| `core/jev_online_sampler_v001.js` | 用户认可的固定版本：原始概率逐帧输入，滤波＋采样，返回新输出 |
| `core/jev_online_filter_v001.js` | 同一数值规则的独立滤波器，供网页仅看滤波时使用 |
| `core/jev_online_sampling_v001.json` | 默认参数；与采样器 defaults 一致 |
| [JEV_SAMPLING_V001.md](JEV_SAMPLING_V001.md) | 算法、时间语义、输入输出及边界规则 |
| `scripts/replay_jev_online_sampling.cjs` | 无模型依赖的回放命令，可作为移植对照 |
| `tests/fixtures/jev_online_sampling_v001.json` | 固定原始分数与参考输出，含33条记录轨迹和8组合成情形 |
| `tests/test_jev_online_sampling.cjs` | 一致性、延迟、前缀不变性、间距及有限状态检查 |
| `core/jev_sampling_lab/` | 本地网页模板和版本注册入口 |
| `scripts/export_jev_sampling_lab.py` | 从已有数据包/HTML生成独立离线网页 |

这些是可直接合并的独立模块与工具，未假设另一台机器上尚未同步的运行接口。当前参考实现为 JavaScript，没有暗含一份已集成的 Python 实现。

## 合并和本地验证

合并前先记录工作区状态，并将需要保留的未提交修改保存为本地提交或 stash。已有未推送提交可以保留在当前分支。不要为接入而执行 hard reset 或覆盖整份仓库。

```bash
git fetch origin
git merge origin/codex/jev-online-sampling-v001
```

如有冲突，保留目标机器的现有业务逻辑并加入本次独立模块；文档索引的新增条目也需保留。运行以下命令不需要 RGB、模型权重、GPU或网络。依赖为 Node.js 18+、Python 3.10+；本次实际验证 Node.js 25.5、Python 3.11。

```bash
node tests/test_jev_online_sampling.cjs
python tests/test_export_jev_sampling_lab.py
node scripts/replay_jev_online_sampling.cjs --input tests/fixtures/jev_online_scores_example.json --output outputs/jev_sampling_check_01/result.json
```

固定样例的参考输出在本次冻结时由用户认可的 v001 生成。测试运行不会重建参考答案。数值比较容差为 `1e-12`；候选位置、编号、确认时刻必须一致。v001 源码哈希按 UTF-8、LF 换行计算，兼容 Git 的 Windows 换行转换。

## 接入当前 JEV 运行循环

1. 在目标机器定位每次 JEV 概率返回的位置。每个 episode 使用独立采样器；参数在本次 episode 开始时固定。
2. 每收到一条新概率调用一次 `push(probability, frame)`。frame 从0连续递增；缺失反馈用 null 占位。已有评测的 image_frame/导航动作序号可以另外建立映射，不能把不连续序号直接当作本接口的连续 frame。
3. `result.filtered` 是本次新确认的曲线值；`result.node` 是本次新确认的候选。将候选追加到缓存、日志，并保留 `index`、`emittedAt`、概率、类型和对应图像引用。
4. **候选位置不是候选可用时刻。** 默认 F20 的候选在收到 F25 时才可使用；后续大模型审阅只能在确认后启动。生成候选本身不等于已判断走错，也不直接执行回退动作。
5. 先用固定样例及现有记录验证输出，再接入后续大模型队列。导航收益、候选准确率尚未建立，不用候选数量代替真阳性或任务成功数。

若主程序需要 Python/C++，按方法文档逐项移植，并使用同一 fixtures 比较滤波值和候选事件。保持时刻、边界与间距处理一致，通过后再连接实际运行循环；JavaScript CLI 可作为参考输出工具。

## 重建用户当前网页

大体积 RGB、地图和字体保留在已有离线数据包，不提交到这个源码分支。`tests/fixtures` 中的概率足以验证算法，但不足以还原带 RGB 的网页。

准备原数据包 `wrong_choices34_fullwave_site_20261109_05.zip`，或已解压的 `jev_noul_v004_vs_qwen4b.html` 及相邻 `assets/`。如果目标机器没有该数据包，复制这份已有文件即可，无需重新推理。

```bash
python scripts/export_jev_sampling_lab.py --source /path/to/wrong_choices34_fullwave_site_20261109_05.zip --destination outputs/jev_sampling_lab_run_01
```

Windows同样支持该命令，替换为本地路径。直接打开输出目录的 `index.html`；保留相邻的 JS 与 assets。工具拒绝覆盖已存在的目标目录，每次改用新运行编号。已有HTML也可作为 `--source`；ZIP有多份HTML时用 `--html-entry` 指明入口。

完整曲线来自 `app.js` 中独立的 `fullCurve()` 离线回放缓存，**不传入实时采样器**。`fullSampling()` 顺序回放原在线采样器后缓存完整节点，仅用于离线展示。移植时保留这种职责划分，不能为了显示全图而向真实运行中的采样器提前送入后续记录。

## 后续版本迭代

保留 v001 及其固定输出，在新文件实现 v002 等版本，并在 `core/jev_sampling_lab/app.js` 的 `SAMPLING_VERSIONS` 中新增定义。各版本拥有独立状态和勾选项；随后更新模板的脚本依赖及导出脚本的复制清单。始终默认不勾选采样，沿用波形/地图同步编号和完整轨迹展示。

本分支不启动历史导航实验，不恢复取消任务，不改变既有模型输入，不上传网页。下一步需要在目标机器的真实工作区完成运行循环适配，并由用户复核候选及下一阶段模型调用成本。
