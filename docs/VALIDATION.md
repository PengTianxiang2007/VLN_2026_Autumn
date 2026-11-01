# 迁移验证

日期：2026-11-01。验证对象为本目录中的源码、独立环境和共享 Resource_Peng 资源。
两模型 × 三 benchmark 均已完成单条完整导航，启动器和评估进程退出码均为 0。

## 完整单条导航

每路验证一条完整任务，保留原生推理和 benchmark 的终止规则。SR 与 SPL 取值范围为
0–1，NE 单位为米。运行通过表示程序正常完成且评分完整，不要求这一条任务到达目标。
这些单条分数不代表全集成绩，也不用于模型能力排名。

| Backbone | Benchmark | 完成条数 | 退出码 | SR | SPL | NE |
| --- | --- | --- | --- | --- | --- | --- |
| StreamVLN | R2R-CE | 1 | 0 | 0 | 0 | 3.3686 |
| StreamVLN | RxR-CE | 1 | 0 | 1 | 0.8586 | 0.6016 |
| JanusVLN | R2R-CE | 1 | 0 | 1 | 0.9484 | 0.4222 |
| JanusVLN | RxR-CE | 1 | 0 | 1 | 1.0000 | 1.0268 |
| StreamVLN | VLNVerse physical | 1 | 0 | 0 | 0 | 7.9308 |
| JanusVLN | VLNVerse physical | 1 | 0 | 1 | 0.7627 | 0.9415 |

VLNVerse 使用 H1 physical、640×480 RGB、500 warm-up ticks、25,000 physics ticks 上限。
StreamVLN 执行 211 个动作、53 次模型生成，最终由原模型动作队列输出 STOP；没有 smoke
强制停止。JanusVLN 执行 57 个动作、57 次模型生成，最后输出 STOP，同样没有 smoke
强制停止。两路的模型服务、真实相机、物理动作和官方评分均完成，仿真子进程退出码均为 0。

本次经用户授权共享 GPU 0；JanusVLN 的 VLNVerse 仿真另经授权共享 GPU 1。
验证只逐项运行，没有启动全集评测或训练，没有停止其他使用者的进程。
运行结束后，本次启动的模型服务、仿真与 launcher 进程均已退出，GPU 进程检查通过。

## 环境和数据检查

- 六项 CPU 单元检查通过：覆盖六路入口、原生参数、源码优先级和不完整结果拒绝。
- 两个模型的新源码、Habitat、VLNVerse adapter 导入通过；R2R/RxR 数据实际加载成功。
- 三套 venv、基础 Python、软链接、可编辑安装配置的独立性检查通过；运行中动态库
  检查也未发现旧项目依赖。模型环境为独立文件副本。
- 共享权重、数据、场景的路径与软链接检查通过，没有指回旧项目的链接。
- R2R val_unseen 1,839 条、RxR 英语 Guide val_unseen 3,669 条，所需 11 个 MP3D 场景及
  navmesh 齐全；VLNVerse fine val_unseen 的 825 条任务对应 33 个场景，26,354 个场景
  文件存在且大小符合既有清单。以上为数据完整性检查范围。
- VLNVerse 的 126 个依赖通过 `uv pip check`，Torch/OpenCV CPU 运算和关键包导入通过。
  带版本快照约束的离线安装预演显示无需更改已安装环境。

## 记录位置

简明验证凭据保存在 [validation/](validation/)，已安装版本在
[migration/](../migration/) 的三个 `*_requirements.lock.txt` 中。
Habitat 日志位于 `outputs/validation/{streamvln,janusvln}_{r2r,rxr}/`。
VLNVerse 运行信息、官方评分、动作记录、两张初始 RGB 和 LMDB 位于
`outputs/vlnverse/<backbone>/results/<run_id>/`。完整日志、环境和缓存不进入 Git。

首次运行曾花较长时间从 NAS 读取权重并编译 Isaac 渲染缓存；缓存已保存在新项目中。
本次验证覆盖原生推理和 physical 仿真，未执行训练、VLNVerse flash 或全集评测。
