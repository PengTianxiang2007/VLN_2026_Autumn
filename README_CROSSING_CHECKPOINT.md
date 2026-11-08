# Crossing Checkpoint v1：27B 离线识别与存档

本文对应 **2026-11-03 完成的 `qwen27_fp8_dev_v1_nothinking` 版本**，以及同时显示“原 C”和“现 P”的 HTML。项目根目录为：

```text
/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn
```

**当前状态：8 条开发轨迹评测已完成，等待 HTML 人工复核；下一轮方法迭代和 40 条验证集尚未启动。** 下文的启动命令供后续手动运行，本次编写文档没有启动新实验。

## 1. 当前版本做什么

利用已完成的 StreamVLN / VLNVerse seed2 录像，按时间顺序模拟机器人当时能看到的信息，让本地 Qwen3.8-27B-FP8 识别 crossing，并构建视觉存档点。Crossing 指除来路外，存在至少两条不同、可通行的后续路线的位置；清晰的家具绕行分岔可以计入，狭小缝隙、单纯转弯、关闭的门不计入。

本版只实现 crossing 识别和存档构建。存档包含视觉描述、分支方向、证据帧、首次发现及确认时间；尚未判断指令完成进度、此前路线是否正确，也没有错误恢复或可还原物理状态的存档。

每个可用观测的处理流程：

1. 从原视频左上角裁取 **640×480 纯 RGB**，不输入轨迹示意或文字覆盖区域。
2. 输入截至当前的最近 **8 个可用观测**、最近 **32 个已执行动作**及当前活动存档的语义记忆。当前尚未执行的动作、未来画面、地图、GPS、参考路径、原导航指令、最终成败均不进入模型请求。
3. 模型返回结构化 JSON：是否为 crossing、位置关系 `here/ahead/behind/unknown`、是否同一地点、置信等级、分支及证据帧。证据编号必须属于本次实际输入的图像。
4. `here` 或 `ahead` 可以建立候选；最近 3 次判断至少 2 次为 `here` 且置信度非低时确认存档，确认时间记录为当前步，不倒填到首次发现步。连续 3 次不再处于该区域后关闭记录；明确是另一地点时切换候选。
5. 推理完成后，才使用记录位置和固定地图 crossing 进行匹配、评分与 HTML 展示。

不同轨迹最多 4 路并行，每条轨迹内部严格按时间推进。两张 GPU 共同承载一个张量并行模型服务，并不是每张卡各加载一个模型。这里模拟的是**信息可见范围和输入时序**，尚未验证真实机器人上的实时响应延迟。

## 2. 固定数据与本版结果

开发集固定为 8 条轨迹，原导航成功、失败各 4 条，分布在 `kujiale_0036/0113/0208/0259`。另预留 40 条验证轨迹，成功、失败各 20 条，与开发集场景不重叠。样本已按已有筛选记录排除跌倒、卡住等情况。清单以 `protocol.json` 为准，不重新抽样。

| 项目 | 本版结果 |
| --- | --- |
| 完整轨迹 / 有效观测 | 8/8；573/573 |
| 确认存档 / 地图 crossing 访问次数 | 7 / 21 |
| 1.0m 匹配：TP / FP / FN | 5 / 2 / 16 |
| 1.0m Precision / Recall / F1 | 71.43% / 23.81% / 35.71% |
| 0.7m Precision / Recall | 42.86% / 14.29% |
| 1.5m Precision / Recall | 71.43% / 23.81% |
| 重复存档 / 失败请求重试 | 0 / 0 |
| 平均请求耗时 / 本轮总耗时 | 约 14.1 秒 / 约 40 分钟，4 路并行 |

以上是 **crossing 与地图先验的一致性指标**，不是 StreamVLN 导航成功率。固定地图共有 55 个 crossing，评分只计当前轨迹实际访问的点：进入 0.7m 邻域构成一次访问，离开 1.2m 后重新进入另算；预测还须满足对应访问的时间窗口及匹配距离。一对一匹配，重复预测计误报。没有经过的地图点不计漏检。

