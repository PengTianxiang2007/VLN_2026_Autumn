# Qwen27B人工错误集在线发布

2026-11-07，状态：发布完成。只发布已有结果，不重新运行模型、仿真或导航。

源HTML：outputs/agent_route_choice/human_v002/run_20261107_01/exports/run_20261106_01/crossing_two_stage_review.html。
原实验为34错误点/33轨迹、102份回答；全部错误点保留。页面展示分支清单、纯视觉实际路线识别、程序锁定排除和任务替代选路，属于离线恢复选路评价，不是新的实际机器人恢复导航。

用户本次提供人工复核汇总18/33（约54.5%）选择正确道路，并总结模型基本可判断错路与纠错方向。汇总注明用户来源，未提供逐点金标对应；不擅自挑选33个错误点、生成逐条正确标签或将其解释为导航成功率。旧协议有效32/34及原始异常保留，不能混为语义正确率。

产物：outputs/visualization_publishing/qwen27b_human33_20261107_01/；在线目录online/。
使用scripts/prepare_online_visualization.py提取媒体，localize.py在展示层增加全局双语选择；translations_zh.json保存467条自然语言译文，英文原答保持。现有任务完整译文复用原始instruction_zh字段；其他译文仅用于展示。机器字段、枚举、ID和引用图像编号保持。

本地验证：全部34错误点、3161回放帧、双滑条同步、中英文切换保持任务/帧位置、中文显示无已知英文正文漏译、移动端与零JS错误通过。原始34条case JSON及summary完全相同。导出Git、哈希、源文件及限制见source.json、export_audit.json；localize.py保存实际展示改动，translations_zh.json在本目录留存。

不进行全量公网重复下载。上传后核验所有远端哈希与入口HEAD，补齐发布记录。后续为用户网页审阅，人工逐点正确性标签另行登记。

发布网址：[人工错误集Qwen27B选路回放](http://134.175.18.101/vln/qwen27b_human33_20261107_01/crossing_two_stage_review.html)。全部3072个发布文件远端哈希通过，公网入口HEAD返回200、类型及大小正确。发布记录：`outputs/visualization_publishing/publish_20261107_084857_713529/publication.json`。
