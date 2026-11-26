# GPT-6 Astra v006 九例对照

C01、C03、C05、C11、C17、C19、C34 共 54 个原始候选，七路并行；复用 run_20261124_01 的 C04/C32。沿用该轮 gpt-6-astra / medium、常规档、代理 17982，v006 二元规则，前视三帧，轨迹 seed=2。启动见 launch.json。源码快照与进度在 outputs/codex_tasks/checkpoint_dedup/v006/run_20261124_04_astra_remaining7。

GPT-6 Astra v006 九例已完成，77 个原始候选保留 24 个，23 个不具备回退点资格，30 个因重复被替换。同批 Terra Fast 保留 18 个。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[九例对照网页](http://134.175.18.101/vln/astra_terra_v006_selected9_web_20261124_01/index.html)。

新跑七例耗时 29 分 33 秒。九例候选调用均值 117.20 秒，中位数 119.58 秒。0 格式错误，0 失败 case。结果见输出目录 selected9/results.json、selected9/timing.json 与[导出记录](exports/selected9_01/README.md)。