地图标注是几何先验，尚非独立人工视觉金标准；最近接近步也不等于实际选择路线的时刻。因此需要结合 RGB 检查可见性、定义及确认时机。本版尚未达到扩大验证门槛：1.0m Precision ≥85%、Recall ≥80%、重复比例 ≤10%，并通过视觉复核。

## 3. 文件与环境

| 路径（相对项目根目录） | 用途 |
| --- | --- |
| `/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/Qwen3.8-27B-FP8/` | 已下载并校验的本地权重；旧 `.runtime/models/` 路径为兼容软链接 |
| `.runtime/crossing_vllm27/bin/python` | 27B 模型服务环境 |
| `benchmarks/vlnverse/.venv/bin/python` | 录像读取、离线回放、报告环境 |
| `core/crossing_checkpoint.py` | 提示词、JSON schema、存档状态机和地图匹配 |
| `scripts/serve_crossing_vlm.py` | GPU 准入检查及本地 vLLM 服务启动 |
| `scripts/run_crossing_development.py` | 8 条开发轨迹的运行控制器 |
| `scripts/replay_crossing_checkpoint.py` | 数据准备、因果回放、评分 |
| `scripts/build_crossing_review.py` | 完整因果审计及供模板读取的源报告 |
| `scripts/export_crossing_iteration.py` | 每轮默认交付入口：按双进度条模板自动导出独立HTML，见[规范](docs/CROSSING_VISUALIZATION_TEMPLATE.md) |
| `core/crossing_checkpoint_review.html` | 上述 HTML 模板 |
| `docs/CROSSING_CHECKPOINT.md` | 历史版本、修复与迭代记录 |

现有服务环境为 vLLM **0.19.1**、PyTorch **2.10.0**、Transformers **5.8.1**、Tokenizers **0.22.2**。使用权重自带的原生 FP8 量化配置，计算 dtype 为 BF16，CPU offload 为 0。不要把早期 Transformers 反量化 BF16 的前缀结果与本轮合并。

**在当前服务器运行不需要重新下载权重或安装环境。** 模型服务离线加载，回放通过服务器本机 HTTP API 请求。Git 不包含权重、虚拟环境或实验输出；仅克隆源码到另一台机器不能直接获得这些资源。

本轮产物位于：

```text
outputs/crossing_checkpoint/seed2_v1_20261103/
├── protocol.json                       # 固定样本、定义与评测口径
├── inputs.json                         # 原始录像、观测和动作索引
├── evaluation/
│   ├── maps.json                       # 固定地图 crossing，仅评测/展示使用
│   └── cases.json                      # 记录位置、参考路径等评测信息
├── service_qwen27_tp2/
│   ├── service.json                    # 服务实际端口、进程、模型和配置
│   └── server.log
├── iteration_status.json               # 最近控制器状态；历史 PID 不代表进程仍存活
├── runs/qwen27_fp8_dev_v1_nothinking/
│   ├── manifest.json                   # 冻结配置及输入/代码哈希
│   ├── source/                         # 本轮冻结的核心和回放源码
│   ├── cases/<episode>/                # predictions.jsonl、status.json、result.json
│   ├── scores.json
│   ├── diagnostics.json
│   └── replay.log
└── reports/qwen27_fp8_dev_v1_nothinking_review/
    ├── crossing_dev8_review.html        # 推荐查看的最新对照报告
    ├── README.md                       # 本文的分发副本
    ├── verification.json               # 输入、状态机和评分核验
    └── ui_verification.json             # Node DOM 模拟交互检查
```

回放还依赖 `inputs.json` 引用的原始录像，来源为 `outputs/reproduction/streamvln_scene250_5seeds_20261101_v2/visualization/`；地图来源为 `outputs/checkpoint_review/seed2_25_20261103/`。不要只复制一个 run 目录就认为可以重新推理。**已生成的单文件 HTML 则可以独立复制到 Windows 打开。**

