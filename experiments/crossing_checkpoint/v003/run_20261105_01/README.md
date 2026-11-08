# v003第2稿：五条离线测评，每两步调用一次

登记时间：2026-11-05T05:27:10.656785+00:00。实际Git基线：`0a805dfcf4457f80300822abb4eff7cabba43aae`；未提交源码与差异已冻结至运行目录。

<!-- CROSSING_V003_BATCH_STATUS_START -->
已完成；5条固定离线样本，每2个动作步调用一次。 TP 4 / FP 2 / FN 9。 GPU已释放。
<!-- CROSSING_V003_BATCH_STATUS_END -->

## 用户授权与协议

只评测v002原来的5条开发轨迹，不运行15条验证，不新增调参。使用第2稿prompt（SHA256 `54ab928263fefa2684d9317550e59cfdbf72d2febd42d5c804beb53296cea851`），模型为Qwen3.8-27B-FP8，单GPU 0、单并发、32K上下文、FP8、关闭思考、8192输出上限、temperature=0，服务种子20261103。原导航seed=2，逐请求seed仍按原episode和原动作编号生成。

调用位置为原动作编号0、2、4……，终止/复用画面仍按原规则排除。原292次调用减为146次；5条调用数依次为29、35、20、29、33。每次输入仍为最近8张有效RGB、最近32个已执行动作及当前存档记忆，含未调用步骤的画面和动作。仅真实回答更新状态机；2/3确认、连续3次非正例关闭等参数保持不变，计数单位仍是模型观测，因此覆盖的动作步跨度相应增加。

地图、实际轨迹与13次标定访问保持原样，1m首次确认位置和访问时间窗一对一匹配，重复计FP。提示词与调用频率同时变化，分数差不能单独归因于prompt。

## 启动与后台收尾

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/test_crossing_single_gpu.py --gpu 0 --output outputs/crossing_checkpoint/v003/run_20261105_01/service_01 --campaign outputs/crossing_checkpoint/v003/run_20261105_01 --finish-when-queue-empty
```

入口先重验3个既有部署请求，再执行固定的单个五条回放作业。每请求最多重试一次、600秒超时；失败即中止该回放并清理本项目进程；服务加载最多2700秒、就绪后最多8小时。完成后自动评分、诊断、按既定双进度条模板导出HTML并关闭本次服务，记录显存释放证据。确认本轮结果正常产出后停止人工持续跟踪。

## 产物

运行目录：`outputs/crossing_checkpoint/v003/run_20261105_01/`。最终摘要为`final_summary.json`，逐例原始回答在`runs/v003_region_choice_stride2/cases/`，分数为`runs/v003_region_choice_stride2/scores.json`，HTML路径记于`runs/v003_region_choice_stride2/visualization.json`。最终状态和资源清理由后台写入本README及项目状态索引。

## 启动前检查

16项原Crossing CPU检查及3项隔步调用检查通过。0/2/4…抽样保留所有中间RGB与动作，状态机仅按真实回答计票；冻结检测器除prompt与版本号外与baseline相同。CPU浏览器样例验证8张历史图像（含未调用步骤）、同步进度条、未调用图像说明及离线打开均通过。样例仅用于UI检查，不计入方法测评结果。
