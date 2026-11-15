# StreamVLN + Isaac Sim 实时 JEV

更新时间：2026-11-09（UTC）
状态：首轮40条完成并发布

此类别区别于离线三帧数据集上的 JEV 批量评分。这里在 VLNVerse/Isaac Sim
真实导航过程中，每个新策略观测到达后立即把截至三帧 RGB 送入 JEV，同时保持
StreamVLN 动作、停止规则和官方评分不变。

首轮使用新场景`kujiale_0272`全部40条 episode、seed 0、H1 physical；
StreamVLN GPU4、仿真 GPU5。JEV v004 使用最多5个未决请求和`N=11,D=5`
Streaming Prominence。

首轮结果：40/40完成，SR45.0%、SPL39.10%；2878次JEV回答0错误，215个节点。
在线入口：
http://134.175.18.101/vln/streamvln_live_jev_0272_40_template_20261109_03/streamvln_live_jev_0272_40.html 。

具体记录：

- [run_20261109_01_0272_40](run_20261109_01_0272_40/README.md)

结果不得与离线 JEV 开发集分数混算；JEV 概率和采样节点不是导航成功率，也不改变
StreamVLN 的决策。
