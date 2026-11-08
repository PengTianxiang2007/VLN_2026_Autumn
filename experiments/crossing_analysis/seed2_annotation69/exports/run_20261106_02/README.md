# 69条人工标注工具：中文导航指令

更新时间：2026-11-06。状态：已完成。用户要求将HTML内原导航指令翻译成中文。

交付：[中文导航指令版HTML，约147.76 MiB](../../../../../outputs/crossing_annotation/seed2_69/run_20261106_02/crossing_annotation_69_zh.html)。

固定使用原69条，中文逐条对应英文，保留原路线顺序、方向、参照物与停止位置，不根据地图修正原指令。英文保留在数据的instruction字段，新增instruction_zh用于显示。
复用原6409帧和地图，不重新编码、不运行模型或导航。dataset_id和标注结构保持兼容。

译文：`experiments/crossing_analysis/seed2_annotation69/instructions_zh.json`。
来源：`outputs/crossing_annotation/seed2_69/run_20261106_01/crossing_annotation_69.html`。
新输出：`outputs/crossing_annotation/seed2_69/run_20261106_02/crossing_annotation_69_zh.html`；原文件保留。

命令（仓库根目录）：

```bash
python3 scripts/export_crossing_annotation_zh.py --output outputs/crossing_annotation/seed2_69/run_20261106_02
node scripts/check_crossing_annotation.cjs outputs/crossing_annotation/seed2_69/run_20261106_02/crossing_annotation_69_zh.html
```

验证完成：覆盖69条译文，原英文按SHA256逐条校验；6409帧、地图、标签状态与dataset_id保持一致。逐条检查了指令的行动顺序、左右方向、参照物和停止条件；原文的重复转向或不自然表述按原意保留。辅助方向词计数有一条英文重复两次“左侧”，中文合写为“左侧的浴室门口和嵌入式柜子”，已核对两者都在左侧。

实际浏览器验证69条中文显示、207帧双图同步，以及标注、删除、撤销、下载两代HTML后在无本地缓存的上下文重开；中文与标注保留，零外部请求、零浏览器错误。嵌入字体覆盖译文的287个不同汉字。结果见[浏览器检查](../../../../../outputs/crossing_annotation/seed2_69/run_20261106_02/browser_check.json)和[来源与媒体一致性记录](../../../../../outputs/crossing_annotation/seed2_69/run_20261106_02/manifest.json)。

初始HTML中的人工标注仍为空；预览图的点仅为自动功能测试。未重新运行导航或模型，等待用户标注后的HTML。
