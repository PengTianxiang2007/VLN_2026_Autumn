# StreamVLN R2R 复现运行说明

## 目标与范围

使用作者发布的 `StreamVLN_Video_qwen_1_5_r2r_rxr_envdrop_scalevln_v1_3` checkpoint，在 **R2R_VLNCE_v1-3 `val_unseen` 全集**上评测：1839 个 episode、11 个 MP3D 场景。没有抽样、缩短 episode 或降低模型与传感器配置。这是作者权重的推理评测，不是从头训练。作者公布的 R2R 参考值：NE 4.90、OS 63.6%、SR 56.4%、SPL 50.2%。

## 仓库与环境

- 仓库：`/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/StreamVLN`
- uv 虚拟环境：`/tmp/streamvln-venv`；仓库 `.venv` 是指向它的软链接。`/tmp` 清理后，在仓库运行 `bash scripts/setup_r2r_uv.sh` 重建。
- Python 3.9.25、PyTorch 2.1.2+cu121、Habitat-Lab/Sim 0.2.4、Transformers 4.45.1、FlashAttention 2.7.0.post2。GPU 是 NVIDIA L20；完整模型加载测试约占 15 GiB 显存。
- 环境脚本使用上海交大 PyPI/PyTorch 镜像；Habitat-Sim 包和 FlashAttention wheel 缓存在 `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/software/StreamVLN/`。

## 数据与权重

| 资源 | 位置 | 状态 |
| --- | --- | --- |
| R2R_VLNCE_v1-3 episode | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN/r2r/` | `val_unseen` 1839 个；仓库 `data/datasets/r2r` 指向此目录 |
| MP3D Habitat 归档 | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN/mp3d_habitat.zip` | SHA256 `470948ee78ff4d6dc4c4870395d1e790a0f15c72065d1f62cdd229b2bcbe0d36` |
| MP3D 场景 | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN/mp3d/` | 已提取 `val_unseen` 所需的 11 个；仓库 `data/scene_datasets/mp3d` 指向此目录 |
| StreamVLN checkpoint | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/StreamVLN_R2R_v1_3/` | 4 个 safetensors 分片均已校验 |
| SigLIP 视觉塔 | `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/siglip-so400m-patch14-384/` | 已校验；checkpoint 的 `mm_vision_tower` 指向这里 |

目前只提取了 `val_unseen` 的 11 个场景；不要直接用这套目录运行完整 `val_seen` 或 `test`。MP3D 原始归档仍保留在资源目录，后续可以按需要继续提取。

## 启动完整 R2R `val_unseen` 评测

先用 `nvidia-smi` 确认目标 GPU 没有被其他任务占满。在仓库目录运行，参数是**物理 GPU 编号**；脚本会通过 `CUDA_VISIBLE_DEVICES` 映射并使用 `torchrun`：

```bash
cd /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/StreamVLN
bash scripts/streamvln_eval_r2r.sh 1
```

多个空闲 GPU 可写 `1,2`。脚本固定使用本地 v1.3 checkpoint、`config/vln_r2r.yaml` 和 `val_unseen`，保留仓库默认的 `num_frames=32`、`num_future_steps=4`、`num_history=8`、640×480 RGB/深度传感器与每 episode 最多 500 步。原仓库脚本写死 8 卡和旧 checkpoint 路径；这里的启动脚本只调整运行资源和路径。

默认输出目录是 `results/val_unseen/streamvln_r2r_v1_3/`。其中 `result.json` 是逐行 JSON 的 episode 结果，可用 `wc -l` 查看已完成数量；全部结束后 `summary.json` 保存汇总指标。启动脚本支持 `STREAMVLN_OUTPUT_PATH=/path/to/output` 覆盖输出目录。使用同一个输出目录重启单卡评测时，评测器会跳过已经记录的 episode；不要删除已有结果文件。

## 当前后台运行与检查

本次运行使用 GPU 1，完整命令是 `bash scripts/streamvln_eval_r2r.sh 1`。最初进程在完成 25 个 episode 后无 Python traceback 退出；2026-10-01 09:57 UTC 已在独立 tmux 会话 `streamvln_r2r_peng_20261001` 中从现有结果续跑，确认计数增长到 26。不要再启动第二份相同评测。日志写入 `/tmp/streamvln-r2r-val-unseen.log`，tmux 窗格进程号写入 `/tmp/streamvln-r2r-val-unseen.pid`。需要时做一次检查即可：

```bash
tail -n 40 /tmp/streamvln-r2r-val-unseen.log
tmux has-session -t streamvln_r2r_peng_20261001
ps -p "$(cat /tmp/streamvln-r2r-val-unseen.pid)" -o pid,stat,etime,cmd
wc -l results/val_unseen/streamvln_r2r_v1_3/result.json
cat results/val_unseen/streamvln_r2r_v1_3/summary.json
```

评测运行期间不应停止或占用其他人的进程。`/tmp` 中的日志和环境可能被清理；场景、权重和归档保存在 `Resource_Peng`。

## 已完成的验证

- `bash scripts/smoke_r2r.sh` 通过：评测入口、CUDA、配置、tokenizer 和 R2R episode 加载正常。
- Habitat 成功打开一个真实 `val_unseen` episode，获得 480×640 RGB 和深度观测。
- 完整 8.03B 模型连同本地 SigLIP 处理器、FlashAttention 已在单张 L20 上加载成功。
- 评测代码把逐 episode 记录和最终 `summary.json` 分开保存，避免中断续跑时把汇总行当作 episode。
