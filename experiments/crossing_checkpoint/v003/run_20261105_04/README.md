# v003第3稿：追加六条离线测评

登记：2026-11-05T08:43:47.322972+00:00。Git：`0a805dfcf4457f80300822abb4eff7cabba43aae`。

<!-- CROSSING_V003_DRAFT03_EXTRA6_STATUS_START -->
失败/未完成；6条固定离线样本，每1个动作步调用一次。 GPU已释放。
<!-- CROSSING_V003_DRAFT03_EXTRA6_STATUS_END -->

## 目的与样本

用户明确确认追加6条新样本，与上一批三条不重叠。每个现有验证场景选择有效帧最少的一条，不按检测分数或crossing数量筛选；包括零标定访问样本以检查误报。与刚完成三条不重叠。

- kujiale_0123_fix_30_2：44次调用，1次标定访问。
- kujiale_0207_12_1：57次调用，2次标定访问。
- kujiale_0232_65_2：66次调用，3次标定访问。
- kujiale_0234_56_3：37次调用，1次标定访问。
- kujiale_0240_30_3：54次调用，1次标定访问。
- kujiale_0257_11_2：55次调用，0次标定访问。

合计313次方法调用，8次标定访问。原v002曾使用这些验证样本，属于既有验证子集复测，不能称为全新盲测。固定提示词，不根据本批次结果自动调参。

## 版本与协议

完全复用run_20261105_03冻结的检测/回放源码，prompt为crossing-v003-region-choice-draft03，SHA256 `efca53a7c341a7717096e8d730f09fc21ee7d4fae93688849a884281f37273dc`。仅样本不同。每步调用、GPU 0单并发、Qwen3.8-27B-FP8、32K、temperature=0、8192输出、关闭思考、8帧历史、32动作、2/3确认、3次缺失关闭与1m/时间窗匹配不变。导航seed2、服务seed20261103，请求seed仍按episode和原动作编号生成。输入/标定来自v002原样本；实际Git、源码哈希、工作区差异已保存。

## 启动与退出

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/test_crossing_single_gpu.py --gpu 0 --output outputs/crossing_checkpoint/v003/run_20261105_04/service_01 --campaign outputs/crossing_checkpoint/v003/run_20261105_04 --finish-when-queue-empty
```

只追加六条，不启动仿真或更多任务。GPU双次准入，加载上限2700秒，就绪后8小时，单请求600秒、最多重试1次。三个历史服务检查请求独立于方法调用。确认第0、1、2步正常产出后停止人工持续跟踪。完成/异常退出自动清理本项目服务，写回结果；公共代码仅修正完成文案的样本计数，使其兼容validation批次。

## 产物与状态

固定HTML：`/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/v003/run_20261105_04/exports/final/visualization/crossing_review_offline.html`，使用crossing-review-v1模板；三条旧版结果不覆盖。本批次完成且审计通过后才生成HTML，final_summary.json记录结果与GPU释放，原始数据在runs/v003_draft03_stride1_extra6/。

结果尚未完成。前批次第3稿三条已完成：TP4/FP3/FN4；不同样本集分数不直接比较为方法提升。完成后自动退出，不追加新批次。
