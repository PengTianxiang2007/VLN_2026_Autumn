# Codex 在常驻 H1 上调用观察和动作工具

2026-11-26，实测通过。使用 seed 2 的 kujiale_0036_0_0，起点为[当前常驻的 F38](../../pose_hold/run_20261126_01/README.md)。单 H1 physical、GPU 3。复用同一 Isaac 进程和原生离散步态。主实验停留点和输出目录独立保留。这次仅验证真实图像传递、一步前进及反馈，未启动完整导航评分。

Git 基线 d551421，开始时工作区含刚完成的 pose_hold 运行和三个索引文件的未提交登记。本次实际源码、Git 状态和哈希保存于输出 source/。工具端使用 Python MCP SDK 2.x 和 stdio，连接本机同一仿真主线程的 Unix socket。模型只收到当前原生 RGB、执行状态和帧号；坐标保存为本地实测证据。观察和 finish_return 均不推进物理。测试限制一个移动，测试结束由操作者在同一进程恢复 F38，正常待用接入点使用原生物理预算。

启动顺序为在既有 f38 控制台载入本目录 attach.py 的 attach(env, task, world, art)，再从仓库根目录运行以下命令。代理 127.0.0.1:7892。

```bash
run=outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38
VLNVERSE_ROBOT_ENDPOINT="$run/smoke/endpoint.json" bash scripts/codex_vlnverse_robot.sh exec --json --ephemeral --sandbox read-only --disable shell_tool --disable unified_exec --enable code_mode_host -c project_doc_max_bytes=0 -c 'model_reasoning_effort="medium"' -o "$run/codex-final.txt" - < experiments/inverse_rollback/codex_tools_v001/run_20261126_01_f38/prompt.txt > "$run/codex-events.jsonl" 2> "$run/codex.log"
```

[实际调用与轨迹](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/smoke/calls.jsonl) · [初始状态](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/start.json) · [测试后还原](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/restored.json) · [待用机器人接口](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/live/endpoint.json)。

## 实测结果与当前接入方式

Codex 0.164.0、gpt-6-astra / medium，使用指定的 CODEX_HOME 和 7892 代理。真实的一个 turn 完成了三个 MCP 调用。观察 F38 和动作后观察 F39 均推进 0 个物理 tick。中间的一次 forward 推进 50 tick，水平位移 0.022256 米，沿初始朝向的位移为 0.011975 米。三个返回均为 640×480 PNG，Codex 工具事件中的图像字节哈希逐一对应本地原生 RGB。F39 表示本次控制的下一动作边界。完整导航的 SR 和平均 SPL，当前版与配对原版均为“暂无，已评分 0 条”。

结束单步测试后，操作者触发 smoke 附着的 detach_marker。原进程恢复初始根位姿和速度、关节状态、步态控制器、原始任务计数及相机，最大位置分量差 5.97e-8 米。任务计数恢复为 1901，世界计数从测试前的 503 推进到 553。PID 3122551 继续常驻 GPU 3，live 会话起始帧为 38。

[逐项实测摘要](summary.json) · [动作前的原生图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/smoke/frames/00001.png) · [动作返回的原生图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/smoke/frames/00002.png) · [Codex 回答](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/codex-final.txt)。

从项目根目录打开可控制当前机器人的交互式 Codex，启动器注册此次附着的工具。

```bash
VLNVERSE_ROBOT_ENDPOINT=outputs/inverse_rollback/codex_tools_v001/run_20261126_01_f38/live/endpoint.json \
  bash scripts/codex_vlnverse_robot.sh
```

工具名为 `observe()`、`step(action)`。参数为 `forward`、`turn_left`、`turn_right`、`finish_return`。最后一项表示模型主动声明已回到目标，只结束本次回退。控制权保持在现有 Isaac 进程中，待用时不推进物理，实际调用保存在 live/calls.jsonl。人工需要交回 Python 控制台时，在本机创建该附着 endpoint.json 给出的 detach_marker 即可。

## 环境记录

当前登录账户拒绝默认 gpt-6.2-astra，启动器默认使用本项目可用的 gpt-6-astra，可通过 VLNVERSE_CODEX_MODEL 选择其他可用模型。原 0.164.0 单文件安装缺少工具路由所需的 codex-code-mode-host。已补入[OpenAI 同版本官方发布件](https://github.com/openai/codex/releases/tag/rust-v0.164.0)，核验压缩包 SHA256 后放在项目 .runtime/tools/codex-0.164.0/，并向用户的 codex-bin 添加同名软链接。前三次尝试分别记录在 attempt01_default_model、attempt02_no_tool_router、attempt03_missing_host，均未触发物理动作。有效源码快照位于本次输出的 source/effective/。
