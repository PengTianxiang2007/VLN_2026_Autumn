# 两例阶段一窗口后移可视化

状态：完成。复用主视图/俯视地图同步回放模板，保留原C与新P、4张实际输入、旧新阶段一原答、分支证据跳转和复核导出。无阶段二选择。两例12个关键位置、分支数、双滑条、移动端和导出检查通过；无网络外部请求或页面错误。

产物：outputs/agent_route_choice/human_v002/run_20261106_01/exports/run_20261106_01/window_shift_stage1_review.html。源码和哈希见同目录source/与export_audit.json；浏览器证据见browser_check.json。该导出新增模型调用0次。

命令：
```sh
backbone/streamvln/.venv/bin/python scripts/export_route_window_probe.py --run outputs/agent_route_choice/human_v002/run_20261106_01
/root/.nvm/versions/node/v20.20.2/bin/node scripts/check_route_window_probe.cjs outputs/agent_route_choice/human_v002/run_20261106_01/exports/run_20261106_01/window_shift_stage1_review.html
```