## 4. 如何查看当前 HTML

打开 `reports/qwen27_fp8_dev_v1_nothinking_review/crossing_dev8_review.html`：

| 图上标记 | 含义 |
| --- | --- |
| 蓝色圆点/圆圈“原 Cxx” | 先前地图标定、本轨迹经过的 crossing |
| 灰色虚线“原 Cxx” | 地图标定、但本轨迹没有进入其 0.7m 邻域的 crossing；不计漏检 |
| 红色菱形“现 Pxxx” | 本版已确认的存档，坐标取确认时记录的机器人位置 |
| 绿色线 | 原始实际行走轨迹 |

**P 是确认存档时的机器人位置，不是模型预测的路口中心坐标。** 原 C 位于路口中心，未必恰好落在行走线上；不要把“没有经过的 C 点”理解为模型漏检。

默认“全程对照”显示完整轨迹和全部 P，便于直接比较两套标注。取消它才按时间逐步显示存档。可以分别隐藏 C/P、只显示经过的 C、点击两侧编号跳转。右侧支持当前 RGB、历史输入、模型回答、逐步播放和复核备注；备注可导出 JSON。备注存储在当前浏览器，换电脑前请导出。

报告约 21.2 MiB，内嵌 573 个观测及地图，打开不需要模型服务或网络。生成器已核验因果输入、最终存档及评分；交互检查使用 Node DOM 模拟器，未进行真实浏览器渲染自动测试。

## 5. 启动前：公共变量与现有服务检查

以下为 Linux Bash 命令。**每个新终端先执行这一段**；`CROSSING_TAG` 默认指向已完成版本，后续真正重跑时会改成新标签。

```bash
cd /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn
export CROSSING_OUTPUT="$PWD/outputs/crossing_checkpoint/seed2_v1_20261103"
export CROSSING_SERVICE="$CROSSING_OUTPUT/service_qwen27_tp2"
export CROSSING_TAG="qwen27_fp8_dev_v1_nothinking"
```

先检查已存在的服务，成功即可复用，避免重复加载模型：

```bash
python3 -B - <<'PY'
import json, os, urllib.request
from pathlib import Path
info = json.loads((Path(os.environ['CROSSING_SERVICE']) / 'service.json').read_text())
assert info['phase'] == 'ready', info['phase']
assert info['base_url'].startswith('http://127.0.0.1:')
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(info['base_url'] + '/models', timeout=10) as response:
    models = json.load(response)
assert info['served_model'] == 'crossing-qwen27b'
assert any(m['id'] == info['served_model'] for m in models['data'])
print('READY', info['base_url'], info['served_model'], 'GPUs:', info['gpus'])
PY
```

服务使用自动选择的本机空闲端口，**以 `service.json` 的 `base_url` 为准，不固定写死端口**。`service.json` 存在或显示 `ready` 本身不能代替上述实际连通检查。检查失败时先看日志和进程，确认旧服务已退出后再启动。

## 6. 如何启动本地 27B 模型

本版验证过的配置使用两张约 48 GiB 的卡。启动器要求每张卡无计算进程、已用显存 <1024 MiB、可用显存 ≥46000 MiB、利用率 ≤10%，间隔 5 秒检查两次；不满足就拒绝启动。GPU 锁只协调本项目，不能代替查看共享服务器占用。

在一个独立的 tmux 窗口执行第 5 节公共变量，然后查看全部卡及计算进程：

```bash
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory,process_name --format=csv
```

确认两张空闲卡后执行下列命令。它要求手动输入卡号，并使用新的服务目录，保留旧启动记录：

