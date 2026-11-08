# 上午第一版：按同步回放模板重新导出

用户要求按照刚交付的手工标注版模板导出上午第一版。来源为 v001/preparation_20261106_04 与 run_20261106_01/qwen32b，原十条、seed2、20次响应。使用两版共同的同步时间线布局，保留原十条的中英译文、C/P真实偏移和第7条排除后再选择B1的矛盾。不运行模型或仿真，不修改原始回答或旧HTML。

导出命令：
```sh
backbone/streamvln/.venv/bin/python scripts/export_agent_route_timeline.py --output outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_04
/root/.nvm/versions/node/v20.20.2/bin/node scripts/check_agent_route_timeline.cjs outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_04/crossing_v001_timeline_zh.html
```

状态：已完成。十条/31支路/737帧逐帧浏览器验证通过，地图像素位置、双进度条、证据跳转、返回Crossing暂停、原第7条矛盾、复核导出与移动端均通过，零外部请求和页面错误。独立HTML约55.4 MiB。源文件哈希、实际Git HEAD与源码快照由导出器保存于 export_audit.json 和 source/。协议有效不代表语义正确；回放是原始轨迹，并非执行新选择的轨迹。GLM无有效回答，不生成虚构对照。
