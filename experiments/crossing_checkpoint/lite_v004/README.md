# lite_v004：逐方向显式检查

2026-11-08 UTC。状态：单帧探针完成，结果未改善。

以用户指定的 `best_v001` 为底稿，其他内容、三帧输入、模型、参数、评分和输出 schema 均不变，只在 prompt 中加入：

```text
Before assigning a score, inspect each direction separately: forward,
left, right, and the incoming route. For each direction, consider
whether it contains one or more possible branches, including branches
supported by partial visual cues. Then assign the score.
```

中文含义：评分前分别检查前方、左侧、右侧和来路；每个方向都要考虑是否存在一个或多个可能支路，包括只能由部分视觉线索支持的支路；完成检查后再评分。

本次只运行 `kujiale_0257_11_2` frame 26 一次，不运行整批，不代表方法整体改善。

结果：仍返回1分，理由为“当前视野中仅显示一条通往客厅深处的路径，左侧为墙壁和柜子，无其他可通行的分支。”与 `best_v001`、`lite_v002` 同为1分；逐方向检查句没有改变该帧结果。

提示词：[英文实际版本](run_20261108_01/prompt_en.txt) · [中文翻译](run_20261108_01/prompt_zh.txt)
