# 原十条 Crossing 的360°离线画面补采：限制CUDA可见设备

<!-- AGENT_ROUTE_360_CAPTURE_START -->
2026-11-06T06:19:58.578576+00:00：v002补采或自动导出未完成：RuntimeError: Capture failed: RuntimeError: Target GPU is no longer idle; no foreign process will be stopped.。保留原始状态及日志；没有模型调用，不能报告选路结论。运行目录 `outputs/agent_route_choice/v002/capture_20261106_02`。
<!-- AGENT_ROUTE_360_CAPTURE_END -->

更新时间：2026-11-06。状态：场景间GPU检查退出，56张已保存，本轮进程已释放。

## 目的与方法

继续用户授权的“先补足画面”。原固定十条、八场景、九个唯一Crossing；每点8张、45°间隔，计划72张独立RGB。没有模型调用或导航执行。

采集协议与 [capture_20261106_01](../capture_20261106_01/README.md)相同：光心XY为标定点，Z为该点旧判断帧根部Z均值+H1静态相机偏移0.72m；水平FOV90°、俯视15°、640×480、0°=世界+X、正向逆时针。原轨迹seed2，渲染seed20261106。每点固定光心，只旋转相机。灯光使用原任务相同类型与强度，定位到当前点。

旧数据未保存朝向/完整物理状态，新增静态视图不构成旧画面的精确恢复。保留标注来源状态，不使用Oracle正确朝向、参考路线、人工正确支路作为取景依据。旧判断位置与标定点差值逐条记录，最大0.95m。第9、10条共享全景；各自到达前、走错后原录像独立。

## 修复与运行设置

首轮在初始化期间发现非目标GPU的CUDA上下文后停止，未产图。本轮显式 `CUDA_VISIBLE_DEVICES=<目标GPU UUID>`；PhysX使用逻辑设备0，Vulkan使用核验空闲的物理GPU0。原环境不修改，场景资产不改动。逐场景独立进程、每场景1800秒上限，结束/异常均清理核验归属的子进程并记录GPU快照。

Git、未提交差异、实际源码快照、场景资产及相机配置哈希保存在输出 `source/` 与 `provenance.json`。与首轮分开留存。

## 启动命令

```bash
python3 scripts/prepare_crossing_panorama.py --output outputs/agent_route_choice/v002/capture_20261106_02
python3 scripts/run_crossing_panorama.py --output outputs/agent_route_choice/v002/capture_20261106_02 --gpu 0
```

## 结果与产物

05:41 UTC启动，采集主管PID3381368，GPU0；CPU自动收尾主管PID3383720。PID仅作来源记录，查看实时状态须核验。输出：[补采目录](../../../../outputs/agent_route_choice/v002/capture_20261106_02/)。`manifest.json` 固定清单，`status.json` 记录采集进度，`postprocessing.json` 记录自动导出进度，`panoramas/` 存原图与相机位姿，`logs/` 存日志，`cleanup.json` 记录GPU释放。

采集后由 `scripts/finish_crossing_panorama.py` 自动验证并导出 `exports/run_20261106_01/crossing_360_zh.html` 和 `crossing_360_images.zip`，进行十条/80全景画面/10原帧/80放大图的浏览器检查，更新实验记录。该收尾代码另存于 `postprocessing_source/`，保留实际哈希。自动校验通过不等于已经人工复核支路语义。

首个点的8张真实画面已产出并人工查看：材质/门口/客餐厅关系可辨，没有黑图；尺寸、位置、角度和不同视图的像素哈希通过。检查中确认 Isaac `ReferenceTime` 在零物理时间步的静态渲染中始终为0，不能作为递增渲染计数。因此只修正自动导出校验，保留原字段并说明含义，以实际像素差异和相机位姿核验。采集代码、相机配置及产图未改动；首版等待中的CPU收尾进程停止，新收尾代码另存 `postprocessing_source_02/`，首次状态保留 `postprocessing_attempt01.json`。

## 下一步

06:28 UTC接手核验：六个场景均成功退出，七个Crossing共56张；06:19:55的GPU0快照是显存0MiB、无计算进程、利用率30%。旧入口将单次利用率读数直接判为失败。已改为等待两次连续空闲，以 [capture_20261106_03](../capture_20261106_03/README.md)复用这56张，仅补剩余16张；本轮图像、状态、日志保持原样。

补采完成后核验72张图片、方位和固定位置，导出中文离线预览。正式Qwen支路盘点/排除来路与错误路线属于下一阶段，尚未执行。