```bash
read -r -p "输入刚确认空闲的两张 GPU 编号（空格分隔）: " CROSSING_GPU_A CROSSING_GPU_B
export CROSSING_SERVICE="$CROSSING_OUTPUT/service_qwen27_tp2_$(date -u +%Y%m%dT%H%M%SZ)"
printf '本次服务目录：%s\n' "$CROSSING_SERVICE"

python3 -B scripts/serve_crossing_vlm.py \
  --output "$CROSSING_SERVICE" \
  --gpus "$CROSSING_GPU_A" "$CROSSING_GPU_B" \
  --model "/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/Qwen3.8-27B-FP8" \
  --python "$PWD/.runtime/crossing_vllm27/bin/python" \
  --served-model crossing-qwen27b \
  --reasoning-parser qwen3 \
  --max-num-seqs 4 \
  --max-model-len 32768
```

必须显式传入以上 `--model`、`--python`、`--served-model`：通用启动器的默认值仍对应早期 32B。FP8 配置从本地权重读取，此处不另传 `--quantization`。

启动后保持该 tmux 窗口运行。另开窗口执行第 5 节公共变量，再把 `CROSSING_SERVICE` 改为刚打印的完整目录，重复服务检查，直到得到 `READY`。可通过 `tail -n 80 "$CROSSING_SERVICE/server.log"` 查看加载日志。初始化完成前不要启动回放。

`--reasoning-parser qwen3` 负责解析响应格式；**关闭思考是在每次 API 请求中设置 `chat_template_kwargs={"enable_thinking": false}`**，不是删除这个服务参数。第 7 节控制器会显式设置关闭思考。

## 7. 如何重新运行 8 条开发轨迹

本节会真正请求模型。目前处于人工复核阶段；查看报告、生成 HTML 都不需要执行本节。现有 `protocol.json` 和 `inputs.json` 已准备好，复现本版不需要重新运行 `prepare`。

在另一个 tmux 窗口执行第 5 节公共变量，确认 `CROSSING_SERVICE` 指向可用服务；如果刚重启服务，务必设置为第 6 节新生成的目录。随后用**新标签**开始独立重跑：

```bash
export CROSSING_TAG="qwen27_fp8_dev_v1_nothinking_repro_$(date -u +%Y%m%dT%H%M%SZ)"
printf '本次运行标签：%s\n' "$CROSSING_TAG"

python3 -B scripts/run_crossing_development.py \
  --output "$CROSSING_OUTPUT" \
  --tag "$CROSSING_TAG" \
  --service "$CROSSING_SERVICE" \
  --workers 4 \
  --no-thinking \
  --max-tokens 8192
```

控制器复用模型服务，不另占 GPU，不运行导航仿真；支持 1–4 个 worker。`8192` 是输出上限，不要求生成满。请求温度为 0，采样种子随轨迹和观测固定。每个新标签冻结源码、配置和输入哈希；硬件及后端数值差异仍可能影响模型回答。

每次控制器启动会更新顶层 `iteration_status.json`，旧 run 目录保留。控制器运行中定期生成已处理前缀的预览；结束后生成评分、诊断和旧式报告。**第 4 节的 C/P 单文件对照 HTML 需另执行第 8 节。** 控制器不会自动改进方法，也不会自行运行保留的 40 条验证集。

若仅想接着同一未完成 run 运行，保留原 `CROSSING_TAG` 和完全相同配置，重新执行控制器命令。已缓存观测会经过请求哈希核验并重建状态；已完成轨迹会跳过。改变提示词、源码、模型或配置必须使用新标签，不能删除 manifest 来绕过冻结检查。因此使用本文已完成的原标签并不会从头重新推理。

## 8. 如何只生成 HTML，不重新推理

在新终端执行第 5 节公共变量，即默认处理已完成的本版；若处理另一个完成的 run，只修改 `CROSSING_TAG`。

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/analyze_crossing_checkpoint.py \
  --output "$CROSSING_OUTPUT" --tag "$CROSSING_TAG"

benchmarks/vlnverse/.venv/bin/python -B scripts/build_crossing_review.py \
  --output "$CROSSING_OUTPUT" --tag "$CROSSING_TAG"
