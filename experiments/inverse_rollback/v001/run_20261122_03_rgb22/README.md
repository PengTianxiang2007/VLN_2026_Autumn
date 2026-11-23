# 原始报警点对的物理回退与原生 RGB 采集

[全部 22 组掉头与倒走回退的实采对照回放](http://134.175.18.101/vln/roundtrip_rxr20_h1_22_rgb_20261122_01/index.html?case=C03) · [导出与校验记录](../../exports/paired_rgb_20261122_01/README.md)

2026-11-22 17:12 UTC 完成 22/22 组。掉头回退 2/22 达标，平均水平误差 1.999 米、平均朝向误差 60.27°。同组直接 reset 22/22 达标，平均水平误差 0.0176 米、朝向误差 0.31°。[逐例结果](../../../../outputs/inverse_rollback/v001/run_20261122_03_rgb22/summary.json)

2026-11-22 16:13 UTC，首两例 C03、C05 的[双语实采回放](http://134.175.18.101/vln/inverse_rollback_rgb_c03_c05_20261122_01/index.html)已发布。包含 52 张历史去程图、105 张回退实采图及 97 个逆动作。核对起点图的相机记录发现，刚放置时相机到机器人 B 点的水平距离在 C03 约 5.90 米，C05 约 7.60 米。页面在两种回退的起始帧标明差值，并提供历史 B 图。两例的逐逆动作帧和末态中，相机与机器人的水平距离均小于 0.30 米。

导出命令使用 `scripts/export_inverse_rollback_replay.py`，传入本轮 `--run` 及 `--cases C03 C05`。[离线页面](../../../../outputs/inverse_rollback/v001/run_20261122_03_rgb22/exports/c03_c05_rgb_01/index.html) SHA256 为 `f1d4e3683fe3cecd9b26a7a2e94e37c679ecfc200dbfdf5ce7ef999150037554`。[本地浏览器检查](../../../../outputs/inverse_rollback/v001/run_20261122_03_rgb22/exports/c03_c05_rgb_01/browser.json)已验证起点提示、逐步 RGB、落点切换、双语及地图控件。[在线资源清单](../../../../outputs/visualization_publishing/inverse_rollback_rgb_c03_c05_20261122_01/online_manifest.json)含 160 项资源，全部远端 SHA256 校验通过，入口 HTTP 200。[发布回执](../../../../outputs/visualization_publishing/publish_20261122_161304_424395/publication.json)

启动已确认并交后台。GPU 3 上的主管 PID 3941325，首个 Isaac PID 3941366。首例 C03 从 F45 回退至 F25，水平距离 1.618910 米。B 起点与第一次左转的两张 PNG 已成功读回，均为 640×480 RGB，文件 SHA256 与动作记录一致且两帧不同。仿真步分别为 503 和 553。独立 Qwen27B 服务随后按用户要求停止，不参与本轮采集。

2026-11-22，用户确认只采原 v006 的 22 组。对 seed 2 的 47 个首次报警点对，按原采集机器人根位姿计算 A 和 B 的水平直线距离，保留全部 ≥1.5 米的不同 episode。A 为原回退目标，B 为原报警点。样本距离 1.619–6.011 米。[逐例 A/B 帧及距离](cases.csv)

沿用[运行 02](../run_20261122_02/README.md)的 H1 原生仿真、逆动作与直接 reset 对照。两组均在 B 就位后采集一张原生前视。逆动作组在每个实际执行的动作边界保存 PNG，在最终落点再保存一张。直接 reset 组在最终落点保存一张。观测为实测 640×480 RGB，保存在 `cases/<案例>/rgb/<组>/`。起点、逐动作轨迹及末态 JSON 各自关联相机位姿、仿真步和时间、文件路径及 SHA256。起点采用原场景零时长渲染观察，首次完成逆动作并实际保存起点与动作图像后交后台。

筛选、运行和原生轨迹均沿用 seed 2。代码版本与哈希在[清单](../../../../outputs/inverse_rollback/v001/run_20261122_03_rgb22/manifest.json)，运行侧使用冻结脚本。命令从仓库根目录执行。

```bash
out=outputs/inverse_rollback/v001/run_20261122_03_rgb22
python3 -B scripts/run_inverse_rollback.py prepare --count 22 --min-ab-xy-m 1.5 --capture-rgb --output "$out"
tmux -L peng_inverse_rgb22_20261122 new-session -d -s rgb22 'exec python3 -Bu scripts/run_inverse_rollback.py run --output outputs/inverse_rollback/v001/run_20261122_03_rgb22 --gpu 3 >> outputs/inverse_rollback/v001/run_20261122_03_rgb22/supervisor.log 2>&1'
```

[实时状态](../../../../outputs/inverse_rollback/v001/run_20261122_03_rgb22/status.json) · [首例两张图及动作证明](../../../../outputs/inverse_rollback/v001/run_20261122_03_rgb22/startup.json) · [配对结果](../../../../outputs/inverse_rollback/v001/run_20261122_03_rgb22/summary.json)。回退几何达标要求水平误差 ≤0.35 米、朝向误差 ≤15° 且可继续行动。实验不进行整条导航评分。
