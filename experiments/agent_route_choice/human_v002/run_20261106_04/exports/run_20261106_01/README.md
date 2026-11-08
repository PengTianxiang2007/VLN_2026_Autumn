# 原C锚定七帧可视化

状态：完成。十例，固定原标注C为当前判断帧；7张图偏移-4/-2/0/+2/+4/+6/+10，明确前后关系，主视图和地图默认停C。样本11字段错误仍保留为无效，仅展示内部清单，原JSON可展开。无阶段二。

产物：outputs/agent_route_choice/human_v002/run_20261106_04/exports/run_20261106_01/crossing_centered_stage1_review.html。导出源码与哈希、浏览器检查、截图保存同目录；仅展示，不增加模型调用。

命令：
```sh
backbone/streamvln/.venv/bin/python scripts/export_route_anchor_probe.py --run outputs/agent_route_choice/human_v002/run_20261106_04
/root/.nvm/versions/node/v20.20.2/bin/node scripts/check_route_anchor_probe.cjs outputs/agent_route_choice/human_v002/run_20261106_04/exports/run_20261106_01/crossing_centered_stage1_review.html 10
```
