# JEV 节点评分接口 v001

状态：接口实现、6 项 CPU 测试和三帧真实请求完成。40 帧混合面板属于额外扩展，
用户在完成 10/40 后询问并停止，不用于最终结论。

目的：尝试用 TypeSafe JEV 的 System One 接口判断当前位置是否为局部路线选择节点。
该版本不沿用文本生成式的自由回答，而是发送一个五级 `Score` 和三个彼此独立的
`Noul`（前方、左侧、右侧是否存在局部可通行路线），直接读取分数、各档概率和置信度。

接口：

- API 根地址：`https://api.site`；
- 端点：`POST /v1/systemone`；
- 模型：`jev-1.14.0`；
- 鉴权：运行时从 `JEV_API_KEY` 读取，或交互式 stdin 输入；密钥不落盘；
- 图像：严格使用 `t-2,t-1,t` 三帧，内存中转成 PNG，附
  `TypeSafe-Danger-Zone-Images: true`；
- 输入隔离：不发送任务指令、动作、位置、地图、成败标签、旧模型回答或未来帧。

输出：JEV 原始 `Score` 为 0–4，期望值加 1 后四舍五入映射到现有 1–5 整数尺度；
同时保留连续分、原始分数、各档概率、最高概率档位和三个方向概率。

入口：

```bash
.runtime/crossing_vllm27/bin/python -B scripts/probe_jev_node_score.py \
  --output outputs/crossing_checkpoint/jev_v001/run_20261108_01 \
  --episode kujiale_0207_14_4 \
  --frame 58 --frame 96 --frame 105 \
  --baseline-run outputs/crossing_checkpoint/lite_v002/run_20261108_01
```

限制：当前只做单帧诊断时，不构成方法准确率或优于 Qwen 的结论。所有英文请求问题
均在 `core/jev_node.py`，完整中文翻译由 `question_translation()` 生成并随运行写入
`questions_zh.json`。

真实结果：`kujiale_0207_14_4` 的 F58/F96/F105 映射分数均为 3；连续分分别为
2.72/3.31/2.91，置信度分别为 0.07/0.03/0.00。对应 `best_v001` 均为 1 分。
这证明接口能接收三帧图像并返回可解析的 JEV Score/Noul，但低置信度和平铺概率不支持
“准确率提升”或“优于 Qwen”的结论。正式产物为
`outputs/crossing_checkpoint/jev_v001/run_20261108_04/`。