```

输出为 `$CROSSING_OUTPUT/reports/${CROSSING_TAG}_review/crossing_dev8_review.html` 和 `verification.json`。这些命令使用 CPU 读取记录、重建存档、核验评分并生成展示，不调用 27B，不需要服务在线；会更新该标签对应的报告文件。

若已有 `diagnostics.json`，可以省略第一条命令。生成器要求完整完成，不能将未处理片段算作漏检。未完成时使用：

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/preview_crossing_checkpoint.py \
  --output "$CROSSING_OUTPUT" --tag "$CROSSING_TAG"
```

前缀预览位于 `reports/${CROSSING_TAG}_preview/index.html`，与完整 C/P 对照版用途不同。当前原版 8 条报告还可执行现有交互检查：

```bash
/root/.nvm/versions/node/v20.20.2/bin/node scripts/check_crossing_review.cjs \
  "$CROSSING_OUTPUT/reports/qwen27_fp8_dev_v1_nothinking_review/crossing_dev8_review.html"
```

此检查包含本版固定的 573 个观测、7 个 P 等断言，只适用于本版报告；不能直接拿来判断未来不同预测数量的版本是否正确。

## 9. 查看进度、停止与常见问题

运行期间在另一个终端设置正确变量后查看：

```bash
python3 -m json.tool "$CROSSING_OUTPUT/iteration_status.json"
tail -n 60 "$CROSSING_OUTPUT/runs/$CROSSING_TAG/replay.log"
tail -n 60 "$CROSSING_SERVICE/server.log"
```

重点看 `processed/expected`、`completed_cases/expected_cases`、`replay_exit_code` 和 `postprocessing`。只有 `scores.json` 的 `summary.complete=true` 才代表该标签全部轨迹完成。顶层状态只代表最近一次控制器，可另外查看 `runs/<tag>/status.json`、`cases/<episode>/status.json`。当前原版顶层状态为 `awaiting_user_html_review`，已完成评测，不是在等待 GPU 或继续推理。

停止回放时，在**该回放控制器的 tmux 窗口**按 `Ctrl+C`，控制器会终止自己启动的回放进程组，保留已有结果；模型服务仍在运行。停止模型时，在**该模型启动器的 tmux 窗口**按 `Ctrl+C`，启动器会向自己的模型进程组发送终止信号。先停止调用它的回放，再停模型。若只是离开 tmux 并保持运行，使用 `Ctrl+B` 后按 `D`。

不要使用面向所有 Python/vLLM 的 `pkill`，也不要按文档中的历史 PID 直接杀进程。服务就绪但没有回放时仍会保留显存；是否空闲须结合进程及实际请求判断。模型的主动停止可能在 `service.json` 中记为 `failed` 或非零退出码，应结合停止时间和日志区分人为停止与异常。

| 现象 | 处理 |
| --- | --- |
| `GPU admission rejected` / GPU 锁冲突 | 重新检查卡和本项目服务；已有可用服务就复用，否则等待空闲资源，不终止他人任务 |
| `Expected an existing local model service` / 连接拒绝 | 核对 `CROSSING_SERVICE`、实际 `base_url`、服务日志和进程；不要沿用旧端口 |
| `Run tag is frozen` | 配置或源码已变化；新建标签，保留原始结果 |
| `Another replay ... still running` / 控制器锁冲突 | 同一 campaign 不重复启动控制器；核实原运行是否仍在执行 |
| 提示证据帧越界、JSON 无效或输出截断 | 查看该 case 的响应与错误记录；不能跳过校验或把未完成轨迹算成完整结果 |
| HTML 提示输入、地图或源码哈希改变 | 恢复对应冻结输入并排查路径；不要修改原地图来提高匹配分数 |
| 没有新预测但进程已经退出 | 检查 run 状态及 `postprocess.log`，不要仅凭旧 PID 或显存占用判断进度 |

保留的 40 条验证集需在开发方案选定、冻结并记录真实选择依据后运行；底层入口会检查 `selection_decision.json`。本版尚未达到门槛，本文不提供绕过该检查的启动方式。后续迭代应保留旧结果，用新标签比较，而不是覆盖本版。
