# Astra 常规档 v006.1 全 53 例

seed 2，冻结 VLNVerse 53 例 494 个原始候选。同配置复用 C01/C11 的 12 个判断，另跑 51 例 482 个候选，包括 C32。GPT-6 Astra medium 常规档，17982，最多 20 个同时评审的 case；按 case 开新会话、按时间顺序判断，空位自动补下一例。冻结输入和命令见 input.json、reuse.json、launch.json；Git 状态、源码快照、日志与会话记录在 outputs/codex_tasks/checkpoint_dedup/v006_1/run_20261124_04_astra_standard_all53。

后台主管 PID 3847914，实验状态见 outputs/codex_tasks/checkpoint_dedup/v006_1/run_20261124_04_astra_standard_all53/status.json；技术补跑、汇总、双语导出和发布由 finish.py 接续，阶段见 outputs/codex_tasks/checkpoint_dedup/v006_1/run_20261124_04_astra_standard_all53/delivery_status.json。

GPT-6 Astra 常规档 v006.1 完成 53 例。494 个原始候选保留 146 个，排除 161 个不合格候选与 187 个重复候选。候选调用均值 94.19 秒。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[完整回放](http://134.175.18.101/vln/astra_standard_v006_1_all53_web_20261124_01/index.html)。
