# 十例阶段一：前4帧＋后10帧内3张

2026-11-06，状态：已完成并导出。固定取[C-4,C+3,C+6,C+10]；后段按用户最终指定固定取+3、+6、+10。P=C+10，原C保留，动作历史随P更新。本轮继续阶段一，不执行阶段二。原英文prompt、Qwen27B权重、请求参数与派生种子保持一致。

固定样本：01、02、05、06、07、08、09、10、11、23。保留两例诊断样本11/23，另外按原编号选择最前8个能完整满足窗口的样本；无C-4真实观测的0帧案例不伪造历史。已核验40张均为有效真实观测；这是开发子集，不代表34条全集盲测。

命令：
```sh
.runtime/crossing_vllm27/bin/python -B scripts/probe_route_inventory_window.py --registration experiments/agent_route_choice/human_v002/run_20261106_03/registration.json --output outputs/agent_route_choice/human_v002/run_20261106_03 --execute
backbone/streamvln/.venv/bin/python scripts/export_route_window_probe.py --run outputs/agent_route_choice/human_v002/run_20261106_03
/root/.nvm/versions/node/v20.20.2/bin/node scripts/check_route_window_probe.cjs outputs/agent_route_choice/human_v002/run_20261106_03/exports/run_20261106_01/window_shift_stage1_review.html 10
```

实际Git与源码快照、请求和响应、图片与动作审计均保存在输出目录。C之后的观测只在延迟后的P可用，不冒充原C时刻因果判断。结构通过不等于分支正确。GPU0服务按用户要求保留待用。结果待补充。


本批替代中途停止的02批，全部十例使用最终规则重新请求。


最终结果：10/10响应、10/10格式校验通过、22条分支，模型自报9条complete/1条partial，语义未评分。各1次网络请求，无错误；阶段二0次。HTML完成浏览器检查（70个位置、10例分支、双滑条、离线、复核导出、移动端）。原窗口+1的02批被用户新指令替代，6条保存结果独立保留。

产物：`outputs/agent_route_choice/human_v002/run_20261106_03/exports/run_20261106_01/window_shift_stage1_review.html`。样本11新答为左前门口与右前卧室两条；样本23仍有历史场景混合及来路证据需复核，不把格式通过当作正确。服务保持待用。
