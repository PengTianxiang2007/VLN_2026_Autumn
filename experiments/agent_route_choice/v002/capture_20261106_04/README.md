# GPU0续采最后一个Crossing：复用64张，补齐8张

<!-- AGENT_ROUTE_360_CAPTURE_START -->
2026-11-06T06:58:35.413777+00:00：外部 Agent v002 的原十条360°画面补采完成：八场景、九个Crossing、72张唯一RGB（十条引用80张）。本轮复用64张，新增8张。图像哈希、640×480、固定光心、八方向覆盖、不同方位像素差异及离线浏览器检查通过；模型调用0次、导航动作0次，本次仿真进程已退出。原图与相机元数据位于 `outputs/agent_route_choice/v002/capture_20261106_04/panoramas/`；中文预览位于同目录 `exports/run_20261106_01/crossing_360_zh.html`，原图压缩包为 `crossing_360_images.zip`。尚未进行Qwen支路识别/选路，视觉语义复核另记。
<!-- AGENT_ROUTE_360_CAPTURE_END -->

更新时间：2026-11-06。状态：完成。06:58 UTC全量图片校验、导出及浏览器检查完成；本项目仿真与收尾进程均退出。

## 用户授权与范围

用户在得知GPU0被其他进程占用后明确指示“继续，用GPU0”。本轮按此指令使用GPU0剩余资源；不停止现有进程。仅采 `kujiale_0036/C03` 的八个方向，为sample_09、sample_10共用。原十条仍是八场景、九个Crossing、72张唯一图片。

上轮 [capture_20261106_03](../capture_20261106_03/README.md)已完成8个Crossing、64张；因默认要求空卡而等待。该轮等待主管在核验PID/启动时间/工作目录后正常停止，没有在途仿真子进程，已完成图片和日志保留。

## GPU条件与实现

06:49 UTC核验GPU0占用约4989MiB，剩余43531MiB、利用率0；已有进程属于其他用户目录，不属于本项目。本轮显式 `--allow-shared-gpu`，连续两次（相隔5秒）利用率≤10%、可用显存≥24576MiB且主存可用≥64GiB才启动。只占用本项目仿真所需资源；完成/异常时仅清理本次进程。默认运行仍要求空卡，新的共享模式只在显式指定时生效。

GPU UUID限定CUDA可见设备，Vulkan物理卡0，PhysX逻辑0。每场景1800秒限时。未修改系统环境或他人进程。

## 数据、版本与限制

逐字节验证复用上轮64张，仅新增8张。`reuse.json`保存原始时间、来源与哈希；采样、场景、灯光、相机、seed与前三轮保持一致。原导航seed2，渲染seed20261106；标定XY、根部Z均值+0.72m、640×480、水平FOV90°、俯视15°、世界+X起始逆时针每45°一张。

仍为静态补充观察，未恢复旧相机朝向或完整物理状态；没有模型调用、导航执行或Oracle正确路线取景。Git、未提交差异、实际源码及资产来源冻结于输出 `source/`、`provenance.json`；原有运行不覆盖。

## 启动命令

```bash
python3 scripts/prepare_crossing_panorama.py --output outputs/agent_route_choice/v002/capture_20261106_04 --reuse-completed-from outputs/agent_route_choice/v002/capture_20261106_03
python3 scripts/run_crossing_panorama.py --output outputs/agent_route_choice/v002/capture_20261106_04 --gpu 0 --allow-shared-gpu --min-free-mib 24576
python3 scripts/finish_crossing_panorama.py --output outputs/agent_route_choice/v002/capture_20261106_04
```

## 结果、产物及下一步

已完成原十条、九个Crossing、72张唯一图：本轮新增8张，逐字节复用64张；十条任务共引用80张，第9、10条共用全景。图像尺寸、哈希、固定位置、角度与不同视图像素差异通过；九处72张均已人工查看，未发现黑图或重复取景。浏览器验证十条任务、80次全景显示、10张原判断帧及80次放大，零页面错误、零外部请求。ZIP完整性通过，包含72张PNG和9份相机元数据。

输出：[capture_20261106_04](../../../../outputs/agent_route_choice/v002/capture_20261106_04/)。

- [中文单文件预览，27.99MiB](../../../../outputs/agent_route_choice/v002/capture_20261106_04/exports/run_20261106_01/crossing_360_zh.html)
- [原图与元数据ZIP，18.47MiB](../../../../outputs/agent_route_choice/v002/capture_20261106_04/exports/run_20261106_01/crossing_360_images.zip)
- [自动汇总](../../../../outputs/agent_route_choice/v002/capture_20261106_04/summary.json)、[九处人工图像质量复核](../../../../outputs/agent_route_choice/v002/capture_20261106_04/capture_review/final_review.json)、[进程清理](../../../../outputs/agent_route_choice/v002/capture_20261106_04/cleanup.json)

本项目采集和自动收尾进程均已退出，GPU0恢复到原有其他用户约4989MiB占用，该进程保留。0036场景初始化日志含原资产嵌套刚体层级错误，静态图像采集正常结束，exit_code=0；没有执行采集期间物理步进，本结果不代表物理导航验证。源视图中面对墙面和高亮窗帘的画面原样保留。

交付完整画面后，再准备Qwen的支路盘点和排除来路/错误路线；本轮不调用Qwen。
