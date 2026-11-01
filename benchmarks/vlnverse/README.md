# VLNVerse 迁移入口

`upstream/` 保存本机实际使用的 VLNVerse 源码和官方评测器；`runner/` 保存原公共模型 HTTP 服务、完整运行与恢复逻辑和重建脚本。各模型适配层在 `backbone/<model>/vlnverse/adapter.py`，已指向新仓库源码。

统一入口示例见 [experiments/README.md](../../experiments/README.md)。模型与仿真运行于不同 Python 环境，可使用不同 GPU。physical 和 flash 评估协议需分别记录。

历史结果位于 `experiments/reproductions/<model>/vlnverse/`；大日志和 LMDB 通过原 Resource_Peng 链接访问。新运行元数据位于 `outputs/vlnverse/<model>/results/`。`runner/stop_run.py` 仅核对新仓库启动的进程身份，历史 PID 文件仅作归档。
