# Terra Fast v006.1 九例并行评审

沿用 Astra v006.1 资格与去重提示词、前视观测 F-2/F0/F+2、seed 2 原轨迹。C01、C03、C04、C05、C11、C17、C19、C32、C34，共 77 个原始候选，九个新会话，逐例并行。gpt-6.1-terra，medium，priority，17982。清单与命令见 input.json 和 launch.json。源码快照、状态和各次请求位于 outputs/codex_tasks/checkpoint_dedup/v006_1/run_20261124_02_terra_fast_selected9。

GPT-6.1 Terra Fast v006.1 九例全部完成，77 个原始候选保留 21 个，排除 26 个不合格候选、30 个重复候选，0 格式错误。Terra v006 同批保留 18 个。九路并行 9 分 16 秒，候选调用均值 32.85 秒。当前版及配对原版的 SR、平均 SPL 均暂无，已评分 0 条。[九例双语对照](http://134.175.18.101/vln/terra_fast_v006_1_selected9_web_20261124_01/index.html)。

C01 保留 0 个；C11 保留 S04；C17 从 3 个增至 5 个。
