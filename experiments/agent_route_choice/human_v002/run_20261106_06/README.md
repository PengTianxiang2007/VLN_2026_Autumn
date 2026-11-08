# 七帧十例接续第二阶段

状态：准备。仅运行第二阶段10次，沿用run_20261106_04第一轮原始结果；sample_11包装格式异常原样传递，显示/校验提取properties但不改原答。

每例以原C为当前位置，7张上下文[-4,-2,0,2,4,6,10]加旧prep错误片段均匀4张，按帧去重、双用途标记。超过错误终点的上下文不是错误经历。指令/动作与第一轮原答完整提供；上午第二轮system prompt不变。Qwen27B GPU0服务仅max_images从8改11，模型参数/seed保持；第一轮0次新调用。

用户已授权执行并导出完整双进度条可视化。历史输出不覆盖，实际Git/工作区及源码快照保存在outputs。

启动：后台service主管395599，第二阶段worker395600；服务记录outputs/model_services/qwen27b_gpu0_20261106_02/service.json。启动命令：`.runtime/crossing_vllm27/bin/python -B scripts/continue_route_stage2.py --output outputs/agent_route_choice/human_v002/run_20261106_06`。导出命令：`backbone/streamvln/.venv/bin/python scripts/export_route_stage2_continuation.py --run outputs/agent_route_choice/human_v002/run_20261106_06`。

模型沿用Qwen3.8-27B-FP8，temperature=0、seed基数20261106、enable_thinking=false、max_tokens=8192；请求seed按sample和stage派生。仅服务max_images改11，默认8不变；7项相关CPU检查通过。实际状态以outputs/status.json为准。

## 完成结果

10/10第二轮完整响应，第一轮新增调用0，十份第一轮原答逐字节保留。3例选择：sample_08识错B3→选B1/front；sample_11识错B2→选B1/left；sample_23识错B2→选B1/front。其余7例insufficient_evidence，不应解释为请求失败。选择正确性尚待人工复核，不能把3/10当作成功率。

七例弃答将route_description填null，不符合冻结上午严格schema；原答保留不修复。sample_11第一轮properties额外包装原样传入，第二轮自身格式通过。因此第二轮格式通过3/10，两轮均格式通过2/10；与语义正确性分开报告。保留原始错误信息Expected a bounded text field。

实际请求重建10/10通过；图像哈希、固定七帧偏移、去重集合与第一轮原答传递全部核验。7项相关CPU检查通过。源码快照/工作区差异与实际Git提交记录在manifest及source/。

完整HTML：outputs/agent_route_choice/human_v002/run_20261106_06/exports/run_20261106_01/crossing_two_stage_review.html（约43.86MiB）；包括965帧完整回放、主视图/地图双滑条、两轮输入用途、分支/错误/排除/最终选择、原答、复核导出。浏览器十例40关键位置、分支标记、包装异常提示、复核JSON与移动端通过，零外部请求、零JS错误。

GPU0新服务保持待用，outputs/model_services/qwen27b_gpu0_20261106_02/service.json，max_images=11；旧01服务已正常关闭。下一步人工复核选择与弃答，不自动重跑或修改第一阶段。
