# 手工标注 Qwen27B 离线复核 HTML

用户在推理结束后要求制作可视化，更新此前推理阶段“不做HTML”的交付要求。只读取已有结果，不调用模型或导航，不生成全景。

来源：human_v001/run_20261106_01/qwen27b；34个事件、33条轨迹，65次响应，4条选择、27条证据不足、3条未调用第二轮，原协议有效7条；语义正确率待复核。模型描述保留英文原文，中文界面与原数据集中文任务。seed沿用2，无新随机实验。

产物：[离线HTML](../../../../../../outputs/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/human_qwen27b_review.html)。全内嵌约116 MiB，34例共3161帧（共享轨迹重复计），双同步进度条、主视图、俯视地图、分支清单/排除/选择、关键证据跳转、原答及校验错误、复核意见导出。全程保留无选择和失败结果。

地图为原导航轨迹，并非执行模型新选择的轨迹。C/P与手工帧重合；模型只有相对方向且缺少可靠朝向/像素定位，未伪造分支空间箭头。参考路线仅供复核。人工错误标签不包含正确分支；短错误片段未必足以呈现错误。GLM因账户额度不足无回答，未生成对照结果。

命令：
```sh
backbone/streamvln/.venv/bin/python scripts/export_human_route_review.py --output outputs/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01
/root/.nvm/versions/node/v20.20.2/bin/node scripts/check_human_route_review.cjs outputs/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/human_qwen27b_review.html
```

源码快照、实际Git HEAD、工作区清单、原响应和HTML哈希见产物目录 export_audit.json 与 source/。输入图片/地图哈希及第二轮完整清单传递均核验。浏览器检查记录见 browser_check.json。历史推理结果和旧HTML均不改写。
