# Qwen27B v002 中文全景、支路和俯视地图导出

2026-11-06完成。实际10条、20次响应、38条支路；第二次10条均证据不足，没有选择任何最终支路。本次仅离线导出及兼容复核，无新模型或导航调用。

- [单文件HTML](../../../../../../outputs/agent_route_choice/v002/run_20261106_01/exports/run_20261106_01/crossing_v002_qwen27b_zh.html)，约51.47 MiB。
- [逐条摘要CSV](../../../../../../outputs/agent_route_choice/v002/run_20261106_01/exports/run_20261106_01/results_summary_zh.csv)。
- [浏览器验证](../../../../../../outputs/agent_route_choice/v002/run_20261106_01/exports/run_20261106_01/browser_check.json)。
- [中文译文](translations_zh.json)，绑定20份原始响应哈希，沿用已有任务中文译文。
- [主实验与校验修复说明](../../README.md)。

页面先展示实际判断位置的八方向观测、俯视地图和最终“未选择”结论，再列出模型全部支路卡片。点击支路可联动其全景引用图及粗方向示意；没有推测或添加门口像素框。地图C为补采位置，P为原存档位置，保留两者偏差；地图和参考路线未进入模型请求。

延续双进度条、C/P对照、因果历史和复核导出；为本次双调用全景实验采用单独页面布局，模型文本使用中文译文，英文原答可切换和展开。八张来路/错误尝试输入帧的地图与画面同步回放，明确不冒充完整导航录像。

旧校验要求路线描述非空，将未选择时的空字符串判错。修复仅允许未选择时的空路线描述，没有更改实际响应或重跑；复核9/10条协议有效。第7条第二次来路证据只有历史帧、没有全景引用，保留并明确标注。界面统计按实际模型状态显示10次证据不足，不沿用旧校验后的0次计数。

HTML内嵌152张唯一输入图、8场景地图、中文字体、20份回答及译文，可断网打开。浏览器验证覆盖十条、80个全景入口、38张支路卡片、历史帧双滑条同步、地图、中英文切换、图片放大、复核意见导出、手机布局；无外部网络请求和JS错误。实际桌面截图已检查。

```bash
backbone/streamvln/.venv/bin/python scripts/export_agent_panorama_choice.py \
  --run outputs/agent_route_choice/v002/run_20261106_01/qwen27b \
  --translations experiments/agent_route_choice/v002/run_20261106_01/exports/run_20261106_01/translations_zh.json \
  --review-audit outputs/agent_route_choice/v002/run_20261106_01/review_20261106_01/review_audit.json \
  --output outputs/agent_route_choice/v002/run_20261106_01/exports/run_20261106_01
node scripts/check_agent_panorama_html.cjs outputs/agent_route_choice/v002/run_20261106_01/exports/run_20261106_01/crossing_v002_qwen27b_zh.html
```

以上为实际导出命令记录，重导出必须使用新目录。原运行状态、冻结源码与既有HTML不覆盖。
