# VLNVerse H1 · VLM 动作回退的 22 例样本集

当前使用[每例 7 张图的运行 02](../run_20261123_02/README.md)。以下为运行 01 的历史记录。

2026-11-23 UTC，样本集已完成。22 个 episode 覆盖 13 个场景，A/B 水平距离 1.619～6.011 米。供后续从历史报警位置 B 出发，依靠模型输出的离散动作走回有效存档节点 A。

[22 例索引 CSV](cases.csv) · [数据包总清单](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_01/manifest.json) · [C03 模型参考输入](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_01/cases/C03/reference.json) · [C03 仿真状态](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_01/cases/C03/simulation.json)

## 样本与版本

使用[原 22 例冻结清单](../../v001/run_20261122_03_rgb22/cases.csv)的案例、顺序、scene、episode 和 A/B 帧。seed 为 2，源清单从 v006 首次报警中选取原始 A/B 水平距离至少 1.5 米的点对。后续[倒走实验](../../v002/run_20261122_01_backward_rgb22/README.md)使用同批点对。

每条取 A 至 B 的全部原始动作，按动作边界均匀抽取含 A、B 在内的 5 张原生前视 RGB。仿真端单独保存历史 B 状态和 A 位姿。工作区 Git 基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，样本集随附实际构建脚本、原仿真配置和来源 SHA256。

## 构建

从仓库根目录运行以下离线命令。重建时指定新的输出目录。

```bash
python3 -B outputs/inverse_rollback/vlm_action_v001/run_20261123_01/source/prepare_vlm_rollback_dataset.py outputs/inverse_rollback/vlm_action_v001/run_20261123_01
```

## 如何读取一个案例

- 按总清单 `cases` 中的 `reference` 打开模型参考输入。`actions[0]` 把机器人从 F(A) 带到 F(A+1)，最后一个动作对应 F(B−1) 到 F(B)。`observations` 给出帧号、角色、PNG 路径和 SHA256；图片路径相对该案例目录。5 帧取去程动作区间的 0%、25%、50%、75%、100% 处，遇到半步取较大帧号。C03 从 F25 到 F45，参考帧为 F25、F30、F35、F40、F45。
- 用 `simulation` 读取 seed、episode、scene、B 的根位姿、19 个关节的位置和速度、相机位姿及历史环境偏移。复现沿用[前序 H1 初始化](../../../../outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22/source/run_inverse_rollback.py)：在同一 episode 的新环境中站立热身 500 个物理步，将 B 的世界位置加上新旧环境偏移之差，写入 B 的完整四元数和关节状态。历史根线速度、角速度缺失，沿用原实验的全零设置；低层控制器沿用热身状态。历史仿真时刻和步号仅用于帧对齐。
- `target_A.robot_pose` 供后续测量实际回退误差。VLM 的固定参考材料取自 `reference.json`。后续第一轮还要在 B 实际掉头后采集当前 RGB，此后每执行完一组动作再采集当前 RGB。这些实时观测在未来运行时产生。

## 构建结果

已核对冻结的案例顺序、完整动作序列、A/B 状态和 110 张原生前视 PNG 的 SHA256。共 538 个历史动作，其中前进 391、左转 67、右转 72、STOP 8。8 个 STOP 分别通向 8 个历史终止帧 B，索引用 `historical_B_terminal` 标记。重建这些 B 时直接装载其物理状态，历史 STOP 只作去程记录。

总清单 SHA256 为 `01c1437646832f5d83dc9eab89b73deb19d3dfbdfcee71063cd2f18f035a59ae`。本次完成范围为离线数据构建，VLM 控制与 H1 回程均待后续实验。
