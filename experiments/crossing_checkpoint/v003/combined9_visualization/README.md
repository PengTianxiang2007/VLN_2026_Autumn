# Qwen第三稿九条合并可视化

目的：用户要求将第三稿原3条与追加6条放入一个离线HTML。仅CPU合并已完成且审计通过的报告，不启动模型/仿真，不修改原始输出或评分。

来源：run_20261105_03原3条（TP4/FP3/FN4）和run_20261105_05追加6条（TP2/FP3/FN6）。已核验样本不重叠、同一prompt SHA256、均为逐步调用。共9条481观测，TP6/FP6/FN10，P50%、R37.5%、F1 42.86%。原开发与既有验证子集分组保留，不能称为全新独立测试。

导出使用scripts/export_crossing_campaign.py的build(report_paths=...)，默认crossing-review-v1模板。新目录/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/v003/combined9_export_20261105_01，可视化visualization/qwen_draft03_9_cases.html。版本按钮分别为原3条和追加6条；每批描述注明九条合计。来源SHA256与原始metrics保存在aggregate_summary.json；模板源码快照由导出器保存。只检查合并完整性、图像池往返、浏览器切换及双进度条，不重跑推理。

状态：准备导出。

已完成：9条/481观测，HTML 21,934,183字节（约20.9 MiB）。原审计报告哈希及图像池往返校验通过；实际浏览器核验两批切换、九条图片解码和同步双进度条通过，0脚本错误、0外部网络请求。
