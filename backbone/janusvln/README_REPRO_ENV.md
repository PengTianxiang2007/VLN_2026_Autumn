# JanusVLN R2R / RxR 复现环境

已阅读同级 StreamVLN 的 README_R2R_REPRO.md 和 README_RXR_REPRO.md。当前阶段配置作者 checkpoint 推理评测所需环境，未开始完整评测或训练。

## 独立 uv 环境

仓库版本：`8cfe3129f7af4ca276bd5e38f1fae7e5367a09ec`。

环境 `/tmp/janusvln-venv`，仓库 `.venv` 指向它。Python 3.9.25；PyTorch 2.5.1+cu124、Torchvision 0.20.1+cu124、Torchaudio 2.5.1+cu124、Transformers 4.50.0、FlashAttention 2.7.1.post4、Habitat-Lab/Sim/Baselines 0.2.4、NumPy 1.26.4。

```bash
cd /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/JanusVLN
bash scripts/setup_eval_uv.sh
source .venv/bin/activate
bash scripts/smoke_eval_cpu.sh
```

安装脚本仅在自身进程中取消代理变量，PyPI/PyTorch 优先直连上海交大镜像，FlashAttention wheel 从 GitHub 发布文件镜像 ghfast.top 下载。现有终端的 7892 代理配置不变。FlashAttention 使用与 Torch 2.5/Python 3.9 匹配的预编译 wheel；系统 CUDA_HOME 指向 11.8，无需修改系统 CUDA 或编译扩展。GPU 驱动支持 CUDA 12.4。

Habitat-Sim 复用 `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/software/StreamVLN/habitat-sim-0.2.4-py3.9-headless-bullet.tar.bz2`，安装前校验 MD5。Habitat-Lab/Baselines 复用同级 `habitat-lab-v0.2.4` 源码。依赖清单在 `requirements-eval.txt`；作者的 `requirements.txt` 包含训练、视频等其他依赖，本环境用于 R2R/RxR checkpoint 评测。

`/tmp` 清理后可用安装脚本重建；可通过 `JANUSVLN_VENV` 指定其他环境目录。CPU 检查屏蔽 GPU，限制计算线程，不加载大模型权重。

## 复用数据

所有数据和场景仍位于 `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/`，仓库只有软链接：

| 仓库路径 | 共享资源路径 |
| --- | --- |
| `data/datasets/r2r` | `assets/StreamVLN/r2r` |
| `data/datasets/rxr` | `assets/StreamVLN/rxr` |
| `data/scene_datasets/mp3d` | `assets/StreamVLN/mp3d` |

R2R `val_unseen` 共 1839 条。RxR `val_unseen` 英语 Guide 子集共 3669 条，真值文件已存在。共享 MP3D 已提取这两个验证集需要的 11 个场景。其他 split 尚未核对场景完整性。无需重复下载数据，不下载需要另行申请的场景资源。

## 权重和评测入口

本次优先准备 `JanusVLN_Extra`，对应论文使用 ScaleVLN 与 DAgger 额外数据的主结果；Base 是独立的无额外数据版本，尚未下载。下载命令：

```bash
.venv/bin/python scripts/download_checkpoint.py --model Extra
```

下载位置 `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/JanusVLN_Extra/`。下载器直连作者 ModelScope 国内站，逐文件使用发布清单的 SHA256 校验；已校验文件跳过，`.part` 文件断点续传，已有不同内容的文件保留并报错。`download_manifest.json` 记录来源和文件版本，全部完成后生成 `download_verified.json`。下载日志 `/tmp/janusvln-download-extra.log`。

离线检查分片索引及 tokenizer/processor：

```bash
.venv/bin/python scripts/check_checkpoint_cpu.py
```

专用 RxR 配置 `config/vln_rxr.yaml` 和数据集注册 `src/habitat_extensions/rxr_dataset.py` 已补齐，使用 3669 条英语 Guide episode。RxR 按真实模拟器位置计算精确 DTW，`ndtw = exp(-DTW/(真值轨迹点数 × 3m))`；去除连续重复位置，轨迹和真值只用于评分，不输入模型。作者原有 `NDTW` 类使用 FastDTW 近似值，本次新增评分与已复现 StreamVLN 的精确 DTW 实现一致，比较时应注明。

启动命令（GPU 编号须替换为允许使用的物理卡）：

```bash
bash scripts/janusvln_eval.sh r2r GPU_ID extra
bash scripts/janusvln_eval.sh rxr GPU_ID extra
```

脚本每次仅启动单张 GPU，检查至少 30000 MiB 可用显存、checkpoint 校验完成状态，并通过文件锁避免同一输出目录或同一 GPU 重复启动 JanusVLN。默认输出为 `results/val_unseen/r2r_extra/` 和 `rxr_extra/`，可通过 `JANUSVLN_OUTPUT_PATH` 指定其他目录。`result.json` 只保存逐 episode 结果，`summary.json` 独立保存汇总；单卡重启可跳过已有 episode。

保留作者模型、RGB/深度 640×480、15° 转向、0.25m 前进、`num_history=8`、seed=42 和 `max_steps=400` 的默认设置；Habitat 配置 `max_episode_steps=500`。作者推理代码从 step_id=400 起强制 STOP，所以总步数最多 401，勿与 StreamVLN 的 500 步上限混淆。

独立单 episode 检查示例：

