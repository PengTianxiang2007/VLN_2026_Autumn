# v004：当前画面与已选入口 → 无歧义局部导航指令

2026-11-07；状态：仅提示词修改，待审阅；未调用模型或仿真。

目的：把已有分支选择转换为当前视角下具体可执行的局部R2R指令。输入仅当前画面、selected_direction和selected_entrance_description；入口描述只包含该入口的局部视觉识别信息，不包含原任务要求或入口之后的路线。不直接复制旧route_description：其中已混入原任务的目的地与后续路线。

相对v003：移除StreamVLN、回退点、记忆等实验背景；移除固定动作示例；移除route_description和checkpoint_context字段。保留依据画面决定必要前进/转弯/短距离进入的空间，使门口/房间名称可用于识别眼前入口，但不延伸后续导航。

产物：prompt_en.txt及prompt_zh.txt。已核验两版占位符一致、移除字段与示例不再出现。无新seed、模型结果或导航成绩。历史v001/v002/v003保留。

后续运行前需准备并记录selected_entrance_description的来源，确保它只有局部视觉描述。现有run_local_correction_commands.py仅适配v003，本次未修改或启动该运行器。用户本次只要求审阅prompt。
