# JEV v004 流式 40 条扩展运行

更新时间：2026-11-09（UTC）
状态：失败并排除；流式截止时间审计发现最大调用滞后7–8 step

## 目的

在当前最好 JEV 组合 `jev_noul_v004 + Streaming Prominence` 上新增 40 条离线
episode，验证流式部属协议及 `N=11` 采样。此批只产生开发集概率、流式轨迹和
候选节点，不宣称准确率或优于 Qwen。

## 方法与版本

- Prompt：`jev_noul_v004`，英文请求、中文展示翻译；
- 模型：JEV `jev-1.14.0`，单问题 `fallback_point: noul`；
- 输入：当前帧及前两帧 RGB，即严格 `t-2,t-1,t`；
- API：`https://api.site/v1/systemone`；
- 滤波：Streaming Prominence，`N=11`、最大延迟 `D=5` 个 step；
- 采样：高点阈值0.6、低峰阈值0.18、峰谷差至少0.03、节点间距3帧、
  平台阈值0.45且至少3帧；
- 实时性：每个 episode 顺序消费观测，观测到达即提交对应 JEV 请求；
  每个 worker 最多保留5个未决请求，不先跑完整条轨迹再补调用；
- 并行：两个独立 episode worker，各自一次处理一条轨迹；
- GPU：JEV 为云端请求，本批不启动本地模型，也不占用 GPU。

源码入口：

- `scripts/run_jev_noul_v004_40_stream.py`
- `core/jev_node.py`
- `core/crossing_lite.py`

运行时会复制源码快照、Git HEAD 和工作区状态到输出目录。

## 实验设置

- 数据：`outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001`
- 样本：从冻结的61条选择中排除已完成 v004 的12条，再按原顺序取
  20条失败和20条成功；
- 两个 shard 各20条，各含10条失败和10条成功；
- 计划调用：3369次，三帧窗口与既有 v004 完全一致；
- 无真实导航、无仿真动作、无人工标签输入模型；
- 停止规则：单个请求最多5次重试；调用失败原样保留，不补造分数。

## 启动方式

准备：

```bash
backbone/streamvln/.venv/bin/python \
  scripts/run_jev_noul_v004_40_stream.py prepare \
  --output outputs/crossing_checkpoint/jev_noul_v004/run_20261109_01_stream40
```

启动时密钥只通过无回显 stdin 进入父进程内存，再经子进程环境传给两个 worker；
密钥不写入命令参数、日志或结果文件：

```bash
backbone/streamvln/.venv/bin/python \
  scripts/run_jev_noul_v004_40_stream.py supervise \
  --output outputs/crossing_checkpoint/jev_noul_v004/run_20261109_01_stream40 \
  --max-in-flight 5 --attempts 5 --timeout 120
```

## 结果与限制

启动后首批运行发现旧实现只限制同时5个在途请求，没有强制最老请求在5个step内
完成；shard 0/1 的实际最大滞后分别为7/8 step。核验后于2026-11-09T01:24:16Z
停止本项目两个worker及主管，保留174个已完成请求文件和1条完成episode，但不计入
最终40条结果。

修正版改为 FIFO 顺序回收最早请求，两个worker各20条，运行号
`run_20261109_02_stream40`。本目录只作为失败审计记录，不与修正版结果混算。

## 产物与运行记录

- 输出根目录：`outputs/crossing_checkpoint/jev_noul_v004/run_20261109_01_stream40`
- 计划：`plan.json`
- 根状态：`status.json`
- 启动器 PID：`supervisor.pid`
- 分片日志：`logs/shard_0.log`、`logs/shard_1.log`
- 分片状态：`shard_0/status.json`、`shard_1/status.json`
- 原始逐帧结果：`results.json`
- 汇总：`summary.json`

## 下一步

不再恢复本运行。使用修正后的 `run_20261109_02_stream40`；两片完成后自动合并并
核对40条、3369次调用，再制作 `N=11` 双语流式可视化和在线对照页。
