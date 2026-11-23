# 第一次调用 v001 · v006 十例

2026-11-21 用户明确授权执行并导出可视化；仅第一次调用，无恢复指令生成、无导航。

## 协议与输入

依次 C42、C46、C49、C50、C07、C05、C09、C10、C20、C21。使用 v006 首次报警指定的去重后回退节点，非 v6.1。
每例固定节点左 +70°、正前 0°、右 −70° 补采图，以及 C+2、+5、+8、+10 原生前视，共七图；70 张文件已具备。
只发送图像、图像 ID、时间与视角标签、冻结中文 Prompt 和输出 Schema，不发送原任务指令、地图、参考路线或位姿。
支路限定为当前决策位置的直接选择；后续分叉不得拆成当前支路。此前尝试需纠正来自上游，模型只匹配此前实际走的支路，允许 uncertain。

| 案例 | v006 节点 | C | 后续四帧 |
|---|---|---:|---|
| C42 | S02 | 27 | 29,32,35,37 |
| C46 | S01 | 6 | 8,11,14,16 |
| C49 | S04 | 22 | 24,27,30,32 |
| C50 | S04 | 15 | 17,20,23,25 |
| C07 | S03 | 41 | 43,46,49,51 |
| C05 | S06 | 26 | 28,31,34,36 |
| C09 | S02 | 5 | 7,10,13,15 |
| C10 | S01 | 0 | 2,5,8,10 |
| C20 | S03 | 19 | 21,24,27,29 |
| C21 | S04 | 21 | 23,26,29,31 |

## 模型与命令

复用用户要求保留的 GPU3 `route53-qwen27b`，`http://127.0.0.1:56923/v1`。
权重 Qwen3.8-27B-FP8，单卡；temperature=0、top_p=1、top_k=-1、seed=2、max_tokens=4096、enable_thinking=false，JSON object 输出。
每例一次请求，顺序执行，不做语义重试；保存格式不合法或接口错误。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_recovery_branch_review.py \
  --output outputs/agent_recovery/branch_review_v001/run_20261121_01 --execute
```

输出目录 `outputs/agent_recovery/branch_review_v001/run_20261121_01/`：manifest 含实际 Git HEAD、源码快照哈希、服务记录、样本与输入 PNG 哈希；保存工作区差异，每例 input/request/response/result 和未改写原答。
运行完成继续保留模型待用。状态以输出 `status.json` 为准。

## 状态与可视化

09:16:07–09:20:25 UTC 完成十次调用，10/10 格式有效，24 条支路，10 次 identified、0 次 uncertain。worker PID 1032832 已完成任务。首次启动在 Python 语法阶段退出，未发送请求；修复并检查后启动上述实际运行，详见 launch.json。

| 案例 | 模型支路数 | 此前所走支路（模型回答） |
|---|---:|---|
| C42 | 2 | B1 正前 |
| C46 | 3 | B3 右侧 |
| C49 | 3 | B1 正前 |
| C50 | 1 | B1 正前 |
| C07 | 2 | B2 左前 |
| C05 | 2 | B1 正前 |
| C09 | 3 | B3 左侧 |
| C10 | 3 | B2 左侧 |
| C20 | 3 | B1 正前 |
| C21 | 2 | B2 右侧 |

格式有效不代表语义正确，尚无人工真值评分。C09 原答将明确描述为“门扇关闭”的门列为可选支路，并以靠近、面对该门判断已选支路，存在 Prompt 遵循问题；展示与译文均不修正模型原答。C50 仅列出一条支路，未强行补足。

可视化沿用 v006 多视角页面的地图、RGB 与双进度条，突出当前支路清单、此前实际所走支路、七图证据；默认中文并提供 English 切换。已于 2026-11-21T09:29:30.577726+00:00 发布。


## 可视化交付

- [打开在线页面](http://134.175.18.101/vln/recovery_branch_review_v001_ten_web_20261121_02/index.html)；[下载完整离线 ZIP](http://134.175.18.101/vln/recovery_branch_review_v001_ten_web_20261121_02/recovery_branch_review_v001_ten_offline.zip)（11,650,500 字节）。
- 本地完整页面与资源：`outputs/visualization_publishing/recovery_branch_review_v001_ten_web_20261121_02/`；源模板为 `outputs/visualization_publishing/v006_node_multiview70_web_20261121_01/index.html`。
- 页面显著展示当前支路清单与此前所走支路；非选中支路只标为模型列出的其他支路，不宣称它们是正确路线。支持七图放大定位、地图/RGB 双进度条、中英文、逐字原答与实际 Prompt。原任务指令只在上下文中展示，明确未输入本次调用。
- 第一次页面检查覆盖十例、70 张图、完整中英文输出、原答一致性、支路高亮与双进度条。发现旧字体缺字后生成新导出，复用已通过的交互检查，仅复核字形覆盖与首例双语；818 个汉字均覆盖，零 JS 错误。
- 发布记录：`outputs/visualization_publishing/publish_20261121_092921_326287/publication.json`；723 个文件远端 SHA256 校验通过，入口公网 HEAD HTTP 200。没有执行公网全量下载或在线浏览器回放。
- HTML SHA256：`ad0cb8f22ffd8b1d9013215c6312054d29a80f61c5d692d772cc56b8b8a28ebe`。模型结果未因翻译或显示修复而改变。

导出命令：

```bash
backbone/streamvln/.venv/bin/python -B scripts/export_recovery_branch_review.py \
  --run outputs/agent_recovery/branch_review_v001/run_20261121_01 \
  --translations experiments/agent_recovery/branch_review_v001/run_20261121_01/display_translations_en.json \
  --output outputs/visualization_publishing/recovery_branch_review_v001_ten_web_20261121_02
```

发布使用 `docs/VISUALIZATION_PUBLISHING.md` 的已有在线目录标准流程，传入 online_manifest.json 的全部资源。
