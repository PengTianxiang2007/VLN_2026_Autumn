# Codex 在线串行接管 v001

2026-11-27 07:09 UTC 已核对快照：0036 完成 25/25，0208 完成 10/25，0240 完成 21/23；当前 SR **38/56（67.86%）**、平均 SPL **0.4851**，同 episode/seed 2 原版 SR **29/56（51.79%）**、平均 SPL **0.4148**，失败计入均值。失败→成功 14、成功→失败 5。两路仍在运行，2 条进行中、15 条待跑；此为固定快照，不代表队列最终结果。[逐条配对 CSV](run_20261127_02_resume30/reports/paired56_20261127_0709.csv)、[完整快照](run_20261127_02_resume30/reports/status_summary_20261127_0709.json)。

### 当前已确认的限制（尚未修改运行协议）

- 这是实时观测下的同步串行实现：每个动作边界先等 JEV，出现候选点再等 Codex 资格/去重与偏航评审，完成后才执行动作；单机器人导航与评审没有异步并行。两张 GPU 并行的是两个 episode。
- STOP 会等待末段偏航评审，但没有独立的任务完成校验。评审即使说明任务尚未完成，只要未判 deviated，当前仍放行 STOP。
- 回退点资格过滤和去重影响偏航审阅时机；同一区域反复替换唯一节点时可能一直只做初始化，原地无进展没有独立接管触发。
- 同 seed 配对保证任务/派生种子一致，不保证物理轨迹逐帧一致。0208 的三条退化在 GPT 接管前就与历史原版动作分叉，不能将结果变化全部归因于 recovery。
- [0208 六条分析](run_20261127_02_resume30/reports/analysis_scene0208_scored6_20261127.json)中三次 recovery 都以 fall 结束（其中一条因已进入目标半径，原生 SR 仍为成功）。提高动作预算不能直接解决该问题。
- [耗时实例](run_20261127_02_resume30/reports/timing_pair_0208_27_3.json)：0208_27_3 原版 72.861 秒，当前 1322.929 秒，其中 JEV/Codex 等待 1245.531 秒；两版 SR 均 1/1（100%），平均 SPL 分别 0.9567 / 0.9518。不同日期、服务器的实际记录对照，非严格同机性能基准。

2026-11-27 最新：[run_20261127_02_resume30](run_20261127_02_resume30/README.md)已提交后台队列 PID 2120500，0208/0240 剩余 21/9 条；用户确认 JEV 已充值，复用模型 2117878/2117879，保留已有 43 条成绩。按用户要求不人工跟踪。续跑前当前 SR 31/43（72.09%）、平均 SPL 0.4920；配对原版 SR 21/43（48.84%）、平均 SPL 0.3867。

2026-11-27 最新：[run11](run_20261126_11_scene0036_terminal_rgbfix/README.md)0036 全 25 条完成；[run12](run_20261126_12_scene0208_0240_after_terminalfix/README.md)0208/0240 分别 4/25、14/23 后因 JEV HTTP 402 余额不足退出。累计当前 SR 31/43（72.09%）、平均 SPL 0.4920；同 seed 原版 21/43（48.84%）、SPL 0.3867。进行中 0，技术中断未评分 2，未开始 28；恢复依赖 JEV 余额/有效凭据，不能盲目重启。

2026-11-26 21:28 UTC 最新状态：[run11](run_20261126_11_scene0036_terminal_rgbfix/README.md)首条完整 JEV→回退点→偏航→GPT 物理恢复→原生 STOP/评分已完成。当前 SR 1/1（100%）、平均 SPL 0.5970；同 seed 原版 SR 1/1（100%）、平均 SPL 0.8171。两路继续，当前 1/25 已评分、2 进行中、22 待跑、技术跳过 0。[run12](run_20261126_12_scene0208_0240_after_terminalfix/README.md)等待接续 0208/0240。原版本例也成功，不把链路验证等同于方法收益。

2026-11-26 20:06 UTC：[0208/0240 后续 48 条](run_20261126_04_scene0208_0240_high_queued/README.md)已入队。0208 等待 GPU0 前置；0240 因 GPU1 前置 BrokenPipeError 技术中断阻塞，不自动继续。排除 0128，0234 已替换。新增批次当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。

