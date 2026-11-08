# seed2 69 条人工 Crossing 标注工具

更新时间：2026-11-06。状态：工具制作与验证完成；用户标注已接收并冻结为[61条人工离线数据集](../../crossing_dataset/seed2_human_v001/README.md)。8条零标注按用户要求剔除，128个人工点保留。仅处理已有录像，不运行模型或导航，不使用 GPU。

最新交付：[中文导航指令版 HTML（约147.76 MiB）](../../../outputs/crossing_annotation/seed2_69/run_20261106_02/crossing_annotation_69_zh.html)，69条导航指令均显示中文，英文原文保留在数据中；[中文导出记录](exports/run_20261106_02/README.md)。[原英文版](../../../outputs/crossing_annotation/seed2_69/run_20261106_01/crossing_annotation_69.html)保留。

下载后用桌面 Chrome / Edge 打开；标注完成后点击右上角“保存标注后的 HTML”，上传下载的新文件。无需附带媒体目录。不要依赖浏览器普通“保存网页”操作。

## 目的与样本

制作可离线打开、标注、删除、撤销删除、保存为新 HTML 并重新上传的单文件工具。
固定 seed2：39 条来自既有48条 Crossing 错选候选且至少三个 seed 最终失败；30 条成功样本从10个场景各选3条。
成功候选按 `SHA256("crossing69-success-v1:" + episode_id)` 排序取前三，保证可重复；固定清单写入 samples.json。
其他 seed 的失败不等于确认相同 Crossing 错误。旧辅助标签不预填为人工标注。

## 实现与协议

新入口 `scripts/build_crossing_annotation.py`；页面和控制器在 `core/crossing_annotation_page.html`、`core/crossing_annotation.js`。
逐帧裁取原960×640录像左上640×480 RGB，内嵌WebP，不漏帧；位置与原 steps.jsonl 对齐。
地图显示正确参考路线、完整实际路线、当前帧位置和人工标注点。原记录未包含朝向，保存 null，禁止伪造。
普通Crossing与错误选择Crossing为同一帧的互斥类型；后者同时属于Crossing。重复点击更新类型。
沿用RGB的帧可查看但不能标注。完成状态独立于标注数量，允许确认本条无Crossing。
保存HTML时内嵌有效标注及当前位置；浏览器自动暂存只是辅助。删除点不进入有效标注，撤销栈仅在当前页面会话保留。

## 命令与版本

从仓库根目录执行：

```bash
benchmarks/vlnverse/.venv/bin/python scripts/build_crossing_annotation.py --output outputs/crossing_annotation/seed2_69/run_20261106_01
node scripts/check_crossing_annotation.cjs outputs/crossing_annotation/seed2_69/run_20261106_01/crossing_annotation_69.html
```

当前导出Git提交、工作区差异、源码快照和输入哈希记录在输出manifest及source目录；历史复现版本引用原复现manifest。
复用StreamVLN环境的fontTools做中文字体子集，不安装依赖。

## 产物与检查

输出：`outputs/crossing_annotation/seed2_69/run_20261106_01/`，保留历史数据。

- [固定69条清单](samples.json)：39条失败；成功30条，10个场景各3条。
- [输入与源码 manifest](../../../outputs/crossing_annotation/seed2_69/run_20261106_01/manifest.json)：6409帧全部保留，其中68帧为原档案沿用RGB，禁用标注；6341帧可标注。位置逐项等于原始steps，且等于原pred_path去除启动记录后的坐标。
- [数据检查](../../../outputs/crossing_annotation/seed2_69/run_20261106_01/data_check.json)：全部6409张内嵌WebP的哈希及输入文件哈希通过，初始标注为空。
- [浏览器检查](../../../outputs/crossing_annotation/seed2_69/run_20261106_01/browser_check.json)：69条各首/中/末帧，共207帧实际显示与地图像素位置同步；重复点击不新增点，修改类型、地图选点、列表删除、选中删除、撤销及跨任务撤销通过。
- 两代下载HTML分别在全新浏览器上下文重开，标注和完成状态恢复，删除点未复活；所有69组媒体在再导出后保持字节一致。本地暂存重载及无点任务完成状态也通过。浏览器错误0，外部网络请求0。
- [桌面预览](../../../outputs/crossing_annotation/seed2_69/run_20261106_01/preview_annotation.png)和[手机预览](../../../outputs/crossing_annotation/seed2_69/run_20261106_01/preview_mobile.png)仅包含浏览器功能测试点，不是用户标注；正式HTML仍为全空白标签。

限制：RGB为原始压缩录像解码后裁取，并以WebP质量90保存用于人工查看；原始录像未改。时间为每动作一帧、6fps的回放时间，不能作为物理仿真时长。原档案未记录逐帧朝向，heading=null。成功和失败是原生评分；原工具交付时没有人工标签，后续用户标签已单独冻结在61条数据集；仍未计算新方法成绩。

## 下一步

用户已上传保存后的HTML。已提取 `script#annotations` 并按 `dataset_id`、episode、frame、position和image_sha256校验，构建61条数据集。后续测评读取冻结数据集，不改写原上传文件。
