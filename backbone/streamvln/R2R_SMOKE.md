# R2R smoke test setup

Run from this repository:

```bash
bash scripts/setup_r2r_uv.sh
bash scripts/smoke_r2r.sh
```

The uv environment is at `/tmp/streamvln-venv`; `.venv` links to it. Re-run the setup script if `/tmp` is cleared. The script uses the SJTU PyPI and PyTorch mirrors, Habitat-Lab v0.2.4, and checksum-verified Habitat-Sim 0.2.4 and FlashAttention 2.7.0.post2 archives stored under `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/software/StreamVLN/`. FlashAttention was installed from the official prebuilt CUDA 12 / PyTorch 2.1 / Python 3.9 wheel and verified with a small CUDA kernel call.

The public R2R_VLNCE_v1-3 episode archive is under `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN/`. `data/datasets/r2r` links to the extracted episodes. The smoke test imports the real evaluation entry point, checks CUDA and Habitat, and loads 778 `val_seen` plus 1839 `val_unseen` episodes without opening a scene.

The MP3D Habitat archive is stored at `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/assets/StreamVLN/mp3d_habitat.zip` and passed SHA256 verification. All 11 scenes required by R2R `val_unseen` were extracted under `assets/StreamVLN/mp3d/`, with `data/scene_datasets/mp3d` linked there. A real `val_unseen` episode opened successfully in Habitat on a single GPU and produced 480x640 RGB and depth observations. The full 8.03B-parameter model loaded on one GPU with FlashAttention and the local SigLIP processor, using about 15 GiB VRAM. Full model inference and R2R benchmark scoring have not yet been run.

To run the complete `val_unseen` benchmark later, choose currently available GPU indices explicitly: `bash scripts/streamvln_eval_r2r.sh 1`. The per-episode results are written to `result.json` as JSON lines, while aggregate metrics are written to `summary.json`.

The benchmark checkpoint directory `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/StreamVLN_R2R_v1_3/` contains its config, Qwen2 tokenizer, and all four SHA256-verified weight shards. The separate SigLIP vision tower weights are SHA256-verified under `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/siglip-so400m-patch14-384/`; the checkpoint config points to this local directory. Weight downloads are complete.