状态：实现与 CPU 定向验证完成；[kujiale_0036 全 25 条双路 high](run_20261126_03_scene0036_high_dual/README.md)已启动，交后台时处于模型初始化阶段。

2026-11-26 更新：加入 [guard1 有限重试与超时保护](run_20261126_02_guards/README.md)。按用户最新要求，JEV 与 Codex 评审最多 **10 次请求（含首次）**，同时受累计时长上限约束。

本版将实时 JEV 打分、回退点确立与去重、同会话偏航判断、GPT 回退并完成剩余全程接到原生 StreamVLN 导航循环。实施记录见 [run_20261126_01_implementation](run_20261126_01_implementation/README.md)。

## 协议

每个原生动作边界保存真实第一人称 RGB，取得 StreamVLN 的待执行动作，然后等待 JEV v004 → v002 active 采样 → Codex v006.1 资格与去重 → v002 同会话偏航评审。候选使用 F−2/F0/F+2；评审区间按最大 6 帧间隔补图。只有该边界的必要判定全部结束，才能执行待执行动作。

StreamVLN 输出 STOP 时，机器人先停留在当前动作边界，保存当前 RGB，将其作为待终止端点评审最后一段。此时未执行原生 STOP，也未评分、reset。末段未判偏航才执行原生 STOP；末段判偏航则与中途报警完全一样，丢弃待执行动作并交给 GPT。未形成有效回退点时沿用现有终止初始化规则，不凭空生成回退目标。

偏航后从**刚完成偏航判断的会话末轮** fork，绑定当前 episode 的 H1 工具。机器人从当前真实位置出发，实际走回指定回退点附近，观察其他支路，选择路线并继续完成原始任务；必要时回到更早的有效回退点。没有离线摆位、瞬移或重新开始任务，也不恢复或移交给 StreamVLN。模型不接收目标坐标、参考路线或评分结果。

英文恢复提示词为 [prompt_en.txt](prompt_en.txt)，与已确认的 goal180 提示词一致，仅替换 `{checkpoint}`。GPT 全程共享 **180 个移动动作**，前进、左转、右转各计 1；observe 和 finish_return 不计。接口拒绝第 181 个移动，在线控制器在第 180 个动作完成后退出。finish_return 表示模型声明已到原始指令终点。

模型声明完成、耗尽预算或正常结束回复但未声明时，均使用原生 STOP 完成评分。若已跌倒、卡住或达到原生物理预算，则直接沿用该物理终止，不再执行 STOP。请求故障按下表有限重试，机器人等待；控制客户端故障按技术中断退出，不伪造一致结论或导航评分。若 Codex 正常退出却一次成功工具调用都没有，也视为技术中断。取消和超时时清理本次拥有的工作进程与控制进程。

## 故障保护（guard1）

| 环节 | 当前上限 | 达到上限后 |
| --- | --- | --- |
| JEV | 单次 HTTP 120 秒；最多 10 次请求；累计 420 秒 | 停止队列，技术中断，不执行待定动作 |
| Codex 回退点/偏航评审 | 单次 300 秒；每个逻辑评审最多 10 次请求；累计 600 秒 | 停止队列，不生成默认一致结论 |
| 单个动作边界 | 导航进程独立监督 1800 秒 | 终止挂起 worker，处理无响应/半行输出/采样器挂起 |
| GPT 接管 | 300 秒无成功工具调用；600 秒无移动动作；总计 2700 秒 | 关闭控制端，记录技术中断，不自动重放动作 |
| GPT 移动 | 整次恢复最多 180 步 | 按原预算终止规则完成原生评分 |

次数与累计时间先达到者生效；10 次包含首次请求，不承诺等待每次超时满额后仍发足 10 次。退避为 2、4、8、16、32、60…秒，单次等待最多 60 秒，且不得超出累计时间。JEV 的 Python 子进程留有最多 15 秒退出余量；累计预算包括该开销与等待。Codex 子进程清理也有短暂退出余量。

