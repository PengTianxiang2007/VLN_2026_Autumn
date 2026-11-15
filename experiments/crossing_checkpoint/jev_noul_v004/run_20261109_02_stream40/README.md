# JEV v004 流式 40 条扩展运行（截止时间修正版）

更新时间：2026-11-09（UTC）
状态：已取消并由 VLNVerse 实时导航任务替代（2026-11-09T01:27:25Z停止）

## 目的

在 `jev_noul_v004 + Streaming Prominence` 上新增40条episode，验证实时调用、
最大5-step延迟及`N=11`流式采样。只报告开发集概率和节点，不宣称准确率。

## 方法与版本

- JEV `jev-1.14.0`，单问题`fallback_point: noul`；
- 严格当前帧及前两帧RGB `t-2,t-1,t`；
- 云端端点`https://api.site/v1/systemone`；
- Streaming Prominence：`N=11,D=5`；
- 两个独立episode worker，各处理20条轨迹；
- 每个worker最多5个在途请求，并用FIFO顺序强制先完成最早请求；
- 观测到达即提交，不先跑完整条轨迹再补调用；
- JEV为云端服务，不占用本地GPU。

本版修正`run_20261109_01_stream40`的问题：旧版只限制在途数量，未限制最老请求
年龄，实测出现7–8 step滞后。`_01`保留为失败审计，不进入结果。

## 实验设置

- 数据：`outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001`
- 从冻结61条中排除已完成的v004 12条，再按原顺序取20失败＋20成功；
- 两片各20条，各含10失败＋10成功；
- 共3369次三帧JEV调用；
- 单请求最多5次重试，失败原样保留；
- 无真实导航、无仿真动作、人工标签不输入模型。

## 启动方式

`JEV_API_KEY`只经无回显stdin进入父进程内存，再经环境变量传给两个worker；
不写入命令参数、日志或结果。

```bash
backbone/streamvln/.venv/bin/python \
  scripts/run_jev_noul_v004_40_stream.py supervise \
  --output outputs/crossing_checkpoint/jev_noul_v004/run_20261109_02_stream40 \
  --max-in-flight 5 --attempts 5 --timeout 120
```

## 结果与限制

两个worker曾启动并完成首批真实JEV回答核验，最大未决step滞后为4。随后用户澄清
目标不是在离线轨迹上批量评分，而是本地 Isaac Sim + StreamVLN 导航过程中实时调用
JEV；本运行随即停止。已完成请求和进程状态保留，但不计入最终40条结果。

## 产物与运行记录

- 输出根目录：`outputs/crossing_checkpoint/jev_noul_v004/run_20261109_02_stream40`
- 主管PID：`2105765`
- Worker PID：`2105803`、`2105804`
- 计划：`plan.json`
- 分片日志：`logs/shard_0.log`、`logs/shard_1.log`
- 分片状态：`shard_0/status.json`、`shard_1/status.json`
- 原始逐帧结果：`results.json`
- 汇总：`summary.json`

## 下一步

本运行不再恢复。替代实验见
`experiments/crossing_checkpoint/jev_live_vlnverse/run_20261109_01_0272_40`。