```bash
JANUSVLN_OUTPUT_PATH=results/smoke/r2r_extra bash scripts/janusvln_eval.sh r2r GPU_ID extra --episode_limit 1
JANUSVLN_OUTPUT_PATH=results/smoke/rxr_extra bash scripts/janusvln_eval.sh rxr GPU_ID extra --episode_limit 1
```

正式评测不传 `--episode_limit`。单 episode 结果不计入论文复现结果。完整运行前核对 `summary.json` 的 `length`：R2R 1839，RxR 3669；比例指标乘 100 后与论文比较。

论文 v2 主表参考：Extra 在 R2R 为 NE 4.78、OS 65.2%、SR 60.5%、SPL 56.8%；RxR 为 NE 6.06、SR 56.2%、SPL 47.5%、nDTW 62.1%。来源：[论文表 1 / 2](https://arxiv.org/html/2509.22548v2)。同一论文附录表 8 的 Extra SPL 写为 56.6%，与主表不同；本次按主表记录。

公共服务器上不终止任何运行进程。用户已指定 GPU 2 用于本次 RxR 评测。未修改 StreamVLN 环境、评测脚本或运行任务。

## 已完成验证（2026-10-01 UTC）

- 安装脚本退出码 0；Torch / FlashAttention / Transformers 版本与导入正常。
- `bash scripts/smoke_eval_cpu.sh` 退出码 0：作者评测入口、JanusVLN 自定义 Qwen2.5-VL/VGGT 模型类、Habitat-Lab/Sim/Baselines 均可导入。
- R2R `val_unseen` 1839 条，所有场景文件存在；RxR 英语 Guide 3669 条，所有场景文件和真值条目存在。
- `uv pip check --python /tmp/janusvln-venv/bin/python` 通过，119 个包无依赖冲突。
- 完整版本快照：`requirements-eval.lock.txt`（Habitat-Sim 以缓存归档手动安装，重建仍使用安装脚本）。
- 安装日志 `/tmp/janusvln-setup.log`；检查日志 `/tmp/janusvln-smoke.log`。尚未验证 GPU 模拟器和完整权重加载，未产生论文指标。

## RxR 接入验证

实际 Habitat 注册加载器与新增 RxR 配置已通过 CPU 检查，加载 3669 条英语 Guide episode；已知轨迹的 nDTW 检查通过。使用独立临时目录及模拟环境检查了新增 nDTW 写出、单 episode 检查结束关闭环境、续跑不重复记录。GPU 模型加载与真实 episode 尚待验证。

## Checkpoint 准备结果（2026-10-01 UTC）

`JanusVLN_Extra` 已从作者 ModelScope 直连下载到 `Resource_Peng/models/JanusVLN_Extra/`，4 个权重分片和配套配置全部通过发布清单的 SHA256 校验。最新权重分片版本 `8631eee38a4c688256473ec6a59917fb5eec58ff`（作者 2025-11-06 修正上传），下载时未使用 7892 代理。

离线 CPU checkpoint 检查通过：4 个分片、2068 个 tensor 与索引一致，包含 VGGT；tokenizer 和 `Qwen2_5_VLProcessor` 可离线加载。日志 `/tmp/janusvln-checkpoint-cpu.log`。仍未进行 GPU 模型加载、真实 Habitat episode 或完整评测；待指定允许使用的 GPU 后继续。

## RxR 正式运行（2026-10-02）

GPU 2 的真实单 episode smoke 正常结束，退出码 0，模型、Habitat、导航和 nDTW 输出正常。Smoke 结果保存在 `results/smoke/rxr_extra_gpu2/`，不计入正式结果。

3669 条英语 Guide `val_unseen` 正式评测已在 tmux 会话 `janusvln_rxr_peng_gpu2_20261002` 启动，使用 `JanusVLN_Extra`，命令为 `bash scripts/janusvln_eval.sh rxr 2 extra`。正式目录 `results/val_unseen/rxr_extra/`，日志 `run.log`，父进程记录 `run.pid`；正常结束后保存 `run.exit_code` 和 `summary.json`。启动脚本 `scripts/run_rxr_gpu2.sh`。同目录和 GPU 均有文件锁，勿启动重复任务。

按用户要求，确认启动正常后不持续监控；未终止任何现有进程。需要时手动查看日志和结果数量即可，全集完成前不报告最终论文指标。

## R2R 正式运行（2026-10-02）

用户要求使用新空闲 GPU 运行 R2R。启动前 GPU 1 无计算进程，剩余显存 45576 MiB。GPU 1 上 R2R 真实单 episode smoke 退出码 0，SR=1、SPL=0.9484、NE=0.4222m；这不是正式全集指标。Smoke 目录 `results/smoke/r2r_extra_gpu1/`，日志 `/tmp/janusvln-r2r-smoke-gpu1.log`。

1839 条 R2R `val_unseen` 正式评测在 tmux 会话 `janusvln_r2r_peng_gpu1_20261002` 启动，使用 `JanusVLN_Extra`；命令 `bash scripts/janusvln_eval.sh r2r 1 extra`，后台脚本 `scripts/run_r2r_gpu1.sh`。正式输出 `results/val_unseen/r2r_extra/`，日志 `run.log`，父进程记录 `run.pid`。GPU 2 上 RxR 继续运行，未干预任何现有进程。确认启动正常后不持续监控。


2026-10-03：用户明确要求停止 RxR-CE，仅对核实的 RxR torchrun 父进程发送 SIGTERM；保留逐 episode 结果及日志，可后续续跑。R2R 任务继续运行。
