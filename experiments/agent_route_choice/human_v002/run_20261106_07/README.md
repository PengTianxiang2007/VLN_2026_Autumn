# 第二阶段强制选择十例

状态：准备。用户要求强制做出选择，复用06批同十例七帧+四帧输入、任务、动作及第一轮原答。仅改变第二阶段system与选择schema/validator，未知错路不阻断选择；禁止新增分支或选择已排除分支。不提供目标方向。原提示词保留previous_02_choose_en.txt。

模型Qwen27B常驻GPU0服务02，temperature=0、seed基数20261106、max_tokens=8192、thinking=false，单并发。sample_11第一轮包装异常照旧保留。新输出run_20261106_07，不覆盖旧结果；实际Git/源码/工作区快照随运行保存。

命令：`.runtime/crossing_vllm27/bin/python -B scripts/force_route_stage2.py --output outputs/agent_route_choice/human_v002/run_20261106_07 --prompt experiments/agent_route_choice/human_v002/run_20261106_07/02_choose_en.txt`

完成后导出完整同步HTML。强制选择率不等于正确率。

## 完成

10/10第二轮完整响应且通过新版校验，10选择、0弃答；第一轮0次新调用。sample_11原有包装问题保留，因此两轮格式均有效9/10。强制选择率不等于正确率。用户关注的第4/10例sample_06选择B3/right（客厅），wrong_branch_id=null、medium置信度；没有强制其输出左侧，语义需复核。

十例数据集与第一轮原答和06批逐字节一致；请求重建、图片/元数据/模型参数与第一轮清单传递审计10/10通过。新版validator允许未知错路，并拒绝弃答、空选择、虚构分支、方向不匹配、选已排除支路以及虚构任务引用。实际源码及Git状态在outputs/source与manifest保存。

完整HTML：outputs/agent_route_choice/human_v002/run_20261106_07/exports/run_20261106_01/crossing_two_stage_review.html，约43.85MiB，965帧完整回放。十例40关键帧浏览器验证通过：分支选择标记、双滑条同步、包装异常显示、复核导出、移动端及零外部请求。旧06批HTML未变。

GPU0服务02按用户要求保留，未重启服务。下一步人工复核选择，未自动扩大实验范围。
