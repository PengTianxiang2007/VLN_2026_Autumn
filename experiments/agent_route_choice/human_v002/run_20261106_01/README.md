# 两例阶段一：窗口后移10帧

2026-11-06，状态：两例阶段一已完成。目的：检验晚间两例的时间窗口后移是否改善阶段一支路盘点。

统一规则：保留4图、5帧间距，C为原人工标注帧，新判断帧P=C+10，采样[C-5,C,C+5,C+10]。sample_23：原[46,51,56,61]→[56,61,66,71]；sample_11：原[0,2,5,7]→[2,7,12,17]。后者接近上午同轨迹的[3,8,13,18]。规则在调用前固定，不根据新回答挑图或重试语义结果。

只改变观察/判断时间窗口及随P更新的已执行动作；输入动作最多32条、均发生在P之前。保持原英文阶段一提示词、JSON schema、temperature=0、max_tokens=8192、enable_thinking=false和sample_id派生种子不变。模型沿用晚间Qwen27B-FP8，复用GPU0常驻服务；模型服务别名变化不代表权重变化。无阶段二、指令输入、地图或正确分支标签输入。

这是相对原标注点延迟10帧的离线观察试验，不将C之后的图像冒称为C时刻已有历史。C保留，实际current_view_id改为P。两例为已检查的开发案例，不是盲测，不据两例推断全部差距仅由窗口造成。

启动：
```sh
.runtime/crossing_vllm27/bin/python -B scripts/probe_route_inventory_window.py --registration experiments/agent_route_choice/human_v002/run_20261106_01/registration.json --output outputs/agent_route_choice/human_v002/run_20261106_01 --execute
```

验证：新阶段一构造器需与原构造器在原输入上完全一致；原请求除服务别名外采样参数一致，图片哈希和无损PNG像素校验、动作时间边界检查。原始请求/响应与源码快照保存到输出目录。后续记录真实回答和视觉复核，服务保持待用。

## 实际结果

两次请求各一次网络尝试，均finish_reason=stop，网络错误0、原schema通过。sample_23从0条到3条：恢复门口候选，但仍以第一张F0056的四联画描述当前F0071，并把“Dead end or wall”列为B3；不能认定清单正确。sample_11从2条到3条：补出黑衣柜、床、窗帘所指的卧室分支；B1与B3是否重复、方向及来路仍待复核。两例均自报coverage=complete，不代表实际覆盖完整。

本次支持“后移可改善部分视觉内容”，不支持“只有时间窗口一个问题”。未执行阶段二或新导航，常驻Qwen仍保留。输入审计、原始请求/响应、semantic_review.json及同步回放HTML位于输出目录。下一步应分开检查当前帧对应与同一入口去重；未自动追加模型调用。
