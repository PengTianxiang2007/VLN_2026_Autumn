# 智谱十条统一low思考强度重试

默认max多条请求长时间不结束，之前8192 token全用于思考，扩容与流式后仍仅缓慢推进。已核验官方支持low/high/max，改用low（https://docs.bigmodel.cn/api-reference/模型-api/对话补全）；prompt、样本、逐步调用、10并发、存档和评分不变。

为不混合思考强度，588次从头运行；run_01与run_02保留。实际输出上限32768，长度截断可翻倍至131072；流式网络错误最多8次退避重试；整体8小时。密钥只走stdin进入内存，进程退出释放，不落盘。

命令：benchmarks/vlnverse/.venv/bin/python -B scripts/run_crossing_remote.py outputs/crossing_checkpoint/v004/run_20261105_03

状态见status.json。完成后自动评分、模板导出至exports/final/visualization/crossing_review_offline.html。此批次应标为GLM-5.3-Flash low，不能冒充此前max设置。
