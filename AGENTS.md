# VLN_2026_Autumn 工作约定

先读 README.md、docs/RUNNING.md、docs/ENVIRONMENT.md 和 docs/MIGRATION.md。
这是放弃 TTA 研究路线后建立的独立初始项目。当前范围为 StreamVLN、JanusVLN 在
R2R-CE、RxR-CE 和 VLNVerse fine val_unseen 上的原生推理与评估；后续研究机制尚未指定。

两个模型的 .venv 和所依赖的 Python 运行时均独立迁入本目录，不依赖旧项目是否存在。
不要将 .venv、Python 或可编辑安装重新链接到旧项目。升级环境前保留当前依赖快照。
统一入口显式优先导入本目录源码与 Habitat 源码，不能只看解释器路径来判断源码来源。
权重、数据与场景复用 Resource_Peng。新产物写入 outputs/，环境与缓存不进入 Git。

用户要求完成新项目迁移与运行验证。验证使用当前空闲且显存足够的 GPU，逐项执行完整少量
episode；不要启动完整 benchmark、训练或停止他人进程。历史文档中的 GPU 编号、PID、
运行状态和成绩只作来源记录。声明通过范围时区分 CPU 检查、单条 GPU 导航和全集评测。

推理行为保留原提示词、精度、历史抽样、动作队列与缓存生命周期。修改公共路径/入口后运行
tests/ 中的 CPU 检查及对应环境检查。不要重新引入旧 TTA/PRM、baseline、iterations。
本项目使用独立 Git 仓库；旧仓库与旧运行产物保持不变。远程仓库尚未配置。
