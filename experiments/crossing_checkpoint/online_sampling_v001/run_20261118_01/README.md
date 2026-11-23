# 53 条离线轨迹的 JEV 前视评分与候选回退点

[打开公网节点回放](http://134.175.18.101/vln/jev_route53_sampling_v001_web_20261118_01/index.html) · [网页发布记录](exports/web_20261118_01/README.md)

2026-11-18 已完成。53 条轨迹、4,837 个评分位置全部有效，得到 **494 个去重前候选节点**。逐帧实答核对和 53 条轨迹的浏览器验收均通过。[本地节点回放](../../../../outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/front_candidates_01/index.html) · [候选清单](../../../../outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/candidates.json)

## 版本与样本

沿用用户指定的[当前最新固定版本](../../current_jev_version.json)。上游使用服务器历史评分实现 `jev_noul_v004`，采样器和参数使用分支 `codex/jev-online-sampling-v001` 提交 `9cd8f75180fa3a3ff0c296f937396b1eca738cd9` 的原件。登记时服务器工作区 HEAD 为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，实际执行版本待开跑时记录。

输入为[选路错误离线数据集 v001](../../../offline_route_dataset/v001/run_20261118_01/README.md)，数据集 ID 为 `route_choice_multiview53_seed2_20261118_v001`，原轨迹 seed 为 2。按 53 个不同 episode 处理；4,890 个观测包含每条轨迹的终止观测，沿用旧评分协议，预计 4,837 个动作前评分位置。

## 执行协议

- 以 `mode='front'` 读取原生前视 RGB。每步取截至当前的最近三张，开头按已有一张、两张处理。全景观测、任务指令、参考路线和事件标签均不送入 JEV。
- 用户指定的 EasyJEV 服务为 `https://api.easyjev.online`，沿用已有的 `/v1/systemone` 接口及 `jev-1.14.0` 模型名。JEV 评分按 **300 个进程并行**。凭据由运行环境提供。
- 将评分按 episode 和步号还原顺序，每条轨迹独立使用固定 v001 配置（窗口 7，总确认延迟 5 步）。标出全部原始候选回退点，记录节点编号、所在步、确认步及对应前视观测。本轮到此结束，节点消除、去重、偏航判断和回退导航均未排入。

## 启动命令

```bash
nice -n 10 env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 benchmarks/vlnverse/.venv/bin/python -u -B scripts/run_offline_route_jev.py --dataset outputs/offline_route_dataset/v001/run_20261118_01/dataset --output outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01
```

本次复用逐帧评分 worker 和冻结 JS 采样器，新增数据适配入口 `scripts/run_offline_route_jev.py`。工作区含未提交的读取器和适配入口，输出 `manifest.json` 和 `source/` 记录执行时的提交、文件及 SHA256。仅 CPU 和远程 JEV 接口。

## 接续记录

2026-11-18 06:28 UTC 启动。首条轨迹 `kujiale_0036_0_0` 第 2 步使用前视帧 0/1/2，HTTP 200，`probability_yes=0.67`，实际响应模型为 `typesafe/jev-1.14-20261014`。首个主管在 303 个评分文件写入后停止分发，汇总状态滞后。已核验旧进程组 3581075 的 301 个成员均属于本次任务，正常中断后结束该组。

06:35 UTC 同一运行从 303 份已完成记录接续。按任务、步号及输入图像哈希核对缓存，剩余 4,534 个位置使用 300 个进程通过 `Pool.imap_unordered` 分发。评分、端点、数据、采样和参数哈希一致，仅调度入口有变更。初始代码保存在输出 `source/`，接续入口、对应 manifest 和旧主管状态保存在 `recovery/`。

## 结果与验证

06:51:06 UTC 完成全部评分与采样。首轮成功 4,791 个位置，46 个初次失败位置在下一轮全部补齐。最终成功响应均为 `typesafe/jev-1.14-20261014`，未用缺失值插补。各轨迹有 2–25 个候选，中位数 9。按冻结采样器类别统计，起点 `initial` 40、局部峰 `peak` 125、高分区域入口 `entry` 60、区域内间隔采样 `plateau` 269。本轮只统计候选，节点有效性尚待复核。

独立读取全部 4,837 份原始响应及前视窗口记录，逐一核对概率、步号、原生前视 SHA256；494 个候选的前视索引与确认延迟均核对通过。[逐轨迹计数和验收结果](../../../../outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/validation.json)。

网页复用分支模板，默认在地图与波形显示原始候选。浏览器逐轨迹核对页面全部概率及节点与保存结果一致，并检查双语任务指令、前视图加载及回放进度切换。[网页验收](../../../../outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/viewer_validation.json)。本地入口 SHA256 为 `026dfe5db51731bbe5e597320ad997bf1a9b8b07550438fe194968e272fd0667`；页面通过相对路径加载本仓库已有原始前视图和地图。

```bash
run=outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01
replay=outputs/offline_route_dataset/v001/run_20261118_01/exports/replay_20261118_01
backbone/streamvln/.venv/bin/python -B scripts/export_offline_route_jev.py --run "$run" --replay "$replay" --output "$run/exports/front_candidates_01"
node scripts/check_offline_route_jev.cjs "$run" "$run/exports/front_candidates_01/index.html" "$run/viewer_validation.json"
```
