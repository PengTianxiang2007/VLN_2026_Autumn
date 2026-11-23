# v006 回退节点的 DeepSeek 第二次调用

运行协议于启动前登记。按 C42、C46、C49、C50、C07、C05、C09、C10、C20、C21 排列，使用同例 DeepSeek v1 的冻结结果。第二次调用使用 deepseek-flash、temperature=0、top_p=1、关闭 thinking，接口不指定 seed，历史导航 seed=2。每例发三张节点原始 PNG，只发送该节点的 Completed、Current 和完整英文指令，以及上次识别的入口 ID、方向、入口描述与已走匹配。每例独立调用一次，十例并行，不做语义重试。空结果与原答照录。只生成指令。

启动命令：

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_recovery_branch_instruction.py --output outputs/agent_recovery/branch_instruction_v001/run_20261121_01
```

逐例输入、请求、响应和结果写入对应 outputs 目录。manifest 登记源码快照、Git HEAD 与输入来源。

2026-11-21 11:55:12 UTC 完成。运行时 Git HEAD 为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，工作区有未提交变更，实际运行源码保存在输出的 `source/`。十例各返回一份有效回答，选中 ID 均在本例 DeepSeek 第一次调用清单内，且与此前 ID 不同。每条指令为 8–12 个英文单词（空格计数）。未执行恢复导航或人工正确率评分。

| 案例 | 回退节点 | 先前 → 本次 | 模型英文原答中的局部指令 |
|---|---|---|---|
| C42 | S02 · F27 | B1 → B2 | Turn right and walk down the white hallway. |
| C46 | S01 · F6 | B3 → B2 | Turn left and walk down the white hallway. |
| C49 | S04 · F22 | B1 → B3 | Turn right and enter the doorway with the pink curtain. |
| C50 | S04 · F15 | B1 → B3 | Turn right and walk toward the orange artwork. |
| C07 | S03 · F41 | B1 → B2 | Turn slightly right and walk forward between the white cabinets. |
| C05 | S06 · F26 | B1 → B3 | Turn right toward the living room with the grey sofa. |
| C09 | S02 · F5 | B1 → B3 | Turn right toward the living room with the TV and sofa. |
| C10 | S01 · F0 | B3 → B2 | Turn left toward the open white doorway and walk through it. |
| C20 | S03 · F19 | B1 → B2 | Turn left toward the room with the desk and hexagonal shelves. |
| C21 | S04 · F21 | B1 → B2 | Turn left and walk toward the narrow hallway beside the white cabinets. |

C07、C09、C21 的局部指令与 v006 的 Current 对左右方向的用词相反。尤其是 C21，第一阶段仅列出正前和左前两条，正前又是上次走过的支路，第二阶段清单中只剩左前。这里记录的是两份模型输出之间的差异，尚无轨迹执行结果。逐条展示译文与原答分开保存。

## 双语回放与发布

[在线查看](http://134.175.18.101/vln/recovery_instruction_v001_deepseek10_web_20261121_01/index.html) · [下载离线包](http://134.175.18.101/vln/recovery_instruction_v001_deepseek10_web_20261121_01/recovery_instruction_v001_deepseek_10_offline.zip)（11,619,560 字节）。源 HTML 为 `outputs/visualization_publishing/recovery_instruction_v001_deepseek10_web_20261121_01/index.html`，SHA256 为 `829f0737b0732bcb485da1d907dc15abb6e6be6e4b87871a582b51672509d960`。逐例展示两次选择、指令原答／译文、三张实际输入观测、原任务与 A 处进度，继承有效节点地图和 RGB 双进度条。第一次调用的 Qwen 面板仅供对照，第二次实际使用 DeepSeek 的支路编号与入口描述。

发布于 2026-11-21T12:00:37.889858+00:00。标准流程记录 `outputs/visualization_publishing/publish_20261121_120027_510619/publication.json`，723 个文件远端 SHA256 通过，入口公网 HEAD HTTP 200。本地浏览器核对十份原答与原始结果一致，C50 和 C21 抽查三图放大、语言及同帧联动，无页面脚本错误。

## 当前观测布局更新

[新版在线回放](http://134.175.18.101/vln/recovery_instruction_v001_deepseek10_web_20261121_02/index.html) · [新版离线包](http://134.175.18.101/vln/recovery_instruction_v001_deepseek10_web_20261121_02/recovery_instruction_v001_deepseek_10_offline.zip)。当前观测的画面进度条下方直接展示俯视地图及地图进度条。标题旁的“回到回退点”按钮会暂停播放，并将 RGB 和地图同步定位到当前案例的回退帧。三张模型输入图仍可在第二次调用面板中放大查看。

源文件 `outputs/visualization_publishing/recovery_instruction_v001_deepseek10_web_20261121_02/index.html`，SHA256 `e46d011ee364f03bb3a1572ce6d8fbb1a1d2482d889c392058d5f78c739e9cee`。2026-11-21T12:09:32.509648+00:00 发布，记录 `outputs/visualization_publishing/publish_20261121_120923_700782/publication.json`。全部资源远端 SHA256 通过，公网入口 HTTP 200。本地浏览器检查中文 C50 回到 F15、英文 C07 回到 F41，并确认地图位于当前观测下方。本次复用十例已有模型结果。
