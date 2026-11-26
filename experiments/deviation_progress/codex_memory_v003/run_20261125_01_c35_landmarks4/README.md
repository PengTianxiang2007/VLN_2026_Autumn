# C35 英文标志物提示词复跑

原始轨迹 seed 2、JEV v002 active。GPT-6 Astra 常规档、medium，经 17982。从 C35 原会话完成 S04 筛选而尚未判断 F0→F28 的截点新建一个分支。改用 v003 英文偏航提示词。第一段与上一版四图分支同帧（F5、F11、F17、F22）。若第一段报警即停；只有第一段 consistent，才沿同一分支提交原生终止观测 F44，并使用本支更新的进度，对 F28→F44 也均匀增加四张未输入的中间图。用原等分、就近未输入帧、等距取较晚帧的规则。

命令为 `.runtime/crossing_vllm27/bin/python -B experiments/deviation_progress/codex_memory_v003/run_20261125_01_c35_landmarks4/replay.py`。

## 结果

第一段 consistent，判定 80.186 秒；第二段实际补 F31、F34、F38、F41，判定 consistent，耗时 81.573 秒。另有终止观测确认 61.714 秒。上一版相同首段四图为 deviated。每版仅一次同输入判断。

第一段原答：序列支持机器人接近浴室入口，但不足以证明它在可识别的指定路口选错分支或越过了所需左转。衣柜和卧室的视角变化不能单独证明错误转向。帧22的圆形墙饰位于画面左侧，但其颜色及与指令地标的对应关系不明确，因此沿走廊直行和在指定地标左转的完整过程仍需保留为未确认。

第二段原答：实际选择浴室入口并进入，符合指令的目的区域；进入后的设施方位也与要求相符。终点更靠近窗户，但画面没有清晰的淋浴房边界，无法证明机器人越过了指定停车位置。此前未确认的走廊行进和地标处左转仍未得到补充验证，也没有新的冲突证据。

[逐轮时间与结果](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v003/run_20261125_01_c35_landmarks4/result.json) · [运行快照、采样及哈希](../../../../outputs/codex_tasks/deviation_progress/codex_memory_v003/run_20261125_01_c35_landmarks4/protocol.json)。当前版与配对原版导航 SR、平均 SPL 均暂无，已评分 0 条。
