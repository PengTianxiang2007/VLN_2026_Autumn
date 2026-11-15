# JEV Noul 回退点判断 v001

状态：接口、7 项 CPU 测试和三帧真实调用完成。

定义与输入保持 v1 不变：使用 `t-2,t-1,t` 三帧 RGB，只判断当前 step 是否符合
最初的局部路线选择定义，因此能否作为回退点。JEV 只接收一个
`fallback_point` Noul 问题，不接收任务指令、动作、位置、地图、标签或旧回答。

必要适配：

- v1 的五档评分不再使用；
- JEV 返回 `P(fallback_point=yes)`，范围 0–1；
- 同时保存 `P(no)=1-P(yes)`；
- 不生成自然语言理由、置信度或移动动作。

入口：

```bash
.runtime/crossing_vllm27/bin/python -B scripts/probe_jev_node_score.py \
  --question-type noul \
  --output outputs/crossing_checkpoint/jev_noul_v001/run_20261108_01 \
  --episode kujiale_0207_14_4 \
  --frame 58 --frame 96 --frame 105 \
  --baseline-run outputs/crossing_checkpoint/lite_v002/run_20261108_01
```

真实返回：

- F58：`P(fallback_point=yes)=0.22`
- F96：`P(fallback_point=yes)=0.32`
- F105：`P(fallback_point=yes)=0.26`

三帧均成功解析为 Noul 概率；F105 首次传输状态为 0，自动重试后 HTTP 200。
