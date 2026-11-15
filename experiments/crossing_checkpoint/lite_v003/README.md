# lite_v003：局部侧向转弯的小幅放松

2026-11-08 UTC。状态：单帧诊断完成，不进行完整批次。

目的：只验证一个通用边界修改，即附近的侧向开口即使需要短距离转弯，也不应与“沿当前朝向直行”区别对待。该实验不针对某个样本制定特例规则，也不据单帧结果更新“最优版本1”。

- 基准：`lite_v002/run_20261108_01`
- 唯一修改：在 `WHAT COUNTS AS A ROUTE` 中加入一条通用说明
- 诊断样本：`kujiale_0113_1_4` frame 56
- 输入：与 v002 完全相同的 F0054、F0055、F0056 三帧
- 模型：复用 GPU0 常驻服务 `qwen35-4b-standby`
- 协议：相同 seed、temperature=0、thinking=false、max_tokens=256、JSON schema
- 范围：仅 1 次离线模型调用，不运行导航，不翻译，不导出完整 HTML

提示词：[英文实际版本](run_20261108_01/prompt_en.txt) · [中文翻译](run_20261108_01/prompt_zh.txt)

运行：

```bash
python3 -B scripts/probe_crossing_lite_single.py \
  --output outputs/crossing_checkpoint/lite_v003/run_20261108_01 \
  --prompt experiments/crossing_checkpoint/lite_v003/run_20261108_01/prompt_en.txt \
  --episode kujiale_0113_1_4 --frame 56 \
  --baseline-run outputs/crossing_checkpoint/lite_v002/run_20261108_01
```

结果：`kujiale_0113_1_4` frame 56 仍返回 1 分，原因为“当前视野中仅显示前方走廊和左侧房间，右侧为固定柜体，无其他可选择的通行路径。”该回答与 `lite_v002` 相同。新增一句没有改变该帧判断，结果只说明这一处措辞不足以修正该诊断点，不代表该修改对所有样本无效，也不更新最优版本。
