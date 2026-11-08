# 原十条 Crossing 360°补采续跑：复用56张，补齐16张

<!-- AGENT_ROUTE_360_CAPTURE_START -->
2026-11-06T06:51:31.927211+00:00：v002补采或自动导出未完成：RuntimeError: Capture failed: KeyboardInterrupt: Capture termination requested。保留原始状态及日志；没有模型调用，不能报告选路结论。运行目录 `outputs/agent_route_choice/v002/capture_20261106_03`。
<!-- AGENT_ROUTE_360_CAPTURE_END -->

更新时间：2026-11-06。状态：已保留64张，等待空卡的主管已正常停止，改由04轮按用户新指令继续。

## 目的与范围

继续已授权的画面补采，不调用模型、不运行导航。原十条任务、八场景、九个Crossing，完整数据集72张唯一图。上轮已完成六场景、七个Crossing、56张；本轮仅补 `kujiale_0207/C06` 和 `kujiale_0036/C03`，共16张。后者由sample_09、sample_10共用。

## 停止原因与修复

上轮 [capture_20261106_02](../capture_20261106_02/README.md)于06:19:55 UTC在场景间空闲检查退出。快照显示GPU0显存0MiB、无GPU进程，但利用率仍为30%；六个场景均以exit_code=0结束。不是图片渲染失败。原进程全部退出、资源已释放。

只修改调度逻辑：遇到瞬时负载或资源被占用时等待，连续两次空闲检查（间隔5秒）后才能启动；每次资源等待上限1800秒，不停止任何他人进程。CUDA仍只暴露目标GPU UUID，Vulkan使用物理GPU0、PhysX使用逻辑0。

旧56张以原字节复制到新目录，不重新渲染、不覆盖历史。准备时核对相机、样本、场景哈希、灯光、seed、位置和角度一致；逐张验证SHA256、元数据并再次验证复制后的哈希。`reuse.json` 保存来源、原始采集时间和哈希。统计区分复用56张与本轮新增16张。

## 协议与版本

采集代码与相机协议保持不变：标定点XY，旧判断帧根部Z均值+0.72m；640×480、水平FOV90°、俯视15°；0°=世界+X，逆时针每45°一张。原导航seed2，渲染seed20261106。固定光心、只旋转相机，无机器人运动。零物理时间步的Isaac ReferenceTime可保持0，不作为递增帧号校验；用实际位姿和像素差异验证。

旧轨迹没有相机朝向/物理状态，本数据仍为新增静态观察，不代表像素级复位。旧位置与标定点差距、标注来源和未复核状态继续保留，不使用Oracle正确路线取景。Git、未提交差异及实际源码冻结于输出 `source/`、`provenance.json`。

## 启动方式

```bash
python3 scripts/prepare_crossing_panorama.py --output outputs/agent_route_choice/v002/capture_20261106_03 --reuse-completed-from outputs/agent_route_choice/v002/capture_20261106_02
python3 scripts/run_crossing_panorama.py --output outputs/agent_route_choice/v002/capture_20261106_03 --gpu 0
python3 scripts/finish_crossing_panorama.py --output outputs/agent_route_choice/v002/capture_20261106_03
```

GPU启动前重新检查，采集主管与CPU收尾各自后台运行；本轮仿真进程结束/异常自动清理。每场景1800秒时限，自动收尾完成图片校验、中文离线HTML和原图包导出、浏览器验证及文档更新。

## 产物与下一步

06:38 UTC新完成0207/C06八张，累计64张；随后GPU0出现其他用户约5GiB的占用，因本轮要求空卡而等待。用户06:49 UTC明确“继续，用GPU0”，核验本项目无仿真子进程后停止等待主管，以 [capture_20261106_04](../capture_20261106_04/README.md)在GPU0剩余资源上仅采最后8张。没有停止他人进程，本轮状态与原图保留。

输出：[capture_20261106_03](../../../../outputs/agent_route_choice/v002/capture_20261106_03/)。`status.json` 区分复用/新增数量；`postprocessing.json` 是自动导出状态；完成后见 `summary.json`、`exports/run_20261106_01/crossing_360_zh.html` 和 `crossing_360_images.zip`。

先补齐并核验画面，Qwen支路识别和选路仍未开始。
