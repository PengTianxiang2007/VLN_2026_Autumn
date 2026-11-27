# 0036 双路重启：修复 Node 运行时路径

最终 GPU0 状态：21:02:18 UTC，GPT 在 150 步后声明完成，原生 STOP terminated=true；随后终止 RGB 记录层 RuntimeError，正式评分未提交。详见 [run11](../run_20261126_11_scene0036_terminal_rgbfix/README.md)的原因和修复。本轮全部轨迹、图像和会话保留，不将声明完成或派生指标作为正式成功。

20:31:32 UTC GPU1 在 F28 已完成偏航判断，首次进入 recovery 时因上游 `scripts` 包遮蔽项目恢复接口而技术退出，未执行恢复动作、未评分；已新增兼容入口并在仿真实际解释器验证，仅 GPU1 在 [run07](../run_20261126_07_scene0036_gpu1_bridgefix/README.md)重启。GPU0 继续运行，延迟导入可读取兼容入口，无需重启。原核心源码哈希保持本轮启动时一致，新增入口来源/时间/哈希及副本另存输出 `runtime_import_patch/`；不覆盖原快照。最终后续队列为 [run08](../run_20261126_08_scene0208_0240_high_after_bridgefix/README.md)。

日期：2026-11-26 UTC。用户要求修复 GPU1 故障，并跟踪至两路真实开跑。实际状态以输出 `launch.json`、各路 `serial/live.json` 和原生日志为准。

20:14:56 UTC 实际 worker/JEV/采样器验证通过，首帧返回 continue；随后 GPU0/1 launcher **1657996 / 1658038**、模型 **1658019 / 1658055** 启动。用户随后要求跟踪直到首条任务完整评分，同时确认另一路正常推进。当前仍在初始化，尚不宣称完成导航验证。

## 原因与范围

run03 两路都在首帧、尚未执行待定动作时技术退出，正式评分 0/25。GPU1 于 20:06:33、GPU0 于 20:08:21 写入 BrokenPipeError；原始 worker.log 表明根因是 `FileNotFoundError: node`。净化 Isaac 子进程环境时，固定 PATH 排除了服务器提供的 `/etc/dsw/runtime/export_bin/node`。原生 launcher 已清理本轮模型/仿真。旧保留仿真 1548476/1548482 不动。

本轮保存旧日志，不覆盖、不删除 halt、不恢复旧输出目录。重跑同一 kujiale_0036 全 25 条、seed 2、GPU0/1 原始 13/12 分配。原版配对成绩、Codex high、180 移动预算、10 次请求及累计期限、提示词和原生评分协议与 run03 相同。全部 25 条尚未正式评分，没有重复计分。

## 修复与验证

清理环境前保存 Node 绝对路径到 `VLN_NODE_BINARY`，JEV 采样器使用该路径；启动器也显式传入。依赖缺失以结构化 `jev_sampler/node_unavailable` 上报，父进程不再用 BrokenPipeError 掩盖 worker 原因；其他 worker 异常保留类型及独立日志。

3 项针对性检查通过：真实 Node 采样器在净化后的环境中启动并处理帧、实际 worker 的运行时缺失原因经过断管返回父进程、原有半行响应超时保护。启动还使用历史真实 RGB，经实际 ReviewWorker→JEV→v002 active 采样器往返一次；此项成功后才加载模型/场景，探测不计导航成绩。

实际 Git HEAD、差异、修复源码、提示词、启动器快照位于同名 outputs 目录。`manifest.json`、`baseline25.csv` 保存任务和原版成绩。

## 启动及后续

```bash
.runtime/crossing_vllm27/bin/python -Bu \
  experiments/serial_recovery/codex_v001/run_20261126_05_scene0036_high_dual_nodefix/run.py
```

每卡独立模型+仿真，当前初始化需重新加载。核对资源与保留进程归属后启动。按最新要求持续跟踪两路实际在线评审通过与动作执行，不以 PID 存活作为开跑验证。后续 [0208/0240 队列](../run_20261126_06_scene0208_0240_high_after_nodefix/README.md)接本轮正常完成结果，原 run04 因前置失败阻塞并结束，保持历史状态。

当前版和配对原版 SR、平均 SPL 均暂无，已评分 0 条。技术失败尝试单列、不计导航失败。
