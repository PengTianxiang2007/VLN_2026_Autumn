# VLN_2026_Autumn

**JEV 采样版本**　v001 原版（当前默认） · v003 覆盖优先（候选） · v002 精简（候选）。[版本记录与验证指标](docs/STATUS.md#jev-sampling-selection)

> **严禁过度、无意义的检测验证（2026-11-20）**
>
> 小改动只做与改动直接相关的必要验证，通过后立即交付或启动已授权任务。禁止追加无关回归、全量历史回放或重复检查。后台任务按用户指定范围确认启动后结束跟踪。具体执行约定见 [AGENTS.md](AGENTS.md)。

## 新会话须知

本项目保留 StreamVLN/JanusVLN 等 backbone 的导航适配与复现，开展 Crossing 存档点
离线迭代、错误分析及 Oracle 恢复实验；原 TTA 路线已放弃。
新 Codex 会话必须先读 [AGENTS.md](AGENTS.md)，再读 [当前状态](docs/STATUS.md)
和 [实验目录](experiments/README.md)。

- 公共服务器：不得随意删除数据、停止他人进程、修改共享环境或干扰他人 GPU 任务。
- Python 环境使用 uv 管理，优先复用已有环境。
- 用户当前终端代理端口为 7892；环境依赖、权重和数据优先从镜像站下载，必要时对单次命令禁用代理直连。PyTorch 优先尝试上海交大源并核对兼容性；镜像不可用再使用用户授权代理。
- 权重、数据集、场景 assets 等统一放 `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/`，分别使用 `models/`、`assets/`；不下载到代码仓库。
- 每个实验及时维护 README；任务结束后释放本项目已无任务的 GPU 服务。
- HTML 可视化生成后必须发布到用户服务器，并交付可直接访问的网址；统一入口与操作见
  [新窗口发布操作手册（可直接复制命令）](docs/VISUALIZATION_PUBLISHING.md)，公开前缀为 `http://134.175.18.101/vln/`。
- HTML 中的模型输出、prompt、任务指令等英文内容须提供完整中文翻译及“中文 / English”切换，默认中文，保留英文原文。

完整规则及历史要求的优先关系以 AGENTS.md 为准；本说明不触发任何下载或新实验。


接手入口：[当前状态](docs/STATUS.md) · [分类实验总目录](experiments/README.md) · [代码导航](docs/CODE_LAYOUT.md)。
每类实验及具体实验均在 `experiments/` 下维护 README，实验产物仍保留在 `outputs/`。

当前 Crossing Checkpoint 研究版本的流程、27B 模型启动、离线评测及 HTML 使用方式，见
[Crossing Checkpoint README](README_CROSSING_CHECKPOINT.md)。

10 条任务的 Oracle 位置与朝向纠正实验、实时审阅和 GPU 释放规则，见
[Oracle Crossing 实验说明](docs/ORACLE_CROSSING_PILOT.md)及 [AGENTS.md](AGENTS.md)。

StreamVLN 与 JanusVLN 的导航研究初始项目，保留 R2R-CE、RxR-CE 和 VLNVerse 的既有适配。
项目于 2026-11-01 从 VLN_TTA2026_Autumn 分离，后续研究方向重新开始；两个 backbone
的既有环境及 Python 运行时独立迁入本目录，模型权重、数据和场景继续复用 Resource_Peng。
旧项目已清理，删除后的环境、资源读取与独立性检查均通过；详见 [清理记录](docs/CLEANUP_20261101.md)。
本机环境随目录保留，Git 保存源码、验证记录和恢复说明。
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

## 权重与数据存放位置

所有新下载的权重、数据集、场景等统一放在 `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/`：权重使用 `models/`，数据和场景使用 `assets/`。仓库仅保存代码、配置和资源引用。27B 权重实际位于 `Resource_Peng/models/Qwen3.8-27B-FP8/`，旧 `.runtime/models/Qwen3.8-27B-FP8` 路径为兼容软链接。详见 `docs/ENVIRONMENT.md`。
