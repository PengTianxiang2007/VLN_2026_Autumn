# 串行单目恢复：EasyJEV端点单条联调02

更新时间：2026-11-16 06:48 UTC（北京时间14:48）。状态：单条导航与官方评分已完成1/1，导航失败；未触发回退纠错，完整恢复闭环尚未验证通过。模型与仿真引擎按用户要求保留。

## 目的与协议

继续用户原授权的首条完整串行验证：实时JEV → 在线采样建点 → 去重 → 偏航/语义进度 → 单目选路 → 实际回退 → v007局部纠错 → 恢复接管前原任务记忆并续走。具体协议见[版本README](../README.md)。只跑开发样本`kujiale_0208_21_4`、seed2，原生25000物理tick预算，包括回退稳定与局部纠错开销。不输入参考轨迹/人工标签做偏航或选路判断。

01在导航前因scripts包名冲突失败，当前已修复。新增去重无效输出保留双方及完整恢复循环证据检查；新源代码完整冻结，不修改01。正式配置仅将JEV端点换为用户新提供并已验证的`https://api.easyjev.online/v1/systemone`；请求模型仍`jev-1.14.0`，实际返回版本以原答为准。新渠道预检2/2有效，见[接口记录](../jev_easyjev_20261116_01/README.md)。

DeepSeek用于去重/偏航/单目三阶段选路/v007指令，端点`https://api.deepseek.com`、模型`deepseek-flash`。局部纠错清空StreamVLN记忆，交还时必须恢复接管前快照并核验内容hash；局部STOP不送入原任务终止逻辑。

## 环境与版本

GPU3原StreamVLN PID3194667/端口40617保留，不重载模型。启动前已读取全部GPU与进程归属，GPU3另有他人SAM3进程，不操作。仿真按原生eval生命周期运行，仅加串行钩子；输出、评分、LMDB与新运行隔离。

实际Git基线、未提交差异、源码/提示词和配置hash见新输出manifest.json及code/。启动时再次检查GPU资源和模型身份。密钥仅从无回显输入进入本轮主管/仿真内存，不写源码或配置。

## 命令

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_serial_pipeline.py --episodes kujiale_0208_21_4 --jev-endpoint https://api.easyjev.online/v1/systemone --output outputs/serial_recovery/v001/run_20261116_02

benchmarks/vlnverse/.venv/bin/python -u -B outputs/serial_recovery/v001/run_20261116_02/code/scripts/run_serial_pipeline.py --campaign outputs/serial_recovery/v001/run_20261116_02 --model-pid 3194667 --port 40617 --gpu 3 --keys-stdin
```

## 结果范围与产物

`outputs/serial_recovery/v001/run_20261116_02/`保存status、evaluator.log、逐帧实际观测/姿态、JEV与各语义模块请求原答、回退/记忆证明、官方评分及validation。只有出现实际局部动作、记忆交还、原任务续接，才能称完整恢复循环已执行；导航评分完成但未触发恢复不能冒充全链路通过。

2026-11-16 06:28 UTC启动验证：主管836172、仿真836845，复用原模型3194667。已记录6帧真实仿真观测、前5次有效JEV返回及5个原任务动作；无runtime_failure，正式评分0/1。DeepSeek实际图像/偏航提示词预检通过，证据`outputs/serial_recovery/deepseek_preflight_20261116_02/result.json`。启动验证记录见本轮`startup_verified.json`；它只证明导航和实时JEV正常，不能替代回退、纠错及交还闭环验证。

用户于此时再次要求正常开跑后不再持续跟踪，已停止人工轮询，由现有主管继续单条任务及最终验证，不扩大样本量。完成后按用户要求保留模型与仿真。失败保留结果并先恢复原任务记忆，主管只清理本轮仿真，不停止原模型。

## 最终结果（06:48 UTC查验）

本条于06:41 UTC（北京时间14:41）结束，主管正常退出，状态`complete_without_full_recovery`。共40个动作（含最后STOP）、40次有效JEV判断、7个候选节点、6次去重；最终保留S05、S07两个节点。7次偏航评审为5次consistent、2次uncertain，未输出deviated，故实际回退0次、局部纠错0次、记忆交还0次。官方评分成功0/1，fail_reason为not_reach_goal，NE=8.543米，TL=5.257米，物理steps=2451。没有runtime_failure；本次是原任务STOP后未到目标，不是进程崩溃。

结论范围：实时图像→JEV→建点→去重→偏航评审及原版导航评分已实际执行；回退、单目选路、局部纠错和记忆恢复分支本次未触发，不能宣称完整pipeline已验证通过。未据此修改判定阈值、强制偏航或启动更多任务。下一步需复核去重和偏航评审证据，再验证真实纠错分支。原始证据为`validation.json`、`official_result.json`、逐请求原答及`completion_summary_20261116_0648.json`。

06:48 UTC查验原模型PID3194667、仿真引擎PID836845仍在GPU3；原生任务结束已清理本条场景，保留的是引擎进程。没有继续导航或新增任务。

## 可视化交付

2026-11-16：已发布[串行联调双语回放](http://134.175.18.101/vln/serial_pipeline_v001_run02_web_20261116_01/serial_pipeline_replay.html)。40帧、原始/参考/本次轨迹、节点发生/确认时刻、完整JEV/去重/偏航请求和原答、双进度条及复核导出均已核验。详见[导出登记](exports/replay_20261116_02/README.md)。无新模型或导航调用。

2026-11-16 用户指定改用原JEV模板：已发布[原JEV模板回放](http://134.175.18.101/vln/serial_jev_template_run02_web_20261116_01/serial_jev_replay.html)。保留完整波形、采样标记、地图回退点/去重开关，7→2点在地图和波形同步；旧版保留。见[本次导出登记](exports/jev_template_20261116_01/README.md)。
