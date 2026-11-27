# 0036 双路：终止 RGB 与正式评分衔接修复

## 最终结果（2026-11-27 04:26 UTC 核对）

0036 全部 **25/25** 正式评分完成。GPU1 于 00:22 UTC 完成 12 条，GPU0 于 01:37 UTC 完成 13 条，原生 launcher 均正常退出并清理本轮服务；随后 run12 已自动接续。当前 **SR 19/25（76%）、平均 SPL 0.4714796713**；同 episode、seed 2 原版 **SR 12/25（48%）、平均 SPL 0.3624008773**。平均 SPL 包含所有失败任务。正式完成任务中 13 条触发 recovery；当前进行中 0、未评分任务 0、技术跳过 0。历史修复过程的技术中断尝试保留，未并入正式分母。

后续 0208/0240 于 04:10–04:12 UTC 因 JEV HTTP 402 / insufficient_balance 保护退出，具体见 run12；当前两张卡仅保留用户要求保留的旧仿真 PID 1548476/1548482。本轮完成不等于后续 48 条完成。

## 首条正式评分与交后台（21:28 UTC）

用户要求的首条完整任务已于 21:26:56 UTC 完成恢复并随后正式评分：GPU1 `kujiale_0036_32_4`、seed 2，原生 success=1，SPL=0.5969933612085507，NE=1.0684869398703265 米。StreamVLN 执行 28 个动作后偏航报警，fork 同一评审会话，GPT recovery 执行 **84** 个移动动作并声明完成，原生 STOP 和正式评分提交成功，随后自动进入 `kujiale_0036_50_1`。这条实际覆盖 JEV、回退点、偏航、物理恢复、STOP、终止 RGB 与原生评分的完整通路。

本条运行 **769.057 秒（12 分 49 秒，不含模型/场景加载）**：评审 401.504 秒、recovery 343.797 秒、policy 4.906 秒、原生动作 11.834 秒。保存 native RGB 30 张、recovery RGB 88 张，共 **118 张**；终止图像来源为 terminal_camera_read，无额外物理推进。详细摘要见 [first_scored_summary.json](first_scored_summary.json)，原始 result 路径亦在摘要中。

按这一条正式评分唯一 ID 与 seed 2 配对：**当前版 SR 1/1（100%）、平均 SPL 0.5970；原版 SR 1/1（100%）、平均 SPL 0.8171**。原版本例也成功，当前 SPL 更低，不将本例解释为恢复带来的成功率提升。历史技术中断尝试未混入评分，当前批次技术跳过 0。

21:28:22 查询：GPU0 仍在 `kujiale_0036_19_4` F73，GPU1 下一条 `kujiale_0036_50_1` F5，均无 halt。正式完成 1/25，进行中 2 条，其余 22 条待跑。launcher 1702969/1703002；模型 1702987/1703025；仿真 1703344/1703339。后续 run12 队列 PID 1703531，0208/25 条与 0240/23 条均 waiting_predecessor。按用户要求首条完成后交后台，后续按询问查看，不停止运行。

2026-11-26 UTC。用户授权持续排障，跟踪到首条完整正式评分。沿用 0036 全 25 条、seed 2、两路原始 13/12 划分、Codex high、180 移动步、全部请求/故障保护、原始提示词和原生评分。

run05 GPU0 已走完 StreamVLN 171 动作、末段偏航评审、GPT recovery 150 移动步并声明完成，实际原生 STOP 返回 terminated=true；随后记录层 capture 错误地要求终止观测必须有 RGB，导致原生结果提交之前退出。原生 VlnEvalTask STOP 观测包含 metrics 但不包含 RGB，故问题属于记录层。旧恢复用时 557.457 秒、整例截至失败 2276.537 秒，全部轨迹/图像/会话保留，未正式提交的指标不冒充评分结果。

修复：终止观测缺 RGB 时，在 reset 前直接读取当前 `task.get_rgb_depth()`，核对 world/task tick 均不变化，保存来源为 terminal_camera_read；其他观测仍严格要求实际 RGB。使用真实 STOP 的缺 RGB 结构，验证终止图像保存且同一原生指标提交，直接受影响的 NativeGateTests 共 6 项通过。保留之前已验证的 Node 路径、上游 scripts 包兼容、本地 /tmp socket 修复。一般 RuntimeError 的原因和缺失模块名也写入 halt，避免只剩异常类型。

没有正式评分任务可跳过，故同一 25 条在全新输出重启。旧运行均保留；原始两台保留仿真不动。`manifest.json`、`baseline25.csv` 保存任务和相同 seed 原版成绩；同名 outputs 保存实际 Git HEAD、差异、源码、提示词、兼容入口和进程身份。启动前实际 worker/JEV/采样器检查通过后才加载 GPU 模型与仿真。

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_11_scene0036_terminal_rgbfix/run.py
```

后续 0208/0240 由 run12 接本轮正常完成。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。技术中断尝试不纳入正式 SR/SPL。
