# 初始迁移

来源：同级 VLN_TTA2026_Autumn，提交 `860e200ce253826fc9c9e951dfc46879cd010f9a`。
原项目保持不变；此项目使用独立 Git 历史，`initial-20261101` 标签保存通过迁移验证的
初始状态。新项目尚未配置 GitHub 远程仓库。

迁入两个 backbone 的源码、R2R/RxR evaluator、VLNVerse adapter、Habitat 0.2.4、
VLNVerse 上游及运行组件。保留原生模型训练相关源文件以维持上游包完整性，但本次只验证推理。
未迁入旧 TTA adapter、baseline、PRM、iterations、实验调度队列、历史输出和教程结果归档。

`migration/source_manifest.json` 保存最初复制的 1,385 个文件的来源 SHA256。
迁移后的差异集中在统一入口、资源路径、环境定位和输出位置；模型推理主体保持原样。
`scripts/evaluate.py` 将两个模型在三种 benchmark 上的入口统一为六种组合。
原 StreamVLN RxR 使用 --max_eval_episodes，其他 Habitat evaluator 使用 --episode_limit；
统一入口据此选择参数，不截断单条任务的导航步数。

两套已配置的模型环境及 Python 3.9 被独立复制，随后校正绝对路径和可编辑安装。
本项目不靠指向旧目录的软链接运行。VLNVerse 原 /tmp 环境已不存在，因此使用已有
Isaac 4.5 安装包及其内置 Torch/CUDA 库恢复独立仿真环境，持久保存在本项目。
共享 Resource_Peng 中的权重、数据、场景仍直接复用。

历史 backbone README 中可能包含原机器路径、旧状态和历史成绩；当前使用依据为根 README
与 docs/。本次验证结果另记，不将历史复现成功视作迁移后的成功。
