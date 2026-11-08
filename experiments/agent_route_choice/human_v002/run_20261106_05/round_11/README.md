# 通用放宽第8稿（运行第11轮）

仅增加通用候选输出规则，固定sample_01与七帧、C=37、模型、seed，只阶段一。原稿均保留。

命令：`.runtime/crossing_vllm27/bin/python -B scripts/tune_route_inventory_prompt.py --output outputs/agent_route_choice/human_v002/run_20261106_05/round_11 --prompt experiments/agent_route_choice/human_v002/run_20261106_05/prompts/11_general_relax_en.txt --registration experiments/agent_route_choice/human_v002/run_20261106_05/round_11/registration.json`

状态：已登记，待调用。

结果：2条（前方客厅、后方来路），coverage=complete，右侧候选仍未出现。请求审计通过，只有system prompt改变；阶段二0调用。
