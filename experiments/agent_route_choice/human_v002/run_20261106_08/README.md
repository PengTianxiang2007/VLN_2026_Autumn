# 先识别实际路线再排除选路：单例

状态：准备。仅sample_08 / kujiale_0113_1_4（原页面6/10）。用户授权修改逻辑后只跑本episode。以07批为对照，保持第一轮原答、10张去重图片、任务、动作、schema、模型与seed不变；仅system prompt改为观察实际路线→按已知错误排除→结合指令强制选择。没有定向提示、目标分支ID或地图。仍为一次第二阶段调用内的顺序约束，不是隔离任务信息的两次调用。

Qwen27B GPU0待用服务02，temperature0、seed基数20261106、max_tokens8192、thinking=false。旧prompt与结果保留，新输出08批；实际Git和源码快照随运行保存。

命令：`.runtime/crossing_vllm27/bin/python -B scripts/force_route_stage2.py --base outputs/agent_route_choice/human_v002/run_20261106_07 --sample-id sample_08 --output outputs/agent_route_choice/human_v002/run_20261106_08 --prompt experiments/agent_route_choice/human_v002/run_20261106_08/02_choose_en.txt`

完成后导出单例完整同步HTML。

## 完成结果

仅1次第二轮调用，格式通过；仍识别/排除B3右侧、选择B1前方、high置信度，未纠正目标问题。新理由声称沙发由右侧移至正前方，与连续图像不符。第一轮原答、全部图片、user消息（包括schema）、模型参数与07批逐字一致；实际请求重建通过，仅system改变。

同步HTML位于outputs/agent_route_choice/human_v002/run_20261106_08/exports/run_20261106_01/crossing_two_stage_review.html；旧版保留，GPU0服务02继续待用。此结果说明同次调用中的顺序提示尚不足以纠正实际路线匹配；并不能证明去除任务信息的独立视觉调用会如何表现。
