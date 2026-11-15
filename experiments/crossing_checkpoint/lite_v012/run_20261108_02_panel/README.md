# lite_v012 / 非目标控制面板

状态：已完成。

目的：检查 `lite_v012` 在目标三帧上产生变化后，是否只是在普遍抬分。

范围：

- 20条固定episode中的全部47个人工标注帧；
- 每个episode选1个远离人工标注、且 `best_v001` 与 `lite_v002` 均为1分的稳定性控制帧；
- 用户指定的非标注目标F58、F96。

共约69帧，每帧按原三帧规则调用Qwen4B一次。该面板用于诊断，不把未标注控制帧称为人工负金标准，也不更新最优版本。

结果：实际69/69完成。

- 人工标注47帧：1/2/3/5分别为9/8/22/8；`>=3` 共30，对照best_v001为25；
- 稳定性控制20帧：1/2分别为17/3，没有 `>=3`；
- 用户目标F58=2、F96=3；F105作为人工标注帧仍为1；
- 全体相对best_v001升分18、降分19；人工标注降分主要是5→3。

运行：

```bash
python3 -B scripts/run_crossing_lite_prompt_panel.py \
  --output outputs/crossing_checkpoint/lite_v012/run_20261108_02_panel \
  --prompt experiments/crossing_checkpoint/lite_v011/run_20261108_01/prompt_en.txt \
  --prompt-addendum experiments/crossing_checkpoint/lite_v012/run_20261108_01/addendum_en.txt \
  --baseline-run outputs/crossing_checkpoint/lite_v002/run_20261108_01 \
  --candidate-label lite_v012
```
