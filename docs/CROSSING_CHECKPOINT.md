# Crossing 存档点离线迭代

当前完整版本的操作入口见 [README_CROSSING_CHECKPOINT.md](../README_CROSSING_CHECKPOINT.md)，
包含 27B 服务启动、关闭思考、开发集回放和最新 C/P 对照 HTML 生成命令。2026-11-05起每轮完成必须使用[默认双进度条模板](CROSSING_VISUALIZATION_TEMPLATE.md)，统一入口为 `scripts/export_crossing_iteration.py`。下文保留历史演进记录。

当前使用已有 StreamVLN / VLNVerse seed2 记录，模型为本地
Qwen3.8-27B-FP8。先用 Transformers 完成直接推理的短前缀验证，随后已切换至
本地 vLLM 原生 FP8 推理。没有重新运行导航，没有错误纠正或回退。

输出目录：`outputs/crossing_checkpoint/seed2_v1_20261103/`。
固定 8 条开发轨迹（成功和失败各 4 条），另留 40 条验证轨迹；场景不重叠。
此前标定的 55 个地图 crossing 保持固定，原始录像和结果保持只读。

## 因果输入

每次读取当前动作执行前的纯 RGB（原视频左上 640×480），最近 8 个可用观测、
已执行的最近 32 个动作和当前视觉存档记忆。下一动作、未来画面、GPS、地图、参考路径、
最终成败均不得进入模型请求。逐条轨迹保持时间顺序，不同轨迹可以并行。
模型结构化输出视觉证据、路线选项及 here/ahead/behind/unknown 判断。
与原地图保持一致：家具形成两条清晰可通行路线时也计为分岔；家具微小间隙不计。
在首个模型运行前已修正该定义差异，地图标签未修改。
v1 在最近 3 次判断中至少 2 次确认已到路口时建立存档，保存真实确认步，禁止倒填时间。

## 开发与验证

每个版本固定源码、提示词、模型配置、采样设置和样本清单；更改版本必须使用新的 run tag。
先检查 API 输出、因果输入及逐步覆盖完整性，再分析误检、漏检、重复存档和迟报。
修改只基于开发集；逐版保留原始响应和统计，不覆盖先前结果。

进入扩大验证的预设参考门槛：按 1.0m 地图匹配，precision ≥85%、recall ≥80%，
重复存档占确认存档比例 ≤10%，同时必须检查证据画面，排除信息泄漏或匹配漏洞。
冻结候选后运行保留的 40 条验证集，不反复利用同一验证集调参。
如果连续至少 3 轮针对已知问题的独立修改都无法改善，报告最佳版本、逐轮证据和具体瓶颈。
这个条件并不允许把部署错误、未完成的推理或空结果当作方法已达到瓶颈。

地图标签是几何先验，不是独立人工视觉金标准。轨迹进入 0.7m 邻域构成访问，
离开 1.2m 后再次进入另算访问；另报告 0.7/1.0/1.5m 匹配容差。
预测与访问一对一匹配，额外重复计为误报。最近接近步只是时间代理，
不能声称它等于实际做出路线选择的时刻；可见性与可操作时机仍须结合 RGB 复核。

## 运行与状态

`iteration_status.json` 记录环境、模型与开发集的阶段。
`runs/<tag>/cases/<episode>/status.json` 记录每条轨迹真实进度。
`runs/<tag>/scores.json` 仅统计完整完成的轨迹，不将未完成样本当作未检出。

```bash
python3 -B scripts/replay_crossing_checkpoint.py prepare
python3 -B scripts/report_crossing_checkpoint.py --output outputs/crossing_checkpoint/seed2_v1_20261103 --tag qwen27_fp8_dev_v1
```

HTML 位于 `reports/<tag>/index.html`，与同目录 videos 一起复制即可离线查看。
尚未完成的轨迹可以生成独立预览，不调用最终评分，也不将未处理片段计为漏检：

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/preview_crossing_checkpoint.py \
  --output outputs/crossing_checkpoint/seed2_v1_20261103 --tag qwen27_fp8_dev_v1