鉴权失败、已知配置错误、不可用会话等永久错误立即终止；超时、429、5xx 和无效模型格式可在预算内重试同一逻辑评审。重试仅用于读图评审，恢复动作不会自动重试或从起点重跑。动作接口继续按请求 ID 去重，并在读取请求后再次检查期限，迟到请求不能绕过保护推进机器人。仅日志/心跳更新不算进展；重复 observe 无法绕过无移动期限。

保护触发后写 `worker_failure.json` 或 `recovery/failure.json`、episode 的 `failure.json`，以及运行根目录的 `halt.json`。本轮外层 launcher 停止，不通过重启 chunk 绕过内部上限；修复后使用新运行目录显式接续。已评分结果与轨迹保留，技术中断不计入 SR/SPL。进程兜底清理核对记录的 PID、启动 tick、进程组与 session，不按模糊名称批量停止进程。

这些是当前串行仿真的保护，不等同于实体机器人的硬件急停；尚未进行真实导航闭环故障演练。

## 入口

原生入口新增 `--codex-serial-output`；不传入时行为不变。要求 physical StreamVLN、显式 seed、单环境单进程。一个进程使用一个独立输出目录。与旧 `VLN_SERIAL_OUTPUT`、旁路 observer 及旧 review capture 互斥；本版自行保存完整 RGB 和轨迹。

下面是启动形式，**本次没有执行**。选定任务、核验 GPU 归属与空闲资源后，将 `GPU_INDEX`、`EPISODE_ID` 换成实际值；`JEV_API_KEY` 通过进程环境提供。该原生 launcher 会管理自己的 StreamVLN 模型及仿真进程，不会自动使用当前保留的仿真。

```bash
.runtime/crossing_vllm27/bin/python -B benchmarks/vlnverse/runner/run_full.py \
  --method StreamVLN --mode physical --seed 2 \
  --gpu GPU_INDEX --sim-gpu GPU_INDEX \
  --episode-ids EPISODE_ID \
  --run-id peng_fine_codex_serial_v001_run01 \
  --codex-serial-output outputs/serial_recovery/codex_v001/run01
```

如已有独立管理的原生模型服务，也可以使用 `run_full.write_config(..., review=None, jev_live=None, codex_serial={'output_dir': '/absolute/new/run'})` 生成评测配置，由原生 `run_eval.sh` 启动仿真；须设置 `VLN_EVAL_SEED`，模型端口仍通过原 `port` 参数传入。该接入不依赖离线 case 编号或历史摆位记录。

## 产物与评分

每次运行保存实际 Git HEAD、相关工作区差异、源码/提示词快照和 SHA256。每个 episode 独立建立 `episodes/<episode_id>/attempt_<timestamp>/`，历史尝试不覆盖。

- `start.json`、`config.json`：任务、seed、180 步协议。
- `frames/`、`observations.jsonl`：原生动作边界与最终 RGB、机器人位姿、仿真时间；坐标仅用于本地记录。
- `jev/`、`jev_calls.jsonl`、`candidates.jsonl`、`review/`：评分请求、候选、有效节点、偏航轮次及完整会话证据。
- `boundary_decisions.jsonl`、`events.jsonl`：动作等待、STOP 阻塞、实际接管与执行事件；`live.json` 为当前阶段。
- `recovery/live/frames/`、`recovery/live/calls.jsonl`：GPT 每次工具调用的原始第一人称 RGB、实际动作、位姿与耗时。
- `recovery/result.json`：分支会话、执行步数、模型是否声明完成和退出原因。
- `result.json`：原生 scorer 成功处理后提交，包含原生 metrics、整条任务耗时、policy/review/native action/recovery 耗时。SPL 累计包含接管前后所有实际运动，没有离线前缀长度估计。
- `failure.json`：技术失败或取消；不计入已评分任务。

汇报按唯一 episode ID 与相同 seed 配对原版，分别列 SR 成功数/已评分数/百分比与全部已评分任务的 SPL 算术平均（含失败）。`model_declared_success` 与原生 success 分开；二者可能不同。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条。
