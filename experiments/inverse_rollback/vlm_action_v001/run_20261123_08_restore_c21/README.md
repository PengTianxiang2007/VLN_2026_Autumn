# C21 · 七图回退与独立到达判断

2026-11-23 UTC，seed 2，仅 C21（`kujiale_0165_57_0`）。[协议与提示词中文全文](../run_20261123_07_restore_c21/README.md)。上次尝试的首组四个左转已执行，首次判断收到 DeepSeek HTTP 400，未评分。本次从相同历史 B 位姿重新开始，沿用[动作提示词](action_en.txt)，在[判断提示词](judge_en.txt)的输出要求中显式写出 JSON。该句中文为“仅返回 JSON 对象 `{"arrived": true}` 或 `{"arrived": false}`”。

七张去程 RGB 与六段共 31 个原生动作直接传给每次模型调用，另附一张当前前视。完成 12 次初始左转后，先请求 4 个动作；执行完才用 R4 作第一次判断，以后重复。达标要求模型主动退出且距 A 不超过 0.35 米。两版完整导航的 SR 与平均 SPL 均为“暂无，已评分 0 条”。

从仓库根目录执行 `bash experiments/inverse_rollback/vlm_action_v001/run_20261123_08_restore_c21/run.sh`。[运行清单与源码哈希](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_08_restore_c21/manifest.json) · [实时状态](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_08_restore_c21/status.json)。上一轮 C34 保持挂起。

C21 已完成。动作调用 122 次，到达判断 121 次，实际执行 488 个回程动作。仿真终止（exceed_total_max_step），终点距 A 3.999 米，局部达标 0/1。 [正式结果](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_08_restore_c21/cases/C21/result.json)
