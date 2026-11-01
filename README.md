# VLN_2026_Autumn

StreamVLN 与 JanusVLN 的导航研究初始项目，保留 R2R-CE、RxR-CE 和 VLNVerse 的既有适配。
项目于 2026-11-01 从 VLN_TTA2026_Autumn 分离，后续研究方向重新开始；两个 backbone
的既有环境及 Python 运行时独立迁入本目录，模型权重、数据和场景继续复用 Resource_Peng。
旧项目后续删除不会影响新项目；本机环境随目录保留，Git 保存源码、验证记录和恢复说明。
初始状态标签为 `initial-20261101`，六路完整单条导航已通过，详见验证报告。

| 目录 | 内容 |
| --- | --- |
| backbone/streamvln | StreamVLN 模型、R2R/RxR evaluator、VLNVerse RGB 适配 |
| backbone/janusvln | JanusVLN Extra 模型、R2R/RxR evaluator、VLNVerse RGB 适配 |
| benchmarks/habitat_ce | 已适配的 Habitat 0.2.4 源码 |
| benchmarks/vlnverse | VLNVerse 上游源码、H1 physical/flash runner 与模型服务 |
| core、scripts | 统一路径、环境检查、推理启动与恢复工具 |
| docs、migration | 当前使用说明、验证记录、原始源码哈希 |
| outputs | 新运行日志和结果，Git 忽略 |

从当前目录运行：

```bash
python3 scripts/evaluate.py --backbone streamvln --benchmark r2r --gpu 0 --episodes 1 --dry-run
python3 scripts/evaluate.py --backbone janusvln --benchmark rxr --gpu 0 --episodes 1 --dry-run
python3 scripts/evaluate.py --backbone streamvln --benchmark vlnverse --gpu 0 --episodes 1 --dry-run
```

去掉 --dry-run 才会启动模型。GPU 编号只是示例，启动前检查实际占用。
--episodes 1 运行一条完整任务；默认 --episodes 0 才是完整 split。

详细命令见 [运行指南](docs/RUNNING.md)，环境复用关系见 [环境说明](docs/ENVIRONMENT.md)，
迁移来源见 [迁移记录](docs/MIGRATION.md)。本次验证状态见 [验证报告](docs/VALIDATION.md)。
上游自带 README 与复现记录保留历史内容；本目录 docs/ 中的说明是新项目运行依据。
