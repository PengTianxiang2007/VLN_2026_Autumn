# 环境与资源

本机新目录开箱即用：两套 backbone 环境从原项目完整复制，依赖版本不变。
环境目录、Python 解释器、脚本 shebang、可编辑安装路径均指向本项目。
原 VLN_TTA2026_Autumn 可在后续单独删除，不是运行依赖。

| 用途 | 本项目内位置 | 核心版本 |
| --- | --- | --- |
| StreamVLN | backbone/streamvln/.venv | Python 3.9.25、Torch 2.1.2+cu121、Transformers 4.45.1、FlashAttention 2.7.0.post2 |
| JanusVLN Extra | backbone/janusvln/.venv | Python 3.9.25、Torch 2.5.1+cu124、Transformers 4.50.0、FlashAttention 2.7.1.post4 |
| Python 3.9 | .runtime/python/cpython-3.9.25-linux-x86_64-gnu | 两套模型环境的基础解释器 |
| uv | .runtime/tools/bin/uv | 已有工具的独立副本 |
| VLNVerse | benchmarks/vlnverse/.venv | Python 3.10，仿真与模型依赖分开 |
| Isaac Sim | .runtime/isaac45 | 4.5.0，项目私有运行时 |

环境与运行时不加入 Git。仅克隆 Git 仓库不会得到这些二进制目录；本机现有目录已经包含。
环境创建于本机固定路径，任意重命名整个项目后，需要重新校正 venv 的绝对路径。

`core/paths.py` 为每个进程配置当前 backbone 和 Habitat 源码优先级，避免两套模型
的同名模块混用。模型进程固定使用自己的 Python，不使用系统 Python 加载模型。
新缓存写入本项目 .runtime，运行结果写入 outputs。

## 共享资源

默认根目录 `/mnt/nas/gezuhao/shared_dataset/Resource_Peng`，可用 `VLN_RESOURCE_ROOT` 覆盖。

| 资源 | 根目录下路径 |
| --- | --- |
| StreamVLN | models/StreamVLN_R2R_v1_3 |
| JanusVLN Extra | models/JanusVLN_Extra |
| StreamVLN 视觉编码器 | models/siglip-so400m-patch14-384 |
| R2R、RxR、MP3D | assets/StreamVLN/{r2r,rxr,mp3d} |
| VLNVerse 场景、任务、机器人 | assets/VLNVerse |
| 已缓存安装包 | software |

模型目录下 data/ 的软链接指向共享资源，与旧项目没有依赖关系。
`python3 core/paths.py` 检查并创建缺失链接，拒绝覆盖冲突目录。
R2R val_unseen 为 1,839 条，RxR 英语 Guide val_unseen 为 3,669 条。
VLNVerse fine val_unseen 为 825 条；这些是数据规模，不代表本次进行了全集评测。

## 检查和恢复

日常直接运行，无需 activate 或重新安装：

```bash
python3 scripts/check_environment.py --backbone streamvln --output outputs/checks/streamvln.json
python3 scripts/check_environment.py --backbone janusvln --output outputs/checks/janusvln.json
```

只有环境确实丢失时才使用 `bash scripts/setup.sh streamvln|janusvln|vlnverse`。
模型安装脚本使用迁入的 Habitat 源码；独立 venv 不合并版本。
Isaac 缺失时用 `python3 scripts/restore_isaac.py` 从已有 4.5 安装包恢复，默认落到
.runtime/isaac45，不依赖 /tmp，也不改服务器系统 Isaac。

可显式覆盖 `STREAMVLN_VENV`、`JANUSVLN_VENV`、`VLNVERSE_VENV` 和 `PENG_ISAAC_ROOT`。
默认配置已独立；不要继承指向旧项目的同名环境变量。`VLN_OUTPUT_ROOT` 可更改结果根目录。
