# 回退退出条件候选稿：回到 A 的选路位置

以[首批实际使用的回退 prompt](../../run_20261123_03_deepseek3/return_en.txt)为底稿，在[英文全文](return_en.txt)中替换原先以 “If the evidence supports” 开头的退出句。已用于[四例重跑](../../run_20261123_06_choice_position4/README.md)。

新判据的中文译文：

> 只有当回程观测表明你已经回到 A 当时的选路位置，才将 `arrived` 设为 true 并返回空动作列表。在当前站位（允许原地转向），你应当能看到并选择 A 当时可走的那些通路。如果还得继续往回走才能到达可作出这些选择的位置，或者回程开始后你只在 B 转过向，就保持 `arrived=false`。
