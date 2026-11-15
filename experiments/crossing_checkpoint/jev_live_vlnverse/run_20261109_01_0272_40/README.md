# StreamVLN + Isaac Sim 实时 JEV 评分：kujiale_0272 40 条

更新时间：2026-11-09（UTC）
状态：完成并发布

## 目的

在 40 条新的 VLNVerse navigation episode 上，用 StreamVLN 执行真实本地导航，
同时用 JEV v004 对策略每一步观测做因果回退点评分。JEV 旁路运行，不改变
StreamVLN 动作、导航停止规则或官方评分。

## 样本

- 数据：VLNVerse fine `val_unseen`；
- 新场景：`kujiale_0272`，该场景全部40条 episode；
- 该场景不在已完成的 StreamVLN 10-scene/250-episode 复现中；
- seed：0；
- 40条 ID 由完整 scene 选择器固定，不按模型输出筛选。

## 导航协议

- StreamVLN `StreamVLN_R2R_v1_3`；
- Isaac Sim 4.5 / VLNVerse H1 physical；
- 640×480 RGB，500 warm-up physics ticks，最多25000 physics ticks；
- 模型 GPU 4，仿真 GPU 5（启动时重新核验空闲与进程归属）；
- 原模型贪心动作、历史缓存、动作队列、提示词与评分公式不变；
- 计划结果目录：
  `outputs/vlnverse/streamvln/results/peng_fine_streamvln_physical_20261109_01_0272jev`。

## 实时 JEV 协议

- JEV `jev-1.14.0`，问题类型 `noul`；
- 当前策略观测及前两个不同 RGB，即截至 `t-2,t-1,t`；
- 不传任务指令、动作、位置、地图、标签或导航结果；
- 每个 episode 顺序接收观测；每帧到达即提交 JEV；
- 最多5个未决请求；按FIFO强制最老请求不得超过5 step；
- Streaming Prominence：`N=11,D=5`；节点写入 `i+5` 后冻结；
- JEV 不参与导航决策，不改变 StreamVLN 输出；
- API key 仅从环境变量进入进程内存，不写命令参数、日志或结果。

JEV 输出目录：

`outputs/crossing_checkpoint/jev_noul_v004/vlnverse_live_0272_40/run_20261109_01`

## 启动方式

预检：

```bash
python3 scripts/evaluate.py \
  --backbone streamvln --benchmark vlnverse \
  --gpu 4 --sim-gpu 5 --mode physical \
  --scenes kujiale_0272 --seed 0 \
  --run-id peng_fine_streamvln_physical_20261109_01_0272jev \
  --jev-live-output outputs/crossing_checkpoint/jev_noul_v004/vlnverse_live_0272_40/run_20261109_01 \
  --preflight-only
```

正式启动由持久 tmux 会话等待无回显 API key 后执行；日志和实际 PID 写入产物目录。

## 结果与限制

40/40条完成并通过结果验证：SR 45.0%、SPL 39.10%、NE 3.984 m、OS 57.5%、
TL 7.378 m、FR 10.0%、StR 0%。JEV共2878次有效回答、0错误，最大step延迟5，
生成215个`N=11,D=5`流式采样节点。

JEV概率与采样节点是开发集旁路观测，不代表导航准确率提升；真实导航指标单独来自
VLNVerse/StreamVLN。JEV调用变慢时在5-step上限处等待导航步进，不改变动作序列或
评分输入。

## 产物与运行记录

- 导航结果：上述 VLNVerse run 目录；
- JEV 原始请求、回答、逐step概率、滤波和节点：上述 JEV 输出目录；
- 启动状态：`outputs/crossing_checkpoint/jev_noul_v004/vlnverse_live_0272_40/run_20261109_01/launch_status.json`；
- 启动日志：同目录 `logs/launcher.log`；
- 本地HTML：`outputs/crossing_checkpoint/jev_noul_v004/vlnverse_live_0272_40/exports/run_20261109_01/streamvln_live_jev_0272_40.html`
- 在线入口：http://134.175.18.101/vln/streamvln_live_jev_0272_40_template_20261109_03/streamvln_live_jev_0272_40.html
- 发布记录：`outputs/visualization_publishing/publish_20261109_105150_732749/publication.json`
- 首发坐标网格版和自定义户型图版均保留；当前入口使用既定三栏模板。

## 下一步

实验完成。后续若继续扩大样本，使用新运行目录，不覆盖本次结果与在线版本。
