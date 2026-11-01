# StreamVLN RxR 复现运行说明

## 目标与范围

使用作者发布的 `StreamVLN_Video_qwen_1_5_r2r_rxr_envdrop_scalevln_v1_3` checkpoint，在 **RxR_VLNCE_v0 `val_unseen` Guide 英语子集**上评测：`en-US` 1223 条、`en-IN` 2446 条，共 **3669 个 episode、11 个 MP3D 场景**。全集运行不抽样、不缩短 episode，也不降低模型或传感器配置。这是作者权重的推理评测，不是从头训练。

作者公布的 RxR 参考值为 NE 5.65、SR 54.4%、SPL 45.4%、nDTW 63.7。该说明明确采用 VLN-CE 常用的英语 Guide 口径；作者仓库没有提供独立 RxR 评测配置，最终比较时应同时报告此口径。

## 仓库与环境

- 仓库：`/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/StreamVLN`
- 复用 R2R 的 uv 虚拟环境 `/tmp/streamvln-venv`；仓库 `.venv` 指向它。环境若被 `/tmp` 清理，可按 [R2R 运行说明](README_R2R_REPRO.md)用 `bash scripts/setup_r2r_uv.sh` 重建。
- Python 3.9.25、PyTorch 2.1.2+cu121、Habitat-Lab/Sim 0.2.4、Transformers 4.45.1、FlashAttention 2.7.0.post2。单张 NVIDIA L20 即可运行；环境脚本优先使用上海交大 PyPI/PyTorch 镜像。
- RxR 使用独立的 `config/vln_rxr.yaml`、`streamvln/rxr_dataset.py`、`streamvln/rxr_metrics.py` 和 `streamvln/streamvln_eval_rxr.py`；R2R 正在使用的评测入口未改动。

## 数据与权重

