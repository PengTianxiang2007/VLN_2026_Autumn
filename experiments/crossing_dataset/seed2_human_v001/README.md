# seed2 人工 Crossing 数据集 v001

更新时间：2026-11-06。状态：已完成。用户已上传标注并明确要求“一个都没标的舍掉”。

交付：[完整数据集ZIP（190.42 MiB）](../../../outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001.zip)；[只读离线HTML（126.85 MiB）](../../../outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001/crossing_seed2_human_v001_offline.html)。ZIP包含HTML、逐帧RGB、标签、轨迹、说明和可移植读取器。

## 范围和标签

输入为 `outputs/crossing_annotation/seed2_69/crossing_annotation_69_zh_annotated.html`，SHA256为 `afb4e7868989415cf38351524d2f1e814f698f1274003f475916c988ecfc8748`。
只按是否存在人工标注筛选：61条保留（34失败、27成功），8条无点剔除（5失败、3成功）。128个点包括94个普通Crossing和34个错误选择Crossing；错误选择仍属于Crossing。
页面的completed复选框全部为false，保留原始记录，以用户本次“好了”的明确提交及非空标注作为收录依据，不额外要求复选框。
每个点保持用户选定的帧号、坐标、类型、UUID，不自动吸附至旧地图路口、不合并重复经过，不依据模型最终失败替换人工标签。

## 产物与协议

新输出：`outputs/crossing_dataset/seed2_human_v001/run_20261106_01/`。
已制作完整可移植数据目录、ZIP和61条只读离线HTML。保留61条完整5439帧，包含61帧终止/复用RGB标记；可推理观测5378帧。34个错误选择点分布在33条任务中；另有一条失败任务只有普通Crossing标注，按用户原标注保留。
RGB逐字节复用用户实际看到的640×480 WebP，不再次编码。原始录像、中文/英文指令、原始步骤和标签通过来源哈希关联。
模型输入清单与评估专用位置/地图/参考路线/最终结果/标签分别保存；因果读取器只返回当前及过去图像，以及当前观测前已经执行的动作。
本版是点事件标注；未标帧不自动置为负类，普通Crossing不自动变成“已确认选择正确”。匹配容差和train/dev/test划分不在本次数据冻结中擅自设定。

## 命令与版本

```bash
python3 scripts/build_crossing_dataset.py --output outputs/crossing_dataset/seed2_human_v001/run_20261106_01
python3 scripts/verify_crossing_dataset.py --dataset outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001
node scripts/check_crossing_dataset.cjs outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001/crossing_seed2_human_v001_offline.html
```

当前Git提交、工作区差异和本轮代码快照保存于运行目录；原复现版本引用原始manifest。
CPU整理，无模型调用、无导航运行、无GPU。

## 检查与下一步

已完成检查：

- [数据与归档校验](../../../outputs/crossing_dataset/seed2_human_v001/run_20261106_01/verification.json)：5586个文件SHA256、5439帧、5378个因果读取观测、128个人工点均通过；原始标签逐字段保持，8条剔除任务没有图像进入包内，ZIP全部成员完整。
- [浏览器检查](../../../outputs/crossing_dataset/seed2_human_v001/run_20261106_01/browser_check.json)：61条、128个人工点逐点跳转，合计311次帧检查，图像/位置/地图像素/双进度条同步。中文指令、任务筛选、播放与只读状态通过，外部请求和浏览器错误均为0。
- [排除与收录清单](selection.json)、[统计](summary.json)、[数据说明](../../../outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001/README.md)已保存。

原上传HTML未修改；12个位于第0帧的人工点原样保留，没有生成虚构历史。数据集ID为 `crossing_seed2_human_v001-afb4e7868989415c`。
下一步可在这份冻结数据上设计测评协议；不把该批次声称为场景独立的保留验证集，本轮没有执行新模型测评或计算方法成绩。
