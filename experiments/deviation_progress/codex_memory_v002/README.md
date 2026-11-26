# Codex 同会话偏航识别 v002

2026-11-26 [Terra xhigh 43 例 · 7892](run_20261126_02_terra_xhigh43_7892/README.md) 依用户指令停止剩余评审和自动重试，完成 39/43，取消 C02, C15, C31, C39。 [Astra / Terra 双模型回放](http://134.175.18.101/vln/codex_deviation_v002_terminal4_map_layers_web_20261125_01/index.html)。

2026-11-26 [Terra xhigh 43 例离线评审](run_20261126_01_terra_xhigh43/README.md) 已按用户要求停止，完成 0/43。

回退点候选固定使用 JEV v002 精简档（active），筛选沿用 v006.1。沿用 v001 的二分类、单轨迹会话与零附件偏航 Prompt。新增真实终止节点 END。尚未报警时，先把原生终止前视图作为终止观测传入同一会话，然后以最后有效节点为 A、END 为 B 进行纯文本判定。首次报警结束该例。没有保留节点时，单独记录 END 的初始化，不能据此认定此前路线正常。

[首轮四例与冻结输入](run_20261125_01_terminal4/README.md)

[随机追加五例](run_20261125_02_random5/README.md)

[C01 S04 单候选复判](run_20261125_03_c01_s04/README.md)

[C27 终止段七张中间图对照](run_20261125_04_c27_interval7/README.md)

[C27 终止段补 3–7 张图对照](run_20261125_05_c27_frames3to7/README.md)

[C27 补图五档计时复测](run_20261125_06_c27_frames3to7_repeat/README.md)

[C35 两段条件补图评审](run_20261125_07_c35_conditional/README.md)

[八例最大间隔六帧重跑](run_20261125_08_gap6_eight/README.md)

[34 个未跑 case 六帧补图评审](run_20261125_09_gap6_remaining34/README.md)
