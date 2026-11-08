# 确认走错后尽早纠正

更新时间：2026-11-04。本文依据既有记录整理；本次整理没有启动实验。

状态：10/10 已完成。与上级 pilot10 共用十条任务和对照。

全组成功 10/10；实际干预 10 条；纠正 18 次；无干预成功 0 条。
完整协议和限制见上级 README 与原文档。实际源码版本以该组 manifest、code_oracle 快照为准。

启动入口（仅供新获授权的运行参考；旧结果不得覆盖）：

```bash
python3 -B scripts/run_oracle_crossing.py --campaign outputs/oracle_crossing/seed2_10_multi_20261103 --arm oracle --gpu <已核验GPU> --sim-gpu <已核验GPU>
```

命令从仓库根目录执行。实时审阅使用 scripts/oracle_crossing_console.py；不能无人审阅地当作自动恢复模型。
该组已结束，不需要继续运行。

## 代码、启动说明与产物

- [实验配置、任务与版本](../../../../outputs/oracle_crossing/seed2_10_multi_20261103/manifest.json)
- [原始结果](../../../../outputs/oracle_crossing/seed2_10_multi_20261103/report/results.json)
- [该组报告](../../../../outputs/oracle_crossing/seed2_10_multi_20261103/report/index.html)
- [运行与审阅说明](../../../../docs/ORACLE_CROSSING_PILOT.md)

## 按配对实验模板重新导出的离线 HTML（2026-11-04）

用户要求重新制作最初 10/10 全成功组的可视化，已按共享前缀三档报告的布局与交互风格导出单组版本。文件约 6.82 MB（6.50 MiB），内嵌 915 张图像。包含任务切换、播放/暂停/拖动、18 次纠正精确前后跳转、真实 RGB 与地图、历史无干预轨迹开关、近目标/多次纠正/局部碰撞筛选、结果表和 CSV 下载。旧组与历史对照仍是独立运行，没有标为共享前缀。

- [新版单文件 HTML](../../../../outputs/oracle_crossing/seed2_10_multi_20261103/oracle_early10_offline.html)
- [构建元数据与原始记录核验](../../../../outputs/oracle_crossing/seed2_10_multi_20261103/oracle_early10_offline.build.json)
- [浏览器检查结果](../../../../outputs/oracle_crossing/seed2_10_multi_20261103/early_visualization_validation/browser_verification.json)

只读取既有结果，并从旧五组离线 HTML 提取本组已导出的图像；十条指标、动作数、18 次接管位置与原始 intervention.json/memory_proof.json 逐项核验。首次落点在成功半径内的为 3 条，若包含后续接管则有 4 条含半径内纠正；两种口径在界面中区分。终止帧沿用旧记录的末次 RGB，明确显示复用说明。没有重新运行模型或仿真。

浏览器检查十条任务及 18 个纠正边界全部通过，播放、拖动、缩放、筛选、RGB 放大、CSV 导出和移动端布局正常，无页面错误或外部网络请求。导出代码、模板、当前导出版本与来源哈希保存在本组 `visualization_export_20261104_early/`；原实验源码版本以 manifest/code_oracle 为准。

```bash
python3 -B scripts/build_oracle_early_replay.py
```
