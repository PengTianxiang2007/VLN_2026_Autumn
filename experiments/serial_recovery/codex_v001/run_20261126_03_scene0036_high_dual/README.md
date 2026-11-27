# kujiale_0036 全场景：双 GPU 在线串行恢复，Codex high

最终状态：2026-11-26 20:06:33 / 20:08:21 UTC，两路均在首帧技术退出，正式评分 0/25。worker 找不到 Node（净化 PATH 排除了服务器安装路径），父进程显示 BrokenPipeError；原生 launcher 已清理本次模型和仿真，旧保留仿真不动。用户授权修复并重启，后续见 [run05](../run_20261126_05_scene0036_high_dual_nodefix/README.md)，本目录保留故障证据，不覆盖。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

日期：2026-11-26 UTC。用户明确授权两路并行、Codex high。状态以输出 launch.json、各路原生日志和 serial/live.json 为准。

两路于 19:35:26 / 19:35:28 UTC 启动。GPU0 launcher **1615677**、模型 **1615694**，GPU1 launcher **1615721**、模型 **1615734**。已通过资源准入并进入模型权重加载；交后台时模型尚未 ready，新仿真将在对应模型 ready 后自动启动。没有把进程启动表述为已完成导航验证。JEV 当前凭据已通过一次真实请求验证，耗时 **3.279 秒**，记录于输出 `jev_probe/verification.json`。

## 范围与协议

VLNVerse fine val_unseen 的 kujiale_0036 全部 25 条，seed 2。按原始 split 顺序交错分为 GPU0 的 13 条和 GPU1 的 12 条；无重复、不按原版成绩筛选。每张卡独立部署 StreamVLN 与原生 H1 仿真，模型端口自动分配，任务、会话和输出目录独立。

Codex 使用 gpt-6-astra，**回退点/偏航评审与 recovery 均为 high**，ChatGPT 登录与用户 7892 代理。JEV v004 → v002 active → v006.1 回退点/去重 → v002 同会话偏航，最大 6 帧补图。两条任务并行，每条内部仍在动作边界串行等待评审。STOP 必须等待末段判定；偏航后 fork 刚完成评审的会话，GPT 物理回退并接管剩余全程，共享 180 个移动步。

保留 guard1：最多 10 次请求（含首次），JEV 累计 7 分钟、Codex 每轮评审累计 10 分钟，次数/时间先到即止；永久错误立即停止该路，接管无进展和总时长限额不变。原生物理预算 25000 ticks，回退与导航运动全部累计进入原生评分。技术中断不伪造导航失败、不自动重放。

每条任务沿用原生 env.reset，不固定逐条重启进程。原生 reset 会清理旧任务的场景节点并重新 set_up_scene，即使 scene ID 相同也不是只复位机器人。正常切换保留模型权重、清空策略状态；若 evaluator RSS 达到 24000 MiB，则在已评分的任务边界结束 chunk，原 launcher 重启该路模型与仿真，跳过已经评分的任务。此次没有改为场景常驻缓存。

JEV key 只从仓库私有 `.env.easyjev.local` 加载到进程环境，不写入清单、命令行或日志。启动前用一张已有真实 RGB 验证当前 JEV 服务；该探测不计导航任务。已有两台仿真 PID 1548476/1548482 按用户要求继续保留，仅在显存和主存满足准入时并存新任务。

## 启动与产物

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_03_scene0036_high_dual/run.py
```

`manifest.json` 保存完整任务分配与协议，`baseline25.csv` 保存相同 episode、seed 2 的历史原版逐条成绩。实际 Git HEAD、工作区差异和相关源码/提示词快照保存于 `outputs/serial_recovery/codex_v001/run_20261126_03_scene0036_high_dual/`，不以当前 HEAD 冒充旧结果版本。

各路 `gpu*/launcher.log` 为启动日志，`gpu*/serial/` 保存实时 RGB、JEV/评审请求、有效节点、偏航、接管及耗时。原生评分输出位于 launch.json 的 native_output；launcher 管理自己的模型和仿真，结束或异常后清理新服务，不操作保留的旧仿真。

确认两路正常开始后交后台，不持续等待评审或完整任务结束。当前版与配对原版 SR、平均 SPL 均暂无，已评分 0 条；后续只按当前版已正式评分的唯一 episode 配对统计，平均 SPL 包含失败任务，技术中断单列。
