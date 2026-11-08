# 十例阶段一：前4帧＋后10帧内3张

2026-11-06，状态：已登记待运行。固定取[C-4,C+1,C+6,C+10]；后段按1到10的区间均匀抽3张，四舍五入中点为6。P=C+10，原C保留，动作历史随P更新。本轮继续阶段一，不执行阶段二。原英文prompt、Qwen27B权重、请求参数与派生种子保持一致。

固定样本：01、02、05、06、07、08、09、10、11、23。保留两例诊断样本11/23，另外按原编号选择最前8个能完整满足窗口的样本；无C-4真实观测的0帧案例不伪造历史。已核验40张均为有效真实观测；这是开发子集，不代表34条全集盲测。

命令：
```sh
.runtime/crossing_vllm27/bin/python -B scripts/probe_route_inventory_window.py --registration experiments/agent_route_choice/human_v002/run_20261106_02/registration.json --output outputs/agent_route_choice/human_v002/run_20261106_02 --execute
backbone/streamvln/.venv/bin/python scripts/export_route_window_probe.py --run outputs/agent_route_choice/human_v002/run_20261106_02
/root/.nvm/versions/node/v20.20.2/bin/node scripts/check_route_window_probe.cjs outputs/agent_route_choice/human_v002/run_20261106_02/exports/run_20261106_01/window_shift_stage1_review.html 10
```

实际Git与源码快照、请求和响应、图片与动作审计均保存在输出目录。C之后的观测只在延迟后的P可用，不冒充原C时刻因果判断。结构通过不等于分支正确。GPU0服务按用户要求保留待用。结果待补充。


用户在运行中将后段改为+3/+6/+10。本批已停止，已保存6条响应，保留但不作为最终交付；替代批次run_20261106_03。未停止Qwen常驻服务。
