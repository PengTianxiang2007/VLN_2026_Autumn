# 五帧节点消除 v001 / run01

2026-11-12，本地离线实验。只评估可视化列表第 1、2、3、4、7 条轨迹的默认 v001 在线采样候选。

用户复核更新：本版出现关键误删，暂不采用。用户明确要求保留 04 的 S01/F0、S02/F5，以及 01 的 S05/F35、S06/F38；原模型均判为 reject。四个案例记录于 `user_feedback.json`，原模型响应及统计保留供对照，没有覆盖预测，也未新增 API 调用。这些反馈不能替代全量人工标注。

输入由逐帧调用原有 `JevOnlineSampler.push` 产生，每个候选最多五张 RGB：t-2、t-1、t、t+1、t+2。F0 为唯一待判断位置。起点缺历史时提供三帧，并明确缺失标签。相对/绝对帧号、候选编号之外不提供额外导航信息。

`prompt_zh.txt` 为实际系统提示词；用户消息逐张标注图像。模型为 `deepseek-flash`，官方 `https://api.deepseek.com/chat/completions`，支持图像的账户模型列表记录于 `model_catalog.json`。图像以原始本地 WebP 的 base64 输入，`detail=high`，JSON 输出，thinking enabled / high。

12 个进程并发，每个候选单独请求。首轮 42 次、max_tokens=8192；3 个 length 截断响应单独重试、max_tokens=32768，其余设置和输入保持一致。重试文件带 `_retry01`，原始响应保留。没有因语义不满意而重试，也没有进行节点去重。第一步正常流程为一次模型调用；此次实际异常重试使 3 个候选各发生两次调用。

最终 42/42 成功，keep=22、reject=20、uncertain=0。第 7 条：15 个候选，9 个剔除，6 个保留。全批 45 次请求含重试，共计 prompt_tokens=93405、completion_tokens=118986、total_tokens=212391（以 API usage 返回为准）。

文件说明：

- `manifest.json`：范围、采样配置、节点/图像窗口、输入哈希、模型配置和异常重试说明。
- `responses/`：每次实际响应、时间、进程编号和解析校验状态；包含原始失败记录。
- `results.json`：按原候选顺序汇总，重复尝试使用最后一次结果。
- `prompt_zh.txt`：实际中文版提示词。
- `run_review.py`：并发执行与结果打包。依赖 Python 和 httpx。
- `verification.json`：完整性、并发、密钥扫描和浏览器交互检查。

从当前项目目录执行 `python outputs/jev_sampling_lab_20261112/node_elimination/v001_run01/run_review.py --pack-only` 可从已有响应重新生成网页数据包，不调用 API。执行调用时从 `DEEPSEEK_API_KEY` 环境变量或 `--key-stdin` 标准输入读取密钥。不得把密钥写入文件。已有响应不会重复发送；更改提示词、案例或采样条件应新建运行目录，避免覆盖历史。

在线时序：请求需等待 `max(node.emittedAt,t+2)`，实际判定需再等待 API 返回。网页以输入齐备的帧号应用已完成的离线缓存，网络/推理耗时单独记录，不代表零等待的在线部署结果。

页面的“节点消除”只隐藏 reject。uncertain/error/未评估点保留在候选视图中；参数或图像不匹配时不套用旧结果。模型回答是待人工复核的预测，并非准确率或导航恢复效果。