| 资源 | 位置 | 状态 |
| --- | --- | --- |
| RxR_VLNCE_v0 归档 | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN/RxR_VLNCE_v0.zip` | 公开 Hugging Face 镜像副本；ZIP 完整性检查通过；本地 SHA256 `c6f26f084ebafd71d759472e38cea9aaa417687eb8fa8f3c7bcb65e4e670ceb0` |
| RxR episode 与真值 | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN/rxr/val_unseen/` | 只提取 `val_unseen_guide.json.gz` 和 `val_unseen_guide_gt.json.gz`；仓库 `data/datasets/rxr` 指向该目录 |
| MP3D 场景 | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN/mp3d/` | 所需 11 个场景的 `.glb` 均已存在；仓库 `data/scene_datasets/mp3d` 指向该目录 |
| StreamVLN checkpoint | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/StreamVLN_R2R_v1_3/` | 与 R2R 共用，4 个 safetensors 分片已校验 |
| SigLIP 视觉塔 | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/siglip-so400m-patch14-384/` | 与 R2R 共用，权重已校验 |

归档来源：[VLN-CE 数据说明](https://github.com/jacobkrantz/VLN-CE/blob/master/README.md)、[镜像副本](https://huggingface.co/datasets/anhdao69/R2R_RxR_VLNCE_preprocessed/tree/main)。仅准备了上述 `val_unseen` 文件；运行其他 split 前须另行核对数据和场景。

## 启动完整 RxR `val_unseen` 评测

先确认目标 GPU 空闲，且**同一输出目录没有正在运行的 RxR 评测进程**。在仓库目录运行；参数是物理 GPU 编号，脚本通过 `CUDA_VISIBLE_DEVICES` 映射并用单进程 `torchrun` 启动：

```bash
cd /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/StreamVLN
bash scripts/streamvln_eval_rxr.sh 3
```

脚本固定使用本地 v1.3 checkpoint、`config/vln_rxr.yaml` 与 `val_unseen`，保持 `num_frames=32`、`num_future_steps=4`、`num_history=8`、640×480 RGB/深度传感器、15° 转向、0.25 米前进和每 episode 最多 500 步。脚本仅接受一张 GPU，便于同目录安全续跑。

默认输出目录为 `results/val_unseen/streamvln_rxr_v1_3/`，可用 `STREAMVLN_OUTPUT_PATH=/path/to/output` 覆盖。`result.json` 是逐行 JSON 的 episode 结果，包含 `success`、`spl`、`os`、`ne`、`ndtw`、语言及步数；全部结束后 `summary.json` 保存平均值，其中 `ones_all` 对应 NE、`sucs_all` 对应 SR、`spls_all` 对应 SPL、`ndtws_all` 对应 nDTW。比例指标以 0–1 保存，与论文百分数比较时乘 100。同一目录单卡重启会跳过已记录 episode；不要删除已有结果，也不要同时启动两份写同一目录的进程。

nDTW 用 Guide 真值轨迹按 `exp(-DTW 距离 / (参考轨迹点数 × 3 米))` 计算。评测器记录每步模拟器位置并去除连续重复位置；轨迹仅用于事后评分，不作为模型输入。

## 全集结果与待解决问题

2026-10-03 08:01 CST，物理 GPU 3 上的 RxR 全集评测结束。`results/val_unseen/streamvln_rxr_v1_3/result.json` 有 3669 条互不重复的结果，`summary.json` 的 `length` 为 3669。原始汇总为 SR 54.92%、nDTW 63.94%、OS 63.80%，但 NE 为 `Infinity`、SPL 为 `NaN`；不要将后两项作为有效复现结果。

异常全部来自场景 `oLBMNvg9in8`：345 条英语 Guide episode 中有 99 条（33 条轨迹各对应 3 条指令）的 NE 为 `Infinity`、SPL 为 `NaN`，且成功率均为 0。用当前 `.navmesh` 对这 345 条逐一调用 Habitat-Sim 的 `PathFinder.find_path`，结果与评测完全一致：99 条异常样本均找不到起点到目标的路径，另外 246 条均能找到。当前资源目录中只找到这一份该场景的 `.navmesh`。直接用现有资源重跑这 99 条无法解决导航距离为无穷大的问题。

若按失败轨迹的 SPL 为 0 重新汇总，得到 45.89%，但这是事后修正值，需与原始 `NaN` 分开报告。只对其余 3570 条取平均会得到 NE 5.65 米，**不能**与论文的全量 NE 5.65 米直接比较。`result.json` 未保存每条轨迹的终点位置，因而不能从现有结果补算这 99 条 NE。

下一步先核对与 VLN-CE 基准兼容的场景/导航网格版本，保持现有资产和原始结果不变，在独立路径做验证。如果替代网格改变了另外 246 条的路径或导航指标，应至少重新评测该场景全部 345 条，而不是混用两个网格版本的结果；随后才生成新的全量汇总。公共服务器上不要停止或占用其他人的进程。

需要时做一次只读检查：

```bash
cd /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/StreamVLN
wc -l results/val_unseen/streamvln_rxr_v1_3/result.json
cat results/val_unseen/streamvln_rxr_v1_3/summary.json
tail -n 20 results/val_unseen/streamvln_rxr_v1_3/run.log
```

`/tmp` 环境可能被清理，但数据、权重和 MP3D 归档保存在 `Resource_Peng`。

## 已完成的验证

- `bash scripts/smoke_rxr_cpu.sh` 通过：入口、配置、3669 条英语 Guide episode、11 个场景文件、全部 nDTW 真值及指标基本计算正常。
- 在物理 GPU 3 上完成 1 条真实 RxR episode 的独立 smoke 评测，模型、Habitat 导航和指标汇总均正常，退出码为 0；结果在 `results/val_unseen/streamvln_rxr_smoke_gpu3/`，不计入正式全集。
- 正式评测已完成 3669 条；除上述 99 条 NE/SPL 异常外，其余条目的这两项指标均为有限值。
