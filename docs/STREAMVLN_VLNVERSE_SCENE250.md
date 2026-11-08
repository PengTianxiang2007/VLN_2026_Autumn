# StreamVLN / VLNVerse：完整场景五 seed 复现

2026-11-02 的[实现与论文可用性审计](STREAMVLN_VLNVERSE_AUDIT_20261102.md)指出：本实验采用官方
RGB agent 适配，与官方 Habitat evaluator 不完全等价；评分保留发布代码的 XY 距离成功规则。
报告结果时还应披露预热失败及尚未触发的变长动作窗口缺陷，不能仅凭 `validation.json` 的
`passed` 声明所有任务都完成过模型推理。审计没有修改此实验的冻结推理和评分。

用户于 2026-11-01 批准启动。范围为 fine/val_unseen 的 10 个完整 scene，250 条不同任务，
seed 0、1、2、3、4 使用同一清单，总计 1250 次评测。完整 scene 指该 split 内的全部任务。
本次子集结果不能当作 825 条全集结果。

| Scene | 每个 seed 的任务数 |
| --- | ---: |
| kujiale_0036 | 25 |
| kujiale_0113 | 25 |
| kujiale_0123_fix | 25 |
| kujiale_0207 | 23 |
| kujiale_0208 | 25 |
| kujiale_0232 | 25 |
| kujiale_0234 | 32 |
| kujiale_0240 | 23 |
| kujiale_0257 | 23 |
| kujiale_0259 | 24 |
| 合计 | 250 |

选择规则：scene ID 排序后使用独立抽样 seed 20261101 打乱，在 10 个完整 scene、合计
250 条的组合中选择打乱顺序排名元组最靠前的一组。选择不参考模型输出。准备阶段将验证
本地标注仍与已批准的表格一致，冻结 250 个 episode ID 和标注内容 SHA256。

## 推理与种子

使用既有 StreamVLN_R2R_v1_3、视觉编码器、环境和共享数据，离线加载，不运行安装或下载。
保留 RGB 推理、贪心解码、提示词、历史缓存、完整动作队列和既有评分公式。
H1 physical：640×480 RGB、500 warm-up ticks、25000 physics ticks 上限。

`--seed` 传递到模型服务及物理评测进程。每条任务种子为
`int.from_bytes(SHA256('sha256-episode-v1:<run_seed>:<episode_id>')[:4], 'big') % (2**31 - 1)`。
仿真任务初始化使用该种子设置 Python、NumPy、PyTorch、Isaac 和 Replicator 的已有种子入口；
模型服务在每条任务 reset 时使用同一派生种子，服务回执与最终指标均记录种子。
相同 run seed 和 episode ID 在进程重启后保持相同派生值；不承诺 GPU 物理/渲染逐位确定性。
保持原有贪心解码；不同 seed 的结果可能相同，照实报告。
不传 `--seed` 时保留迁移初始版本的默认种子行为。

## 后台执行

`scripts/reproduce_streamvln_vlnverse.py prepare` 创建独立 campaign 目录，保存 Git 提交的
源码快照、源码 SHA256、既有模型文件 SHA256、运行环境位置和 50 个 seed × scene 单元。
快照仍复用主项目已配置的解释器和 Isaac，不复制环境、不修改共享权重或数据。
后续运行使用快照中的源码，主目录后续编辑不会改变已冻结代码。

用户进一步授权所有卡按实际空闲资源并行使用。`run` 默认最多两组，每卡最多一组；
只有空闲显存至少 34000 MiB、连续两次检查利用率不高于 15% 的卡才接收新任务，
同时要求主机可用内存至少 64 GiB。组内每次仿真重启前仍检查显存。
资源不足时队列等待；程序错误会记录失败并停止本队列，保留已评分任务。
CUDA 设备可见性和 Isaac Vulkan 的物理设备编号分别配置：模型/物理使用所选卡的
CUDA 映射，渲染通过 `--/renderer/activeGpu` 显式绑定同一张物理卡，禁用跨卡渲染。
runner 原有内存预算机制在 episode 边界重启，以 LMDB 跳过已评分任务。
崩溃未完成的任务使用同一 seed 重试；已有有效评分不重跑、不挑选最好成绩。
首个完整 scene 必须通过 ID、数量、种子与评分核验后，才会自动进入余下 49 组。

准备与运行方式（`<campaign>` 和 `<fingerprints>` 为实际本地路径）：

```bash
python3 scripts/reproduce_streamvln_vlnverse.py prepare --campaign <campaign> --fingerprints <fingerprints>
python3 <campaign>/code/scripts/reproduce_streamvln_vlnverse.py run --campaign <campaign> --max-workers 2 --allow-shared-gpu
python3 scripts/reproduce_streamvln_vlnverse.py status --campaign <campaign>
```

只有协调后才可指定 `--allow-shared-gpu`，不停止其他用户进程。可用 `--gpus 0 1` 限制卡范围和优先顺序。
恢复使用同一 `run` 命令，完成的 scene 跳过，未完成的 run 由保存的清单和种子继续。
若需要修改运行代码，保留本次快照及结果，明确记录新版本，不混合不同实现的成绩。

## 结果与体积控制

默认每条任务最多保存两张初始 RGB，保留紧凑动作 JSONL、位姿轨迹、指标和恢复所需 LMDB。
2026-11-02 用户追加要求：为 seed 2、3 各完整 250 条任务启用可视化，用于后续错误分析。
其余 seed 继续使用默认记录。具体文件格式和入口见 [可视化复盘说明](VLNVERSE_VISUALIZATION.md)。
目录内 `status.json` 是即时状态，`first_scene_gate.json` 是首场景验收，`episodes.csv` 是
已完整验收场景的逐任务结果，`summary.json` 保存逐场景/逐 seed 指标。
五个 seed 全部完成后才计算跨 seed 均值和样本标准差（n=5，ddof=1）。
主要指标 SR、SPL、NE，附 OS、TL、FR、StR；SR/SPL/OS/FR/StR 为 0–1，NE/TL 为米。
每个 seed 恰好 250 个唯一 episode，50 组全部通过才标记整项复现完成。
