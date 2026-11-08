# v003第2稿：前三条离线样本，每步调用

登记时间：2026-11-05T06:17:49.487811+00:00。Git：`0a805dfcf4457f80300822abb4eff7cabba43aae`。用户要求恢复逐步调用，只跑三个；按原五条顺序取前三条。

<!-- CROSSING_V003_DEV3_STRIDE1_STATUS_START -->
已完成；3条固定离线样本，每1个动作步调用一次。 TP 3 / FP 3 / FN 5。 GPU已释放。
<!-- CROSSING_V003_DEV3_STRIDE1_STATUS_END -->

## 目的与设置

保持第2稿prompt及其他流程，恢复每一步调用。样本：kujiale_0036_10_0, kujiale_0113_1_4, kujiale_0208_21_4，计划调用58、70、40，共168次；标定访问8次。只跑这三条，不运行15条验证或自动调参。上一轮五条已完成并释放GPU，保留全部历史结果。

模型Qwen3.8-27B-FP8，GPU 0单卡单并发、32K、temperature=0、max_tokens=8192、关闭思考。原导航seed=2，服务20261103，请求seed按原episode/动作编号生成。最近8帧有效RGB与32动作，2/3确认和3次缺失关闭不变。评分仍为1m及时间窗一对一匹配，重复计FP。Prompt SHA256：`54ab928263fefa2684d9317550e59cfdbf72d2febd42d5c804beb53296cea851`。

协议、输入、地图来自上一轮，输入限制前三条，冻结检测与回放源码完全复用上一轮。公共主管仅将收尾文案改为读取实际样本数/stride及独立状态标记，避免覆盖旧批次记录。实际源码哈希及未提交差异见registration.json和orchestration_source/。

## 启动

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/test_crossing_single_gpu.py --gpu 0 --output outputs/crossing_checkpoint/v003/run_20261105_02/service_01 --campaign outputs/crossing_checkpoint/v003/run_20261105_02 --finish-when-queue-empty
```

启动前双次GPU准入检查；沿用三个历史部署请求检查，再开始168次方法调用。仅确认本轮0、1、2步正常产出后停止人工持续跟踪。服务加载最多2700秒，就绪后8小时，单请求600秒、最多重试一次；失败立即清理自己的进程。

## 产物与限制

产物目录`outputs/crossing_checkpoint/v003/run_20261105_02`。后台完成后评分、使用crossing-review-v1模板导出HTML，释放本项目GPU服务并写入final_summary.json和本记录。原始结果在runs/v003_region_choice_stride1_dev3/，HTML路径见visualization.json。未完成前不报告最终成绩；与上一轮比较应限相同三条，不能直接比较三条与五条总分。

## 下一步

正常启动后交给后台；完成/失败后自动退出，不追加其他样本。
