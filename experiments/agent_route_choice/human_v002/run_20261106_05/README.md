# sample_01：局部线索阈值逐步放宽

状态：本轮通用放宽试验已收尾，目标未达成；没有选定成功提示词。用户要求仅重跑sample_01直到右侧通道候选被识别，prompt每轮仅小幅放宽，旧版保留。本目录00_previous_en.txt为七帧版原system prompt的逐字节副本。

样本kujiale_0036_0_0，C=37，固定[33,35,37,39,41,43,47]、原C方向基准、完整user消息、schema、模型、temperature与派生seed。唯一变化为system prompt；每轮保存差异、请求、原答和核验。原C右边缘存在狭窄开口/地面迹象，此为已知开发目标，不作为独立测试成绩；不向模型直接写入“本图右侧必有路”或固定分支数量。

第1轮：只补充2句通用边缘线索与候选保留规则。正式提示词见prompts/01_relaxed_en.txt，中文变更见01_change_zh.txt。阶段二不运行，GPU0服务保留。

命令：
```sh
.runtime/crossing_vllm27/bin/python -B scripts/tune_route_inventory_prompt.py --output outputs/agent_route_choice/human_v002/run_20261106_05/round_01 --prompt experiments/agent_route_choice/human_v002/run_20261106_05/prompts/01_relaxed_en.txt --registration experiments/agent_route_choice/human_v002/run_20261106_05/round_01/registration.json
```


用户纠正：前三轮新增的边缘/门框等检查过于针对案例，不采纳。前三轮提示词和结果保留为已否决开发记录。第4轮从00_previous原稿重启，只替换一条通用阈值句；不沿用前三轮附加句。

## 用户纠正后的实际结果

第04—11轮均只使用通用证据阈值调整；相邻轮逐步修改，未加入目标方向、场景物体提示或固定分支数量。8轮每轮返回2条：前方客厅、后方来路，右侧候选均未出现。第10轮只在uncertainties提到潜在侧向分支，不计识别成功。现有结果不支持宣称通用放宽解决了问题。

最终尝试稿：prompts/11_general_relax_en.txt；旧稿00_previous_en.txt和所有中间稿均保留，不把最新稿提升为成功版。输入七帧、C=37、模型与seed固定，请求审计全部通过。0阶段二调用。按用户既有要求保留GPU0待用服务。

每轮原答位于outputs/agent_route_choice/human_v002/run_20261106_05/round_XX；第04—11轮同步主视图/地图HTML位于各轮exports/run_20261106_01/crossing_centered_stage1_review.html。最新HTML显示实际失败结果，与原七帧基准对照，不伪造选择。

下一步仍需解决视觉候选漏检；本轮未改变输入、模型或选路阶段，也未证明原因仅是阈值。
