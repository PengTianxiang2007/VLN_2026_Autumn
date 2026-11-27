# kujiale_0208 / kujiale_0240 完整场景后续队列

最终状态：20:08:35 UTC，因两路前置均技术失败，本队列阻塞退出，新增导航启动 0 条。用户授权修复后使用 [run06](../run_20261126_06_scene0208_0240_high_after_nodefix/README.md)接修复后的新前置；本轮不恢复、不重复启动。

日期：2026-11-26 UTC。20:06:35 已入队，后台队列 PID **1648990**、启动 tick **72742221**。GPU0/0208 等待前置任务；GPU1/0240 因前置技术失败阻塞。实际状态见输出 `queue_launch.json` 和 `queue_status.json`。

## 目的与范围

用户要求在当前 kujiale_0036 双路实验之后追加两个完整场景，明确排除 0128（含 fix 变体），随后指定用 **0208 替换 0234**。最终 GPU0 等待当前 GPU0 的 0036 子集正常完成后运行 kujiale_0208 全部 **25 条**；GPU1 对应接续 kujiale_0240 全部 **23 条**。新增 48 条，连同当前 0036 共 73 条。0234 未启动，不进入队列。

每个场景沿用数据集原始顺序，seed 2，整场景纳入，不按原版成败筛选。`manifest.json` 冻结任务 ID、前置进程 PID/启动 tick、输出目录及协议；`baseline48.csv` 保存全部任务同 seed 原版成绩。实际运行采用不同场景的独立 run ID，不覆盖当前或历史输出。

## 方法与保护

沿用 [0036 双路 high](../run_20261126_03_scene0036_high_dual/README.md) 的全部导航协议：StreamVLN 与仿真同 GPU，实时串行 JEV → 回退点/去重 → 偏航评审 → GPT 实走回退并完成剩余任务；Codex gpt-6-astra / high，经用户 7892 代理，恢复预算 180 个移动动作。保留第一人称 RGB、完整计时、原生评分与 guard1 的 10 次请求及累计期限。STOP 等待末段评审。

只追加调度，不修改运行中的算法或提示词。前置 launcher 必须退出、正式评分 ID 必须完整、原生结果必须为 complete、清理状态必须为 stopped；任何 failure/halt 或未评分退出都会阻塞该路后续场景，不自动绕过故障保护。两路独立接续，不额外增加同时运行的模型/仿真组数。保留之前明确要求保留的旧仿真。

后续场景开始前重新核对 GPU 进程归属、两次低负载读数、至少 32000 MiB 可用显存和保守主存准入。资源不足只等待，不停止其他进程。前置实验结束后新场景通过原生 launcher 重新加载自己的模型和仿真；场景内保持原生 reset/内存重启规则。

队列等待期间若相关算法源码、提示词或启动辅助代码变化，则停止启动并记录错误，须新建运行目录接续。输出保存实际 Git HEAD、工作区差异、源码和本队列快照。凭据从私有配置传入环境，不写入命令或记录。

## 启动

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_04_scene0208_0240_high_queued/queue.py
```

该命令仅首次执行：冻结清单并启动后台等待进程，不立即新增 GPU 任务。已有输出时拒绝覆盖。`queue.py --worker` 为内部入口，不手动重复执行。

输出根目录：`outputs/serial_recovery/codex_v001/run_20261126_04_scene0208_0240_high_queued/`。`queue_status.json` 记录等待、资源准入、运行、阻塞或结束状态；`gpu*/launch.json` 保存实际新 launcher 身份；`gpu*/launcher.log` 和 `gpu*/serial/` 保存导航产物。原生 launcher 负责自己进程的完成/异常清理。

## 验证、结果与下一步

只对新增队列验证了前置无结果、正式结果完整、技术 halt 优先阻断和不存在 PID 的门控；未重新运行模型测试或导航。准备阶段核对 48 个唯一 ID、场景排除与原版 episode seed。当前版 SR、平均 SPL：暂无，已评分 0 条；同批配对原版 SR、平均 SPL：暂无，已评分 0 条。尚在等待的任务不计为技术跳过或导航失败。

入队检查：最终清单 0208/25 条、0240/23 条，没有 0128 或 0234，队列进程存活。GPU1 前置 0036 在 20:06:33 UTC 写入 `halt.json`：`BrokenPipeError`，episode `kujiale_0036_32_4`、frame 0，正式评分 0/12；原生 launcher 随后停止并清理自己的模型/仿真。该路后续 0240 为 `blocked_predecessor`，不会自动跳过前置失败。GPU0 前置已启动 evaluator，检查时正式评分 0 条；0208 为 `waiting_predecessor`。

正常入队后交后台；后续按用户查询查看状态。GPU1 需修复前置故障后明确接续，队列不会自动重试或恢复已取消任务。
