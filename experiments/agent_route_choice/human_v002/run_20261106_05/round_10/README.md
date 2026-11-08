# 通用放宽第7稿（运行第10轮）

唯一新增变更：开头定义与候选阈值一致，不要求确认可通行性或独立目的地。固定sample_01、七帧、C=37、模型与seed；仅阶段一。

启动命令：`.runtime/crossing_vllm27/bin/python -B scripts/tune_route_inventory_prompt.py --output outputs/agent_route_choice/human_v002/run_20261106_05/round_10 --prompt experiments/agent_route_choice/human_v002/run_20261106_05/prompts/10_general_relax_en.txt --registration experiments/agent_route_choice/human_v002/run_20261106_05/round_10/registration.json`

状态：已登记，待调用。

结果：2条，coverage=partial，右侧候选未出现；仅uncertainties提到潜在侧向分支。
