# RxR-CE 与 H1 实采回退对照回放

2026-11-22 23:53 UTC 已发布。[RxR-CE 入口](http://134.175.18.101/vln/roundtrip_rxr20_h1_22_rgb_20261122_01/index.html?case=RX01) · [H1 入口](http://134.175.18.101/vln/roundtrip_rxr20_h1_22_rgb_20261122_01/index.html?case=C03)。入口与 5,138 项依赖均通过远端 SHA256 核对，公网入口 HEAD 返回 HTTP 200。[发布回执](../../../../outputs/visualization_publishing/publish_20261122_235302_738105/publication.json)

汇集 [RxR-CE 五场景 20 组](../../rxr_ce_v001/run_20261122_01_rgb20/README.md)、[H1 掉头 22 组](../../v001/run_20261122_03_rgb22/README.md)与[同点对 H1 倒走 22 组](../../v002/run_20261122_01_backward_rgb22/README.md)。H1 按原报警案例、episode、场景、A/B 帧和历史动作匹配。两套环境均展示去程、逐步回退和最终位姿，H1 另显示两批各自独立执行的直接 reset。

共 42 个案例、5,060 帧。RxR-CE 去程、掉头、倒走分别为 781、1,261、781 帧。H1 历史去程 560 帧，两批回退及对应 reset 共 1,677 帧。网页使用原始实采图像的 WebP 显示副本。H1 起始帧相机与机器人水平距离超过 1 米时显示实际偏差。左右画面按从 B 开始的动作序号对齐，各自显示帧号，先结束的一侧保留末态。

RxR-CE 两组各 20/20 达标，平均水平误差约 4.49 厘米。H1 掉头 2/22 达标、倒走 0/22 达标，直接 reset 两批均 22/22 达标。整条导航的 SR 与平均 SPL 两组均为“暂无，已评分 0 条”。

本地打开[回放入口](../../../../outputs/inverse_rollback/exports/paired_rgb_20261122_01/index.html)，移动时保留同目录的图片、案例、字体及脚本。[浏览器检查](../../../../outputs/inverse_rollback/exports/paired_rgb_20261122_01/browser.json)覆盖中英文切换、对应案例实采图、终点、缩放、线宽、朝向及同步帧。[资源清单](../../../../outputs/inverse_rollback/exports/paired_rgb_20261122_01/online_manifest.json)含 5,138 项依赖。入口 SHA256 为 `7da7ec24811a9ab79054df03e79fbbcc057fcb2c507cdbff31fe389522c298be`。

导出入口为 [export_roundtrip_comparison.py](../../../../scripts/export_roundtrip_comparison.py)，播放器见 [HTML](../../../../core/roundtrip_comparison.html) 与 [JavaScript](../../../../core/roundtrip_comparison.js)。从仓库根目录运行，输出参数使用新的目录。

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_roundtrip_comparison.py outputs/inverse_rollback/exports/paired_rgb_20261122_01
```
