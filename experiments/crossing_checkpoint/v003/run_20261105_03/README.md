# v003第3稿：相同三条离线样本，每步调用

登记时间：2026-11-05T07:40:02.213429+00:00。Git基线：`0a805dfcf4457f80300822abb4eff7cabba43aae`；冻结源码、实际哈希及未提交差异见registration.json和orchestration_source/。

<!-- CROSSING_V003_DRAFT03_DEV3_STATUS_START -->
已完成；3条固定离线样本，每1个动作步调用一次。 TP 4 / FP 3 / FN 4。 GPU已释放。
<!-- CROSSING_V003_DRAFT03_DEV3_STATUS_END -->

## 目的与依据

用户授权继续跑相同三条，使用已准备的第3稿，每一步调用模型，导出可视化并提供下载。唯一方法变化是第3稿新增的三句提示：具体线索可支持合理的第二支路、尚未完全验证时优先crossing/medium、房间内或开放区域本身不是判否理由。依据是上一轮kujiale_0036_10_0第44帧的判否说明；4/5漏检已有crossing/here观测，因此该修改不保证解决存档合并/定位匹配问题，不扩大修改范围。

## 协议与版本

样本按原顺序为kujiale_0036_10_0, kujiale_0113_1_4, kujiale_0208_21_4；每条58、70、40次，共168次方法调用，8次标定访问。原导航seed=2；Qwen3.8-27B-FP8单GPU 0、单并发、32K、temperature=0、max_tokens=8192、关闭思考，服务seed20261103，请求seed仍按原episode与动作编号生成。最近8张有效RGB与32个已执行动作，2/3确认与连续3次缺失关闭规则不变。保留1m/时间窗一对一匹配和重复惩罚。

输入、标定与地图逐字复用run_20261105_02；冻结检测器只有SYSTEM_PROMPT和PROMPT_VERSION改变，回放脚本保持一致。prompt版本`crossing-v003-region-choice-draft03`，SHA256 `efca53a7c341a7717096e8d730f09fc21ee7d4fae93688849a884281f37273dc`。prompt副本随本记录冻结；共享core baseline提示词保留以继续做既有部署请求校验。

## 启动与退出

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/test_crossing_single_gpu.py --gpu 0 --output outputs/crossing_checkpoint/v003/run_20261105_03/service_01 --campaign outputs/crossing_checkpoint/v003/run_20261105_03 --finish-when-queue-empty
```

只跑这三条，不启动仿真、15条验证或后续调参。先核验所有GPU和占用进程，再由主管双次准入检查。加载最多2700秒，就绪后最多8小时，单请求600秒、最多重试一次；失败即清理本项目进程，正常完成自动导出并释放GPU。保留三个历史部署检查请求，独立于168次方法调用。确认当前prompt第0、1、2步正常产出后停止人工持续跟踪，遵从用户此前节省token的要求。

## 可视化与下载

采用crossing-review-v1模板，地图/RGB旁同步进度条。主管新增可选export_destination队列参数，只为固定新批次的交付路径，不改变推理/评分；导出器仍要求输出目录不存在，不能覆盖历史报告。

固定下载文件：`/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/v003/run_20261105_03/exports/final/visualization/crossing_review_offline.html`。此文件仅在三条完整结束且审计通过后生成，不提前生成空报告。后台状态和成绩见final_summary.json；原始回答、scores、diagnostics、visualization.json位于runs/v003_draft03_stride1_dev3/。

## 结果与限制

尚未完成，不报告成绩。对照为相同三条的第2稿run_20261105_02（TP3/FP3/FN5），该对照已完成且冻结不变。本次开发样本上的结果不作为独立泛化验证。完成后不自动启动下一轮。
