# Terra Fast v006 九例补齐

选择指定回放页面中的七条剩余轨迹，C01、C03、C05、C11、C17、C19、C34，合计54个原始候选。复用已完成的 C04、C32。采用 v006 二元规则，三帧，轨迹 seed=2，gpt-6.1-terra/medium、Fast、17982 代理，每例独立会话，共7个并行进程。启动参数见 launch.json，源码哈希及工作区快照在输出目录 outputs/codex_tasks/checkpoint_dedup/v006/run_20261124_03_terra_fast_remaining7。

Terra Fast v006 九例全部完成，77 个原始候选保留 18 个，删除 59 个。新跑七例 54 次候选调用平均 27.04 秒，七路并行共 489.4 秒；九例全部候选平均 28.05 秒。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。

汇总 outputs/codex_tasks/checkpoint_dedup/v006/run_20261124_03_terra_fast_remaining7/selected9/results.json。

[九例可视化](http://134.175.18.101/vln/terra_fast_v006_selected9_web_20261124_02/index.html)。
