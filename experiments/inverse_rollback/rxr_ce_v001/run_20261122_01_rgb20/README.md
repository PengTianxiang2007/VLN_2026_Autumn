# RxR-CE 随机点对往返与第一人称 RGB

[20 组实采 RGB 和回退轨迹在线回放](http://134.175.18.101/vln/roundtrip_rxr20_h1_22_rgb_20261122_01/index.html?case=RX01) · [导出与校验记录](../../exports/paired_rgb_20261122_01/README.md)

2026-11-22 18:09 UTC 完成 20/20 组。实际 A、B 水平间距为 2.49～7.39 米。掉头与倒走各 20/20 达标，两种返程的平均水平误差均为 4.49 厘米，最大值均为 17.54 厘米。去程保存 781 张 RGB，掉头返程 1,261 张，倒走返程 781 张，合计 2,823 张。队列在 [H1 倒走版](../../v002/run_20261122_01_backward_rgb22/README.md)完成后接续，采集进程已退出。[最终状态](../../../../outputs/inverse_rollback/rxr_ce_v001/run_20261122_01_rgb20/status.json) · [逐例汇总](../../../../outputs/inverse_rollback/rxr_ce_v001/run_20261122_01_rgb20/summary.json)

## 样本与动作

从 RxR-CE 英语 Guide 的 val_unseen 实际引用的 MP3D 场景中，按 scene ID 排序取前五个，每个场景随机选取 4 对同层连通的 A、B，基础 seed 为 2。[点对清单](cases.csv)记录 20 组坐标和距离。水平面为 Habitat XZ，Y 为高度。点对要求水平直距 1.5～8 米，采样时为路径跟随器预留 0.20 米到点容差，冻结目标距离为 2.60～7.37 米。去程规划使用 Habitat GreedyGeodesicFollower，仅用导航网格。语言指令与报警节点均未参与选点。

每个 case 从 A 按冻结的去程动作实际走到 B。两种回退共用实走动作和同一个实测 B。掉头版先左转 180°，倒序执行去程动作，平移仍用前进，左右转互换，最后右转 180°。倒走版从 B 的原朝向开始，倒序执行，前进换成后退，左右转互换。每次平移 0.25 米，转向 15°，由 Habitat 的导航网格约束移动。两条返程均记录到 A 的实际水平误差和朝向误差，沿用 0.35 米、15° 的联合阈值。整条导航 SR 和平均 SPL 两组均为“暂无，已评分 0 条”。

## 观测与运行

去程、掉头和倒走各保存起始 RGB、每个动作后的 RGB（含终点），原生前视相机 640×480、水平视场 79°。每个 case 的 `result.json` 指向对应采集目录，里面三段各有 PNG 和 `trace.jsonl`，逐帧记录动作、是否碰撞、机器人和相机位置、四元数与航向角，另有俯视导航网格及坐标参数。

代码基线 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。本次新增入口和所用 RxR 配置的实际副本保存在输出 `source/` 下，[冻结清单](../../../../outputs/inverse_rollback/rxr_ce_v001/run_20261122_01_rgb20/manifest.json)记录源码哈希、全部选点与去程动作。提交时队列处于 `waiting_for_previous`，尚未采集 RGB。启动命令如下。

```bash
out=outputs/inverse_rollback/rxr_ce_v001/run_20261122_01_rgb20
prior=outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22
CUDA_VISIBLE_DEVICES='' backbone/streamvln/.venv/bin/python -Bu scripts/run_rxr_roundtrip.py prepare --after-run "$prior" --output "$out"
tmux -L peng_rxr_roundtrip20_20261122 new-session -d -s rxr20 'out=outputs/inverse_rollback/rxr_ce_v001/run_20261122_01_rgb20; exec python3 -Bu "$out/source/run_rxr_roundtrip.py" run --output "$out" --gpu 3 >> "$out/supervisor.log" 2>&1'
```
