# v006 报警点到历史存档节点的物理回退，30 例

运行 01 已退出。数据加载器收到多余的 run_type 参数，尚未初始化物理仿真，两个分支均为 0 个动作。相同 30 例已在[运行 02](../run_20261122_02/README.md)接续。

样本来自 seed 2 的 47 例 v006 首次报警。固定 C13 首例，再用 seed 2 从其余 46 例中抽 29 例。每条在原地图与 H1 原生物理环境内分别执行逆动作和直接 reset。案例、动作、位姿、种子、源文件哈希、实际 Git 版本和程序快照见[运行清单](../../../../outputs/inverse_rollback/v001/run_20261122_01/manifest.json)。

两组独立执行原生场景初始化和 500 tick 热身，再放置为报警帧 B 的根位姿、关节位置和关节速度。根线速度、角速度原采集未保存，两组均置零。低层控制器从热身状态开始。直接回退组复用现有物理 reset 至 A（含既有的 50 tick 站稳）。逆动作组按原 A→B 动作逆序、左右互换，含前进时先向左转 12 次，按倒序前进，再向右转 12 次。历史 STOP 记录为无逆向位移。执行中只使用预先冻结的动作序列，完成后站稳 50 tick。两组均按实际末态计算相对 A 的水平误差、最短朝向角误差。水平误差 ≤0.35 米且朝向误差 ≤15°、稳定且可继续行动为达标。保留跌倒、卡住等物理失败。这里评估回退落点，整条导航任务的 SR 和 SPL 不适用。

启动前已核对当前 GPU 进程。无本项目保留的物理仿真。GPU 3 上现有本项目 Qwen 服务，复用原采集 Isaac 4.5 环境，在 GPU 3 原生共享准入通过后另启物理进程，导航和语义模型均无需调用。

```bash
out=outputs/inverse_rollback/v001/run_20261122_01
python3 -B scripts/run_inverse_rollback.py prepare --count 30 --output "$out"
tmux -L peng_inverse30_20261122 new-session -d -s rollback30 'exec python3 -Bu scripts/run_inverse_rollback.py run --output outputs/inverse_rollback/v001/run_20261122_01 --gpu 3 >> outputs/inverse_rollback/v001/run_20261122_01/supervisor.log 2>&1'
```

[主管状态](../../../../outputs/inverse_rollback/v001/run_20261122_01/status.json) · [首个物理动作](../../../../outputs/inverse_rollback/v001/run_20261122_01/startup.json) · [配对结果](../../../../outputs/inverse_rollback/v001/run_20261122_01/summary.json)。各案例目录保留起点读回、逐动作轨迹与两组落点。主管在末条完成后自动退出，24 GiB 原生 RSS 边界处释放并接续剩余分支。
