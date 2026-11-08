# 原C固定：七帧阶段一十例

状态：已完成并导出。用户纠正：保持原人工标注C为当前判断点，固定采样[C-4,C-2,C,C+2,C+4,C+6,C+10]。同样十例01/02/05/06/07/08/09/10/11/23，current_view_id=C；C前历史与C后观测明确分组，不把最后一帧当当前位置。

沿用冻结上午英文system prompt、schema、Qwen27B及请求种子；user元数据增加离线前后观察说明以及C后动作，帮助将后续画面映射回C。C前动作仅发生于C之前，C后动作单列。此为离线回顾，不宣称C时刻因果可用。只执行阶段一10次，保留GPU0服务。

命令：
```sh
.runtime/crossing_vllm27/bin/python -B scripts/probe_route_inventory_anchor.py --registration experiments/agent_route_choice/human_v002/run_20261106_04/registration.json --output outputs/agent_route_choice/human_v002/run_20261106_04 --execute
```

源码、实际Git版本、图片哈希、请求和响应审计保存在输出目录。旧批次均保留，新结果与HTML单独保存。准备时逐例验证七个偏移、第三张即C及当前帧不移动；结果待补充。


完成：10份完整响应，9份原schema有效；样本11额外包装type/properties等字段导致格式失败，原答完整保留，HTML仅提取properties内部清单供展示并明确标记无效。无第二轮、无语义修复重试。十例独立核验current_view_id等于原C、第三张为C、偏移严格[-4,-2,0,2,4,6,10]。浏览器90个位置及十例七图/C锚定/地图同步/复核导出检查通过。

HTML：outputs/agent_route_choice/human_v002/run_20261106_04/exports/run_20261106_01/crossing_centered_stage1_review.html。结果不表示语义正确；例如sample_05仍有将浴室描述对应到C的问题，保留原答待复核。Qwen GPU0服务保持待用。