```

输出 `reports/<tag>_preview/index.html`，已处理的纯 RGB 图片直接嵌入单个 HTML。
生成器使用该 run 冻结的状态机源码逐步重建记忆，并核对原始视频、RGB 编码、
历史动作与请求哈希。各时刻只显示当时已有的存档状态，不提前展示后来确认的事件。
紫色存档点和最近地图点的距离仅供复核，不在未完成前缀上给出最终准确率或召回率。

GPU 调度锁仅协调本项目进程，不是服务器全局独占；实际启动前重新检查他人进程和显存。
权重从官方魔搭仓库国内直连，清除代理环境，校验 SHA256 和 safetensors 结构。
独立推理环境使用国内软件镜像，不修改 StreamVLN、JanusVLN 或仿真环境。

## 当前直接推理路径

Transformers 5.8.1 + Accelerate 1.12.0 放在 `.runtime/crossing_transformers27/overlay`，
只读复用 Resource_Peng/models/qwen3vl-vllm 的 PyTorch 2.9，不修改已有环境。
官方 FP8 权重按其比例因子还原为 BF16 计算，分布于 GPU 0、3；没有下载另一份权重。
这是与 vLLM 原生 FP8 不同的数值路径，使用独立标签 `qwen27_tf_bf16_dev_v1`。
切换后使用新标签，并检查相同因果输入的输出差异，不合并两种后端的统计。
入口：`python3 -B scripts/run_crossing_transformers_development.py`。
该旧路径实际保留了第一条轨迹的 6 个观测，并未完成整条轨迹，不能视为正式结果。
5 个相同输入请求的后端比较已经完成；状态、位置及同一地点判断均一致，
但这不代表完整 benchmark 等价。原生 FP8 开发集使用 `qwen27_fp8_dev_v1` 独立运行。
当前服务为 vLLM 0.19.1、Torch 2.10.0、Transformers 5.8.1，部署信息见
`service_qwen27_tp2/service.json`。旧 Transformers 进程已退出，不应与当前服务重复启动。

## 历史窗口越界修复

原生 FP8 首轮在 `kujiale_0036_10_0` 的第 8 帧连续两次产生不属于当前输入集合的
证据编号，校验拒绝该回答。原日志只保留了异常消息，未保存无效回答原文，因此不能
从旧日志确定具体越界编号。该 run 的 34 个有效观测及所有日志完整保留，未完成轨迹不评分。

`crossing-v1-schema2` 保持 crossing 定义、模型设置和存档状态机不变，仅为每次请求的
JSON schema 加入当前 RGB 帧编号的枚举约束，同时保存无效回答的完整原文和请求哈希。
模型在记忆中看过的旧帧不能冒充本次直接提供的视觉证据；本地校验仍然保留。
结构合法并不证明视觉判断正确，仍需完成地图比较及 RGB 复核。
诊断使用旧 run 的因果记忆测试原失败时刻，单独存放在 `schema_regression/`；
正式修正版使用新 tag 从头执行固定 8 条开发轨迹，不将诊断结果或旧版前缀拼入新结果。

`scripts/run_crossing_development.py` 复用现有模型服务，定期更新只含已处理前缀的预览。
开发集结束后自动生成诊断和报告；不会自行改动方法，也不会提前开启保留的验证集。

## 当前运行：关闭思考模式

2026-11-03 用户要求关闭长思考。`qwen27_fp8_dev_v1_schema2` 的控制器和回放进程已停止，
70 个有效观测及 3 个已确认存档保留为未完成前缀；模型服务继续复用。
新标签 `qwen27_fp8_dev_v1_nothinking` 从头评测相同的 8 条开发轨迹，独立保存统计。
不将旧思考模式生成的存档记忆拼接进新版本。

请求显式传入 `chat_template_kwargs={"enable_thinking": false}`。仅省略 `--thinking`
不足以关闭模型模板默认开启的思考。该请求参数写入 manifest 和请求哈希，预览生成器
兼容旧运行的参数形式，并逐步校验新运行实际使用的参数。提示词、8 张历史图像、32 个
历史动作、存档规则、地图评分与 8192 的输出上限均保持不变；模型输出答案即可提前结束。

```bash
python3 -B scripts/run_crossing_development.py \
  --output outputs/crossing_checkpoint/seed2_v1_20261103 \
  --tag qwen27_fp8_dev_v1_nothinking \
  --service outputs/crossing_checkpoint/seed2_v1_20261103/service_qwen27_tp2 \
  --workers 4 --no-thinking --max-tokens 8192
```

此入口默认关闭思考；上面的 tag 已用于实际运行，改动配置时必须使用新 tag。
新运行最初 27 个观测均返回有效 JSON，响应的 reasoning 字段为空，平均耗时约 12.6 秒；
这是早期运行诊断，不是完整速度基准，也不证明识别质量与思考模式相同。
当前预览：`reports/qwen27_fp8_dev_v1_nothinking_preview/index.html`。

## 完整开发集与用户复核

无思考版本已完成 8/8 条轨迹、573/573 个观测，无失败重试，平均推理约 14.1 秒。
在固定 1.0m 地图匹配口径下，7 个确认存档匹配 5 个、未匹配 2 个；21 次地图访问
漏检 16 次，precision 71.4%、recall 23.8%。此为地图一致性指标，尚须 RGB 可见性复核。

用户随后明确要求先制作 HTML，不开始下一轮迭代。当前等待用户复核，不启动新方法版本
或 40 条验证集。完整单文件报告为
`reports/qwen27_fp8_dev_v1_nothinking_review/crossing_dev8_review.html`，内嵌 573 个观测的
RGB 与地图，支持存档/地图访问跳转、历史输入查看、逐步回放及复核意见导出。

报告生成命令：

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/build_crossing_review.py \
  --output outputs/crossing_checkpoint/seed2_v1_20261103 \
  --tag qwen27_fp8_dev_v1_nothinking
```

生成过程使用本轮冻结源码校验所有因果请求、重建存档并复算评分，不调用模型。
`verification.json` 保存数据核验结果；`ui_verification.json` 是 Node DOM 模拟器的
交互检查，包含 573 个观测及 23 个事件入口，不代表已经过真实浏览器渲染验证。

用户要求更清晰地区分两套标注后，报告默认显示全程对照：蓝色圆点/圆圈“原 C”是原先
标定的 crossing，红色菱形“现 P”是当前版本的全部确认存档。当前 P 坐标取确认时的
机器人位置，不是模型估计的路口中心。未进入过 0.7m 范围的原 C 点用灰色虚线表示，
明确注明不计漏检；可用开关只显示经过的原 C 点。取消“全程对照”才按时间逐步显示 P。
两套标注各有可点击的编号列表。此次仅更新报告展示，未改动地图标签、模型输出或评分。
